"""Per-minute features from irregular samples (pure Python, compact arrays).

ESPHome and other sensors report irregularly (on change, every few seconds, or rarely). Each
source keeps a ring buffer of one value per minute – mean and range (max-min) within the
minute – with last-value-hold between reports. 36 h × 2 floats ≈ 17 kB per source; no raw
samples are kept in memory.
"""
from __future__ import annotations

import math
from array import array

NAN = float("nan")
DEFAULT_MINUTES = 36 * 60


class MinuteSeries:
    """Ring buffer: one (mean, range) per minute. Minutes are absolute (epoch minutes)."""

    def __init__(self, size: int = DEFAULT_MINUTES) -> None:
        self.size = size
        self.mean = array("f", [NAN] * size)
        self.rng = array("f", [NAN] * size)
        self.head: int | None = None       # letzte abgeschlossene Minute (absolut)
        self._cur_min: int | None = None
        self._sum = 0.0
        self._n = 0
        self._lo = math.inf
        self._hi = -math.inf
        self.last: float = NAN              # letzter Wert (für last-value-hold)

    def _store(self, minute: int, mean: float, rng: float) -> None:
        i = minute % self.size
        self.mean[i] = mean
        self.rng[i] = rng

    def _close(self) -> None:
        if self._cur_min is None:
            return
        if self._n:
            m = self._sum / self._n
            r = self._hi - self._lo if self._hi >= self._lo else 0.0
            self._store(self._cur_min, m, r)
        else:
            self._store(self._cur_min, self.last, 0.0 if self.last == self.last else NAN)
        self.head = self._cur_min
        self._cur_min = None
        self._n = 0
        self._sum = 0.0
        self._lo, self._hi = math.inf, -math.inf

    def roll(self, now_minute: int) -> None:
        """Finalise all minutes before `now_minute` (carry the last value forward)."""
        if self._cur_min is not None and now_minute > self._cur_min:
            self._close()
        if self.head is None:
            return
        gap = now_minute - 1 - self.head
        if gap <= 0:
            return
        start = self.head + 1 if gap < self.size else now_minute - self.size
        for m in range(start, now_minute):
            self._store(m, self.last, 0.0 if self.last == self.last else NAN)
        self.head = now_minute - 1

    def add(self, minute_f: float, value: float) -> None:
        """Add a sample at time `minute_f` (epoch minutes, float). NaN = unavailable."""
        minute = int(math.floor(minute_f))
        if self._cur_min is not None and minute < self._cur_min:
            return                          # zu alt (Reihenfolge)
        if self._cur_min is None or minute > self._cur_min:
            if self.head is None and self._cur_min is None:
                self.head = minute - 1
            self.roll(minute)
            self._cur_min = minute
            # Wert, der zu Beginn der Minute galt, zählt mit (Spannweite)
            if self.last == self.last and value == value:
                self._lo = min(self._lo, self.last)
                self._hi = max(self._hi, self.last)
        if value == value:
            self._sum += value
            self._n += 1
            self._lo = min(self._lo, value)
            self._hi = max(self._hi, value)
        self.last = value

    def window(self, start: int, end: int) -> tuple[list[float], list[float]]:
        """Mean and range for minutes [start, end). Unknown minutes are NaN."""
        means: list[float] = []
        rngs: list[float] = []
        head = self.head if self.head is not None else -1
        for m in range(start, end):
            if m > head or m <= head - self.size:
                if m > head and self.last == self.last and self.head is not None:
                    means.append(self.last)
                    rngs.append(0.0)
                else:
                    means.append(NAN)
                    rngs.append(NAN)
                continue
            i = m % self.size
            means.append(self.mean[i])
            rngs.append(self.rng[i])
        return means, rngs

    def to_dict(self) -> dict:
        """Compact snapshot (for restart persistence): last 36 h, rounded."""
        if self.head is None:
            return {}
        start = self.head - self.size + 1
        m, r = self.window(start, self.head + 1)
        return {"head": self.head, "m": [None if v != v else round(v, 4) for v in m],
                "r": [None if v != v else round(v, 4) for v in r], "last": None if self.last != self.last else self.last}

    @classmethod
    def from_dict(cls, d: dict | None, size: int = DEFAULT_MINUTES) -> MinuteSeries:
        s = cls(size)
        if not d or "head" not in d:
            return s
        head = int(d["head"])
        m = d.get("m") or []
        r = d.get("r") or []
        start = head - len(m) + 1
        for k, (mv, rv) in enumerate(zip(m, r)):
            s._store(start + k, NAN if mv is None else float(mv), NAN if rv is None else float(rv))
        s.head = head
        s.last = NAN if d.get("last") is None else float(d["last"])
        return s


def movement(occ_raw_range: list[float], scale: float) -> list[float]:
    """Movement 0..1 from the per-minute range of a numeric bed sensor (5-min mean, relative to the load step)."""
    n = len(occ_raw_range)
    out = [NAN] * n
    scale = max(scale, 1e-6)
    for i in range(n):
        lo = max(0, i - 2)
        hi = min(n, i + 3)
        vals = [v for v in occ_raw_range[lo:hi] if v == v]
        if not vals:
            continue
        x = (sum(vals) / len(vals)) / scale
        out[i] = max(0.0, min(1.0, x * 2.0))
    return out


def level_changes(values: list[float], thr: float) -> list[float]:
    """Movement proxy from minute-to-minute level changes (for sources without a range)."""
    out = [NAN] * len(values)
    prev = NAN
    for i, v in enumerate(values):
        if v == v and prev == prev:
            out[i] = 1.0 if abs(v - prev) >= thr else 0.0
        prev = v if v == v else prev
    return out
