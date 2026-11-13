"""Stores, data model, encryption at rest and migrations.

Stores (in `<config>/.storage/`):
  mental_health.config          structure only: persons/profiles, settings, targets (no content)
  mental_health.keys            master key + wrapped person keys (see logic/crypto.py)
  mental_health.person.<pid>    entries per day, encrypted (numbers: DEK, texts: TEK)
  mental_health.model.<pid>     learned models + sensor buffer, encrypted with the DEK

Every store has a version; `migrate_*` functions upgrade older formats when loading.
"""
from __future__ import annotations

import copy
import uuid
from typing import Any

from .const import (
    DEFAULT_DAY_BOUNDARY, DEFAULT_EVENING, DEFAULT_EVENING_FROM, DEFAULT_FAMILY_K, DEFAULT_LATE_ENTRY,
    DEFAULT_LOAD_LEVEL, DEFAULT_LOW_MOOD_DAYS, DEFAULT_LOW_MOOD_MAX, DEFAULT_MORNING, DEFAULT_MORNING_UNTIL,
    DEFAULT_NIGHTLY, DEFAULT_PIN_SESSION_MIN, DEFAULT_REMIND_MIN, DEFAULT_SETUP_REQUEST_COOLDOWN_H,
    DEFAULT_SLEEP_GAP_MIN, DEFAULT_WINDOW_MIN, MODULES, MODULES_DEFAULT, MODULES_LOCKED_ON, SEXES,
)
from .logic.birthday import Birthdate
from .logic.crypto import CryptoError, decrypt_json, encrypt_json
from .logic.daymath import valid_hhmm
from .logic.schedule import SlotSchedule
from .logic.sleep.sources import Source

# ============================================================== Konfiguration
DEFAULT_SETTINGS: dict[str, Any] = {
    "day_boundary": DEFAULT_DAY_BOUNDARY,
    "evening_from": DEFAULT_EVENING_FROM,
    "morning_until": DEFAULT_MORNING_UNTIL,
    "window_min": DEFAULT_WINDOW_MIN,
    "remind_min": DEFAULT_REMIND_MIN,
    "late_entry": DEFAULT_LATE_ENTRY,
    "nightly": DEFAULT_NIGHTLY,
    "load_level": DEFAULT_LOAD_LEVEL,
    "family_k": DEFAULT_FAMILY_K,
    "low_mood_days": DEFAULT_LOW_MOOD_DAYS,
    "low_mood_max": DEFAULT_LOW_MOOD_MAX,
    "request_cooldown_h": DEFAULT_SETUP_REQUEST_COOLDOWN_H,
    "weekly_report": True,
    "workday_entity": None,
    "weather_entity": None,        # vom Admin global freigegeben (Außentemperatur)
    "daylight_entity": None,       # z. B. sun.sun
    "admin_pin": None,             # Hash (nie im Klartext)
    "admin_targets": [],           # Benachrichtigungsziele für Admins
    "llm": {"enabled": False, "mode": "ai_task", "entity": None, "agent": None, "accepted": False},
    "backup": {"auto": "weekly", "keep": 8, "password": None},   # password = Schlüssel-Ableitung (Hash), s. archive.py
}

DEFAULT_NOTIFY = {
    "details": False,              # Details (Schlaf-Score usw.) auf dem Sperrbildschirm
    "remind": True,
    "later": True,
    "persist": True,               # Android: weggewischt -> neu senden (solange offen)
    "importance": "high",
    "ios_level": "time-sensitive",
    "weekly": True,
}


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def _bool(v: Any, default: bool) -> bool:
    return bool(v) if isinstance(v, bool) else default


def _num(v: Any, lo: float, hi: float, default: float | None) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return default
    if f != f:
        return default
    return max(lo, min(hi, f))


def normalize_target(raw: Any) -> dict | None:
    """Notification target: notify service, notify entity or script with field mapping."""
    if not isinstance(raw, dict):
        return None
    kind = raw.get("kind")
    if kind == "service":
        svc = str(raw.get("service") or "")
        if not svc.startswith("notify."):
            return None
        return {"id": raw.get("id") or new_id(), "kind": "service", "service": svc,
                "platform": raw.get("platform") if raw.get("platform") in ("android", "ios", "other") else "auto",
                "name": str(raw.get("name") or svc)[:60]}
    if kind == "entity":
        ent = str(raw.get("entity") or "")
        if not ent.startswith("notify."):
            return None
        return {"id": raw.get("id") or new_id(), "kind": "entity", "entity": ent, "name": str(raw.get("name") or ent)[:60]}
    if kind == "script":
        ent = str(raw.get("entity") or raw.get("script") or "")
        if not ent.startswith("script."):
            return None
        fields = raw.get("fields") if isinstance(raw.get("fields"), dict) else {}
        clean = {k: str(v)[:60] for k, v in fields.items() if k in ("title", "message", "data", "target") and v}
        return {"id": raw.get("id") or new_id(), "kind": "script", "entity": ent, "fields": clean,
                "target_value": str(raw.get("target_value") or "")[:120],
                "platform": raw.get("platform") if raw.get("platform") in ("android", "ios", "other") else "other",
                "name": str(raw.get("name") or ent)[:60]}
    return None


