"""Repairs: missing entities / notification services with a one-click fix (remove the reference)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult


class RemoveReferenceFlow(RepairsFlow):
    def __init__(self, data: dict[str, Any] | None) -> None:
        self.data = data or {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        return await self.async_step_confirm()

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        if user_input is not None:
            from .websocket import get_runtime
            rt = get_runtime(self.hass)
            if rt is not None:
                rt.fix_issue(self.data)
            return self.async_create_entry(data={})
        return self.async_show_form(step_id="confirm", data_schema=vol.Schema({}),
                                    description_placeholders={"entity": str(self.data.get("entity", "")),
                                                              "name": str(self.data.get("name", ""))})


async def async_create_fix_flow(hass: HomeAssistant, issue_id: str, data: dict[str, Any] | None) -> RepairsFlow:
    return RemoveReferenceFlow(data)
