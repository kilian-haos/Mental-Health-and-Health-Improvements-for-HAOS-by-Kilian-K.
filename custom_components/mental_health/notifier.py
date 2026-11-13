"""Notifications: send per device, remind, re-send after swipe-away (Android 14+), clear.

* Every target is called on its own – one broken target never blocks the others.
* The notification only opens the check-in page (deep link). No text input in notifications:
  replies would travel over the event bus and the recorder.
* Android 14+ lets users swipe away even `persistent: true` notifications. When the Companion
  App reports `mobile_app_notification_cleared` for one of our tags while the person's window is
  still open, the notification is re-sent to exactly that device (rate-limited, alert_once).
  The device is encoded in the tag: mh_<person>_<slot>_<index>.
* iOS/macOS: no persistence – time-sensitive interruption level, replacement via tag, reminders.
"""
from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from typing import Any

from .const import NOTIFY_TAG, PANEL_URL_PATH, RESEND_MAX_PER_WINDOW, RESEND_MIN_GAP_S

_LOGGER = logging.getLogger(__name__)
TAG_RE = re.compile(r"^mh_([A-Za-z0-9]+)_(morning|evening|test|weekly)_(\d+)$")
LATER_RE = re.compile(r"^MH_LATER_([A-Za-z0-9]+)_(morning|evening)_(\d+)$")


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", str(text).lower().replace("ä", "a").replace("ö", "o").replace("ü", "u").replace("ß", "ss"))
    return s.strip("_")


def make_tag(pid: str, kind: str, idx: int) -> str:
    return NOTIFY_TAG.format(pid=pid, kind=kind, idx=idx)


def parse_tag(tag: Any) -> tuple[str, str, int] | None:
    m = TAG_RE.match(str(tag or ""))
    if not m:
        return None
    return m.group(1), m.group(2), int(m.group(3))


def deep_link(kind: str) -> str:
    return f"/{PANEL_URL_PATH}?checkin={kind}" if kind in ("morning", "evening") else f"/{PANEL_URL_PATH}"


def build_payload(target: dict, platform: str, *, title: str, message: str, tag: str, url: str, persist: bool,
                  importance: str, ios_level: str, channel: str, actions: list[dict], resend: bool = False,
                  alert: bool = False) -> dict:
    """alert=True: play a sound again although a notification with this tag is already shown (reminders).
    Re-sends after a swipe-away stay silent (alert_once)."""
    """Service data for one target (mobile_app Android/iOS, generic notify, script)."""
    if target["kind"] == "service" and target["service"].startswith("notify.mobile_app_"):
        data: dict[str, Any] = {"tag": tag, "url": url, "clickAction": url}
        if platform == "android":
            data.update({"channel": channel, "importance": importance, "priority": "high", "ttl": 0,
                         "sticky": "true", "alert_once": not alert})
            if persist:
                data["persistent"] = True
            data["actions"] = [
                {"action": "URI", "title": a["title"], "uri": a["uri"]} if a.get("uri") else
                {"action": a["action"], "title": a["title"]} for a in actions]
        else:   # iOS / macOS
            data["push"] = {"interruption-level": ios_level}
            if alert:
                data["push"]["sound"] = "default"
            if resend:
                data["push"]["interruption-level"] = "passive"
            data["actions"] = [
                {"action": "URI", "title": a["title"], "uri": a["uri"]} if a.get("uri") else
                {"action": a["action"], "title": a["title"]} for a in actions]
        return {"title": title, "message": message, "data": data}
    if target["kind"] == "service":
        return {"title": title, "message": f"{message}\n{url}"}
    if target["kind"] == "entity":
        return {"title": title, "message": f"{message}\n{url}"}
    # Skript: Felder frei zuordnen, Persistenz-Daten durchreichen
    fields = target.get("fields") or {}
    out: dict[str, Any] = {}
    if fields.get("title"):
        out[fields["title"]] = title
    if fields.get("message"):
        out[fields["message"]] = message if fields.get("data") else f"{message}\n{url}"
    if fields.get("data"):
        d: dict[str, Any] = {"tag": tag, "url": url, "clickAction": url}
        if target.get("platform") == "android":
            d.update({"channel": channel, "importance": importance, "sticky": "true", "alert_once": not alert, "ttl": 0,
                      "priority": "high"})
            if persist:
                d["persistent"] = True
        elif target.get("platform") == "ios":
            d["push"] = {"interruption-level": ios_level}
        out[fields["data"]] = d
    if fields.get("target") and target.get("target_value"):
        out[fields["target"]] = target["target_value"]
    return out


