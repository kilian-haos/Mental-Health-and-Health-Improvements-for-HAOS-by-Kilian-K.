"""Runtime: connects stores, persons, sensors, schedule, notifications, entities and the card.

One instance per config entry (single entry), kept in `entry.runtime_data`.
"""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import archive
from .const import (
    CONFIG_STORE_VERSION, DOMAIN, KEY_STORE_VERSION, MODEL_STORE_VERSION, MODULES, PANEL_URL_PATH,
    PERSON_STORE_VERSION, PIN_LOCK_S, PIN_MAX_FAILS, PUSH_INTERVAL, STORE_CONFIG, STORE_KEYS, STORE_MODEL,
    STORE_PERSON, VERSION, signal_entities, signal_hub, signal_person,
)
from .i18n import system_lang, tr
from .logic import permissions as PM
from .logic import weight as WT
from .logic.birthday import family_next, family_today
from .logic.checkin import EVENING, MORNING, TimeRules, manual_allowed
from .logic.crypto import CryptoError, Keyring, hash_secret, token, verify_secret
from .logic.daymath import local_at, minutes_of_day, parse_day, parse_hhmm
from .logic.schedule import SlotSchedule, entity_trigger, fixed_time, sleep_trigger
from .logic.sleep.score import recommended_range
from .logic.sleep.sources import (
    KIND_AUX, KIND_BINARY, KIND_ENUM, KIND_NUMERIC, KIND_PROB, Source, binary_value, enum_value, numeric_value,
    prob_value,
)
from .logic.analysis import health_score as HS
from .notifier import LATER_RE, Notifier, parse_tag, slugify
from .person import Clock, Person, analysis, weight_card
from .storage import (
    Locked, PersonVault, decrypt_model, encrypt_model, migrate_config, migrate_model_store, migrate_person_store,
    new_id, normalize_person, normalize_settings,
)

_LOGGER = logging.getLogger(__name__)
LOAD_STEP_MIN = {1: 5, 2: 2, 3: 1}       # Live-Schlaferkennung alle n Minuten je Rechenlast-Stufe
SAVE_DELAY = 15
MODEL_SAVE_DELAY = 300


class _MigratingStore(Store):
    """Store with a migration function for older formats."""

    def __init__(self, hass: HomeAssistant, version: int, key: str, migrate: Callable[[int, dict], dict]) -> None:
        super().__init__(hass, version, key, private=True, atomic_writes=True)
        self._migrate = migrate

    async def _async_migrate_func(self, old_major_version: int, old_minor_version: int, old_data: dict) -> dict:
        return self._migrate(old_major_version, old_data)


