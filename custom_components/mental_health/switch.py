"""Switches: pause per person (holiday, illness), LLM beta on the hub."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HubEntity, PersonEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: Any, async_add_entities: AddEntitiesCallback) -> None:
    rt = entry.runtime_data
    entry.async_on_unload(setup_platform(rt, "switch", async_add_entities, PauseSwitch, LlmSwitch))


class PauseSwitch(PersonEntity, SwitchEntity):
    @property
    def is_on(self) -> bool:
        return bool((self.runtime.values.get(self.pid) or {}).get("paused"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.runtime.async_set_pause(self.pid, True, None)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.runtime.async_set_pause(self.pid, False, None)


class LlmSwitch(HubEntity, SwitchEntity):
    @property
    def is_on(self) -> bool:
        return bool(self.runtime.settings["llm"].get("enabled"))

    @property
    def available(self) -> bool:
        # Einschalten nur über den Admin-Bereich (Datenschutz-Warnung + Zustimmung)
        return bool(self.runtime.settings["llm"].get("accepted"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        if self.runtime.settings["llm"].get("accepted"):
            self.runtime.settings["llm"]["enabled"] = True
            self.runtime.save_config()
            self.runtime.recompute_hub()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.runtime.settings["llm"]["enabled"] = False
        self.runtime.save_config()
        self.runtime.recompute_hub()
