"""Mental Health and Health Improvements for HAOS by Kilian K.

A personal mood, journal, sleep, weight, cycle and training companion for every person in the
household – with a family view, its own small local learning model and an optional LLM beta.
Everything local, everything through the UI. English by default, German if Home Assistant
runs in German.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_CORE_CONFIG_UPDATE
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from . import http as mh_http
from . import services, websocket
from .config_flow import CONF_PANEL, CONF_PANEL_TITLE
from .const import (
    CARD_FILE, CARD_URL, DOMAIN, FRONTEND_DIR, PANEL_COMPONENT, PANEL_FILE, PANEL_ICON, PANEL_URL, PANEL_URL_PATH,
    PLATFORMS, URL_BASE,
)
from .i18n import system_lang, tr
from .runtime import MHRuntime

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type MHConfigEntry = ConfigEntry[MHRuntime]

DATA_URLS = f"{DOMAIN}_urls"


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once: serve card + panel, register websocket commands, HTTP views and services."""
    base = Path(__file__).parent / FRONTEND_DIR
    card_hash = await hass.async_add_executor_job(_file_hash, base / CARD_FILE)
    panel_hash = await hass.async_add_executor_job(_file_hash, base / PANEL_FILE)
    if hass.http is not None:
        await hass.http.async_register_static_paths([StaticPathConfig(URL_BASE, str(base), False)])
    # Karten in allen Dashboards verfügbar (keine manuelle Ressource nötig)
    card_url = f"{CARD_URL}?v={card_hash}&p={panel_hash}"
    frontend.add_extra_js_url(hass, card_url)
    hass.data[DATA_URLS] = {"card": card_url, "panel": f"{PANEL_URL}?v={panel_hash}&c={card_hash}"}
    websocket.async_register(hass)
    mh_http.register(hass)
    services.async_register(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MHConfigEntry) -> bool:
    runtime = MHRuntime(hass, entry)
    await runtime.async_setup()
    entry.runtime_data = runtime
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    @callback
    def _on_core_config(_event: Event) -> None:
        # Systemsprache geändert -> Gerätemodelle, Texte, Panel-Titel neu setzen
        if system_lang(hass) != runtime.lang:
            hass.config_entries.async_schedule_reload(entry.entry_id)

    entry.async_on_unload(hass.bus.async_listen(EVENT_CORE_CONFIG_UPDATE, _on_core_config))
    if entry.options.get(CONF_PANEL, True):
        await _async_register_panel(hass, entry)
    runtime.check_repairs()
    hass.async_create_task(_cold_start_all(runtime))
    return True


async def _cold_start_all(runtime: MHRuntime) -> None:
    for pid, p in list(runtime.persons.items()):
        if p.sources and not any(s.head for s in p.series.values()):
            await runtime.async_cold_start(pid)


async def _async_register_panel(hass: HomeAssistant, entry: ConfigEntry) -> None:
    frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    urls = hass.data.get(DATA_URLS) or {}
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=PANEL_COMPONENT,
        sidebar_title=entry.options.get(CONF_PANEL_TITLE) or tr(system_lang(hass), "panel_title"),
        sidebar_icon=PANEL_ICON,
        module_url=urls.get("panel", PANEL_URL),
        require_admin=False,
        config={"entry_id": entry.entry_id},
    )


async def async_unload_entry(hass: HomeAssistant, entry: MHConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_unload()
        frontend.async_remove_panel(hass, PANEL_URL_PATH, warn_if_unknown=False)
    return unloaded


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Integration removed: delete stores. Own backup files in <config>/mental_health/backups stay."""
    from homeassistant.helpers.storage import Store

    from .const import (
        CONFIG_STORE_VERSION, KEY_STORE_VERSION, MODEL_STORE_VERSION, PERSON_STORE_VERSION, STORE_CONFIG,
        STORE_KEYS, STORE_MODEL, STORE_PERSON,
    )
    cfg = await Store(hass, CONFIG_STORE_VERSION, STORE_CONFIG).async_load() or {}
    for pid in (cfg.get("persons") or {}):
        await Store(hass, PERSON_STORE_VERSION, STORE_PERSON.format(pid=pid)).async_remove()
        await Store(hass, MODEL_STORE_VERSION, STORE_MODEL.format(pid=pid)).async_remove()
    await Store(hass, CONFIG_STORE_VERSION, STORE_CONFIG).async_remove()
    await Store(hass, KEY_STORE_VERSION, STORE_KEYS).async_remove()
