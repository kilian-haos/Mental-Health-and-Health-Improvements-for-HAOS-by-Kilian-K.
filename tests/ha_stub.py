"""Minimal Home Assistant replica to test runtime.py without a real HA.

Only used when the real `homeassistant` package is not installed. It replicates exactly the
interfaces the runtime uses (stores incl. migration hook, registries, events, dispatcher,
services, states, time). Signatures were checked against the HA core source (2026.12.dev).
"""
from __future__ import annotations

import asyncio
import enum
import json
import sys
import types
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

SENT: list[tuple] = []
NOTIFICATIONS: list[dict] = []
ISSUES: dict[str, dict] = {}
STORES: dict[str, Any] = {}
TZ = ZoneInfo("Europe/Berlin")
NOW: list[datetime] = [datetime(2026, 11, 11, 7, 0, tzinfo=TZ)]


def set_now(dt: datetime) -> None:
    NOW[0] = dt


def _mod(name: str) -> types.ModuleType:
    m = sys.modules.get(name)
    if m is None:
        m = types.ModuleType(name)
        sys.modules[name] = m
        parent, _, child = name.rpartition(".")
        if parent:
            setattr(_mod(parent), child, m)
    return m


def install() -> None:
    try:
        import homeassistant  # noqa: F401
        if not getattr(homeassistant, "__mh_stub__", False):
            return
        return
    except ImportError:
        pass
    ha = _mod("homeassistant")
    ha.__mh_stub__ = True
    ha.__path__ = []

    const = _mod("homeassistant.const")

    class Platform(str, enum.Enum):
        SENSOR = "sensor"
        BINARY_SENSOR = "binary_sensor"

    const.Platform = Platform
    const.EVENT_HOMEASSISTANT_STOP = "homeassistant_stop"
    const.EVENT_CORE_CONFIG_UPDATE = "core_config_updated"

    core = _mod("homeassistant.core")
    core.callback = lambda f: f

    class Event:
        def __init__(self, data: dict, context: Any = None) -> None:
            self.data = data
            self.context = context

    core.Event = Event
    core.HomeAssistant = object
    core.ServiceCall = object
    core.ServiceResponse = dict
    core.SupportsResponse = types.SimpleNamespace(OPTIONAL="optional")

    ce = _mod("homeassistant.config_entries")
    ce.ConfigEntry = type("ConfigEntry", (), {"__class_getitem__": classmethod(lambda cls, item: cls)})

    class ConfigEntryState(enum.Enum):
        LOADED = "loaded"
    ce.ConfigEntryState = ConfigEntryState

    # ---- Registries
    dr = _mod("homeassistant.helpers.device_registry")

    class DeviceEntryType(str, enum.Enum):
        SERVICE = "service"

    class DeviceInfo(dict):
        __optional_keys__ = frozenset({"identifiers", "name", "via_device_id"})

    @dataclass
    class Device:
        id: str
        identifiers: set
        config_entries: set

    class DevReg:
        def __init__(self) -> None:
            self.devices: dict[str, Device] = {}

        def async_get_device(self, identifiers=None, connections=None):
            for d in self.devices.values():
                if d.identifiers & set(identifiers or ()):
                    return d
            return None

        def async_get_or_create(self, *, config_entry_id, identifiers, **kw):
            d = self.async_get_device(identifiers=identifiers)
            if d is None:
                d = Device(f"dev{len(self.devices) + 1}", set(identifiers), {config_entry_id})
                self.devices[d.id] = d
            return d

        def async_remove_device(self, device_id):
            self.devices.pop(device_id, None)

    DEV_REG = DevReg()
    dr.DeviceEntryType = DeviceEntryType
    dr.DeviceInfo = DeviceInfo
    dr.async_get = lambda hass: DEV_REG
    dr.async_entries_for_config_entry = lambda reg, eid: [d for d in list(reg.devices.values()) if eid in d.config_entries]

    er = _mod("homeassistant.helpers.entity_registry")

    @dataclass
    class Ent:
        entity_id: str
        unique_id: str
        config_entry_id: str

    class EntReg:
        def __init__(self) -> None:
            self.entities: dict[str, Ent] = {}

        def add(self, entity_id: str, unique_id: str, entry_id: str) -> None:
            self.entities[entity_id] = Ent(entity_id, unique_id, entry_id)

        def async_get(self, entity_id: str):
            return self.entities.get(entity_id)

        def async_remove(self, entity_id: str) -> None:
            self.entities.pop(entity_id, None)

    ENT_REG = EntReg()
    er.async_get = lambda hass: ENT_REG
    er.async_entries_for_config_entry = lambda reg, eid: [e for e in list(reg.entities.values()) if e.config_entry_id == eid]
    er.ENT_REG = ENT_REG

    ir = _mod("homeassistant.helpers.issue_registry")

    class IssueSeverity(str, enum.Enum):
        WARNING = "warning"

    class IssueReg:
        @property
        def issues(self):
            return {("mental_health", k): v for k, v in ISSUES.items()}

    ir.IssueSeverity = IssueSeverity
    ir.async_get = lambda hass: IssueReg()
    ir.async_create_issue = lambda hass, domain, issue_id, **kw: ISSUES.__setitem__(issue_id, kw)
    ir.async_delete_issue = lambda hass, domain, issue_id: ISSUES.pop(issue_id, None)

    disp = _mod("homeassistant.helpers.dispatcher")
    disp.async_dispatcher_send = lambda hass, signal, *args: SENT.append((signal, args))
    disp.async_dispatcher_connect = lambda hass, signal, target: (lambda: None)

    ev = _mod("homeassistant.helpers.event")
    ev.async_call_later = lambda hass, delay, action: (lambda: None)
    ev.async_track_state_change_event = lambda hass, ids, action: (lambda: None)
    ev.async_track_time_interval = lambda hass, action, interval: (lambda: None)
    ev.async_track_time_change = lambda hass, action, hour=None, minute=None, second=None: (lambda: None)

    st = _mod("homeassistant.helpers.storage")

    class Store:
        def __init__(self, hass, version, key, private=False, atomic_writes=False, minor_version=1) -> None:
            self.key = key
            self.version = version

        async def async_load(self):
            raw = STORES.get(self.key)
            if raw is None:
                return None
            if raw["version"] != self.version and hasattr(self, "_async_migrate_func"):
                return await self._async_migrate_func(raw["version"], 1, raw["data"])
            return raw["data"]

        async def async_save(self, data) -> None:
            STORES[self.key] = {"version": self.version, "data": json.loads(json.dumps(data))}

        def async_delay_save(self, func, delay=0) -> None:
            STORES[self.key] = {"version": self.version, "data": json.loads(json.dumps(func()))}

        async def async_remove(self) -> None:
            STORES.pop(self.key, None)

    st.Store = Store

    pn = _mod("homeassistant.components.persistent_notification")
    pn.async_create = lambda hass, message, title=None, notification_id=None: NOTIFICATIONS.append(
        {"message": message, "title": title, "id": notification_id})
    _mod("homeassistant.components").__path__ = []

    dt = _mod("homeassistant.util.dt")
    dt.now = lambda: NOW[0]
    dt.utcnow = lambda: NOW[0].astimezone(timezone.utc)
    dt.get_default_time_zone = lambda: TZ
    dt.as_local = lambda d: d.astimezone(TZ)

    def parse_datetime(s: str):
        try:
            return datetime.fromisoformat(str(s))
        except ValueError:
            return None
    dt.parse_datetime = parse_datetime
    _mod("homeassistant.util").dt = dt
    _mod("homeassistant.helpers")


