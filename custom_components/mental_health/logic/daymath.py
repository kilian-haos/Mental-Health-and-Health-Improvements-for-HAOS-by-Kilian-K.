"""Day arithmetic: logical days, local times, DST-safe helpers (pure Python).

A "day" does not end at midnight: it ends at the configurable day boundary (default 04:00),
so an evening check-in at 00:40 still belongs to the previous day.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, time, timedelta, timezone, tzinfo

_TIME_RE = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


def parse_hhmm(value: str | None, default: str = "00:00") -> time:
    m = _TIME_RE.match(str(value or "").strip())
    if not m:
        m = _TIME_RE.match(default)
    return time(int(m.group(1)), int(m.group(2)))


def fmt_hhmm(t: time) -> str:
    return f"{t.hour:02d}:{t.minute:02d}"


def valid_hhmm(value: str | None) -> bool:
    return bool(_TIME_RE.match(str(value or "").strip()))


def logical_day(local_dt: datetime, boundary: time = time(4, 0)) -> date:
    """The day a local timestamp belongs to (before the boundary = previous day)."""
    if local_dt.time() < boundary:
        return (local_dt - timedelta(days=1)).date()
    return local_dt.date()


def day_key(d: date) -> str:
    return d.isoformat()


def parse_day(s: str) -> date:
    return date.fromisoformat(s)


def local_at(d: date, t: time, tz: tzinfo) -> datetime:
    """Local wall-clock time on a date, DST-safe (non-existent times move forward)."""
    # Rundreise über UTC: eine nicht existierende Zeit (Sommerzeit-Sprung) wird zur echten,
    # späteren Uhrzeit; doppelte Zeiten (Herbst) nehmen das erste Auftreten.
    aware = datetime.combine(d, t).replace(tzinfo=tz)
    return aware.astimezone(timezone.utc).astimezone(tz)


def minutes_of_day(dt: datetime) -> float:
    return dt.hour * 60 + dt.minute + dt.second / 60.0


def days_between(a: date, b: date) -> int:
    return (b - a).days


# ---------------------------------------------------------------- zirkuläre Statistik (Uhrzeiten)
def circ_mean_minutes(values: list[float], weights: list[float] | None = None) -> tuple[float | None, float]:
    """Weighted circular mean of times of day in minutes -> (mean, spread in minutes)."""
    if not values:
        return None, 0.0
    if weights is None:
        weights = [1.0] * len(values)
    sx = sy = sw = 0.0
    for v, w in zip(values, weights):
        a = v / 1440.0 * 2 * math.pi
        sx += w * math.cos(a)
        sy += w * math.sin(a)
        sw += w
    if sw <= 0:
        return None, 0.0
    sx /= sw
    sy /= sw
    r = math.hypot(sx, sy)
    mean = (math.atan2(sy, sx) / (2 * math.pi) * 1440.0) % 1440.0
    if r <= 1e-9:
        return mean, 720.0
    spread = math.sqrt(max(0.0, -2.0 * math.log(r))) / (2 * math.pi) * 1440.0
    return mean, spread


def circ_diff(a: float, b: float) -> float:
    """Signed minimal difference a-b in minutes on a 24 h circle."""
    d = (a - b + 720.0) % 1440.0 - 720.0
    return d