class MHRuntime:
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.lang = system_lang(hass)
        self.cfg_store = _MigratingStore(hass, CONFIG_STORE_VERSION, STORE_CONFIG, migrate_config)
        self.key_store = Store(hass, KEY_STORE_VERSION, STORE_KEYS, private=True, atomic_writes=True)
        self.person_stores: dict[str, Store] = {}
        self.model_stores: dict[str, Store] = {}
        self.config: dict[str, Any] = {"persons": {}, "settings": normalize_settings({}), "requests": {}}
        self.keyring = Keyring()
        self.persons: dict[str, Person] = {}
        self.status: dict[str, dict[str, Any]] = {}
        self.values: dict[str, dict] = {}
        self.hub_values: dict[str, Any] = {}
        self.sessions: dict[str, dict] = {}
        self.pin_fails: dict[str, dict] = {}
        self.subscribers: dict[int, tuple[str | None, Callable[[dict], None]]] = {}
        self._sub_id = 0
        self._unsubs: list[Callable[[], None]] = []
        self._src_unsub: Callable[[], None] | None = None
        self._entity_map: dict[str, list[tuple[str, str]]] = {}
        self._push_pending: set[str] = set()
        self._push_handle: Callable[[], None] | None = None
        self._last_tick_min = 0
        self._weekly_sent: date | None = None
        self._paused_writes = False
        self.backup_info: dict[str, Any] = {}
        self.notifier = Notifier(hass, self._platform_of, self._notify_error)
        self.llm_state: dict[str, Any] = {}

    # ================================================================ Grundlagen
    def t(self, key: str, **kw: Any) -> str:
        return tr(self.lang, key, **kw)

    @property
    def settings(self) -> dict:
        return self.config["settings"]

    def clock(self) -> Clock:
        return Clock(dt_util.now(), self.settings["day_boundary"])

    def tod_of(self, minute: int) -> float:
        return minutes_of_day(datetime.fromtimestamp(minute * 60, tz=dt_util.get_default_time_zone()))

    @property
    def hub_identifier(self) -> tuple[str, str]:
        return (DOMAIN, f"{self.entry.entry_id}_hub")

    def person_identifier(self, pid: str) -> tuple[str, str]:
        return (DOMAIN, f"{self.entry.entry_id}_{pid}")

    # ================================================================ Setup
    async def async_setup(self) -> None:
        raw = await self.cfg_store.async_load() or {}
        raw = migrate_config(CONFIG_STORE_VERSION, raw)
        self.config = {
            "persons": {pid: normalize_person(p, pid) for pid, p in (raw.get("persons") or {}).items()},
            "settings": normalize_settings(raw.get("settings")),
            "requests": dict(raw.get("requests") or {}),
        }
        self.backup_info = dict(raw.get("backup_info") or {})
        self.keyring = Keyring(await self.key_store.async_load())
        for pid in self.config["persons"]:
            self.keyring.ensure_person(pid)
        await self.key_store.async_save(self.keyring.to_dict())
        for pid, profile in self.config["persons"].items():
            await self._load_person(pid, profile)
        self.ensure_hub_device()
        self._track_sources()
        self._unsubs.append(async_track_time_interval(self.hass, self._tick, timedelta(seconds=60)))
        nh = parse_hhmm(self.settings["nightly"], "03:30")
        self._unsubs.append(async_track_time_change(self.hass, self._nightly, hour=nh.hour, minute=nh.minute, second=0))
        self._unsubs.append(self.hass.bus.async_listen("mobile_app_notification_cleared", self._on_cleared))
        self._unsubs.append(self.hass.bus.async_listen("mobile_app_notification_action", self._on_action))
        self._unsubs.append(self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, self._on_stop))
        self._restore_status()
        self.recompute_all()

    async def _load_person(self, pid: str, profile: dict) -> None:
        ps = _MigratingStore(self.hass, PERSON_STORE_VERSION, STORE_PERSON.format(pid=pid), migrate_person_store)
        ms = _MigratingStore(self.hass, MODEL_STORE_VERSION, STORE_MODEL.format(pid=pid), migrate_model_store)
        self.person_stores[pid] = ps
        self.model_stores[pid] = ms
        vault = PersonVault(self.keyring.dek(pid))
        vault.tek_gen = self.keyring.tek_gen(pid)
        data = await ps.async_load() or {}
        vault.load(migrate_person_store(PERSON_STORE_VERSION, data))
        try:
            vault.tek = self.keyring.tek_without_pin(pid)
        except CryptoError:
            vault.tek = None
        model = decrypt_model(vault.dek, await ms.async_load())
        self.persons[pid] = Person(profile, vault, model)
        self.status.setdefault(pid, {})

    async def async_unload(self) -> None:
        for u in self._unsubs:
            u()
        self._unsubs.clear()
        if self._src_unsub:
            self._src_unsub()
            self._src_unsub = None
        if self._push_handle:
            self._push_handle()
        await self.async_save_all()

    async def _on_stop(self, _event: Event) -> None:
        await self.async_save_all()

    # ================================================================ Speichern
    def _config_data(self) -> dict:
        return {"persons": self.config["persons"], "settings": self.config["settings"],
                "requests": self.config["requests"], "backup_info": self.backup_info}

    def _model_data(self, p: Person) -> dict:
        return {
            "sleep": p.sleep.to_dict(), "mood": p.mood.to_dict(), "gap": p.gap.to_dict(), "optimum": p.optimum,
            "series": {k: v.to_dict() for k, v in p.series.items()}, "temps": p.temps,
            "weight_required_served": p.weight_required_served, "since": p.tracking_since,
        }

    def save_config(self) -> None:
        if not self._paused_writes:
            self.cfg_store.async_delay_save(self._config_data, SAVE_DELAY)

    def save_person(self, pid: str, model: bool = False) -> None:
        if self._paused_writes or pid not in self.persons:
            return
        p = self.persons[pid]
        self.person_stores[pid].async_delay_save(p.vault.dump, SAVE_DELAY)
        if model:
            self.model_stores[pid].async_delay_save(lambda: encrypt_model(p.vault.dek, self._model_data(p)), SAVE_DELAY)

    async def async_save_all(self) -> None:
        await self.cfg_store.async_save(self._config_data())
        await self.key_store.async_save(self.keyring.to_dict())
        for pid, p in self.persons.items():
            await self.person_stores[pid].async_save(p.vault.dump())
            await self.model_stores[pid].async_save(encrypt_model(p.vault.dek, self._model_data(p)))

    async def async_pause_writes(self) -> None:
        """Backup platform: flush everything, then pause writes until resumed."""
        await self.async_save_all()
        self._paused_writes = True

    def resume_writes(self) -> None:
        self._paused_writes = False
        self.save_config()
        for pid in self.persons:
            self.save_person(pid, model=True)

    # ================================================================ Personen verwalten
    def person_for_user(self, user_id: str | None) -> Person | None:
        if not user_id:
            return None
        for p in self.persons.values():
            if p.user_id == user_id:
                return p
        return None

    def viewer(self, user: Any, admin_tok: str | None = None) -> PM.Viewer:
        """Viewer for the permission matrix. A non-admin with an admin-PIN session counts as admin."""
        uid = getattr(user, "id", None)
        return PM.Viewer(uid, bool(getattr(user, "is_admin", False)) or self.admin_elevated(uid, admin_tok))

    def ha_persons(self) -> list[dict]:
        """All person.* with linked users (for the admin's person picker)."""
        out = []
        taken = {p.profile["person_entity"] for p in self.persons.values()}
        for st in self.hass.states.async_all("person"):
            uid = st.attributes.get("user_id")
            out.append({"entity_id": st.entity_id, "name": st.attributes.get("friendly_name") or st.entity_id,
                        "user_id": uid, "picture": st.attributes.get("entity_picture"), "taken": st.entity_id in taken,
                        "eligible": bool(uid)})
        return sorted(out, key=lambda x: x["name"])

    async def async_create_person(self, person_entity: str, data: dict | None = None) -> Person:
        st = self.hass.states.get(person_entity)
        if st is None or not st.attributes.get("user_id"):
            raise ValueError("person_without_user")
        if any(p.profile["person_entity"] == person_entity for p in self.persons.values()):
            raise ValueError("already_set_up")
        pid = new_id()
        today = self.clock().today
        profile = normalize_person({**(data or {}), "person_entity": person_entity, "user_id": st.attributes["user_id"],
                                    "name": (data or {}).get("name") or st.attributes.get("friendly_name") or "",
                                    "created": today.isoformat()}, pid)
        self.config["persons"][pid] = profile
        self.config["requests"].pop(profile["user_id"], None)
        self.keyring.ensure_person(pid)
        await self.key_store.async_save(self.keyring.to_dict())
        await self._load_person(pid, profile)
        self.persons[pid].tracking_since = today.isoformat()
        self.save_config()
        self.save_person(pid, model=True)
        self._after_structure_change()
        return self.persons[pid]

    async def async_delete_person(self, pid: str) -> None:
        if pid not in self.persons:
            raise ValueError("not_found")
        p = self.persons.pop(pid)
        self.config["persons"].pop(pid, None)
        self.status.pop(pid, None)
        self.values.pop(pid, None)
        await self.notifier.clear(pid, MORNING, p.profile["targets"])
        await self.notifier.clear(pid, EVENING, p.profile["targets"])
        await self.person_stores.pop(pid).async_remove()
        await self.model_stores.pop(pid).async_remove()
        self.keyring.remove_person(pid)
        await self.key_store.async_save(self.keyring.to_dict())
        self.save_config()
        self._after_structure_change()

    def update_profile(self, pid: str, changes: dict, viewer: PM.Viewer) -> dict:
        """Apply profile changes the viewer is allowed to make. Returns {key: reason} for refused keys."""
        p = self.persons[pid]
        rights = p.rights
        prof = dict(p.profile)
        refused: dict[str, str] = {}
        groups = {
            PM.MANAGE_PERSONS: ("child", "can_edit_own", "llm_child_allowed", "cycle_child_allowed", "person_entity"),
            PM.PROFILE_EDIT: ("name", "birthdate", "sex", "height_cm", "sleep_sources", "cycle_sources", "alarm_entity",
                              "weight_live", "weight_entity"),
            PM.TARGET_WEIGHT_EDIT: ("target_weight",),
            PM.WEIGHT_EDIT: ("weight_kg",),
            PM.MODULES_EDIT: ("modules",),
            PM.SCHEDULE_EDIT: ("schedule", "targets", "notify"),
            PM.PAUSE: ("pause",),
            PM.OWN_PIN: ("pin_session_min",),
            PM.LLM_CONSENT: ("llm_consent",),
        }
        for action, keys in groups.items():
            for k in keys:
                if k not in changes:
                    continue
                ok, why = PM.check(viewer, action, rights)
                if k == "llm_consent" and changes[k] is False and viewer.user_id == p.user_id:
                    ok = True        # Widerruf geht immer
                if not ok:
                    refused[k] = why
                    continue
                if k == "modules":
                    prof["modules"] = {**prof["modules"], **{m: bool(v) for m, v in changes[k].items() if m in MODULES}}
                elif k == "schedule":
                    prof["schedule"] = {**prof["schedule"], **(changes[k] or {})}
                elif k == "notify":
                    prof["notify"] = {**prof["notify"], **(changes[k] or {})}
                else:
                    prof[k] = changes[k]
        if "child" in changes and changes["child"] and "can_edit_own" not in changes:
            prof["can_edit_own"] = False
        new = normalize_person(prof, pid)
        # Zielgewicht auf den gesunden Bereich begrenzen
        if new.get("target_weight"):
            new["target_weight"] = WT.clamp_target(new["target_weight"], new.get("height_cm"), p.age(self.clock().today))
        sources_changed = new["sleep_sources"] != p.profile["sleep_sources"] or new.get("weight_entity") != p.profile.get(
            "weight_entity") or new.get("cycle_sources") != p.profile.get("cycle_sources") or new.get(
            "alarm_entity") != p.profile.get("alarm_entity")
        p.profile.clear()
        p.profile.update(new)
        self.config["persons"][pid] = p.profile
        p.gap.base = new["schedule"]["sleep_gap_min"]
        self.save_config()
        if sources_changed:
            self._track_sources()
            self.hass.async_create_task(self.async_cold_start(pid))
        self._after_structure_change()
        return refused

    def _after_structure_change(self) -> None:
        self.recompute_all()
        async_dispatcher_send(self.hass, signal_entities(self.entry.entry_id))
        self.check_repairs()
        self.broadcast_all()

    # ================================================================ Sitzungen / PINs
    def _fail_key(self, kind: str, who: str) -> str:
        return f"{kind}:{who}"

    def _locked_until(self, key: str) -> float:
        f = self.pin_fails.get(key)
        return f["until"] if f and f.get("until", 0) > time.time() else 0.0

    def _register_fail(self, key: str) -> dict:
        f = self.pin_fails.setdefault(key, {"n": 0, "until": 0})
        f["n"] += 1
        if f["n"] >= PIN_MAX_FAILS:
            f["until"] = time.time() + PIN_LOCK_S
            f["n"] = 0
        return {"left": PIN_MAX_FAILS - f["n"] if not f["until"] or f["until"] < time.time() else 0,
                "locked_until": f["until"] if f["until"] > time.time() else None}

    async def async_unlock_person(self, user_id: str, pin: str) -> dict:
        p = self.person_for_user(user_id)
        if p is None:
            raise ValueError("not_set_up")
        key = self._fail_key("person", p.pid)
        if self._locked_until(key):
            return {"ok": False, "locked_until": self._locked_until(key)}
        if not self.keyring.has_pin(p.pid):
            return {"ok": True, "token": None}
        try:
            tek = await self.hass.async_add_executor_job(self.keyring.tek_with_pin, p.pid, pin)
        except CryptoError:
            return {"ok": False, **self._register_fail(key)}
        self.pin_fails.pop(key, None)
        p.vault.tek = tek
        tok = token()
        self.sessions[tok] = {"kind": "person", "pid": p.pid, "user_id": user_id,
                              "exp": time.time() + 60 * p.profile["pin_session_min"]}
        self.hass.async_create_task(self._catch_up_analysis(p.pid))
        return {"ok": True, "token": tok, "exp": self.sessions[tok]["exp"]}

    def person_session_ok(self, p: Person, user_id: str | None, tok: str | None) -> bool:
        if not self.keyring.has_pin(p.pid):
            return True
        s = self.sessions.get(tok or "")
        return bool(s and s["kind"] == "person" and s["pid"] == p.pid and s["user_id"] == user_id
                    and s["exp"] > time.time() and p.vault.tek is not None)

    def lock_person(self, pid: str) -> None:
        for k in [k for k, s in self.sessions.items() if s.get("pid") == pid]:
            self.sessions.pop(k, None)
        if self.keyring.has_pin(pid) and pid in self.persons:
            self.persons[pid].vault.tek = None

    def _expire_sessions(self) -> None:
        now = time.time()
        for k in [k for k, s in self.sessions.items() if s["exp"] <= now]:
            s = self.sessions.pop(k)
            if s["kind"] == "person" and not any(x.get("pid") == s["pid"] for x in self.sessions.values()):
                if self.keyring.has_pin(s["pid"]) and s["pid"] in self.persons:
                    self.persons[s["pid"]].vault.tek = None

    async def async_set_pin(self, user_id: str, old_pin: str | None, new_pin: str | None) -> dict:
        p = self.person_for_user(user_id)
        if p is None:
            raise ValueError("not_set_up")
        if new_pin is not None and (len(new_pin) != 4 or not new_pin.isdigit()):
            raise ValueError("pin_format")
        if self.keyring.has_pin(p.pid):
            key = self._fail_key("person", p.pid)
            if self._locked_until(key):
                return {"ok": False, "locked_until": self._locked_until(key)}
            try:
                tek = await self.hass.async_add_executor_job(self.keyring.tek_with_pin, p.pid, old_pin or "")
            except CryptoError:
                return {"ok": False, **self._register_fail(key)}
        else:
            tek = self.keyring.tek_without_pin(p.pid)
        if new_pin:
            await self.hass.async_add_executor_job(self.keyring.set_pin, p.pid, tek, new_pin)
        else:
            self.keyring.remove_pin(p.pid, tek)
        p.vault.tek = tek
        await self.key_store.async_save(self.keyring.to_dict())
        res: dict[str, Any] = {"ok": True, "has_pin": bool(new_pin)}
        if new_pin:
            tok = token()
            self.sessions[tok] = {"kind": "person", "pid": p.pid, "user_id": user_id,
                                  "exp": time.time() + 60 * p.profile["pin_session_min"]}
            res["token"] = tok
        return res

    async def async_reset_pin(self, pid: str) -> dict:
        """Admin: reset a forgotten PIN. Protected texts are lost for good (numbers stay)."""
        p = self.persons[pid]
        if not self.keyring.has_pin(pid):
            return {"ok": True, "lost": 0}
        self.lock_person(pid)
        self.keyring.reset_pin(pid)
        p.vault.tek_gen = self.keyring.tek_gen(pid)
        p.vault.tek = self.keyring.tek_without_pin(pid)
        lost = p.vault.drop_unreadable_texts()
        await self.key_store.async_save(self.keyring.to_dict())
        self.save_person(pid)
        return {"ok": True, "lost": lost}

    def admin_pin_set(self) -> bool:
        return bool(self.settings.get("admin_pin"))

    async def async_admin_unlock(self, user_id: str, pin: str) -> dict:
        key = self._fail_key("admin", user_id)
        if self._locked_until(key):
            return {"ok": False, "locked_until": self._locked_until(key)}
        ok = await self.hass.async_add_executor_job(verify_secret, pin, self.settings.get("admin_pin"))
        if not ok:
            return {"ok": False, **self._register_fail(key)}
        self.pin_fails.pop(key, None)
        tok = token()
        self.sessions[tok] = {"kind": "admin", "user_id": user_id, "exp": time.time() + 15 * 60}
        return {"ok": True, "token": tok, "exp": self.sessions[tok]["exp"]}

    def admin_session_ok(self, user_id: str | None, tok: str | None) -> bool:
        if not self.admin_pin_set():
            return True
        return self._admin_session(user_id, tok) is not None

    def _admin_session(self, user_id: str | None, tok: str | None) -> dict | None:
        s = self.sessions.get(tok or "")
        if s and s["kind"] == "admin" and s["user_id"] == user_id and s["exp"] > time.time():
            return s
        return None

    def admin_elevated(self, user_id: str | None, tok: str | None) -> bool:
        """A non-admin user who entered the admin PIN – admin rights for this one session only."""
        s = self._admin_session(user_id, tok)
        return bool(s and s.get("elevated"))

    def admin_access(self, user: Any, tok: str | None) -> bool:
        """May this user use the admin area right now?"""
        uid = getattr(user, "id", None)
        if getattr(user, "is_admin", False):
            return not self.admin_pin_set() or self._admin_session(uid, tok) is not None
        return self.admin_pin_set() and self.admin_elevated(uid, tok)

    async def async_unlock(self, user: Any, pin: str) -> dict:
        """One PIN field for everything.

        * Personal PIN -> personal session (texts readable). An HA admin additionally gets the
          admin area (no second PIN needed).
        * Admin PIN entered instead -> admin rights for this session only (also for non-admin
          users), with an "admin" hint in the UI. It never decrypts anyone's texts.
        """
        uid = getattr(user, "id", None)
        is_admin = bool(getattr(user, "is_admin", False))
        key = self._fail_key("user", uid or "")
        if self._locked_until(key):
            return {"ok": False, "locked_until": self._locked_until(key)}
        p = self.person_for_user(uid)
        res: dict[str, Any] = {"ok": False}
        if p is not None and self.keyring.has_pin(p.pid):
            try:
                tek = await self.hass.async_add_executor_job(self.keyring.tek_with_pin, p.pid, pin)
            except CryptoError:
                tek = None
            if tek is not None:
                p.vault.tek = tek
                exp = time.time() + 60 * p.profile["pin_session_min"]
                tok = token()
                self.sessions[tok] = {"kind": "person", "pid": p.pid, "user_id": uid, "exp": exp}
                res = {"ok": True, "token": tok, "exp": exp, "elevated": False}
                if is_admin and self.admin_pin_set():
                    atok = token()
                    self.sessions[atok] = {"kind": "admin", "user_id": uid, "exp": exp, "elevated": False, "via": "person"}
                    res["admin_token"] = atok
                self.hass.async_create_task(self._catch_up_analysis(p.pid))
        if not res["ok"] and self.admin_pin_set():
            if await self.hass.async_add_executor_job(verify_secret, pin, self.settings.get("admin_pin")):
                atok = token()
                exp = time.time() + 15 * 60
                self.sessions[atok] = {"kind": "admin", "user_id": uid, "exp": exp, "elevated": not is_admin}
                res = {"ok": True, "admin_token": atok, "exp": exp, "elevated": not is_admin}
        if res["ok"]:
            self.pin_fails.pop(key, None)
            return res
        return {"ok": False, **self._register_fail(key)}

    def lock_user(self, user_id: str | None) -> None:
        """Lock now: end all sessions of this user (personal and admin)."""
        for k in [k for k, s in self.sessions.items() if s.get("user_id") == user_id]:
            self.sessions.pop(k, None)
        p = self.person_for_user(user_id)
        if p is not None and self.keyring.has_pin(p.pid):
            p.vault.tek = None

    async def async_set_admin_pin(self, pin: str | None) -> None:
        if pin is not None and (len(pin) != 4 or not pin.isdigit()):
            raise ValueError("pin_format")
        self.settings["admin_pin"] = (await self.hass.async_add_executor_job(hash_secret, pin)) if pin else None
        for k in [k for k, s in self.sessions.items() if s["kind"] == "admin"]:
            self.sessions.pop(k, None)
        self.save_config()

    # ================================================================ Sensor-Quellen
    def _track_sources(self) -> None:
        if self._src_unsub:
            self._src_unsub()
            self._src_unsub = None
        emap: dict[str, list[tuple[str, str]]] = {}
        for pid, p in self.persons.items():
            for s in p.sources:
                emap.setdefault(s.entity, []).append((pid, "sleep:" + s.id))
            if p.profile.get("weight_entity") and p.profile.get("weight_live"):
                emap.setdefault(p.profile["weight_entity"], []).append((pid, "weight"))
            for s in p.profile.get("cycle_sources") or []:
                emap.setdefault(s["entity"], []).append((pid, "temp"))
        self._entity_map = emap
        if emap:
            self._src_unsub = async_track_state_change_event(self.hass, list(emap), self._on_source)
        now_min = time.time() / 60.0
        for eid in emap:
            st = self.hass.states.get(eid)
            if st is not None:
                self._ingest(eid, st.state, st.attributes, now_min)

    @callback
    def _on_source(self, event: Event) -> None:
        new = event.data.get("new_state")
        if new is None:
            return
        ts = new.last_updated.timestamp() / 60.0 if getattr(new, "last_updated", None) else time.time() / 60.0
        self._ingest(event.data["entity_id"], new.state, new.attributes, ts)

    def _ingest(self, entity_id: str, state: Any, attrs: Any, minute_f: float) -> None:
        for pid, what in self._entity_map.get(entity_id, []):
            p = self.persons.get(pid)
            if p is None:
                continue
            if what.startswith("sleep:"):
                sid = what[6:]
                src = next((s for s in p.sources if s.id == sid), None)
                if src is None:
                    continue
                p.feed_sample(sid, minute_f, source_value(src, state))
            elif what == "weight":
                self._ingest_weight(p, state, attrs)
            elif what == "temp":
                v = numeric_value(state)
                if v == v and 34.0 <= v <= 39.5:
                    day = self.clock().today.isoformat()
                    if day not in p.temps:          # erster Wert am Morgen = Basaltemperatur
                        p.temps[day] = round(v, 2)
                        p.temps = dict(sorted(p.temps.items())[-400:])
                        self.save_person(pid, model=True)

    def _ingest_weight(self, p: Person, state: Any, attrs: Any) -> None:
        v = numeric_value(state)
        if v != v:
            return
        unit = (attrs or {}).get("unit_of_measurement")
        kg = WT.to_kg(v, unit)
        prev = None
        if p.vault.weights:
            prev = p.vault.weights[sorted(p.vault.weights)[-1]]
        if not WT.plausible(kg, prev):
            _LOGGER.debug("Mental Health: implausible weight value ignored")
            return
        day = self.clock().today.isoformat()
        p.vault.set_weight(day, kg)
        self.save_person(p.pid)
        self.mark_changed(p.pid)

    async def async_cold_start(self, pid: str, days: int = 7) -> None:
        """Read recorder history for new sources (level models, 36 h buffer). Runs in the executor."""
        p = self.persons.get(pid)
        if p is None or not p.sources:
            return
        try:
            from homeassistant.components.recorder import get_instance, history
        except ImportError:
            return
        end = dt_util.utcnow()
        start = end - timedelta(days=days)
        for src in p.sources:
            if src.kind != KIND_NUMERIC and src.id in p.series:
                continue
            try:
                states = await get_instance(self.hass).async_add_executor_job(
                    history.state_changes_during_period, self.hass, start, end, src.entity, True)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Mental Health: history for %s unavailable (%s)", src.entity, type(err).__name__)
                continue
            rows = states.get(src.entity.lower()) or []
            await self.hass.async_add_executor_job(self._replay, p, src, rows)
        self.save_person(pid, model=True)

    def _replay(self, p: Person, src: Source, rows: list) -> None:
        from .logic.sleep.pipeline import level_model_for
        lm = level_model_for(src, p.sleep.levels) if src.kind == KIND_NUMERIC else None
        prev_t = None
        prev_v = None
        for st in rows:
            m = st.last_updated.timestamp() / 60.0
            v = source_value(src, st.state)
            if lm is not None and prev_v is not None and prev_v == prev_v and prev_t is not None:
                dur = max(0.0, min(600.0, m - prev_t))
                if dur > 0:
                    tod = self.tod_of(int(prev_t))
                    lm.add(prev_v, dur, 600 <= tod < 1080)
            prev_t, prev_v = m, v
            if m >= time.time() / 60.0 - 36 * 60:
                p.feed_sample(src.id, m, v)
        if lm is not None:
            lm.fit()

    async def async_source_preview(self, pid: str, raw_source: dict, hours: int = 48) -> dict:
        """Wizard: recorder history (5-min buckets) + the model's detection on top. No content."""
        p = self.persons[pid]
        src = Source.from_dict({**raw_source, "id": raw_source.get("id") or "preview"})
        try:
            from homeassistant.components.recorder import get_instance, history
            end = dt_util.utcnow()
            start = end - timedelta(hours=hours)
            states = await get_instance(self.hass).async_add_executor_job(
                history.state_changes_during_period, self.hass, start, end, src.entity, True)
            rows = states.get(src.entity.lower()) or []
        except Exception:  # noqa: BLE001
            rows = []
        from .logic.sleep.detector import SleepModel
        from .logic.sleep.features import MinuteSeries
        from .logic.sleep.pipeline import build_window, level_model_for
        series = MinuteSeries(hours * 60 + 60)
        models = {k: v for k, v in p.sleep.levels.items()}
        lm = level_model_for(src, models) if src.kind == KIND_NUMERIC else None
        raw_vals: list[tuple[float, float]] = []
        for st in rows:
            m = st.last_updated.timestamp() / 60.0
            v = source_value(src, st.state)
            series.add(m, v)
            raw_vals.append((m, numeric_value(st.state)))
            if lm is not None and v == v:
                lm.add(v, 5.0, 600 <= self.tod_of(int(m)) < 1080)
        if lm is not None:
            lm.fit()
        end_m = int(time.time() // 60)
        start_m = end_m - hours * 60
        series.roll(end_m)
        win = build_window(start_m, [self.tod_of(m) for m in range(start_m, end_m)], [src],
                           {src.id: series.window(start_m, end_m)}, models)
        model = p.sleep if p.sources else SleepModel()
        res = model.detect(win)
        means, _ = series.window(start_m, end_m)
        buckets = []
        for i in range(0, len(means), 5):
            chunk = [v for v in means[i:i + 5] if v == v]
            buckets.append(round(sum(chunk) / len(chunk), 3) if chunk else None)
        return {
            "start": start_m, "step": 5, "values": buckets,
            "raw": [round(v, 3) if v == v else None for _, v in raw_vals[-2000:]] if src.kind == KIND_NUMERIC else None,
            "sleep": res.sleep.to_dict() if res.sleep else None, "naps": [n.to_dict() for n in res.naps],
            "in_bed": [s.to_dict() for s in res.in_bed][:80], "p_sleep": [round(x, 2) for x in res.p_sleep[::5]],
            "level": lm.summary() if lm else None, "states": sorted({str(st.state) for st in rows})[:40],
        }

    # ================================================================ Takt (jede Minute)
    async def _tick(self, _now: datetime | None = None) -> None:
        clock = self.clock()
        minute = clock.minute
        self._expire_sessions()
        step = LOAD_STEP_MIN.get(int(self.settings.get("load_level", 2)), 2)
        for pid, p in list(self.persons.items()):
            if p.sources and minute - p.live_at >= step:
                p.roll_series(minute, self.tod_of)
                await self.hass.async_add_executor_job(p.detect_live, clock, self.tod_of, self._other_in_bed(pid))
                self._finalize_night(p, clock)
                self.mark_changed(pid)
            await self._schedule_person(p, clock)
        if minute // 5 != self._last_tick_min // 5:
            self.recompute_all()
        if clock.now.weekday() == 6 and clock.now.hour == 19 and self._weekly_sent != clock.today:
            self._weekly_sent = clock.today
            await self._weekly(clock)
        self._last_tick_min = minute

    def _other_in_bed(self, pid: str) -> Callable[[str], list[float] | None]:
        def fn(source_id: str) -> list[float] | None:
            p = self.persons[pid]
            src = next((s for s in p.sources if s.id == source_id), None)
            if src is None:
                return None
            for other_pid in src.shared_with:
                o = self.persons.get(other_pid)
                if o and o.live and o.live.p_sleep:
                    return list(o.live.p_sleep)
            return None
        return fn

    def _finalize_night(self, p: Person, clock: Clock) -> None:
        """After getting up: store the detected night for today (unconfirmed)."""
        r = p.live
        if r is None or r.sleep is None or r.state_now == "asleep":
            return
        if clock.minute - r.sleep.end < 20:
            return
        stored = p.day_numbers(clock.today).get("sleep")
        if stored and stored.get("src") in ("confirmed", "corrected"):
            return
        night = p.night_for_morning(clock)
        if night and night.get("src") == "auto" and night != stored:
            alarm = self._alarm_tod(p)
            if alarm is not None:
                night["alarm_tod"] = alarm
            p.store_night(clock, night)
            if not stored:
                p.sleep.night_done(r, clock.today.isoformat())
                if r.confidence >= 0.8:
                    win = p.window(r.sleep.start - 360, clock.minute, self.tod_of)
                    p.sleep.learn(win, r.sleep.start, r.sleep.end, 0.2)
            self.save_person(p.pid, model=True)

    def _alarm_tod(self, p: Person) -> float | None:
        ent = p.profile.get("alarm_entity")
        if not ent:
            return None
        st = self.hass.states.get(ent)
        if st is None:
            return None
        dt = dt_util.parse_datetime(str(st.state))
        if dt is None:
            return None
        return minutes_of_day(dt_util.as_local(dt))

    # ================================================================ Zeitplan / Fenster
    def _status(self, pid: str) -> dict:
        return self.status.setdefault(pid, {})

    def _restore_status(self) -> None:
        clock = self.clock()
        for pid, p in self.persons.items():
            n = p.day_numbers(clock.today)
            st = n.get("status") or {}
            for slot in (MORNING, EVENING):
                if st.get(slot) == "open" and st.get(slot + "_until"):
                    until = dt_util.parse_datetime(st[slot + "_until"])
                    if until and until > clock.now:
                        self._status(pid)[slot] = {"state": "open", "until": until,
                                                   "opened": dt_util.parse_datetime(st.get(slot + "_opened") or "") or clock.now,
                                                   "next_remind": clock.now + timedelta(minutes=5), "day": clock.today}

    def next_trigger(self, p: Person, slot: str, clock: Clock, day: date | None = None) -> datetime | None:
        day = day or clock.today
        sched = SlotSchedule.from_dict(p.profile["schedule"].get(slot), "07:30" if slot == MORNING else "21:00")
        default = "07:30" if slot == MORNING else "21:00"
        fixed = fixed_time(sched, day, clock.tz, default)
        if sched.mode == "manual":
            return None
        if sched.mode == "entity" and sched.entity:
            st = self.hass.states.get(sched.entity)
            dt = dt_util.parse_datetime(str(st.state)) if st else None
            t = entity_trigger(dt_util.as_local(dt) if dt else None, sched.offset_min)
            if t is not None and abs((t.date() - day).days) <= 1:
                return t
            return fixed
        if sched.mode == "sleep" and p.mod("sleep_tracking"):
            p.gap.base = p.profile["schedule"]["sleep_gap_min"]
            if slot == MORNING:
                stored = p.day_numbers(day).get("sleep")
                woke = dt_util.parse_datetime(stored["end"]) if stored and stored.get("end") else None
                conf = (stored or {}).get("conf") or 0.0
                if woke is None and p.live and p.live.sleep and p.live.state_now not in ("asleep",):
                    woke = datetime.fromtimestamp(p.live.sleep.end * 60, tz=clock.tz)
                    conf = p.live.confidence
                t = sleep_trigger(MORNING, p.gap, woke_at=woke, predicted_bed=None, confidence=max(conf, 0.5), now=clock.now)
                if t is not None and t.date() == day:
                    return t
                return fixed
            pred = p.sleep_prediction(clock, workday=(day + timedelta(days=1)).weekday() < 5)
            if pred.bed is not None:
                base = local_at(day, parse_hhmm("00:00"), clock.tz)
                bed = base + timedelta(minutes=pred.bed if pred.bed >= 12 * 60 else pred.bed + 1440)
                t = sleep_trigger(EVENING, p.gap, woke_at=None, predicted_bed=bed, confidence=pred.confidence, now=clock.now)
                if t is not None:
                    return t
            return fixed
        return fixed

    async def _schedule_person(self, p: Person, clock: Clock) -> None:
        st = self._status(p.pid)
        today = clock.today
        for slot in (MORNING, EVENING):
            cur = st.get(slot)
            if cur and cur.get("state") == "open":
                if clock.now >= cur["until"]:
                    await self.close_window(p.pid, slot, "missed")
                elif p.profile["notify"].get("remind") and self.settings["remind_min"] and clock.now >= cur["next_remind"]:
                    cur["next_remind"] = clock.now + timedelta(minutes=self.settings["remind_min"])
                    await self.send_checkin(p, slot, reminder=True)
                continue
            n = p.day_numbers(today)
            if (n.get("status") or {}).get(slot) in ("done", "missed", "open") or n.get(slot[0]):
                continue
            if p.paused_on(today):
                continue
            t = self.next_trigger(p, slot, clock)
            if t is not None and t <= clock.now < t + timedelta(minutes=self.settings["window_min"]):
                await self.open_window(p.pid, slot)
        # Pause-Tage markieren (Serien reißen nicht)
        if p.paused_on(today) and not p.day_numbers(today).get("paused"):
            n = dict(p.day_numbers(today))
            n["paused"] = True
            p.vault.set_numbers(today.isoformat(), n)
            self.save_person(p.pid)
        pause = p.profile.get("pause")
        if pause and pause.get("until") and parse_day(pause["until"]) < today:
            p.profile["pause"] = None
            self.save_config()

    async def open_window(self, pid: str, slot: str, minutes: int | None = None, notify: bool = True) -> None:
        p = self.persons[pid]
        clock = self.clock()
        until = clock.now + timedelta(minutes=minutes or self.settings["window_min"])
        self._status(pid)[slot] = {"state": "open", "until": until, "opened": clock.now, "day": clock.today,
                                   "next_remind": clock.now + timedelta(minutes=max(1, self.settings["remind_min"] or 9999))}
        n = dict(p.day_numbers(clock.today))
        s = dict(n.get("status") or {})
        s[slot] = "open"
        s[slot + "_until"] = until.isoformat()
        s[slot + "_opened"] = clock.now.isoformat()
        n["status"] = s
        p.vault.set_numbers(clock.today.isoformat(), n)
        self.save_person(pid)
        if notify:
            await self.send_checkin(p, slot)
        self.mark_changed(pid)

    async def close_window(self, pid: str, slot: str, result: str) -> None:
        p = self.persons.get(pid)
        if p is None:
            return
        cur = self._status(pid).pop(slot, None)
        clock = self.clock()
        day = cur["day"] if cur else clock.today
        n = dict(p.day_numbers(day))
        s = dict(n.get("status") or {})
        if s.get(slot) != "done":
            s[slot] = result
        s.pop(slot + "_until", None)
        n["status"] = s
        p.vault.set_numbers(day.isoformat(), n)
        sched = (p.profile["schedule"].get(slot) or {}).get("mode")
        if cur and sched == "sleep":
            resp = (clock.now - cur["opened"]).total_seconds() / 60.0 if result == "done" else None
            p.gap.learn(slot, resp)
        await self.notifier.clear(pid, slot, p.profile["targets"])
        self.save_person(pid, model=True)
        self.mark_changed(pid)

    async def async_set_pause(self, pid: str, on: bool, until: str | None) -> None:
        """Pause (holiday, illness): no check-ins, streaks don't break, forecasts pause."""
        p = self.persons[pid]
        today = self.clock().today
        if on:
            p.profile["pause"] = {"from": today.isoformat(), "until": until}
            for slot in (MORNING, EVENING):
                if self.window_open(pid, slot):
                    await self.close_window(pid, slot, "paused")
        else:
            p.profile["pause"] = None
            n = dict(p.day_numbers(today))
            if n.pop("paused", None):
                p.vault.set_numbers(today.isoformat(), n)
                self.save_person(pid)
        self.config["persons"][pid] = p.profile
        self.save_config()
        self.mark_changed(pid)

    def window_open(self, pid: str, slot: str) -> bool:
        cur = self._status(pid).get(slot)
        return bool(cur and cur.get("state") == "open")

    # ================================================================ Benachrichtigungen
    def _platform_of(self, target: dict) -> str:
        if target.get("kind") == "script":
            return target.get("platform") or "other"
        if target.get("kind") != "service" or not target["service"].startswith("notify.mobile_app_"):
            return "other"
        if target.get("platform") in ("android", "ios"):
            return target["platform"]
        suffix = target["service"].split("notify.mobile_app_", 1)[1]
        for e in self.hass.config_entries.async_entries("mobile_app"):
            if slugify(e.data.get("device_name", "")) == suffix:
                os_name = str(e.data.get("os_name", "")).lower()
                return "ios" if os_name in ("ios", "ipados", "macos") else "android"
        return "android"

    def _notify_error(self, target: dict, error: str) -> None:
        self.check_repairs()

    def _checkin_text(self, p: Person, slot: str) -> tuple[str, str]:
        child = p.child
        first = (p.name or "").split(" ")[0]
        title = self.t(f"n_{slot}_title" + ("_child" if child else ""), name=first)
        msg = self.t(f"n_{slot}_msg" + ("_child" if child else ""))
        if slot == MORNING and p.profile["notify"].get("details"):
            today = self.clock().today
            parts = []
            sl = p.day_numbers(today).get("sleep") or {}
            if sl.get("score") is not None:
                parts.append(self.t("n_sleep_score", score=sl["score"]))
                mx = p.sleepmaxing(today)
                if mx and mx.get("week_pct") is not None:
                    parts.append(self.t("n_week", pct=f"{mx['week_pct']:+d}"))
            tr_ = p.training(today)
            if tr_ and tr_.recommended:
                parts.append(self.t("n_training_child" if child else "n_training"))
            if parts:
                msg = " · ".join(parts)
        return title, msg

    async def send_checkin(self, p: Person, slot: str, reminder: bool = False, only_index: int | None = None,
                           resend: bool = False) -> int:
        if not p.profile["targets"]:
            return 0
        title, msg = self._checkin_text(p, slot)
        nt = p.profile["notify"]
        url = f"/{PANEL_URL_PATH}?checkin={slot}"

        def actions(idx: int) -> list[dict]:
            acts = [{"action": "URI", "title": self.t("n_action_open"), "uri": url}]
            if nt.get("later"):
                acts.append({"action": f"MH_LATER_{p.pid}_{slot}_{idx}", "title": self.t("n_action_later")})
            return acts
        return await self.notifier.send(
            p.pid, slot, p.profile["targets"], title=title, message=msg, persist=bool(nt.get("persist")),
            importance=nt.get("importance") or "high", ios_level=nt.get("ios_level") or "time-sensitive",
            channel=self.t("n_channel"), actions_for=actions, only_index=only_index, resend=resend)

    async def send_test(self, p: Person) -> int:
        return await self.notifier.send(
            p.pid, "test", p.profile["targets"], title=self.t("n_test_title"), message=self.t("n_test_msg"),
            persist=True, importance=p.profile["notify"].get("importance") or "high",
            ios_level=p.profile["notify"].get("ios_level") or "time-sensitive", channel=self.t("n_channel"),
            actions_for=lambda idx: [])

    @callback
    def _on_cleared(self, event: Event) -> None:
        parsed = parse_tag(event.data.get("tag") or (event.data.get("data") or {}).get("tag"))
        if parsed is None:
            return
        pid, slot, idx = parsed
        p = self.persons.get(pid)
        if p is None or slot not in (MORNING, EVENING) or not p.profile["notify"].get("persist"):
            return
        if not self.window_open(pid, slot):
            return
        if idx >= len(p.profile["targets"]) or self._platform_of(p.profile["targets"][idx]) != "android":
            return
        tag = f"mh_{pid}_{slot}_{idx}"
        if not self.notifier.guard.allow(tag):
            return
        self.hass.async_create_task(self.send_checkin(p, slot, only_index=idx, resend=True))

    @callback
    def _on_action(self, event: Event) -> None:
        m = LATER_RE.match(str(event.data.get("action") or ""))
        if not m:
            return
        pid, slot, idx = m.group(1), m.group(2), int(m.group(3))
        p = self.persons.get(pid)
        if p is None:
            return
        cur = self._status(pid).get(slot)
        if cur:
            cur["next_remind"] = self.clock().now + timedelta(minutes=10)
            cur["until"] = max(cur["until"], self.clock().now + timedelta(minutes=15))

        async def later(_now: Any) -> None:
            if self.window_open(pid, slot):
                await self.send_checkin(p, slot, only_index=idx)
        async_call_later(self.hass, 600, later)

    async def async_request_setup(self, user: Any) -> dict:
        uid = getattr(user, "id", None)
        if not uid or self.person_for_user(uid):
            return {"ok": False, "reason": "already"}
        req = self.config["requests"].get(uid)
        now = dt_util.now().timestamp()
        cooldown = self.settings["request_cooldown_h"] * 3600
        if req and now - req.get("ts", 0) < cooldown:
            return {"ok": True, "sent": False, "next": req["ts"] + cooldown}
        name = getattr(user, "name", None) or self.t("default_person")
        self.config["requests"][uid] = {"ts": now, "name": name}
        self.save_config()
        url = f"/{PANEL_URL_PATH}?admin=persons&user={uid}"
        sent = 0
        if self.settings["admin_targets"]:
            sent = await self.notifier.send_admin(self.settings["admin_targets"], self.t("n_setup_title"),
                                                  self.t("n_setup_msg", name=name), url,
                                                  [{"action": "URI", "title": self.t("n_setup_action"), "uri": url}])
        if not sent:
            from homeassistant.components import persistent_notification
            persistent_notification.async_create(self.hass, f"{self.t('n_setup_msg', name=name)}\n\n[{self.t('n_setup_action')}]({url})",
                                                 title=self.t("n_setup_title"), notification_id=f"{DOMAIN}_request_{uid}")
        self.broadcast_all()
        return {"ok": True, "sent": True, "next": now + cooldown}

    # ================================================================ Check-ins (Websocket)
    def time_rules(self) -> TimeRules:
        return TimeRules(parse_hhmm(self.settings["evening_from"], "14:00"), parse_hhmm(self.settings["morning_until"], "14:00"),
                         self.settings["late_entry"])

    def family_birthdays(self, viewer_pid: str | None, today: date, days_ahead: int = 7) -> list[dict]:
        out = []
        for p in self.persons.values():
            b = p.birthdate
            if not b or not p.modules.get("birthday", True):
                continue
            du = b.days_until(today)
            if du <= days_ahead:
                out.append({"name": p.name, "days": du, "self": p.pid == viewer_pid, "turning": b.turning(today)})
        return sorted(out, key=lambda x: x["days"])

    def checkin_form(self, p: Person, slot: str, day: date | None = None) -> dict:
        clock = self.clock()
        day = day or clock.today
        allowed, late = manual_allowed(slot, clock.now, day, clock.today, self.time_rules())
        if self.window_open(p.pid, slot) and day == clock.today:
            allowed, late = True, False
        form = p.form(slot, clock, self.family_birthdays(p.pid, clock.today), self.extra_signals())
        existing = None
        try:
            t = p.vault.texts(day.isoformat()) or {}
        except Locked:
            t = {}
        n = p.day_numbers(day).get(slot[0])
        if n:
            existing = {k: v for k, v in n.items() if not k.startswith("_") and k != "late"}
            te = t.get(slot[0]) or {}
            existing.update({k: te[k] for k in ("good", "bad", "journal") if k in te})
            if "goals" in te:
                existing["goals"] = [g["text"] for g in te["goals"]]
            if "period" in n:
                existing["period"] = {**n["period"], **(te.get("period") or {})}
        return {"slot": slot, "day": day.isoformat(), "allowed": allowed, "late": late,
                "open": self.window_open(p.pid, slot), "fields": [f.to_dict() for f in form], "existing": existing,
                "draft": p.vault.get_draft(slot), "child": p.child}

    async def async_submit(self, p: Person, slot: str, day: date, data: dict) -> dict:
        clock = self.clock()
        allowed, late = manual_allowed(slot, clock.now, day, clock.today, self.time_rules())
        if self.window_open(p.pid, slot) and day == clock.today:
            allowed, late = True, False
        if not allowed:
            return {"ok": False, "errors": {"_": "not_allowed"}}
        errors, info = await self.hass.async_add_executor_job(
            lambda: p.submit(slot, day, data, clock, late, self.tod_of, self.family_birthdays(p.pid, clock.today)))
        if errors:
            return {"ok": False, "errors": errors}
        if day == clock.today:
            if self.window_open(p.pid, slot):
                await self.close_window(p.pid, slot, "done")
            else:
                await self.notifier.clear(p.pid, slot, p.profile["targets"])
        self.save_person(p.pid, model=True)
        self.recompute(p.pid)            # Entitäten sofort aktualisieren
        self.recompute_hub()
        self.mark_changed(p.pid)
        self.hass.async_create_task(self._catch_up_analysis(p.pid))
        return {"ok": True, "info": info}

    def extra_signals(self) -> dict:
        out: dict[str, float] = {}
        ent = self.settings.get("weather_entity")
        if ent and (st := self.hass.states.get(ent)) is not None:
            v = st.attributes.get("temperature") if st.domain == "weather" else numeric_value(st.state)
            try:
                if v is not None and float(v) == float(v):
                    out["temp"] = float(v)
            except (TypeError, ValueError):
                pass
        ent = self.settings.get("daylight_entity")
        if ent and (st := self.hass.states.get(ent)) is not None:
            nr = dt_util.parse_datetime(str(st.attributes.get("next_rising") or ""))
            ns = dt_util.parse_datetime(str(st.attributes.get("next_setting") or ""))
            if nr and ns:
                hours = ((ns - nr).total_seconds() / 3600.0) % 24
                out["daylight"] = hours if hours > 0 else 24 - hours
        return out

    async def _catch_up_analysis(self, pid: str) -> None:
        """Text analysis (needs the text key) – cached encrypted, runs after unlock/submit."""
        p = self.persons.get(pid)
        if p is None or p.vault.tek is None:
            return
        today = self.clock().today
        try:
            res = await self.hass.async_add_executor_job(analysis, p, today)
        except Locked:
            return
        p.vault.set_derived({"day": today.isoformat(), **res})
        self.save_person(pid)
        self.mark_changed(pid)

    # ================================================================ Nacht-Job
    async def _nightly(self, _now: datetime | None = None) -> None:
        clock = self.clock()
        yesterday = clock.today - timedelta(days=1)
        for pid, p in self.persons.items():
            try:
                await self.hass.async_add_executor_job(self._nightly_person, p, yesterday)
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Mental Health: nightly analysis failed for one person")
            self.save_person(pid, model=True)
            await self._catch_up_analysis(pid)
        await self._auto_backup(clock)
        self.recompute_all()

    async def _weekly(self, clock: Clock) -> None:
        """Sunday 19:00: 'your weekly review is ready' (no sensitive content)."""
        if not self.settings.get("weekly_report"):
            return
        for p in self.persons.values():
            if not p.profile["notify"].get("weekly") or not p.profile["targets"] or p.paused_on(clock.today):
                continue
            await self.notifier.send(p.pid, "weekly", p.profile["targets"], title=self.t("n_weekly_title"),
                                     message=self.t("n_weekly_msg"), persist=False, importance="default",
                                     ios_level="active", channel=self.t("n_channel"), actions_for=lambda idx: [])

    def _nightly_person(self, p: Person, day: date) -> None:
        p.learn_day(day, self.extra_signals())
        p.relearn_optimum(day)
        for lm in p.sleep.levels.values():
            lm.fit(40 if int(self.settings.get("load_level", 2)) >= 2 else 20)

    async def _auto_backup(self, clock: Clock) -> None:
        cfg = self.settings["backup"]
        if cfg.get("auto") == "off" or not cfg.get("password"):
            return
        last = self.backup_info.get("last_auto")
        due = timedelta(days=1 if cfg["auto"] == "daily" else 7)
        if last and dt_util.parse_datetime(last) and clock.now - dt_util.parse_datetime(last) < due - timedelta(hours=2):
            return
        try:
            await archive.async_create_auto(self)
            self.backup_info["last_auto"] = clock.now.isoformat()
            self.save_config()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Mental Health: automatic backup failed: %s", type(err).__name__)
            if self.settings["admin_targets"]:
                await self.notifier.send_admin(self.settings["admin_targets"], self.t("n_admin_title"),
                                               self.t("n_backup_failed", error=type(err).__name__), f"/{PANEL_URL_PATH}?admin=backup")

    # ================================================================ Werte, Entitäten, Live-Daten
    def recompute(self, pid: str) -> None:
        p = self.persons.get(pid)
        if p is None:
            return
        clock = self.clock()
        st = {}
        for slot in (MORNING, EVENING):
            st[slot] = "open" if self.window_open(pid, slot) else (p.day_numbers(clock.today).get("status") or {}).get(slot)
            nt = self.next_trigger(p, slot, clock)
            if nt is not None and nt <= clock.now:
                nt = self.next_trigger(p, slot, clock, clock.today + timedelta(days=1))
            st["next_" + slot] = nt.isoformat() if nt else None
        try:
            self.values[pid] = p.entity_state(clock, st)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Mental Health: could not compute values")
            return
        async_dispatcher_send(self.hass, signal_person(self.entry.entry_id, pid))

    def recompute_all(self) -> None:
        for pid in list(self.persons):
            self.recompute(pid)
        self.recompute_hub()

    def recompute_hub(self) -> None:
        clock = self.clock()
        today = clock.today
        moods, scores, sleeps, avg7 = [], [], [], []
        active = done = 0
        for pid, p in self.persons.items():
            v = self.values.get(pid) or {}
            if p.paused_on(today):
                continue
            active += 1
            if v.get("mood_today") is not None:
                moods.append(v["mood_today"])
                done += 1
            if v.get("health_score") is not None:
                scores.append(v["health_score"])
            if v.get("sleep_score") is not None:
                sleeps.append(v["sleep_score"])
            if v.get("mood_avg7") is not None:
                avg7.append(v["mood_avg7"])
        bdays = {pid: p.birthdate for pid, p in self.persons.items() if p.modules.get("birthday", True)}
        today_ids = family_today(bdays, today)
        nxt, who = family_next(bdays, today)
        self.hub_values = {
            "family_mood": round(sum(moods) / len(moods), 1) if moods else None,
            "family_mood_avg7": round(sum(avg7) / len(avg7), 1) if avg7 else None,
            "family_trend": None,
            "family_health": HS.family(scores, 1, admin=True),
            "family_sleep": round(sum(sleeps) / len(sleeps)) if sleeps else None,
            "participation": round(done / active * 100) if active else None,
            "birthdays_today": len(today_ids), "birthdays_today_names": [self.persons[i].name for i in today_ids],
            "next_birthday": local_at(nxt, datetime.min.time(), clock.tz).isoformat() if nxt else None,
            "next_birthday_names": [self.persons[i].name for i in who],
            "persons": len(self.persons), "last_backup": self.backup_info.get("last"),
            "weather": HS.family_weather(sum(moods) / len(moods) if moods else None),
        }
        if avg7:
            v30 = [self.values[p].get("mood_avg30") for p in self.values if self.values[p].get("mood_avg30") is not None]
            if v30:
                self.hub_values["family_trend"] = round(sum(avg7) / len(avg7) - sum(v30) / len(v30), 1)
        async_dispatcher_send(self.hass, signal_hub(self.entry.entry_id))

    def mark_changed(self, pid: str) -> None:
        self._push_pending.add(pid)
        if self._push_handle is None:
            self._push_handle = async_call_later(self.hass, PUSH_INTERVAL, self._flush_push)

    @callback
    def _flush_push(self, _now: Any) -> None:
        self._push_handle = None
        pending, self._push_pending = self._push_pending, set()
        for pid in pending:
            self.recompute(pid)
        self.recompute_hub()
        for sid, (uid, send) in list(self.subscribers.items()):
            p = self.person_for_user(uid)
            if p is None or p.pid in pending:
                send({"type": "changed"})
            else:
                send({"type": "family"})

    def broadcast_all(self) -> None:
        for _sid, (_uid, send) in list(self.subscribers.items()):
            send({"type": "changed"})

    def subscribe(self, user_id: str | None, send: Callable[[dict], None]) -> Callable[[], None]:
        self._sub_id += 1
        sid = self._sub_id
        self.subscribers[sid] = (user_id, send)

        def unsub() -> None:
            self.subscribers.pop(sid, None)
        return unsub

    # ================================================================ Geräte / Registry
    def expected_unique_ids(self) -> set[str]:
        from .entity_defs import person_entity_keys, hub_entity_keys
        out = {f"{self.entry.entry_id}_hub_{k}" for k in hub_entity_keys(self)}
        for pid, p in self.persons.items():
            out |= {f"{self.entry.entry_id}_{pid}_{k}" for k in person_entity_keys(p)}
        return out

    def ensure_hub_device(self) -> None:
        """Create the hub device up front, so person devices can reference it (via_device_id)."""
        from .const import MANUFACTURER
        dr.async_get(self.hass).async_get_or_create(
            config_entry_id=self.entry.entry_id, identifiers={self.hub_identifier}, name=self.t("hub_name"),
            manufacturer=MANUFACTURER, model=self.t("model_hub"), sw_version=VERSION,
            entry_type=dr.DeviceEntryType.SERVICE)

    def cleanup_registry(self) -> None:
        ent_reg = er.async_get(self.hass)
        keep = self.expected_unique_ids()
        for e in er.async_entries_for_config_entry(ent_reg, self.entry.entry_id):
            if e.unique_id not in keep:
                ent_reg.async_remove(e.entity_id)
        dev_reg = dr.async_get(self.hass)
        valid = {self.hub_identifier} | {self.person_identifier(pid) for pid in self.persons}
        for d in dr.async_entries_for_config_entry(dev_reg, self.entry.entry_id):
            if not (d.identifiers & valid):
                dev_reg.async_remove_device(d.id)

    # ================================================================ Repairs
    def check_repairs(self) -> None:
        try:
            from homeassistant.helpers import issue_registry as ir
        except ImportError:
            return
        wanted: dict[str, dict] = {}
        ent_reg = er.async_get(self.hass)

        def exists(eid: str) -> bool:
            return self.hass.states.get(eid) is not None or ent_reg.async_get(eid) is not None
        for pid, p in self.persons.items():
            refs = [(s.entity, "sleep_source") for s in p.sources]
            if p.profile.get("weight_entity"):
                refs.append((p.profile["weight_entity"], "weight_entity"))
            if p.profile.get("alarm_entity"):
                refs.append((p.profile["alarm_entity"], "alarm_entity"))
            for s in p.profile.get("cycle_sources") or []:
                refs.append((s["entity"], "cycle_source"))
            for eid, kind in refs:
                if not exists(eid):
                    wanted[f"missing_{pid}_{slugify(eid)}"] = {"pid": pid, "entity": eid, "kind": kind, "name": p.name}
            for t in p.profile["targets"]:
                if t["kind"] == "service":
                    dom, svc = t["service"].split(".", 1)
                    if not self.hass.services.has_service(dom, svc):
                        wanted[f"target_{pid}_{t['id']}"] = {"pid": pid, "entity": t["service"], "kind": "target",
                                                             "name": p.name, "target_id": t["id"]}
                elif not exists(t["entity"]):
                    wanted[f"target_{pid}_{t['id']}"] = {"pid": pid, "entity": t["entity"], "kind": "target",
                                                         "name": p.name, "target_id": t["id"]}
        reg = ir.async_get(self.hass)
        for issue_id in [i for (d, i) in list(reg.issues) if d == DOMAIN]:
            if issue_id not in wanted:
                ir.async_delete_issue(self.hass, DOMAIN, issue_id)
        for issue_id, data in wanted.items():
            ir.async_create_issue(
                self.hass, DOMAIN, issue_id, is_fixable=True, severity=ir.IssueSeverity.WARNING,
                translation_key="missing_target" if data["kind"] == "target" else "missing_entity",
                translation_placeholders={"entity": data["entity"], "name": data["name"]},
                data={k: v for k, v in data.items() if isinstance(v, str)})

    def fix_issue(self, data: dict) -> None:
        """One-click fix: remove the missing reference (data is kept)."""
        p = self.persons.get(data.get("pid") or "")
        if p is None:
            return
        prof = dict(p.profile)
        eid = data.get("entity")
        if data.get("kind") == "target":
            prof["targets"] = [t for t in prof["targets"] if t["id"] != data.get("target_id")]
        elif data.get("kind") == "sleep_source":
            prof["sleep_sources"] = [s for s in prof["sleep_sources"] if s["entity"] != eid]
        elif data.get("kind") == "cycle_source":
            prof["cycle_sources"] = [s for s in prof["cycle_sources"] if s["entity"] != eid]
        elif data.get("kind") in ("weight_entity", "alarm_entity"):
            prof[data["kind"]] = None
        new = normalize_person(prof, p.pid)
        p.profile.clear()
        p.profile.update(new)
        self.config["persons"][p.pid] = p.profile
        self.save_config()
        self._track_sources()
        self._after_structure_change()

    # ================================================================ Payloads für die Karte
    def me_payload(self, user: Any, admin_tok: str | None = None) -> dict:
        v = self.viewer(user, admin_tok)
        p = self.person_for_user(v.user_id)
        base = {"version": VERSION, "is_admin": v.is_admin, "admin_pin": self.admin_pin_set(),
                "ha_admin": bool(getattr(user, "is_admin", False)), "admin_access": self.admin_access(user, admin_tok),
                "admin_elevated": self.admin_elevated(v.user_id, admin_tok),
                "settings_public": {"evening_from": self.settings["evening_from"],
                                    "morning_until": self.settings["morning_until"],
                                    "family_k": self.settings["family_k"]},
                "llm": {"enabled": bool(self.settings["llm"]["enabled"])}, "persons": len(self.persons)}
        if p is None:
            req = self.config["requests"].get(v.user_id or "")
            return {**base, "setup": False,
                    "request": {"ts": req["ts"], "next": req["ts"] + self.settings["request_cooldown_h"] * 3600} if req else None}
        has_pin = self.keyring.has_pin(p.pid)
        return {**base, "setup": True, "pid": p.pid, "name": p.name, "child": p.child, "has_pin": has_pin,
                "rights": PM.rights_map(v, p.rights), "modules": {k: p.mod(k) for k in MODULES},
                "picture": self._picture(p)}

    def _picture(self, p: Person) -> str | None:
        st = self.hass.states.get(p.profile["person_entity"])
        return st.attributes.get("entity_picture") if st else None

    def dashboard_payload(self, p: Person) -> dict:
        """Everything for the person's own dashboard. Only ever sent to the person."""
        clock = self.clock()
        today = clock.today
        v = self.values.get(p.pid) or {}
        tr_ = p.training(today)
        ws = p.weight_summary(today)
        cy = p.cycle(today)
        hs, comps = p.health(today)
        derived = p.vault.get_derived() or {}
        low = bool(derived.get("low"))
        try:
            low = low or _low_mood(p, today, self.settings["low_mood_days"], self.settings["low_mood_max"])
        except Exception:  # noqa: BLE001
            pass
        ev_from = parse_hhmm(self.settings["evening_from"], "14:00")
        status = {}
        for slot in (MORNING, EVENING):
            cur = self._status(p.pid).get(slot)
            status[slot] = {"state": "open" if cur else (p.day_numbers(today).get("status") or {}).get(slot),
                            "until": cur["until"].isoformat() if cur else None, "next": v.get("next_" + slot)}
        n = p.day_numbers(today)
        days = []
        for i in range(0, 400):
            d = (today - timedelta(days=i)).isoformat()
            if d in p.vault.days:
                r = p.record(d)
                days.append({k: r[k] for k in ("day", "mood", "mood_m", "mood_e", "energy", "health", "sleep_h",
                                               "sleep_score", "trained", "soreness", "period", "late", "weight",
                                               "journal", "slots")})
        sleep_nights = []
        for i in range(0, 60):
            d = (today - timedelta(days=i)).isoformat()
            sl = (p.vault.days.get(d) or {}).get("sleep")
            if sl:
                sleep_nights.append({"day": d, **{k: sl.get(k) for k in ("start", "end", "asleep", "score", "int",
                                                                          "int_min", "naps", "conf", "src", "segments", "comps")}})
        return {
            "today": today.isoformat(), "now": clock.now.isoformat(), "values": v, "status": status,
            "evening_open_from": ev_from.strftime("%H:%M"),
            "evening_manual": clock.now.time() >= ev_from or clock.now.date() > today,
            "forecast": p.forecast(today, self.extra_signals()), "forecast_tomorrow": p.forecast_tomorrow(today, self.extra_signals()),
            "forecast_history": p.mood.history[-60:],
            "sleep": {"enabled": p.mod("sleep_tracking"), "today": n.get("sleep"), "maxing": p.sleepmaxing(today),
                      "optimum_h": round(p.optimum_h(today), 2), "state": p.live.state_now if p.live else None,
                      "learning": p.sleep.learning, "night_of": p.sleep.view()["night_of"], "nights": sleep_nights,
                      "range": list(recommended_range(p.age(today)))},
            "weight": weight_card(ws) if (ws and not p.child) else ({"child": True} if ws else None),
            "weights": [{"day": d, "kg": kg} for d, kg in sorted(p.vault.weights.items())[-400:]] if ws else [],
            "training": {"status": tr_.status, "days_since": tr_.days_since, "overdue": tr_.overdue_days,
                         "soreness": tr_.last_soreness, "highlight": tr_.highlight, "child": p.child} if tr_ else None,
            "cycle": {"next_start": cy.next_start.isoformat() if cy.next_start else None,
                      "next_end": cy.next_end.isoformat() if cy.next_end else None, "window": cy.window_days,
                      "cycle_len": cy.cycle_len, "period_len": cy.period_len, "active": cy.active, "day": cy.current_day,
                      "phase": cy.phase, "confidence": cy.confidence, "learned": cy.cycles_learned} if cy else None,
            "health": {"score": hs, "comps": comps},
            "birthdays": self.family_birthdays(p.pid, today, 14),
            "protect": low, "child": p.child, "days": days, "streak": v.get("streak"),
            "insights": derived.get("insights") or [], "topics": derived.get("topics") or {},
            "goals": derived.get("goals") or [], "on_this_day": derived.get("on_this_day") or [],
            "jar": derived.get("jar"), "locked_analysis": p.vault.tek is None,
            "missing": p.missing_profile(), "paused": p.paused_on(today), "pause": p.profile.get("pause"),
        }

    def family_payload(self, viewer: PM.Viewer) -> dict:
        """Family view for persons: no names next to values, no single values, k-threshold."""
        clock = self.clock()
        today = clock.today
        k = self.settings["family_k"]
        hist = []
        for i in range(0, 30):
            d = (today - timedelta(days=i)).isoformat()
            moods = [m for m in (p.day_mood(p.vault.numbers(d)) for p in self.persons.values()) if m is not None]
            if len(moods) >= k:
                hist.append({"day": d, "mood": round(sum(moods) / len(moods), 1), "n": len(moods)})
        scores = [self.values.get(pid, {}).get("health_score") for pid in self.persons]
        today_moods = [self.values.get(pid, {}).get("mood_today") for pid in self.persons]
        tm = [m for m in today_moods if m is not None]
        show = len(tm) >= k
        return {
            "k": k, "enough": show, "weather": HS.family_weather(sum(tm) / len(tm)) if show else None,
            "mood": round(sum(tm) / len(tm), 1) if show else None,
            "health": HS.family(scores, k), "history": hist[::-1],
            "participation": self.hub_values.get("participation") if len(self.persons) >= k else None,
            "birthdays": self.family_birthdays(None, today, 30), "members": len(self.persons),
        }

    def admin_payload(self) -> dict:
        """Admin area: configuration and model state per person – never contents."""
        clock = self.clock()
        persons = []
        for pid, p in self.persons.items():
            prof = dict(p.profile)
            if prof.get("weight_live"):
                prof["weight_kg"] = None
            persons.append({
                "profile": prof, "has_pin": self.keyring.has_pin(pid), "picture": self._picture(p),
                "model": {"sleep": {k: v for k, v in p.sleep.view().items() if k != "history"},
                          "mood_days": p.mood.days, "optimum": p.optimum},
                "participation": p.checkin_rate(clock.today), "status": {s: self.window_open(pid, s) for s in (MORNING, EVENING)},
                "age": p.age(clock.today),
            })
        return {
            "persons": persons, "ha_persons": self.ha_persons(), "settings": {**self.settings, "admin_pin": self.admin_pin_set(),
                                                                                "backup": {**self.settings["backup"], "password": bool(self.settings["backup"].get("password"))}},
            "requests": [{"user_id": k, **v} for k, v in self.config["requests"].items()],
            "notify_services": sorted(f"notify.{s}" for s in (self.hass.services.async_services().get("notify") or {})),
            "backups": archive.list_backups(self), "backup_info": self.backup_info, "llm_state": self.llm_state,
            "version": VERSION,
        }


def source_value(src: Source, state: Any) -> float:
    if src.kind == KIND_NUMERIC:
        return numeric_value(state)
    if src.kind == KIND_BINARY or src.kind == KIND_AUX:
        return binary_value(src, state)
    if src.kind == KIND_ENUM:
        h, _ = enum_value(src, state)
        return h
    if src.kind == KIND_PROB:
        return prob_value(state)
    return float("nan")


def _low_mood(p: Person, today: date, days: int, max_mood: int) -> bool:
    from .logic.analysis.insights import low_mood_alert
    recs = [p.record((today - timedelta(days=i)).isoformat()) for i in range(days + 2)]
    return low_mood_alert(recs, today, days, max_mood)
