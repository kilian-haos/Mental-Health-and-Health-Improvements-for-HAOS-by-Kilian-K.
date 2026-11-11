"""Entity base classes and platform setup helper (entities follow modules dynamically)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import MANUFACTURER, VERSION, signal_entities, signal_hub, signal_person
from .entity_defs import Def, hub_defs, person_defs

# Ab HA 2026.8 wird das übergeordnete Gerät per Geräte-ID angegeben (via_device_id)
_VIA_BY_ID = "via_device_id" in getattr(DeviceInfo, "__optional_keys__", ())


def via_kwargs(runtime: Any, identifier: tuple[str, str]) -> dict[str, Any]:
    if not _VIA_BY_ID:
        return {"via_device": identifier}
    dev = dr.async_get(runtime.hass).async_get_device(identifiers={identifier})
    return {"via_device_id": dev.id} if dev else {}


class MHEntity(Entity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, runtime: Any, d: Def) -> None:
        self.runtime = runtime
        self.d = d
        self._attr_translation_key = d.key
        if d.icon:
            self._attr_icon = d.icon


class HubEntity(MHEntity):
    def __init__(self, runtime: Any, d: Def) -> None:
        super().__init__(runtime, d)
        self._attr_unique_id = f"{runtime.entry.entry_id}_hub_{d.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={runtime.hub_identifier}, name=runtime.t("hub_name"), manufacturer=MANUFACTURER,
            model=runtime.t("model_hub"), sw_version=VERSION, entry_type=dr.DeviceEntryType.SERVICE)

    @property
    def value(self) -> Any:
        return self.runtime.hub_values.get(self.d.key)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(self.hass, signal_hub(self.runtime.entry.entry_id), self._update))

    @callback
    def _update(self) -> None:
        self.async_write_ha_state()


class PersonEntity(MHEntity):
    def __init__(self, runtime: Any, d: Def, pid: str) -> None:
        super().__init__(runtime, d)
        self.pid = pid
        p = runtime.persons[pid]
        self._attr_unique_id = f"{runtime.entry.entry_id}_{pid}_{d.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={runtime.person_identifier(pid)}, name=runtime.t("device_person", name=p.name),
            manufacturer=MANUFACTURER, model=runtime.t("model_person"), sw_version=VERSION,
            entry_type=dr.DeviceEntryType.SERVICE, **via_kwargs(runtime, runtime.hub_identifier))

    @property
    def person(self) -> Any:
        return self.runtime.persons.get(self.pid)

    @property
    def available(self) -> bool:
        return self.pid in self.runtime.persons

    @property
    def value(self) -> Any:
        return (self.runtime.values.get(self.pid) or {}).get(self.d.key)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(async_dispatcher_connect(
            self.hass, signal_person(self.runtime.entry.entry_id, self.pid), self._update))

    @callback
    def _update(self) -> None:
        self.async_write_ha_state()


def setup_platform(runtime: Any, platform: str, add: Callable[[list], None],
                   person_cls: Callable[[Any, Def, str], Entity] | None,
                   hub_cls: Callable[[Any, Def], Entity] | None) -> Callable[[], None]:
    """Add hub + person entities now and whenever persons/modules change."""
    known: set[str] = set()

    @callback
    def sync() -> None:
        new: list[Entity] = []
        if hub_cls is not None:
            for d in hub_defs(platform):
                uid = f"hub_{d.key}"
                if uid not in known:
                    known.add(uid)
                    new.append(hub_cls(runtime, d))
        if person_cls is not None:
            for pid, p in runtime.persons.items():
                for d in person_defs(p, platform):
                    uid = f"{pid}_{d.key}"
                    if uid not in known:
                        known.add(uid)
                        new.append(person_cls(runtime, d, pid))
        valid = {f"hub_{d.key}" for d in hub_defs(platform)} | {
            f"{pid}_{d.key}" for pid, p in runtime.persons.items() for d in person_defs(p, platform)}
        known.intersection_update(valid)
        if new:
            add(new)
        runtime.cleanup_registry()

    sync()
    return async_dispatcher_connect(runtime.hass, signal_entities(runtime.entry.entry_id), sync)
