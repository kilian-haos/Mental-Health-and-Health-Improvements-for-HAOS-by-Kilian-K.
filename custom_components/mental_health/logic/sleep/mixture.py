"""Level model for numeric bed sensors: Gaussian mixture via EM over a decaying histogram.

The model learns from the value distribution itself:
* the **baseline** (empty bed) – the component that dominates during the day,
* the **direction** (does the value fall or rise under load?),
* the **load levels** (1 person, 2 persons for shared beds),
* a **threshold** between baseline and the first load level (shown as "learned: 2.45 V").

A histogram with exponential decay keeps it robust against baseline drift (temperature,
mattress settling) and keeps memory constant (`array('f')`, 96 bins).
"""
from __future__ import annotations

import math
from array import array
from dataclasses import dataclass

BINS = 96
HALF_LIFE_MIN = 60 * 24 * 10      # Histogramm vergisst mit Halbwertszeit 10 Tage
MIN_SD_FRAC = 0.01                # min. Streuung relativ zur Spannweite


@dataclass
class Comp:
    w: float
    mu: float
    sd: float


class LevelModel:
    def __init__(self, lo: float | None = None, hi: float | None = None, k: int = 2) -> None:
        self.lo = lo
        self.hi = hi
        self.k = k                       # 2 = Bett leer/belegt, 3 = geteiltes Bett (0/1/2 Personen)
        self.hist = array("f", bytes(4 * BINS))
        self.day_hist = array("f", bytes(4 * BINS))   # nur Tageswerte (10–18 Uhr) -> Grundlinie
        self.comps: list[Comp] = []
        self.baseline_idx = 0
        self.user_threshold: float | None = None
        self.user_direction: int | None = None        # -1 fällt bei Belastung, +1 steigt
        self.n = 0.0
        self._decay = math.pow(0.5, 1.0 / HALF_LIFE_MIN)

    # ---------------------------------------------------------- Histogramm
    def _bin(self, x: float) -> int:
        span = (self.hi - self.lo) or 1.0
        return max(0, min(BINS - 1, int((x - self.lo) / span * BINS)))

    def _center(self, i: int) -> float:
        span = (self.hi - self.lo) or 1.0
        return self.lo + (i + 0.5) * span / BINS

    def _rescale(self, x: float) -> None:
        """Wertebereich erweitern (Histogramm umrastern, keine Daten verlieren)."""
        if self.lo is None or self.hi is None:
            self.lo, self.hi = x - 0.5, x + 0.5
            return
        if self.lo <= x <= self.hi:
            return
        new_lo = min(self.lo, x)
        new_hi = max(self.hi, x)
        pad = (new_hi - new_lo) * 0.05
        new_lo -= pad
        new_hi += pad
        for name in ("hist", "day_hist"):
            old = getattr(self, name)
            centers = [self._center(i) for i in range(BINS)]
            fresh = array("f", bytes(4 * BINS))
            span = new_hi - new_lo
            for c, v in zip(centers, old):
                if v:
                    j = max(0, min(BINS - 1, int((c - new_lo) / span * BINS)))
                    fresh[j] += v
            setattr(self, name, fresh)
        self.lo, self.hi = new_lo, new_hi

    def add(self, x: float, minutes: float = 1.0, daytime: bool = False) -> None:
        if x != x or math.isinf(x):
            return
        self._rescale(x)
        f = math.pow(self._decay, minutes)
        h = self.hist
        for i in range(BINS):
            h[i] *= f
        h[self._bin(x)] += minutes
        if daytime:
            dh = self.day_hist
            for i in range(BINS):
                dh[i] *= f
            dh[self._bin(x)] += minutes
        self.n = self.n * f + minutes

    # ---------------------------------------------------------- EM
    def fit(self, iters: int = 30) -> None:
        if self.lo is None or self.n < 30:
            return
        xs = [self._center(i) for i in range(BINS)]
        ws = list(self.hist)
        tot = sum(ws) or 1.0
        span = (self.hi - self.lo) or 1.0
        min_sd = max(1e-6, span * MIN_SD_FRAC)
        if not self.comps or len(self.comps) != self.k:
            self.comps = self._init(xs, ws, tot)
        comps = self.comps
        for _ in range(iters):
            acc = [[0.0, 0.0, 0.0] for _ in comps]
            for x, w in zip(xs, ws):
                if w <= 0:
                    continue
                ps = [c.w * _pdf(x, c.mu, c.sd) for c in comps]
                s = sum(ps) or 1e-300
                for j, p in enumerate(ps):
                    r = w * p / s
                    acc[j][0] += r
                    acc[j][1] += r * x
                    acc[j][2] += r * x * x
            for j, c in enumerate(comps):
                n, sx, sxx = acc[j]
                if n < 1e-6:
                    continue
                mu = sx / n
                var = max(min_sd * min_sd, sxx / n - mu * mu)
                c.w, c.mu, c.sd = n / tot, mu, math.sqrt(var)
        comps.sort(key=lambda c: c.mu)
        self._pick_baseline()

    def _init(self, xs: list[float], ws: list[float], tot: float) -> list[Comp]:
        mode = xs[max(range(BINS), key=lambda i: ws[i])]
        span = self.hi - self.lo
        out = [Comp(0.7, mode, span * 0.03)]
        # weitere Komponenten in der Richtung mit der meisten Masse abseits der Grundlinie
        below = sum(w for x, w in zip(xs, ws) if x < mode - span * 0.1)
        above = sum(w for x, w in zip(xs, ws) if x > mode + span * 0.1)
        sign = self.user_direction or (-1 if below >= above else 1)
        for j in range(1, self.k):
            out.append(Comp(0.3 / (self.k - 1), mode + sign * span * 0.3 * j, span * 0.1))
        return out

    def _pick_baseline(self) -> None:
        if not self.comps:
            return
        dh = list(self.day_hist)
        if sum(dh) > 30:
            xs = [self._center(i) for i in range(BINS)]
            m = sum(x * w for x, w in zip(xs, dh)) / sum(dh)
            self.baseline_idx = min(range(len(self.comps)), key=lambda j: abs(self.comps[j].mu - m))
        else:
            self.baseline_idx = max(range(len(self.comps)), key=lambda j: self.comps[j].w)

    # ---------------------------------------------------------- Auswertung
    @property
    def ready(self) -> bool:
        return len(self.comps) == self.k

    @property
    def baseline(self) -> float | None:
        return self.comps[self.baseline_idx].mu if self.ready else None

    @property
    def direction(self) -> int:
        if self.user_direction:
            return self.user_direction
        if not self.ready:
            return -1
        b = self.comps[self.baseline_idx]
        others = [c for j, c in enumerate(self.comps) if j != self.baseline_idx]
        far = max(others, key=lambda c: c.w * abs(c.mu - b.mu))
        return -1 if far.mu < b.mu else 1

    def load_levels(self) -> list[Comp]:
        """Components beyond the baseline in load direction, nearest first."""
        if not self.ready:
            return []
        b = self.comps[self.baseline_idx]
        d = self.direction
        out = [c for j, c in enumerate(self.comps) if j != self.baseline_idx and (c.mu - b.mu) * d > 0]
        return sorted(out, key=lambda c: abs(c.mu - b.mu))

    def learned_threshold(self) -> float | None:
        if not self.ready:
            return None
        b = self.comps[self.baseline_idx]
        lv = self.load_levels()
        if not lv:
            return None
        c = lv[0]
        # Schnittpunkt nach Streuungen gewichtet (näher an der schmaleren Komponente)
        t = b.mu + (c.mu - b.mu) * b.sd / (b.sd + c.sd)
        # mindestens 3 sd von der Grundlinie weg (Rauschen)
        min_off = 3.0 * b.sd
        if abs(t - b.mu) < min_off:
            t = b.mu + math.copysign(min_off, c.mu - b.mu)
        return t

    def threshold(self) -> float | None:
        """Effective threshold: user prior blended with the learned one (prior wins early)."""
        lt = self.learned_threshold()
        if self.user_threshold is None:
            return lt
        if lt is None:
            return self.user_threshold
        k = min(0.7, self.n / (60 * 24 * 14) * 0.7)   # Prior verliert langsam an Gewicht (max. 70 % gelernt)
        return (1 - k) * self.user_threshold + k * lt

    def occupancy(self, x: float) -> float:
        """Probability that the bed is loaded at value x (0..1)."""
        if x != x:
            return 0.5
        t = self.threshold()
        if t is None:
            return 0.5
        b = self.baseline if self.baseline is not None else t + 1.0
        d = self.direction
        sd = self.comps[self.baseline_idx].sd if self.ready else abs(b - t) / 3 or 0.1
        scale = max(abs(b - t) / 3.0, sd, 1e-6)
        z = (x - t) * d / scale
        return 1.0 / (1.0 + math.exp(-z * 2.0))

    def persons(self, x: float) -> int:
        """Shared bed: 0, 1 or 2 persons by nearest level."""
        if not self.ready:
            return 1 if self.occupancy(x) > 0.5 else 0
        levels = [self.comps[self.baseline_idx]] + self.load_levels()
        j = min(range(len(levels)), key=lambda i: abs(levels[i].mu - x) / max(levels[i].sd, 1e-6))
        return min(j, 2)

    # ---------------------------------------------------------- Speicher
    def to_dict(self) -> dict:
        return {
            "lo": self.lo, "hi": self.hi, "k": self.k, "n": round(self.n, 1),
            "hist": [round(v, 2) for v in self.hist], "day": [round(v, 2) for v in self.day_hist],
            "comps": [[round(c.w, 4), round(c.mu, 4), round(c.sd, 5)] for c in self.comps],
            "base": self.baseline_idx, "uth": self.user_threshold, "udir": self.user_direction,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> LevelModel:
        d = d or {}
        m = cls(d.get("lo"), d.get("hi"), int(d.get("k", 2)))
        for name, key in (("hist", "hist"), ("day_hist", "day")):
            vals = d.get(key) or []
            if len(vals) == BINS:
                setattr(m, name, array("f", [float(v) for v in vals]))
        m.comps = [Comp(*map(float, c)) for c in (d.get("comps") or []) if len(c) == 3]
        m.baseline_idx = int(d.get("base", 0)) if m.comps else 0
        m.n = float(d.get("n", 0.0))
        m.user_threshold = d.get("uth")
        m.user_direction = d.get("udir")
        return m

    def summary(self) -> dict:
        return {
            "baseline": _r(self.baseline), "threshold": _r(self.threshold()), "learned": _r(self.learned_threshold()),
            "direction": self.direction, "levels": [_r(c.mu) for c in self.load_levels()], "minutes": round(self.n),
        }


def _r(v: float | None) -> float | None:
    return None if v is None else round(v, 3)


def _pdf(x: float, mu: float, sd: float) -> float:
    z = (x - mu) / sd
    return math.exp(-0.5 * z * z) / (sd * 2.5066282746310002)
