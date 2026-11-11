"""Home Assistant backup platform: flush stores before a backup and pause writes meanwhile."""
from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN


def _runtimes(hass: HomeAssistant) -> list:
    out = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        rt = getattr(entry, "runtime_data", None)
        if rt is not None and hasattr(rt, "async_pause_writes"):
            out.append(rt)
    return out


async def async_pre_backup(hass: HomeAssistant) -> None:
    for rt in _runtimes(hass):
        await rt.async_pause_writes()


async def async_post_backup(hass: HomeAssistant) -> None:
    for rt in _runtimes(hass):
        rt.resume_writes()
