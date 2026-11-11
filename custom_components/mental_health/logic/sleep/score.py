"""Sleep score 0-100, optimal sleep duration and "sleepmaxing" (pure Python).

Recommended sleep durations (hours):
  National Sleep Foundation – Hirshkowitz et al. 2015, Sleep Health 1:40-43;
  AASM consensus – Paruthi et al. 2016, J Clin Sleep Med 12:785-786 (children/teens).
The personal optimum is learned: the duration after which mood, energy and the feeling of
health on the next day are best – regularised towards the middle of the recommendation,
always kept inside the recommended range, adapting slowly.
Sex: women report a slightly longer sleep need on average (≈ +10 min; e.g. Burgard & Ailshire
2013, Am Sociol Rev 78:51-69) – used only as a small starting nudge. Body weight is *not*
used: there is no robust evidence for a weight-based sleep need.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

AGE_RANGES = (  # (bis Alter inkl., min h, max h)
    (5, 10.0, 13.0),
    (13, 9.0, 11.0),
    (17, 8.0, 10.0),
    (64, 7.0, 9.0),
    (200, 7.0, 8.0),
)
WEIGHTS = {"duration": 35, "regularity": 20, "interruptions": 15, "latency": 10, "subjective": 20}


def recommended_range(age: int | None) -> tuple[float, float]:
    if age is None:
        return 7.0, 9.0
    for upto, lo, hi in AGE_RANGES:
        if age <= upto:
            return lo, hi
    return 7.0, 8.0


def start_optimum(age: int | None, sex: str | None) -> float:
    lo, hi = recommended_range(age)
    opt = (lo + hi) / 2.0
    if sex == "female":
        opt += 10 / 60
    return min(hi, max(lo, opt))


def learn_optimum(age: int | None, sex: str | None, pairs: list[tuple[float, float]]) -> tuple[float, float]:
    """pairs: (duration h, next-day wellbeing 1..10). Returns (optimum h, confidence 0..1).

    Weighted ridge fit of wellbeing = a + b·d + c·d² (d centred at the start optimum),
    regularised towards "no effect", then argmax inside the recommended range.
    """
    lo, hi = recommended_range(age)
    o0 = start_optimum(age, sex)
    pts = [(d, y) for d, y in pairs if 3.0 <= d <= 14.0 and 1.0 <= y <= 10.0]
    n = len(pts)
    if n < 14:
        return round(o0, 2), round(min(0.3, n / 50), 2)
    # Normalgleichungen (3x3) mit Ridge
    lam = 8.0
    xs = [(1.0, d - o0, (d - o0) ** 2) for d, _ in pts]
    ys = [y for _, y in pts]
    ata = [[sum(x[i] * x[j] for x in xs) + (lam if i > 0 and i == j else 0.0) for j in range(3)] for i in range(3)]
    aty = [sum(x[i] * y for x, y in zip(xs, ys)) for i in range(3)]
    try:
        a, b, c = _solve3(ata, aty)
    except ZeroDivisionError:
        return round(o0, 2), 0.2
    if c < -1e-4:
        peak = o0 - b / (2 * c)
    else:
        peak = o0 + (0.5 if b > 0 else -0.5 if b < 0 else 0.0)
    k = min(0.7, n / 90.0)
    opt = (1 - k) * o0 + k * peak
    opt = min(hi, max(lo, opt))
    return round(opt, 2), round(min(0.9, 0.3 + n / 120), 2)


def _solve3(m: list[list[float]], v: list[float]) -> tuple[float, float, float]:
    a = [row[:] + [v[i]] for i, row in enumerate(m)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-12:
            raise ZeroDivisionError
        a[col], a[piv] = a[piv], a[col]
        for r in range(3):
            if r != col:
                f = a[r][col] / a[col][col]
                for k in range(col, 4):
                    a[r][k] -= f * a[col][k]
    return tuple(a[i][3] / a[i][i] for i in range(3))  # type: ignore[return-value]


@dataclass
class ScoreInput:
    asleep_min: float
    optimum_h: float
    bed_dev_min: float | None = None        # Abweichung von der üblichen Zubettgehzeit
    wake_dev_min: float | None = None
    interruptions: int = 0
    interruption_min: float = 0.0
    latency_min: float | None = None
    subjective: int | None = None           # 1..10
    nap_min: float = 0.0


def score(inp: ScoreInput) -> tuple[int, dict[str, int]]:
    """Total 0..100 and the components (0..100 each; missing ones are left out and re-weighted)."""
    comps: dict[str, float] = {}
    eff = inp.asleep_min + min(inp.nap_min, 90.0) * 0.5
    opt = inp.optimum_h * 60.0
    dev = eff - opt
    sigma = 60.0 if dev < 0 else 90.0
    comps["duration"] = 100.0 * math.exp(-0.5 * (dev / sigma) ** 2)
    devs = [d for d in (inp.bed_dev_min, inp.wake_dev_min) if d is not None]
    if devs:
        comps["regularity"] = 100.0 * math.exp(-(sum(abs(d) for d in devs) / len(devs)) / 60.0)
    comps["interruptions"] = max(0.0, 100.0 - 8.0 * inp.interruptions - 0.8 * inp.interruption_min)
    if inp.latency_min is not None:
        comps["latency"] = 100.0 if inp.latency_min <= 20 else max(0.0, 100.0 - (inp.latency_min - 20) * 2.0)
    if inp.subjective is not None:
        comps["subjective"] = (inp.subjective - 1) / 9.0 * 100.0
    tw = sum(WEIGHTS[k] for k in comps)
    total = sum(comps[k] * WEIGHTS[k] for k in comps) / tw if tw else 0.0
    return int(round(total)), {k: int(round(v)) for k, v in comps.items()}


GOOD = "good"
BAD = "bad"
NEUTRAL = "neutral"


def sleepmaxing(last_min: float, week_avg_min: float | None, optimum_h: float) -> dict:
    """+x % vs the weekly average and vs the optimum, coloured by direction to the optimum."""
    opt = optimum_h * 60.0
    out: dict = {"optimum_min": round(opt), "last_min": round(last_min)}
    if week_avg_min:
        out["week_pct"] = round((last_min - week_avg_min) / week_avg_min * 100.0)
        before = abs(week_avg_min - opt)
        now = abs(last_min - opt)
        if now < before - 5:
            out["week_color"] = GOOD
        elif now > before + 5:
            out["week_color"] = BAD
        else:
            out["week_color"] = NEUTRAL
    else:
        out["week_pct"] = None
        out["week_color"] = NEUTRAL
    out["opt_pct"] = round((last_min - opt) / opt * 100.0) if opt else None
    out["opt_color"] = GOOD if abs(last_min - opt) <= 15 else BAD
    return out
