"""Diagnostics download – structure, counters, model state and versions only. No contents.

No names, no entries, no texts, no weights, no cycle data, no notification targets, no keys.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import VERSION


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    rt = entry.runtime_data
    s = dict(rt.settings)
    s["admin_pin"] = bool(s.get("admin_pin"))
    s["admin_targets"] = len(s.get("admin_targets") or [])
    s["backup"] = {**s["backup"], "password": bool(s["backup"].get("password"))}
    s["llm"] = {k: v for k, v in s["llm"].items() if k in ("enabled", "mode", "accepted")}
    for k in ("weather_entity", "daylight_entity", "workday_entity"):
        s[k] = bool(s.get(k))
    persons = []
    for i, (pid, p) in enumerate(rt.persons.items()):
        persons.append({
            "index": i,
            "child": p.child, "can_edit_own": p.profile.get("can_edit_own"),
            "modules": {k: p.mod(k) for k in p.modules},
            "profile_complete": not p.missing_profile(), "has_pin": rt.keyring.has_pin(pid),
            "sources": [{"kind": s_.kind, "role": s_.role, "threshold_set": s_.threshold is not None,
                         "shared": bool(s_.shared_with), "buffer_head": (p.series.get(s_.id).head if p.series.get(s_.id) else None)}
                        for s_ in p.sources],
            "targets": [{"kind": t["kind"], "platform": rt._platform_of(t)} for t in p.profile["targets"]],
            "schedule_modes": {k: (p.profile["schedule"].get(k) or {}).get("mode") for k in ("morning", "evening")},
            "days_stored": len(p.vault.days), "weights_stored": len(p.vault.weights),
            "sleep_model": {k: v for k, v in p.sleep.view().items() if k not in ("history",)},
            "live_state": p.live.state_now if p.live else None,
            "live_confidence": p.live.confidence if p.live else None,
            "mood_model_days": p.mood.days, "optimum_conf": (p.optimum or {}).get("conf"),
            "unlocked": p.vault.tek is not None,
            "windows": {k: rt.window_open(pid, k) for k in ("morning", "evening")},
        })
    return {
        "version": VERSION, "ha_language": rt.lang, "options": dict(entry.options), "settings": s,
        "persons": persons, "sessions": len(rt.sessions), "subscribers": len(rt.subscribers),
        "backup_info": {k: v for k, v in rt.backup_info.items()}, "requests": len(rt.config["requests"]),
    }