def normalize_person(raw: dict, pid: str | None = None) -> dict:
    """Fill defaults, clamp values. Unknown keys are dropped."""
    r = dict(raw or {})
    pid = pid or r.get("id") or new_id()
    mods = dict(MODULES_DEFAULT)
    for k, v in (r.get("modules") or {}).items():
        if k in MODULES and isinstance(v, bool):
            mods[k] = v
    for k in MODULES_LOCKED_ON:
        mods[k] = True
    sex = r.get("sex") if r.get("sex") in SEXES else "unspecified"
    if sex not in ("female", "other"):
        mods["cycle"] = False
    child = _bool(r.get("child"), False)
    bd = Birthdate.parse(r.get("birthdate"))
    sched = r.get("schedule") or {}
    sources = []
    for s in r.get("sleep_sources") or []:
        if isinstance(s, dict) and s.get("entity"):
            src = Source.from_dict(s)
            sources.append(src.to_dict())
    targets = [t for t in (normalize_target(x) for x in r.get("targets") or []) if t]
    cyc_src = [Source.from_dict(s).to_dict() for s in (r.get("cycle_sources") or []) if isinstance(s, dict) and s.get("entity")]
    p = {
        "id": pid,
        "person_entity": str(r.get("person_entity") or ""),
        "user_id": r.get("user_id") or None,
        "name": str(r.get("name") or "")[:40],
        "child": child,
        "can_edit_own": False if child else _bool(r.get("can_edit_own"), False),
        "birthdate": bd.to_str() if bd else None,
        "sex": sex,
        "height_cm": _num(r.get("height_cm"), 50, 250, None),
        "weight_kg": _num(r.get("weight_kg"), 2, 400, None),
        "weight_live": _bool(r.get("weight_live"), False),
        "weight_entity": r.get("weight_entity") or None,
        "target_weight": _num(r.get("target_weight"), 2, 400, None),
        "modules": mods,
        "sleep_sources": sources,
        "cycle_sources": cyc_src,
        "alarm_entity": r.get("alarm_entity") or None,
        "schedule": {
            "morning": SlotSchedule.from_dict(sched.get("morning"), DEFAULT_MORNING).to_dict(),
            "evening": SlotSchedule.from_dict(sched.get("evening"), DEFAULT_EVENING).to_dict(),
            "sleep_gap_min": int(_num(sched.get("sleep_gap_min"), 5, 90, DEFAULT_SLEEP_GAP_MIN)),
        },
        "targets": targets,
        "notify": {**DEFAULT_NOTIFY, **{k: v for k, v in (r.get("notify") or {}).items() if k in DEFAULT_NOTIFY}},
        "pause": r.get("pause") if isinstance(r.get("pause"), dict) else None,   # {"from": day, "until": day|None}
        "llm_child_allowed": _bool(r.get("llm_child_allowed"), False),
        "llm_consent": _bool(r.get("llm_consent"), False),
        "pin_session_min": int(_num(r.get("pin_session_min"), 1, 1440, DEFAULT_PIN_SESSION_MIN)),
        "cycle_child_allowed": _bool(r.get("cycle_child_allowed"), False),
        "created": r.get("created"),
    }
    if child and not p["cycle_child_allowed"]:
        p["modules"]["cycle"] = False
    if child:
        # Gewicht ist bei Kindern standardmäßig aus (nur ausdrücklich durch einen Admin an)
        if (r.get("modules") or {}).get("weight") is None:
            p["modules"]["weight"] = False
        if not p["llm_child_allowed"]:
            p["modules"]["llm"] = False
            p["llm_consent"] = False
    if not p["modules"].get("llm"):
        p["llm_consent"] = False
    return p