# ------------------------------------------------------------------ Fake-Objekte
@dataclass
class FakeState:
    entity_id: str
    state: str
    attributes: dict = field(default_factory=dict)
    last_updated: datetime = field(default_factory=lambda: NOW[0])

    @property
    def domain(self) -> str:
        return self.entity_id.split(".", 1)[0]


class FakeStates:
    def __init__(self) -> None:
        self._s: dict[str, FakeState] = {}

    def get(self, eid: str):
        return self._s.get(eid)

    def set(self, eid: str, state: str, attributes: dict | None = None) -> None:
        self._s[eid] = FakeState(eid, state, attributes or {}, NOW[0])

    def async_all(self, domain: str | None = None):
        return [s for s in self._s.values() if domain is None or s.domain == domain]


class FakeBus:
    def __init__(self) -> None:
        self.listeners: dict[str, list] = {}

    def async_listen(self, event, cb):
        self.listeners.setdefault(event, []).append(cb)
        return lambda: self.listeners[event].remove(cb)

    def async_listen_once(self, event, cb):
        return lambda: None

    def fire(self, event: str, data: dict) -> None:
        from homeassistant.core import Event
        for cb in list(self.listeners.get(event, [])):
            cb(Event(data))


class FakeServices:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.fail: set[str] = set()
        self.registered = {"notify": {"mobile_app_s25": {}, "mobile_app_ipad": {}, "mobile_app_broken": {}}}

    async def async_call(self, domain, service, data, blocking=False, return_response=False):
        self.calls.append((domain, service, json.loads(json.dumps(data))))
        if f"{domain}.{service}" in self.fail:
            raise RuntimeError("service failed")
        return None

    def has_service(self, domain, service):
        return service in self.registered.get(domain, {})

    def async_services(self):
        return self.registered


class FakeConfig:
    def __init__(self, language: str = "de") -> None:
        self.language = language
        self.time_zone = "Europe/Berlin"

    def path(self, *parts: str) -> str:
        import os
        import tempfile
        base = getattr(self, "_base", None) or tempfile.mkdtemp(prefix="mh_cfg_")
        self._base = base
        return os.path.join(base, *parts)


@dataclass
class MobileEntry:
    data: dict


class FakeConfigEntries:
    def __init__(self) -> None:
        self.reloads: list[str] = []
        self.mobile = [MobileEntry({"device_name": "S25", "os_name": "Android"}),
                       MobileEntry({"device_name": "iPad", "os_name": "iPadOS"})]

    def async_entries(self, domain: str):
        return self.mobile if domain == "mobile_app" else []

    def async_schedule_reload(self, entry_id: str) -> None:
        self.reloads.append(entry_id)


class FakeUser:
    def __init__(self, uid: str, is_admin: bool = False, name: str = "User") -> None:
        self.id = uid
        self.is_admin = is_admin
        self.name = name


class FakeHass:
    def __init__(self, language: str = "de") -> None:
        self.config = FakeConfig(language)
        self.states = FakeStates()
        self.bus = FakeBus()
        self.services = FakeServices()
        self.config_entries = FakeConfigEntries()
        self.data: dict = {}
        self.tasks: list = []

    async def async_add_executor_job(self, func, *args):
        return func(*args)

    def async_create_task(self, coro):
        t = asyncio.ensure_future(coro)
        self.tasks.append(t)
        return t

    async def drain(self) -> None:
        while self.tasks:
            t = self.tasks.pop(0)
            await t


class FakeEntry:
    def __init__(self, entry_id: str = "entry1") -> None:
        self.entry_id = entry_id
        self.options: dict = {}


def reset() -> None:
    SENT.clear()
    NOTIFICATIONS.clear()
    ISSUES.clear()
    STORES.clear()
    NOW[0] = datetime(2026, 11, 11, 7, 0, tzinfo=TZ)


def advance(minutes: float) -> None:
    NOW[0] = NOW[0] + timedelta(minutes=minutes)
