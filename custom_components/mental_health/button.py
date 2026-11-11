"""Buttons: start a check-in (for automations), create a backup."""
from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import HubEntity, PersonEntity, setup_platform


async def async_setup_entry(hass: HomeAssistant, entry: Any, async_add_entities: AddEntitiesCallback) -> None:
    rt = entry.runtime_data
    entry.async_on_unload(setup_platform(rt, "button", async_add_entities, StartButton, BackupButton))


class StartButton(PersonEntity, ButtonEntity):
    async def async_press(self) -> None:
        slot = "morning" if self.d.key == "start_morning" else "evening"
        await self.runtime.open_window(self.pid, slot)


class BackupButton(HubEntity, ButtonEntity):
    async def async_press(self) -> None:
        from . import archive
        await archive.async_create_auto(self.runtime)
