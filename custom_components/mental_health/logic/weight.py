"""Weight: healthy range, optimum, smoothed trend, colour logic and safety rules (pure Python).

Safety rules (binding): losing weight below the healthy range is never shown as positive/green;
very fast loss or values below the healthy range show a calm, neutral hint ("best talk to a
doctor") – no praise, no streaks for losing weight. Children: no optimum, no colours, no duty.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

# Gesunder BMI-Bereich (WHO, Erwachsene 18–64): 18,5–24,9.
# Ab 65 Jahren liegt das geringste Risiko höher; häufig empfohlen wird 22–27
# (u. a. Lipschitz 1994, Prim Care 21:55–67; Winter et al. 2014, Am J Clin Nutr 99:875–890).
BMI_ADULT = (18.5, 24.9)
BMI_SENIOR = (22.0, 27.0)
SENIOR_AGE = 65

WARN_DAYS = 7
REQUIRED_DAYS = 15
OPTIMAL_TOLERANCE_KG = 1.0          # „im optimalen Bereich“ = Optimum ± 1 kg
TREND_HALF_LIFE_D = 7.0             # Glättung des Trends (exponentiell, zeitgewichtet)
FAST_LOSS_PCT_PER_WEEK = 1.0        # > 1 %/Woche über 2 Wochen = sehr schnell
MIN_PLAUSIBLE, MAX_PLAUSIBLE = 2.0, 400.0

GOOD = "good"        # grün
BAD = "bad"          # rot
NEUTRAL = "neutral"  # teal/neutral


def healthy_range(height_cm: float | None, age: int | None) -> tuple[float, float] | None:
    if not height_cm or height_cm < 100 or height_cm > 250:
        return None
    lo, hi = BMI_SENIOR if (age is not None and age >= SENIOR_AGE) else BMI_ADULT
    h = height_cm / 100.0
    return round(lo * h * h, 1), round(hi * h * h, 1)


def optimum(height_cm: float | None, age: int | None, target: float | None = None,
            child: bool = False) -> tuple[float | None, tuple[float, float] | None]:
    """(optimum kg, healthy range). A target weight is clamped to the healthy range."""
    if child:
        return None, None
    rng = healthy_range(height_cm, age)
    if rng is None:
        return None, None
    if target:
        return round(min(max(float(target), rng[0]), rng[1]), 1), rng
    return round((rng[0] + rng[1]) / 2.0, 1), rng


def clamp_target(target: float | None, height_cm: float | None, age: int | None) -> float | None:
    rng = healthy_range(height_cm, age)
    if target is None or rng is None:
        return target
    return round(min(max(float(target), rng[0]), rng[1]), 1)


def plausible(kg: float, previous: float | None = None) -> bool:
    if not (MIN_PLAUSIBLE <= kg <= MAX_PLAUSIBLE):
        return False
    if previous is not None and abs(kg - previous) > max(5.0, previous * 0.08):
        return False   # Sprung > 8 % zum letzten Wert: Ausreißer (z. B. falsche Person auf der Waage)
    return True


def to_kg(value: float, unit: str | None) -> float:
    u = (unit or "kg").strip().lower()
    if u in ("lb", "lbs", "pound", "pounds"):
        return value * 0.45359237
    if u in ("st", "stone"):
        return value * 6.35029318
    if u == "g":
        return value / 1000.0
    return value


@dataclass
class WeightSeries:
    days: list[date]
    values: list[float]    # Tageswerte (letzter Wert des Tages)

    def trend(self) -> list[float]:
        """Time-weighted exponential smoothing (gaps handled by elapsed days)."""
        out: list[float] = []
        prev_d = None
        t = None
        for d, v in zip(self.days, self.values):
            if t is None:
                t = v
            else:
                dt = max(1, (d - prev_d).days)
                a = 1.0 - math.pow(0.5, dt / TREND_HALF_LIFE_D)
                t = t + a * (v - t)
            out.append(t)
            prev_d = d
        return out


def week_average(days: list[date], values: list[float], today: date) -> float | None:
    vals = [v for d, v in zip(days, values) if 0 <= (today - d).days < 7]
    return sum(vals) / len(vals) if vals else None


def color(delta: float, current: float, opt: float | None, rng: tuple[float, float] | None) -> str:
    """Colour for a change `delta` (kg) given the current trend value and the optimum.

    Below the optimum: + is good, − is bad. Above: + bad, − good. Within ±tolerance: neutral.
    Below the healthy range a loss is never good (it is bad).
    """
    if opt is None or abs(delta) < 0.05:
        return NEUTRAL
    if abs(current - opt) <= OPTIMAL_TOLERANCE_KG:
        return NEUTRAL
    if rng is not None and current < rng[0] and delta < 0:
        return BAD
    if current < opt:
        return GOOD if delta > 0 else BAD
    return BAD if delta > 0 else GOOD


@dataclass
class WeightSummary:
    trend: float | None
    week_avg: float | None
    delta_week: float | None
    delta_opt: float | None
    optimum: float | None
    range: tuple[float, float] | None
    color_week: str
    color_opt: str
    hint: str | None          # None | below_range | fast_loss | add_height
    days_since: int | None
    due: str                  # none | warn | required


def summarize(days: list[date], values: list[float], today: date, *, height_cm: float | None,
              age: int | None, target: float | None, child: bool, required_served: date | None = None,
              tracking_since: date | None = None) -> WeightSummary:
    opt, rng = optimum(height_cm, age, target, child)
    tr = WeightSeries(days, values).trend() if values else []
    cur = tr[-1] if tr else None
    wk = week_average(days, tr, today) if tr else None
    d_week = (cur - wk) if (cur is not None and wk is not None) else None
    d_opt = (cur - opt) if (cur is not None and opt is not None) else None
    hint = None
    if not child and cur is not None:
        if rng is not None and cur < rng[0]:
            hint = "below_range"
        elif _fast_loss(days, tr, today):
            hint = "fast_loss"
    if not child and rng is None and not height_cm:
        hint = hint or "add_height"
    if child:
        c_week = c_opt = NEUTRAL
    else:
        c_week = color(d_week or 0.0, cur or 0.0, opt, rng) if d_week is not None else NEUTRAL
        # Abstand zum Optimum: Richtung „zum Optimum hin“ ist gut -> Abstand selbst neutral, außer unter dem Bereich
        c_opt = NEUTRAL if (d_opt is None or abs(d_opt) <= OPTIMAL_TOLERANCE_KG) else (
            BAD if (rng is not None and cur is not None and cur < rng[0]) else NEUTRAL)
    last = days[-1] if days else None
    since = (today - last).days if last else ((today - tracking_since).days if tracking_since else None)
    due = due_state(since, child, required_served, last)
    return WeightSummary(
        trend=round(cur, 2) if cur is not None else None, week_avg=round(wk, 2) if wk is not None else None,
        delta_week=round(d_week, 2) if d_week is not None else None,
        delta_opt=round(d_opt, 2) if d_opt is not None else None,
        optimum=opt, range=rng, color_week=c_week, color_opt=c_opt, hint=hint, days_since=since, due=due,
    )


def _fast_loss(days: list[date], trend: list[float], today: date) -> bool:
    if len(trend) < 2:
        return False
    old = None
    for d, v in zip(days, trend):
        if 12 <= (today - d).days <= 16:
            old = v
    if old is None:
        return False
    pct_per_week = (old - trend[-1]) / old * 100.0 / 2.0
    return pct_per_week > FAST_LOSS_PCT_PER_WEEK


def due_state(days_since: int | None, child: bool, required_served: date | None = None,
              last_value: date | None = None) -> str:
    """none | warn (>= 7 days) | required (>= 15 days, once – until a value is entered)."""
    if child or days_since is None:
        return "none"
    if days_since >= REQUIRED_DAYS:
        # „einmalig Pflicht“: wurde im aktuellen Zeitraum schon einmal eingefordert und trotzdem
        # nichts eingetragen (nicht möglich, da Pflichtfeld), gilt wieder nur die Warnung.
        if required_served is not None and (last_value is None or required_served > last_value):
            return "warn"
        return "required"
    if days_since >= WARN_DAYS:
        return "warn"
    return "none"