def clear_payload(target: dict, tag: str) -> dict | None:
    if target["kind"] == "service" and target["service"].startswith("notify.mobile_app_"):
        return {"message": "clear_notification", "data": {"tag": tag}}
    if target["kind"] == "script" and (target.get("fields") or {}).get("data") and (target.get("fields") or {}).get("message"):
        f = target["fields"]
        out = {f["message"]: "clear_notification", f["data"]: {"tag": tag}}
        if f.get("target") and target.get("target_value"):
            out[f["target"]] = target["target_value"]
        return out
    return None


class ResendGuard:
    """Rate limit for re-sending after swipe-away: max 1 per 10 s and N per window per device."""

    def __init__(self, min_gap: float = RESEND_MIN_GAP_S, max_per_window: int = RESEND_MAX_PER_WINDOW,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.min_gap = min_gap
        self.max = max_per_window
        self.clock = clock
        self._last: dict[str, float] = {}
        self._count: dict[str, int] = {}

    def allow(self, tag: str) -> bool:
        now = self.clock()
        if now - self._last.get(tag, -1e9) < self.min_gap:
            return False
        if self._count.get(tag, 0) >= self.max:
            return False
        self._last[tag] = now
        self._count[tag] = self._count.get(tag, 0) + 1
        return True

    def reset(self, prefix: str) -> None:
        for k in [k for k in self._count if k.startswith(prefix)]:
            self._count.pop(k, None)
            self._last.pop(k, None)


class Notifier:
    """Sends via hass.services – one call per target, errors are isolated and reported."""

    def __init__(self, hass: Any, platform_of: Callable[[dict], str], on_error: Callable[[dict, str], None]) -> None:
        self.hass = hass
        self.platform_of = platform_of
        self.on_error = on_error
        self.guard = ResendGuard()

    async def _call(self, target: dict, data: dict) -> bool:
        try:
            if target["kind"] == "service":
                domain, service = target["service"].split(".", 1)
                await self.hass.services.async_call(domain, service, data, blocking=True)
            elif target["kind"] == "entity":
                await self.hass.services.async_call("notify", "send_message",
                                                    {"entity_id": target["entity"], "title": data.get("title"),
                                                     "message": data.get("message")}, blocking=True)
            else:
                await self.hass.services.async_call("script", target["entity"].split(".", 1)[1], data, blocking=False)
            return True
        except Exception as err:  # noqa: BLE001 – ein defektes Ziel darf die anderen nicht blockieren
            _LOGGER.warning("Mental Health: notification target %s failed: %s", target.get("name"), type(err).__name__)
            self.on_error(target, type(err).__name__)
            return False

    async def send(self, pid: str, kind: str, targets: list[dict], *, title: str, message: str, persist: bool,
                   importance: str, ios_level: str, channel: str, actions_for: Callable[[int], list[dict]],
                   only_index: int | None = None, resend: bool = False, alert: bool = False) -> int:
        ok = 0
        url = deep_link(kind)
        for idx, target in enumerate(targets):
            if only_index is not None and idx != only_index:
                continue
            platform = self.platform_of(target)
            payload = build_payload(target, platform, title=title, message=message, tag=make_tag(pid, kind, idx), url=url,
                                    persist=persist, importance=importance, ios_level=ios_level, channel=channel,
                                    actions=actions_for(idx), resend=resend, alert=alert)
            if await self._call(target, payload):
                ok += 1
        return ok

    async def clear(self, pid: str, kind: str, targets: list[dict]) -> None:
        for idx, target in enumerate(targets):
            data = clear_payload(target, make_tag(pid, kind, idx))
            if data is not None:
                await self._call(target, data)
        self.guard.reset(f"mh_{pid}_{kind}_")

    async def send_admin(self, targets: list[dict], title: str, message: str, url: str,
                         actions: list[dict] | None = None) -> int:
        ok = 0
        for idx, target in enumerate(targets):
            platform = self.platform_of(target)
            payload = build_payload(target, platform, title=title, message=message, tag=f"mh_admin_{idx}", url=url,
                                    persist=False, importance="default", ios_level="active", channel="Mental Health",
                                    actions=actions or [])
            if await self._call(target, payload):
                ok += 1
        return ok