def normalize_settings(raw: dict | None) -> dict:
    s = copy.deepcopy(DEFAULT_SETTINGS)
    for k, v in (raw or {}).items():
        if k not in s:
            continue
        if k in ("day_boundary", "evening_from", "morning_until", "nightly"):
            if valid_hhmm(v):
                s[k] = v
        elif k in ("window_min", "remind_min", "request_cooldown_h"):
            s[k] = int(_num(v, 0 if k == "remind_min" else 5, 24 * 60 if k != "request_cooldown_h" else 24 * 14, s[k]))
        elif k == "load_level":
            s[k] = int(_num(v, 1, 3, DEFAULT_LOAD_LEVEL))
        elif k == "family_k":
            s[k] = int(_num(v, 2, 10, DEFAULT_FAMILY_K))
        elif k == "low_mood_days":
            s[k] = int(_num(v, 1, 14, DEFAULT_LOW_MOOD_DAYS))
        elif k == "low_mood_max":
            s[k] = int(_num(v, 1, 6, DEFAULT_LOW_MOOD_MAX))
        elif k == "late_entry":
            s[k] = v if v in ("none", "day_end", "3_days") else DEFAULT_LATE_ENTRY
        elif k == "weekly_report":
            s[k] = bool(v)
        elif k in ("workday_entity", "weather_entity", "daylight_entity"):
            s[k] = str(v) if v else None
        elif k == "admin_pin":
            s[k] = v if (v is None or isinstance(v, dict)) else None
        elif k == "admin_targets":
            s[k] = [t for t in (normalize_target(x) for x in (v or [])) if t]
        elif k == "llm" and isinstance(v, dict):
            s[k] = {**s[k], **{kk: vv for kk, vv in v.items() if kk in s[k]}}
            if s[k]["mode"] not in ("ai_task", "conversation"):
                s[k]["mode"] = "ai_task"
        elif k == "backup" and isinstance(v, dict):
            s[k] = {**s[k], **{kk: vv for kk, vv in v.items() if kk in s[k]}}
            if s[k]["auto"] not in ("off", "daily", "weekly"):
                s[k]["auto"] = "weekly"
            s[k]["keep"] = int(_num(s[k]["keep"], 1, 60, 8))
    return s


def migrate_config(old_version: int, data: dict) -> dict:
    """Upgrade older config formats. 1 is the first format (nothing to do yet)."""
    data = dict(data or {})
    data.setdefault("persons", {})
    data.setdefault("settings", {})
    data.setdefault("requests", {})
    return data


def migrate_person_store(old_version: int, data: dict) -> dict:
    data = dict(data or {})
    data.setdefault("days", {})
    data.setdefault("draft", {})
    return data


def migrate_model_store(old_version: int, data: dict) -> dict:
    return dict(data or {})


# ============================================================== Personen-Tresor
class Locked(Exception):
    """The text key is PIN-protected and the person has not unlocked a session."""


