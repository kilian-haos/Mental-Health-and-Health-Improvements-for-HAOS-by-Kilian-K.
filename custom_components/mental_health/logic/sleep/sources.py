"""Sleep sources: types, roles, mappings -> per-minute channel values (pure Python).

Every source maps a Home Assistant state to one channel value in 0..1 (or NaN = unknown):

  occ      bed is loaded / person in bed     (bed sensors, pressure mats, binary bed sensors)
  hint     person is asleep                  (focus "sleep", sleep apps, wearables, sleep_confidence)
  screen   phone screen on / phone in use
  charging phone is charging
  light    bedroom light on
  away_motion  motion elsewhere in the home (hallway, kitchen …)
  room     presence in the bedroom (mmWave …)
  home     person at home
Timestamp/duration sources (Withings, Fitbit, Garmin, Health Connect …) are references/labels.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

NAN = float("nan")

KIND_BINARY = "binary"
KIND_NUMERIC = "numeric"
KIND_ENUM = "enum"
KIND_PROB = "probability"
KIND_TIMESTAMP = "timestamp"
KIND_AUX = "aux"
KINDS = (KIND_BINARY, KIND_NUMERIC, KIND_ENUM, KIND_PROB, KIND_TIMESTAMP, KIND_AUX)

CHANNELS = ("occ", "hint", "screen", "charging", "light", "away_motion", "room", "home")

# Rollen für binäre Quellen
ROLE_IN_BED = "in_bed"
ROLE_ASLEEP = "asleep"
# Hilfssignale
AUX_ROLES = ("screen", "charging", "light", "away_motion", "room", "home")
# Zeitstempel-Rollen
TS_ROLES = ("sleep_start", "sleep_end", "duration")

ENUM_TARGETS = ("asleep", "awake", "in_bed", "ignore")

# Vorschläge für bekannte Zustände (Sleep as Android, Wearables, Companion App)
ENUM_SUGGESTIONS = {
    "asleep": ("asleep", "sleep", "sleeping", "light", "deep", "rem", "light_sleep", "deep_sleep",
               "sleep_tracking_started", "schläft", "schlaf", "core"),
    "awake": ("awake", "wake", "woke", "sleep_tracking_stopped", "alarm_alert_start", "alarm_alert_dismiss",
              "wach", "out_of_bed"),
    "in_bed": ("in_bed", "inbed", "lying", "im_bett", "sleep_tracking_paused"),
}
UNKNOWN = ("unknown", "unavailable", "none", "", None)


@dataclass
class Source:
    id: str
    entity: str
    kind: str
    role: str = ROLE_IN_BED            # binär: in_bed | asleep; aux: screen|charging|light|away_motion|room|home; ts: …
    on_means: bool = True              # binär: True = „on“ bedeutet im Bett/schläft, False = „off“ bedeutet es
    threshold: float | None = None     # numerisch: optionales Triggerlevel (Startwert)
    direction: int | None = None       # numerisch: -1 fällt bei Belastung, +1 steigt, None = lernen
    mapping: dict[str, str] = field(default_factory=dict)   # Enum: Zustand -> asleep|awake|in_bed|ignore
    shared_with: list[str] = field(default_factory=list)    # geteiltes Bett: andere person_ids
    unit: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> Source:
        kind = d.get("kind") if d.get("kind") in KINDS else KIND_BINARY
        th = d.get("threshold")
        try:
            th = float(th) if th not in (None, "") else None
        except (TypeError, ValueError):
            th = None
        direction = d.get("direction")
        direction = int(direction) if direction in (-1, 1, "-1", "1") else None
        return cls(
            id=str(d.get("id") or d.get("entity")), entity=str(d.get("entity") or ""), kind=kind,
            role=str(d.get("role") or (ROLE_IN_BED if kind in (KIND_BINARY, KIND_NUMERIC) else "")),
            on_means=bool(d.get("on_means", True)), threshold=th, direction=direction,
            mapping={str(k): str(v) for k, v in (d.get("mapping") or {}).items() if v in ENUM_TARGETS},
            shared_with=[str(x) for x in (d.get("shared_with") or [])], unit=d.get("unit"),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id, "entity": self.entity, "kind": self.kind, "role": self.role, "on_means": self.on_means,
            "threshold": self.threshold, "direction": self.direction, "mapping": self.mapping,
            "shared_with": self.shared_with, "unit": self.unit,
        }

    @property
    def channel(self) -> str | None:
        if self.kind == KIND_NUMERIC:
            return "occ"
        if self.kind == KIND_BINARY:
            return "hint" if self.role == ROLE_ASLEEP else "occ"
        if self.kind in (KIND_ENUM, KIND_PROB):
            return "hint"
        if self.kind == KIND_AUX:
            return self.role if self.role in AUX_ROLES else None
        return None


def suggest_mapping(states: list[str]) -> dict[str, str]:
    out = {}
    for s in states:
        key = str(s).strip().lower().replace(" ", "_")
        for target, names in ENUM_SUGGESTIONS.items():
            if key in names:
                out[s] = target
                break
        else:
            out[s] = "ignore"
    return out


def binary_value(src: Source, state: Any) -> float:
    s = str(state).lower() if state is not None else None
    if src.kind == KIND_AUX and src.role == "charging" and s == "none":
        return 0.0                      # charger_type „none“ = lädt nicht
    if s in UNKNOWN:
        return NAN
    on = s in ("on", "true", "home", "1", "open", "detected", "playing")
    if src.kind == KIND_AUX:
        if src.role == "home":
            return 1.0 if (s == "home" or on) else 0.0
        if src.role == "charging":
            return 0.0 if s in ("none", "off", "false", "discharging", "not_charging") else 1.0
        return 1.0 if on else 0.0
    return 1.0 if on == src.on_means else 0.0


def enum_value(src: Source, state: Any) -> tuple[float, float]:
    """-> (hint, occ) for enum sources."""
    s = str(state) if state is not None else None
    if s is None or s.lower() in UNKNOWN:
        return NAN, NAN
    target = src.mapping.get(s) or src.mapping.get(s.lower())
    if target is None:
        target = suggest_mapping([s]).get(s, "ignore")
    if target == "asleep":
        return 1.0, NAN
    if target == "awake":
        return 0.0, NAN
    if target == "in_bed":
        return 0.3, 1.0
    return NAN, NAN


def prob_value(state: Any) -> float:
    try:
        v = float(state)
    except (TypeError, ValueError):
        return NAN
    if v != v or math.isinf(v):
        return NAN
    if v > 1.0:
        v /= 100.0
    return max(0.0, min(1.0, v))


def numeric_value(state: Any) -> float:
    try:
        v = float(state)
    except (TypeError, ValueError):
        return NAN
    return NAN if (v != v or math.isinf(v)) else v
