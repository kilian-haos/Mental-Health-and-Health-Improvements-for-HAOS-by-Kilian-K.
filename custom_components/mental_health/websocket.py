"""Websocket API for cards and panel.

Rules: every command that returns *content* resolves the person from `connection.user.id`
(the person can only ever be oneself – no admin bypass) and checks the person's PIN session.
Admin commands use `require_admin` and the optional admin PIN session.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, callback

from . import archive
from .const import DOMAIN, VERSION
from .logic import permissions as PM
from .logic.analysis import insights as INS
from .person import search_records
from .storage import Locked, normalize_settings, normalize_target

ERR_LOCKED = "locked"
ERR_NOT_SET_UP = "not_set_up"


def get_runtime(hass: HomeAssistant) -> Any:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED and getattr(entry, "runtime_data", None) is not None:
            return entry.runtime_data
    return None


def _rt(hass: HomeAssistant, connection: Any, msg: dict) -> Any:
    rt = get_runtime(hass)
    if rt is None:
        connection.send_error(msg["id"], "not_loaded", "Mental Health is not loaded")
    return rt


def _own_person(hass: HomeAssistant, connection: Any, msg: dict, need_unlock: bool = True) -> tuple[Any, Any]:
    """(runtime, person) of the connected user – or (None, None) after sending an error."""
    rt = _rt(hass, connection, msg)
    if rt is None:
        return None, None
    p = rt.person_for_user(connection.user.id)
    if p is None:
        connection.send_error(msg["id"], ERR_NOT_SET_UP, "Not set up for this user")
        return None, None
    if need_unlock and not rt.person_session_ok(p, connection.user.id, msg.get("session")):
        connection.send_error(msg["id"], ERR_LOCKED, "Locked – enter your PIN")
        return None, None
    return rt, p


def _admin(hass: HomeAssistant, connection: Any, msg: dict) -> Any:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return None
    if not connection.user.is_admin:
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Admins only")
        return None
    if not rt.admin_session_ok(connection.user.id, msg.get("admin_session")):
        connection.send_error(msg["id"], "admin_locked", "Admin PIN required")
        return None
    return rt


def _day(v: Any, default: date) -> date:
    try:
        return date.fromisoformat(str(v)) if v else default
    except ValueError:
        return default


S = vol.Optional("session")
AS = vol.Optional("admin_session")


@callback
def async_register(hass: HomeAssistant) -> None:
    for cmd in (ws_me, ws_subscribe, ws_request_setup, ws_unlock, ws_lock, ws_dashboard, ws_form, ws_submit, ws_draft,
                ws_day, ws_delete_entry, ws_search, ws_insights, ws_family, ws_profile, ws_profile_update, ws_set_pin,
                ws_test_notification, ws_sleep_model, ws_sleep_reset, ws_source_preview, ws_export, ws_import,
                ws_llm, ws_pause, ws_admin, ws_admin_unlock, ws_admin_create_person, ws_admin_delete_person,
                ws_admin_settings, ws_admin_set_pin, ws_admin_reset_pin, ws_backup_create, ws_backup_password,
                ws_backup_preview, ws_backup_restore, ws_backup_download, ws_admin_llm, ws_admin_dismiss_request):
        websocket_api.async_register_command(hass, cmd)


# ============================================================ Allgemein
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/me"})
@callback
def ws_me(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt:
        connection.send_result(msg["id"], rt.me_payload(connection.user))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@callback
def ws_subscribe(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    msg_id = msg["id"]

    @callback
    def send(payload: dict) -> None:
        connection.send_message(websocket_api.event_message(msg_id, payload))

    connection.subscriptions[msg_id] = rt.subscribe(connection.user.id, send)
    connection.send_result(msg_id)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/request_setup"})
@websocket_api.async_response
async def ws_request_setup(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt:
        connection.send_result(msg["id"], await rt.async_request_setup(connection.user))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/unlock", vol.Required("pin"): str})
@websocket_api.async_response
async def ws_unlock(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    try:
        connection.send_result(msg["id"], await rt.async_unlock_person(connection.user.id, msg["pin"]))
    except ValueError as err:
        connection.send_error(msg["id"], str(err), str(err))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/lock", S: str})
@callback
def ws_lock(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    p = rt.person_for_user(connection.user.id)
    if p:
        rt.lock_person(p.pid)
    connection.send_result(msg["id"], {"ok": True})


# ============================================================ Persönlich (nur die Person selbst)
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/dashboard", S: str})
@callback
def ws_dashboard(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if p:
        connection.send_result(msg["id"], rt.dashboard_payload(p))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/form", vol.Required("slot"): vol.In(["morning", "evening"]),
                                  vol.Optional("day"): str, S: str})
@callback
def ws_form(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if p:
        connection.send_result(msg["id"], rt.checkin_form(p, msg["slot"], _day(msg.get("day"), rt.clock().today)))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/submit", vol.Required("slot"): vol.In(["morning", "evening"]),
                                  vol.Optional("day"): str, vol.Required("data"): dict, S: str})
@websocket_api.async_response
async def ws_submit(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return
    try:
        res = await rt.async_submit(p, msg["slot"], _day(msg.get("day"), rt.clock().today), msg["data"])
    except Locked:
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    connection.send_result(msg["id"], res)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/draft", vol.Required("slot"): vol.In(["morning", "evening"]),
                                  vol.Optional("data"): vol.Any(dict, None), S: str})
@callback
def ws_draft(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return
    data = msg.get("data")
    if data is not None and len(json.dumps(data)) > 20000:
        connection.send_error(msg["id"], "too_large", "Draft too large")
        return
    try:
        p.vault.set_draft(msg["slot"], data)
    except Locked:
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    rt.save_person(p.pid)
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/day", vol.Required("day"): str, S: str})
@callback
def ws_day(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return
    d = _day(msg["day"], rt.clock().today).isoformat()
    try:
        rec = p.record(d, with_texts=True)
    except Locked:
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    n = p.vault.numbers(d)
    rec["sleep"] = n.get("sleep")
    rec["edits"] = {s: (n.get(s[0]) or {}).get("_edits") for s in ("morning", "evening")}
    rec["entries"] = {s: {k: v for k, v in (n.get(s[0]) or {}).items() if not k.startswith("_")} for s in ("morning", "evening")}
    connection.send_result(msg["id"], rec)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/delete_entry", vol.Required("day"): str,
                                  vol.Optional("slot"): vol.Any(None, vol.In(["morning", "evening"])), S: str})
@callback
def ws_delete_entry(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return
    p.delete_entry(_day(msg["day"], rt.clock().today), msg.get("slot"))
    rt.save_person(p.pid, model=True)
    rt.mark_changed(p.pid)
    hass.async_create_task(rt._catch_up_analysis(p.pid))
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/search", vol.Optional("query"): str,
                                  vol.Optional("chips"): list, vol.Optional("llm", default=False): bool, S: str})
@websocket_api.async_response
async def ws_search(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return
    today = rt.clock().today
    chips = msg.get("chips")
    used_llm = False
    if msg.get("llm") and msg.get("query") and chips is None:
        from .llm import Llm, LlmUnavailable
        try:
            chips = await Llm(rt).search_filters(p, msg["query"], today, connection.user and rt.lang)
            used_llm = True
        except LlmUnavailable as err:
            rt.llm_state = {"last_error": err.code}
            chips = None
    try:
        results, chips_out = await hass.async_add_executor_job(search_records, p, msg.get("query"), chips, today)
    except Locked:
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    out = []
    for r in results[:200]:
        rec = p.record(r["day"], with_texts=True)
        out.append({**r, "mood": rec["mood"], "good": rec["good"][:3], "bad": rec["bad"][:2],
                    "journal": (rec["journal"] or "")[:280], "trained": rec["trained"], "sleep_h": rec["sleep_h"],
                    "period": rec["period"]})
    connection.send_result(msg["id"], {"results": out, "chips": chips_out, "llm": used_llm})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/insights", S: str})
@websocket_api.async_response
async def ws_insights(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return
    today = rt.clock().today

    def build() -> dict:
        recs = p.records(with_texts=True)
        wk_end = today
        wk_start = today - timedelta(days=6)
        month_start = today.replace(day=1)
        prev_month_end = month_start - timedelta(days=1)
        return {
            "week": INS.period_report(recs, wk_start, wk_end, wk_start - timedelta(days=7), wk_start - timedelta(days=1)),
            "month": INS.period_report(recs, month_start, today, prev_month_end.replace(day=1), prev_month_end),
        }
    try:
        reports = await hass.async_add_executor_job(build)
    except Locked:
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    await rt._catch_up_analysis(p.pid)
    derived = p.vault.get_derived() or {}
    connection.send_result(msg["id"], {**reports, "derived": derived})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/family"})
@callback
def ws_family(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt:
        connection.send_result(msg["id"], rt.family_payload(rt.viewer(connection.user)))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/pause", vol.Required("on"): bool,
                                  vol.Optional("until"): vol.Any(str, None), vol.Optional("pid"): str, AS: str, S: str})
@websocket_api.async_response
async def ws_pause(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    p = rt.persons.get(msg.get("pid") or "") or rt.person_for_user(connection.user.id)
    if p is None:
        connection.send_error(msg["id"], ERR_NOT_SET_UP, "Not set up")
        return
    v = rt.viewer(connection.user)
    if not PM.allowed(v, PM.PAUSE, p.rights) or (v.user_id != p.user_id and not rt.admin_session_ok(v.user_id, msg.get("admin_session"))):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Not allowed")
        return
    until = msg.get("until")
    if until:
        try:
            date.fromisoformat(until)
        except ValueError:
            until = None
    await rt.async_set_pause(p.pid, msg["on"], until)
    connection.send_result(msg["id"], {"ok": True})


# ============================================================ Profil
def _profile_view(rt: Any, v: PM.Viewer, p: Any) -> dict:
    prof = dict(p.profile)
    ok_w, why_w = PM.check(v, PM.WEIGHT_VIEW, p.rights)
    if not ok_w:
        prof["weight_kg"] = None
    if v.user_id != p.user_id:
        prof.pop("llm_consent", None)
    return {"profile": prof, "rights": PM.rights_map(v, p.rights), "weight_hidden": not ok_w, "weight_why": why_w,
            "self": v.user_id == p.user_id, "has_pin": rt.keyring.has_pin(p.pid), "picture": rt._picture(p),
            "age": p.age(rt.clock().today), "missing": p.missing_profile(),
            "notify_services": sorted(f"notify.{s}" for s in (rt.hass.services.async_services().get("notify") or {})),
            "platforms": {t["id"]: rt._platform_of(t) for t in p.profile["targets"]}}


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/profile", vol.Optional("pid"): str, AS: str})
@callback
def ws_profile(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    v = rt.viewer(connection.user)
    p = rt.persons.get(msg["pid"]) if msg.get("pid") else rt.person_for_user(v.user_id)
    if p is None:
        connection.send_error(msg["id"], ERR_NOT_SET_UP, "Not set up")
        return
    if not PM.allowed(v, PM.PROFILE_VIEW, p.rights):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Not allowed")
        return
    if v.user_id != p.user_id and not rt.admin_session_ok(v.user_id, msg.get("admin_session")):
        connection.send_error(msg["id"], "admin_locked", "Admin PIN required")
        return
    connection.send_result(msg["id"], _profile_view(rt, v, p))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/profile_update", vol.Optional("pid"): str,
                                  vol.Required("changes"): dict, AS: str, S: str})
@callback
def ws_profile_update(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    v = rt.viewer(connection.user)
    p = rt.persons.get(msg["pid"]) if msg.get("pid") else rt.person_for_user(v.user_id)
    if p is None:
        connection.send_error(msg["id"], ERR_NOT_SET_UP, "Not set up")
        return
    if v.user_id != p.user_id:
        if not v.is_admin or not rt.admin_session_ok(v.user_id, msg.get("admin_session")):
            connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Not allowed")
            return
    elif not rt.person_session_ok(p, v.user_id, msg.get("session")):
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    changes = dict(msg["changes"])
    if "targets" in changes:
        changes["targets"] = [t for t in (normalize_target(x) for x in changes["targets"] or []) if t]
    refused = rt.update_profile(p.pid, changes, v)
    connection.send_result(msg["id"], {"refused": refused, **_profile_view(rt, v, p)})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/set_pin", vol.Optional("old"): vol.Any(str, None),
                                  vol.Optional("new"): vol.Any(str, None)})
@websocket_api.async_response
async def ws_set_pin(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    try:
        connection.send_result(msg["id"], await rt.async_set_pin(connection.user.id, msg.get("old"), msg.get("new")))
    except ValueError as err:
        connection.send_error(msg["id"], str(err), str(err))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/test_notification", vol.Optional("pid"): str, AS: str})
@websocket_api.async_response
async def ws_test_notification(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    v = rt.viewer(connection.user)
    p = rt.persons.get(msg["pid"]) if msg.get("pid") else rt.person_for_user(v.user_id)
    if p is None or not (v.user_id == p.user_id or (v.is_admin and rt.admin_session_ok(v.user_id, msg.get("admin_session")))):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Not allowed")
        return
    n = await rt.send_test(p)
    connection.send_result(msg["id"], {"sent": n, "targets": len(p.profile["targets"])})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/sleep_model", vol.Optional("pid"): str, AS: str, S: str})
@callback
def ws_sleep_model(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    """Model view: the person sees everything incl. recent nights; an admin (setup) sees no nights."""
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    v = rt.viewer(connection.user)
    p = rt.persons.get(msg["pid"]) if msg.get("pid") else rt.person_for_user(v.user_id)
    if p is None:
        connection.send_error(msg["id"], ERR_NOT_SET_UP, "Not set up")
        return
    own = v.user_id == p.user_id
    if own and not rt.person_session_ok(p, v.user_id, msg.get("session")):
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    if not own and not (v.is_admin and rt.admin_session_ok(v.user_id, msg.get("admin_session"))):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Not allowed")
        return
    view = p.sleep.view()
    if not own:
        view.pop("history", None)
        view.pop("bias", None)
    view["state"] = p.live.state_now if (p.live and own) else None
    view["sources"] = [s.to_dict() for s in p.sources]
    connection.send_result(msg["id"], view)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/sleep_reset", vol.Optional("pid"): str, AS: str, S: str})
@callback
def ws_sleep_reset(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    v = rt.viewer(connection.user)
    p = rt.persons.get(msg["pid"]) if msg.get("pid") else rt.person_for_user(v.user_id)
    if p is None or not PM.allowed(v, PM.PROFILE_EDIT, p.rights):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Not allowed")
        return
    p.sleep.reset()
    rt.save_person(p.pid, model=True)
    rt.mark_changed(p.pid)
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/source_preview", vol.Optional("pid"): str,
                                  vol.Required("source"): dict, vol.Optional("hours", default=48): vol.All(int, vol.Range(min=6, max=168)),
                                  AS: str, S: str})
@websocket_api.async_response
async def ws_source_preview(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt is None:
        return
    v = rt.viewer(connection.user)
    p = rt.persons.get(msg["pid"]) if msg.get("pid") else rt.person_for_user(v.user_id)
    if p is None or not PM.allowed(v, PM.PROFILE_EDIT, p.rights):
        connection.send_error(msg["id"], websocket_api.ERR_UNAUTHORIZED, "Not allowed")
        return
    connection.send_result(msg["id"], await rt.async_source_preview(p.pid, msg["source"], msg["hours"]))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/export", vol.Optional("format", default="json"): vol.In(["json", "md"]), S: str})
@websocket_api.async_response
async def ws_export(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    """Personal export – only the person's own data."""
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return

    def build() -> str:
        recs = p.records(with_texts=True)
        if msg["format"] == "json":
            return json.dumps({"app": "mental_health", "version": VERSION, "person": p.name, "days": recs,
                               "weights": p.vault.weights, "export_format": 1}, ensure_ascii=False, indent=1)
        lines = [f"# Mental Health – {p.name}", ""]
        for r in reversed(recs):
            lines.append(f"## {r['day']}")
            if r.get("mood") is not None:
                lines.append(f"- Mood: {r['mood']:.1f}" + (f" · Energy: {r['energy']:.0f}" if r.get("energy") else ""))
            if r.get("sleep_h"):
                lines.append(f"- Sleep: {r['sleep_h']} h")
            if r.get("trained"):
                lines.append("- Training ✓")
            for g in r.get("good") or []:
                lines.append(f"- 👍 {g}")
            for b in r.get("bad") or []:
                lines.append(f"- 👎 {b}")
            for g in r.get("goals") or []:
                lines.append(f"- 🎯 {g}")
            if r.get("journal"):
                lines += ["", r["journal"]]
            lines.append("")
        return "\n".join(lines)
    try:
        text = await hass.async_add_executor_job(build)
    except Locked:
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    connection.send_result(msg["id"], {"format": msg["format"], "content": text})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/import", vol.Required("content"): str, S: str})
@websocket_api.async_response
async def ws_import(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    """Own import (JSON export of this integration). Existing days are kept, new ones added."""
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return
    try:
        data = json.loads(msg["content"])
        days = data["days"] if data.get("app") == "mental_health" else None
    except (ValueError, KeyError, TypeError):
        days = None
    if not isinstance(days, list):
        connection.send_error(msg["id"], "invalid_format", "Not a Mental Health export")
        return
    added = 0
    for r in days:
        d = str(r.get("day") or "")
        try:
            date.fromisoformat(d)
        except ValueError:
            continue
        if d in p.vault.days:
            continue
        n: dict[str, Any] = {}
        if r.get("mood_m") is not None:
            n["m"] = {"mood": r["mood_m"], "_ts": "import"}
        if r.get("mood_e") is not None or r.get("mood") is not None:
            n["e"] = {"mood": r.get("mood_e") or r.get("mood"), "_ts": "import"}
            if r.get("trained") is not None:
                n["e"]["trained"] = {"done": bool(r["trained"])}
        if not n:
            continue
        p.vault.set_numbers(d, n)
        t = {"e": {k: r[k] for k in ("good", "bad", "journal") if r.get(k)}}
        if t["e"]:
            try:
                p.vault.set_texts(d, t)
            except Locked:
                pass
        added += 1
    for d, kg in (data.get("weights") or {}).items():
        if d not in p.vault.weights:
            try:
                p.vault.set_weight(d, float(kg))
            except (TypeError, ValueError):
                continue
    rt.save_person(p.pid)
    rt.mark_changed(p.pid)
    connection.send_result(msg["id"], {"added": added})


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/llm", vol.Required("action"): vol.In(["summary", "status"]),
                                  vol.Optional("days", default=7): int, S: str})