class PersonVault:
    """Encrypted per-person entries. Numbers are always readable (DEK), texts only with the TEK.

    Day layout (decrypted):
      numbers: {"m": {...}, "e": {...}, "sleep": {...}, "goal_res": {gid: res}}
      texts:   {"m": {...}, "e": {"good": [], "bad": [], "goals": [{"id","text"}], "journal": str, "period": {...}}}
    """

    def __init__(self, dek: bytes) -> None:
        self.dek = dek
        self.tek: bytes | None = None
        self.tek_gen = 0
        self.days: dict[str, dict] = {}          # entschlüsselte Zahlen (immer im RAM, klein)
        self._tok_n: dict[str, str] = {}
        self._tok_t: dict[str, tuple[str, int]] = {}
        self._dirty: set[str] = set()
        self.weights: dict[str, float] = {}      # Tag -> kg (Sensor + manuell)
        self._tok_w: str | None = None
        self._w_dirty = False
        self.drafts: dict[str, str] = {}         # slot -> Token (TEK)
        self.derived_tok: str | None = None      # Textanalyse-Cache (TEK)
        self.dump_tok: str | None = None         # Brain Dump (TEK)
        self.lost_texts = 0                      # Texte, die nach PIN-Reset nicht mehr lesbar sind

    # ---------------------------------------------------------- laden/speichern
    def load(self, data: dict) -> None:
        for day, rec in (data.get("days") or {}).items():
            tok = rec.get("n")
            if tok:
                try:
                    self.days[day] = decrypt_json(self.dek, tok)
                    self._tok_n[day] = tok
                except CryptoError:
                    continue
            if rec.get("t"):
                self._tok_t[day] = (rec["t"], int(rec.get("g", 0)))
        if data.get("w"):
            try:
                self.weights = {k: float(v) for k, v in decrypt_json(self.dek, data["w"]).items()}
                self._tok_w = data["w"]
            except CryptoError:
                self.weights = {}
        self.drafts = dict(data.get("draft") or {})
        self.derived_tok = data.get("derived")
        self.dump_tok = data.get("dump")

    def dump(self) -> dict:
        days = {}
        for day in set(self.days) | set(self._tok_t):
            rec: dict[str, Any] = {}
            if day in self.days:
                if day in self._dirty or day not in self._tok_n:
                    self._tok_n[day] = encrypt_json(self.dek, self.days[day])
                rec["n"] = self._tok_n[day]
            if day in self._tok_t:
                rec["t"], rec["g"] = self._tok_t[day]
            days[day] = rec
        self._dirty.clear()
        if self._w_dirty or (self.weights and not self._tok_w):
            self._tok_w = encrypt_json(self.dek, self.weights)
            self._w_dirty = False
        return {"days": days, "w": self._tok_w, "draft": self.drafts, "derived": self.derived_tok, "dump": self.dump_tok}

    # ---------------------------------------------------------- Zugriff
    @property
    def unlocked(self) -> bool:
        return self.tek is not None

    def numbers(self, day: str) -> dict:
        return self.days.get(day) or {}

    def set_numbers(self, day: str, numbers: dict) -> None:
        self.days[day] = numbers
        self._dirty.add(day)

    def texts(self, day: str) -> dict | None:
        tok = self._tok_t.get(day)
        if tok is None:
            return None
        if self.tek is None:
            raise Locked()
        if tok[1] != self.tek_gen:
            return None                          # nach PIN-Reset verloren
        try:
            return decrypt_json(self.tek, tok[0])
        except CryptoError:
            return None

    def set_texts(self, day: str, texts: dict | None) -> None:
        if texts is None or not any(texts.values()):
            self._tok_t.pop(day, None)
            return
        if self.tek is None:
            raise Locked()
        self._tok_t[day] = (encrypt_json(self.tek, texts), self.tek_gen)

    def has_texts(self, day: str) -> bool:
        tok = self._tok_t.get(day)
        return tok is not None and tok[1] == self.tek_gen

    def delete_day(self, day: str) -> None:
        self.days.pop(day, None)
        self._tok_n.pop(day, None)
        self._tok_t.pop(day, None)

    def set_weight(self, day: str, kg: float | None) -> None:
        if kg is None:
            self.weights.pop(day, None)
        else:
            self.weights[day] = round(float(kg), 2)
        self._w_dirty = True

    def all_texts(self) -> dict[str, dict]:
        """All readable texts (requires the TEK). Used for search/analysis, not kept."""
        if self.tek is None:
            raise Locked()
        out = {}
        for day in self._tok_t:
            t = self.texts(day)
            if t:
                out[day] = t
        return out

    def drop_unreadable_texts(self) -> int:
        """After an admin PIN reset: remove texts encrypted with the old key generation."""
        old = [d for d, (_, g) in self._tok_t.items() if g != self.tek_gen]
        for d in old:
            self._tok_t.pop(d, None)
        self.drafts = {}
        self.derived_tok = None
        self.dump_tok = None                    # Brain Dump war mit dem alten Textschlüssel verschlüsselt
        return len(old)

    def rewrap_texts(self, old_tek: bytes, new_tek: bytes) -> None:
        """Key rotation for texts (not needed for PIN changes – the TEK stays the same)."""
        for day, (tok, g) in list(self._tok_t.items()):
            try:
                obj = decrypt_json(old_tek, tok)
            except CryptoError:
                continue
            self._tok_t[day] = (encrypt_json(new_tek, obj), g)

    # Entwürfe (verschlüsselt, serverseitig – überleben das Schließen der App)
    def set_draft(self, slot: str, draft: dict | None) -> None:
        if draft is None:
            self.drafts.pop(slot, None)
            return
        if self.tek is None:
            raise Locked()
        self.drafts[slot] = encrypt_json(self.tek, draft)

    def get_draft(self, slot: str) -> dict | None:
        tok = self.drafts.get(slot)
        if not tok:
            return None
        if self.tek is None:
            return None
        try:
            return decrypt_json(self.tek, tok)
        except CryptoError:
            return None

    def get_dump(self) -> list[dict]:
        """Brain dump items (requires the text key)."""
        if self.tek is None:
            raise Locked()
        if not self.dump_tok:
            return []
        try:
            from .logic.braindump import normalize
            return normalize(decrypt_json(self.tek, self.dump_tok))
        except CryptoError:
            return []

    def set_dump(self, items: list[dict]) -> None:
        if self.tek is None:
            raise Locked()
        self.dump_tok = encrypt_json(self.tek, items) if items else None

    def set_derived(self, obj: dict) -> None:
        if self.tek is not None:
            self.derived_tok = encrypt_json(self.tek, obj)

    def get_derived(self) -> dict | None:
        if not self.derived_tok or self.tek is None:
            return None
        try:
            return decrypt_json(self.tek, self.derived_tok)
        except CryptoError:
            return None


def encrypt_model(dek: bytes, model: dict) -> dict:
    return {"blob": encrypt_json(dek, model)}


def decrypt_model(dek: bytes, data: dict | None) -> dict:
    if not data or not data.get("blob"):
        return {}
    try:
        return decrypt_json(dek, data["blob"])
    except CryptoError:
        return {}
