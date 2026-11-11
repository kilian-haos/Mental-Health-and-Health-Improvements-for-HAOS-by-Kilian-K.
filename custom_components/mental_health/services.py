"""Services (automations): start/cancel check-ins, pause/resume, backups, setup request."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

ATTR_PERSON = "person"


def _rt(hass: HomeAssistant) -> Any:
    from .websocket import get_runtime
    rt = get_runtime(hass)
    if rt is None:
        raise HomeAssistantError("Mental Health is not loaded")
    return rt


def _person(rt: Any, ref: str) -> Any:
    """person.xyz entity, person id or name."""
    for p in rt.persons.values():
        if ref in (p.profile["person_entity"], p.pid) or ref.lower() == (p.name or "").lower():
            return p
    raise ServiceValidationError(translation_domain=DOMAIN, translation_key="unknown_person",
                                 translation_placeholders={"person": ref})


async def _admin_only(hass: HomeAssistant, call: ServiceCall) -> None:
    if call.context.user_id:
        user = await hass.auth.async_get_user(call.context.user_id)
        if user is None or not user.is_admin:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="admin_only")


def async_register(hass: HomeAssistant) -> None:
    async def start_checkin(call: ServiceCall) -> None:
        rt = _rt(hass)
        p = _person(rt, call.data[ATTR_PERSON])
        await rt.open_window(p.pid, call.data["kind"], call.data.get("window_minutes"))

    async def cancel_checkin(call: ServiceCall) -> None:
        rt = _rt(hass)
        p = _person(rt, call.data[ATTR_PERSON])
        kinds = [call.data["kind"]] if call.data.get("kind") else ["morning", "evening"]
        for k in kinds:
            if rt.window_open(p.pid, k):
                await rt.close_window(p.pid, k, "cancelled")

    async def pause_person(call: ServiceCall) -> None:
        rt = _rt(hass)
        p = _person(rt, call.data[ATTR_PERSON])
        until = call.data.get("until")
        await rt.async_set_pause(p.pid, True, until.isoformat() if until else None)

    async def resume_person(call: ServiceCall) -> None:
        rt = _rt(hass)
        p = _person(rt, call.data[ATTR_PERSON])
        await rt.async_set_pause(p.pid, False, None)

    async def create_backup(call: ServiceCall) -> ServiceResponse:
        await _admin_only(hass, call)
        from . import archive
        rt = _rt(hass)
        try:
            res = await archive.async_create(rt, None, "service")
        except archive.BackupError as err:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="backup_" + err.code) from err
        return res

    async def restore_backup(call: ServiceCall) -> ServiceResponse:
        await _admin_only(hass, call)
        from . import archive
        rt = _rt(hass)
        try:
            blob = await hass.async_add_executor_job(archive.read_file, rt, call.data["file"])
            return await archive.async_restore(rt, blob, call.data["password"], call.data.get("scope", "all"))
        except archive.BackupError as err:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="backup_" + err.code) from err

    async def request_setup(call: ServiceCall) -> None:
        rt = _rt(hass)
        if not call.context.user_id:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="needs_user")
        user = await hass.auth.async_get_user(call.context.user_id)
        await rt.async_request_setup(user)

    async def send_test(call: ServiceCall) -> None:
        rt = _rt(hass)
        p = _person(rt, call.data[ATTR_PERSON])
        await rt.send_test(p)

    kind = vol.In(["morning", "evening"])
    hass.services.async_register(DOMAIN, "start_checkin", start_checkin, vol.Schema({
        vol.Required(ATTR_PERSON): cv.string, vol.Required("kind"): kind,
        vol.Optional("window_minutes"): vol.All(vol.Coerce(int), vol.Range(min=5, max=1440))}))
    hass.services.async_register(DOMAIN, "cancel_checkin", cancel_checkin, vol.Schema({
        vol.Required(ATTR_PERSON): cv.string, vol.Optional("kind"): kind}))
    hass.services.async_register(DOMAIN, "pause_person", pause_person, vol.Schema({
        vol.Required(ATTR_PERSON): cv.string, vol.Optional("until"): cv.date}))
    hass.services.async_register(DOMAIN, "resume_person", resume_person, vol.Schema({vol.Required(ATTR_PERSON): cv.string}))
    hass.services.async_register(DOMAIN, "create_backup", create_backup, vol.Schema({}),
                                 supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "restore_backup", restore_backup, vol.Schema({
        vol.Required("file"): cv.string, vol.Required("password"): cv.string,
        vol.Optional("scope", default="all"): vol.In(["all", "config"])}), supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "request_setup", request_setup, vol.Schema({}))
    hass.services.async_register(DOMAIN, "send_test_notification", send_test, vol.Schema({vol.Required(ATTR_PERSON): cv.string}))
