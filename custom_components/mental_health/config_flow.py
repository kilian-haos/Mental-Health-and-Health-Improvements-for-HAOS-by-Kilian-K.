"""Config flow (one-click setup) and options (sidebar panel).

Everything else – persons, rights, modules, sources, schedules, targets, PINs, backups – is
configured in the admin area of the panel, which is far more comfortable than dialogs.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback

from .const import DOMAIN, NAME

CONF_PANEL = "panel"
CONF_PANEL_TITLE = "panel_title"


class MentalHealthConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title=NAME, data={}, options={
                CONF_PANEL: user_input.get(CONF_PANEL, True), CONF_PANEL_TITLE: user_input.get(CONF_PANEL_TITLE, "")})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Optional(CONF_PANEL, default=True): bool,
            vol.Optional(CONF_PANEL_TITLE, default=""): str,
        }))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MentalHealthOptionsFlow()


class MentalHealthOptionsFlow(OptionsFlow):
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={**self.config_entry.options, **user_input})
        o = self.config_entry.options
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Optional(CONF_PANEL, default=o.get(CONF_PANEL, True)): bool,
            vol.Optional(CONF_PANEL_TITLE, default=o.get(CONF_PANEL_TITLE, "")): str,
        }))
