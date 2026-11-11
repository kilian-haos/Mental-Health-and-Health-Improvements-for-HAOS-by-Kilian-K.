"""Check-in schedule maths (pure Python).

Triggers per person and slot: fixed time per weekday, timestamp entity + offset, sleep based,
or manual/automation only. The sleep-based trigger uses exactly one setting, "gap to sleep"
(default 20 min): morning ≈ gap after getting up, evening ≈ 1.5 × gap before the predicted
bedtime. The actual offset is optimised per person within sensible limits from the response
times (answered quickly = good moment; ignored/late = shift).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, tzinfo

from .daymath import local_at, parse_hhmm

FIXED = "fixed"
ENTITY = "entity"
SLEEP = "sleep"
MANUAL = "manual"
MODES = (FIXED, ENTITY, SLEEP, MANUAL)


@dataclass
class SlotSchedule:
    mode: str = FIXED
    times: list[str] = field(default_factory=lambda: ["07:30"] * 7)   # Mo..So
    entity: str | None = None
    offset_min: int = 0

    @classmethod
    def from_dict(cls, d: dict | None, default_time: str) -> SlotSchedule:
        d = d or {}
        times = d.get("times")
        if not isinstance(times, list) or len(times) != 7:
            times = [d.get("time") or default_time] * 7
        mode = d.get("mode") if d.get("mode") in MODES else FIXED
        try:
            off = int(d.get("offset_min") or 0)
        except (TypeError, ValueError):
            off = 0
        return cls(mode, [str(t) for t in times], d.get("entity") or None, max(-720, min(720, off)))

    def to_dict(self) -> dict:
        return {"mode": self.mode, "times": self.times, "entity": self.entity, "offset_min": self.offset_min}


def fixed_time(sched: SlotSchedule, day: date, tz: tzinfo, default: str) -> datetime:
    t = parse_hhmm(sched.times[day.weekday()], default)
    return local_at(day, t, tz)


@dataclass
class AdaptiveGap:
    """Learned offsets around sleep (minutes). Bounded, slowly adapting."""

    base: int = 20
    morning: float | None = None
    evening: float | None = None

    def morning_offset(self) -> float:
        return self.morning if self.morning is not None else float(self.base)

    def evening_offset(self) -> float:
        return self.evening if self.evening is not None else 1.5 * self.base

    def bounds(self, slot: str) -> tuple[float, float]:
        b = max(5, self.base)
        return (max(5.0, b * 0.5), b * 3.0) if slot == "morning" else (b * 1.0, b * 4.0)

    def learn(self, slot: str, response_min: float | None) -> None:
        """response_min = minutes from notification to answer, None = ignored/missed."""
        cur = self.morning_offset() if slot == "morning" else self.evening_offset()
        lo, hi = self.bounds(slot)
        if response_min is None or response_min > 30:
            step = 4.0      # zu früh am Morgen bzw. zu knapp vor dem Schlaf -> verschieben
        elif response_min > 12:
            step = 1.5
        elif response_min < 4:
            step = -0.5     # sehr schnell beantwortet: guter Zeitpunkt, leicht zurück zur Basis
        else:
            step = 0.0
        new = min(hi, max(lo, cur + step))
        if slot == "morning":
            self.morning = round(new, 1)
        else:
            self.evening = round(new, 1)

    def to_dict(self) -> dict:
        return {"base": self.base, "morning": self.morning, "evening": self.evening}

    @classmethod
    def from_dict(cls, d: dict | None, base: int) -> AdaptiveGap:
        d = d or {}
        g = cls(base, d.get("morning"), d.get("evening"))
        if d.get("base") != base:          # Einstellwert geändert -> Gelerntes neu beginnen
            g.morning = g.evening = None
        return g


def sleep_trigger(slot: str, gap: AdaptiveGap, *, woke_at: datetime | None, predicted_bed: datetime | None,
                  confidence: float, now: datetime) -> datetime | None:
    """Sleep-based time or None (-> fallback to the fixed time)."""
    if slot == "morning":
        if woke_at is None or confidence < 0.35:
            return None
        return woke_at + timedelta(minutes=gap.morning_offset())
    if predicted_bed is None or confidence < 0.35:
        return None
    t = predicted_bed - timedelta(minutes=gap.evening_offset())
    return t


def entity_trigger(value: datetime | None, offset_min: int) -> datetime | None:
    if value is None:
        return None
    return value + timedelta(minutes=offset_min)


def clamp_to_day(t: datetime, earliest: time, latest: time) -> datetime:
    lo = t.replace(hour=earliest.hour, minute=earliest.minute, second=0, microsecond=0)
    hi = t.replace(hour=latest.hour, minute=latest.minute, second=0, microsecond=0)
    if hi <= lo:
        return t
    return min(max(t, lo), hi)
