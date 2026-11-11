"""Select: computing load level 1-3 (hub)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HubEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: Any, async_add_entities: AddEntitiesCallback) -> None:
    rt = entry.runtime_data
    entry.async_on_unload(setup_platform(rt, "select", async_add_entities, None, LoadSelect))


class LoadSelect(HubEntity, SelectEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = ["1", "2", "3"]

    @property
    def current_option(self) -> str:
        return str(self.runtime.settings.get("load_level", 2))

    async def async_select_option(self, option: str) -> None:
        self.runtime.settings["load_level"] = int(option)
        self.runtime.save_config()
        self.runtime.recompute_hub()
