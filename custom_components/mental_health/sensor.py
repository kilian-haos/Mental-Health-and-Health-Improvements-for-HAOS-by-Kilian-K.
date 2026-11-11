"""Sensors (person + family hub). No texts or contents in states or attributes."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .entity import HubEntity, PersonEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: Any, async_add_entities: AddEntitiesCallback) -> None:
    rt = entry.runtime_data
    entry.async_on_unload(setup_platform(rt, "sensor", async_add_entities, PersonSensor, HubSensor))


class _Base(SensorEntity):
    def _apply_kind(self) -> None:
        k = self.d.kind
        if k == "measurement":
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif k == "timestamp":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif k == "date":
            self._attr_device_class = SensorDeviceClass.DATE
        elif k == "enum":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = list(self.d.options)
        elif k == "duration_h":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.HOURS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif k == "percent":
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif k == "kg":
            self._attr_device_class = SensorDeviceClass.WEIGHT
            self._attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif k == "days":
            self._attr_native_unit_of_measurement = UnitOfTime.DAYS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif k == "years":
            self._attr_native_unit_of_measurement = "a"
        elif k == "count":
            self._attr_state_class = SensorStateClass.MEASUREMENT

    def _convert(self, v: Any) -> Any:
        if v is None:
            return None
        if self.d.kind == "timestamp":
            if isinstance(v, datetime):
                return v
            dt = dt_util.parse_datetime(str(v))
            return dt
        if self.d.kind == "date":
            if isinstance(v, date):
                return v
            try:
                return date.fromisoformat(str(v)[:10])
            except ValueError:
                return None
        return v


class PersonSensor(_Base, PersonEntity):
    def __init__(self, runtime: Any, d: Any, pid: str) -> None:
        PersonEntity.__init__(self, runtime, d, pid)
        self._apply_kind()
        if d.key == "mood_forecast":
            self._unrecorded_attributes = frozenset({"confidence"})

    @property
    def native_value(self) -> Any:
        return self._convert(self.value)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.d.key == "mood_forecast":
            return {"confidence": (self.runtime.values.get(self.pid) or {}).get("forecast_confidence")}
        return None


class HubSensor(_Base, HubEntity):
    _unrecorded_attributes = frozenset({"names"})

    def __init__(self, runtime: Any, d: Any) -> None:
        HubEntity.__init__(self, runtime, d)
        self._apply_kind()

    @property
    def native_value(self) -> Any:
        return self._convert(self.value)

    @property
    def extra_state_attributes(self) -> dict | None:
        if self.d.key == "birthdays_today":
            return {"names": self.runtime.hub_values.get("birthdays_today_names") or []}
        if self.d.key == "next_birthday":
            return {"names": self.runtime.hub_values.get("next_birthday_names") or []}
        if self.d.key == "family_mood":
            return {"weather": self.runtime.hub_values.get("weather")}
        return None
