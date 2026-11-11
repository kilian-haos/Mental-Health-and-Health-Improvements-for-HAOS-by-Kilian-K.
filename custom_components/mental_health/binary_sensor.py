"""Binary sensors per person."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import PersonEntity, setup_platform

_SOURCE = {
    "sleeping": ("sleep_state", lambda v: v in ("asleep", "nap")),
    "in_bed": ("sleep_state", lambda v: v in ("in_bed", "asleep", "nap")),
    "weight_due": ("weight_due", bool),
    "training_recommended": ("training_recommended", bool),
    "cycle_active": ("cycle_active", bool),
    "morning_open": ("checkin_morning_open", bool),
    "evening_open": ("checkin_evening_open", bool),
    "birthday_today": ("birthday_today", bool),
}


async def async_setup_entry(hass: HomeAssistant, entry: Any, async_add_entities: AddEntitiesCallback) -> None:
    rt = entry.runtime_data
    entry.async_on_unload(setup_platform(rt, "binary_sensor", async_add_entities, PersonBinary, None))


class PersonBinary(PersonEntity, BinarySensorEntity):
    def __init__(self, runtime: Any, d: Any, pid: str) -> None:
        super().__init__(runtime, d, pid)
        if d.key in ("in_bed", "sleeping"):
            self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY if d.key == "in_bed" else None

    @property
    def is_on(self) -> bool | None:
        key, fn = _SOURCE[self.d.key]
        v = (self.runtime.values.get(self.pid) or {}).get(key)
        if v is None:
            return None if key in ("sleep_state", "cycle_active") else False
        return bool(fn(v))