@websocket_api.async_response
async def ws_llm(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt, p = _own_person(hass, connection, msg)
    if not p:
        return
    from .llm import Llm, LlmUnavailable
    llm = Llm(rt)
    if msg["action"] == "status":
        connection.send_result(msg["id"], {"enabled": bool(rt.settings["llm"]["enabled"]), "consent": p.mod("llm"),
                                           "allowed": PM.allowed(rt.viewer(connection.user), PM.LLM_CONSENT, p.rights),
                                           "backend": rt.settings["llm"].get("entity") or rt.settings["llm"].get("agent")})
        return
    others = [o.name for o in rt.persons.values() if o.pid != p.pid] + [o.name.split(" ")[0] for o in rt.persons.values() if o.pid != p.pid]
    try:
        text = await llm.summary(p, rt.clock().today, msg["days"], rt.lang, others)
    except LlmUnavailable as err:
        connection.send_result(msg["id"], {"ok": False, "error": err.code})
        return
    except Locked:
        connection.send_error(msg["id"], ERR_LOCKED, "Locked")
        return
    connection.send_result(msg["id"], {"ok": True, "text": text})


# ============================================================ Admin
@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin", AS: str})
@callback
def ws_admin(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt:
        from .llm import Llm
        connection.send_result(msg["id"], {**rt.admin_payload(), "llm_caps": Llm(rt).capabilities()})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin_unlock", vol.Required("pin"): str})
@websocket_api.async_response
async def ws_admin_unlock(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _rt(hass, connection, msg)
    if rt:
        connection.send_result(msg["id"], await rt.async_admin_unlock(connection.user.id, msg["pin"]))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin_create_person", vol.Required("person_entity"): str,
                                  vol.Optional("data"): dict, AS: str})
@websocket_api.async_response
async def ws_admin_create_person(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    try:
        p = await rt.async_create_person(msg["person_entity"], msg.get("data"))
    except ValueError as err:
        connection.send_error(msg["id"], str(err), str(err))
        return
    connection.send_result(msg["id"], {"pid": p.pid})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin_delete_person", vol.Required("pid"): str, AS: str})
@websocket_api.async_response
async def ws_admin_delete_person(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    try:
        await rt.async_delete_person(msg["pid"])
    except ValueError as err:
        connection.send_error(msg["id"], str(err), str(err))
        return
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin_settings", vol.Required("changes"): dict, AS: str})
@callback
def ws_admin_settings(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    changes = {k: v for k, v in msg["changes"].items() if k not in ("admin_pin", "backup", "llm")}
    if "backup" in msg["changes"]:
        b = {k: v for k, v in (msg["changes"]["backup"] or {}).items() if k in ("auto", "keep")}
        changes["backup"] = {**rt.settings["backup"], **b}
    old_nightly = rt.settings["nightly"]
    new = normalize_settings({**rt.settings, **changes})
    new["admin_pin"] = rt.settings["admin_pin"]
    new["backup"]["password"] = rt.settings["backup"].get("password")
    rt.config["settings"] = new
    rt.save_config()
    if new["nightly"] != old_nightly:
        hass.config_entries.async_schedule_reload(rt.entry.entry_id)
    rt.recompute_all()
    rt.broadcast_all()
    connection.send_result(msg["id"], rt.admin_payload())


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin_set_pin", vol.Optional("pin"): vol.Any(str, None), AS: str})
@websocket_api.async_response
async def ws_admin_set_pin(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    try:
        await rt.async_set_admin_pin(msg.get("pin"))
    except ValueError as err:
        connection.send_error(msg["id"], str(err), str(err))
        return
    connection.send_result(msg["id"], {"ok": True, "admin_pin": rt.admin_pin_set()})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin_reset_pin", vol.Required("pid"): str, AS: str})
@websocket_api.async_response
async def ws_admin_reset_pin(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None or msg["pid"] not in rt.persons:
        if rt is not None:
            connection.send_error(msg["id"], "not_found", "not found")
        return
    connection.send_result(msg["id"], await rt.async_reset_pin(msg["pid"]))


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin_dismiss_request", vol.Required("user_id"): str, AS: str})
@callback
def ws_admin_dismiss_request(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    rt.config["requests"].pop(msg["user_id"], None)
    rt.save_config()
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/admin_llm", vol.Required("changes"): dict, AS: str})
@callback
def ws_admin_llm(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    cur = dict(rt.settings["llm"])
    ch = msg["changes"]
    if "accepted" in ch:
        cur["accepted"] = bool(ch["accepted"])
    if "enabled" in ch:
        cur["enabled"] = bool(ch["enabled"]) and cur["accepted"]
    if ch.get("mode") in ("ai_task", "conversation"):
        cur["mode"] = ch["mode"]
    for k in ("entity", "agent"):
        if k in ch:
            cur[k] = str(ch[k]) if ch[k] else None
    rt.settings["llm"] = cur
    rt.save_config()
    rt.recompute_hub()
    rt.broadcast_all()
    connection.send_result(msg["id"], {"llm": cur})


# ============================================================ Backup (Admin)
@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/backup_password", vol.Optional("password"): vol.Any(str, None), AS: str})
@callback
def ws_backup_password(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    try:
        archive.set_password(rt, msg.get("password"))
    except archive.BackupError as err:
        connection.send_error(msg["id"], err.code, err.code)
        return
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/backup_create", vol.Optional("password"): str, AS: str})
@websocket_api.async_response
async def ws_backup_create(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    try:
        res = await archive.async_create(rt, msg.get("password"), "manual")
    except archive.BackupError as err:
        connection.send_error(msg["id"], err.code, err.code)
        return
    connection.send_result(msg["id"], res)


async def _blob(hass: HomeAssistant, rt: Any, msg: dict) -> bytes:
    if msg.get("name"):
        return await hass.async_add_executor_job(archive.read_file, rt, msg["name"])
    if msg.get("data"):
        return archive.decode_upload(msg["data"])
    raise archive.BackupError("no_file")


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/backup_preview", vol.Optional("name"): str,
                                  vol.Optional("data"): str, vol.Required("password"): str, AS: str})
@websocket_api.async_response
async def ws_backup_preview(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    try:
        blob = await _blob(hass, rt, msg)
        res = await hass.async_add_executor_job(archive.preview, blob, msg["password"])
    except archive.BackupError as err:
        connection.send_error(msg["id"], err.code, err.code)
        return
    connection.send_result(msg["id"], res)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/backup_restore", vol.Optional("name"): str,
                                  vol.Optional("data"): str, vol.Required("password"): str,
                                  vol.Optional("scope", default="all"): vol.In(["all", "config", "person"]),
                                  vol.Optional("pid"): str, AS: str})
@websocket_api.async_response
async def ws_backup_restore(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    try:
        blob = await _blob(hass, rt, msg)
        res = await archive.async_restore(rt, blob, msg["password"], msg["scope"], msg.get("pid"))
    except archive.BackupError as err:
        connection.send_error(msg["id"], err.code, err.code)
        return
    connection.send_result(msg["id"], res)


@websocket_api.require_admin
@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/backup_download", vol.Required("name"): str, AS: str})
@websocket_api.async_response
async def ws_backup_download(hass: HomeAssistant, connection: Any, msg: dict) -> None:
    rt = _admin(hass, connection, msg)
    if rt is None:
        return
    import base64
    try:
        blob = await hass.async_add_executor_job(archive.read_file, rt, msg["name"])
    except archive.BackupError as err:
        connection.send_error(msg["id"], err.code, err.code)
        return
    connection.send_result(msg["id"], {"name": msg["name"], "data": base64.b64encode(blob).decode("ascii")})
