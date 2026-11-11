"""Menstrual cycle: period detection from check-in answers, learned prediction (pure Python).

Not a contraceptive method and not a medical device – an orientation only.

Starting values: 28-day cycle, 5-day period. Variability is larger in teenagers (cycles are
often irregular in the first years after menarche, ACOG Committee Opinion 651, 2015) and in
the years before menopause. Learned: exponentially weighted mean and spread of the person's
own cycle lengths and period durations. With a (basal) temperature source the post-ovulation
rise (+0.2–0.5 °C, "3 over 6" rule) refines the next start: luteal phase ≈ 14 ± 2 days,
learned per person when earlier cycles show a rise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

PRIOR_CYCLE = 28.0
PRIOR_PERIOD = 5.0
PRIOR_LUTEAL = 14.0
MIN_CYCLE, MAX_CYCLE = 15, 60
GAP_NEW_PERIOD = 10          # Tage ohne Blutung, ab denen ein neuer Beginn zählt
MAX_OPEN_PERIOD = 10         # „aktiv“ ohne „vorbei“ gilt höchstens so lange
WEIGHT_DECAY = 0.85          # neuere Zyklen zählen mehr

ANSWERS = ("no", "yes", "started", "ended")


def prior_spread(age: int | None) -> float:
    if age is None:
        return 3.5
    if age < 20:
        return 7.0
    if age >= 45:
        return 6.0
    return 3.5


@dataclass
class Period:
    start: date
    end: date | None      # None = läuft noch


def collapse_day(answers: list[str]) -> str:
    """Several answers on one day (morning + evening) -> one value.

    'last' = bleeding on this day and over by the end of it.
    """
    bleeding = started = ended = ended_after = False
    for a in answers:
        if a in ("yes", "started", "last"):
            bleeding = True
            started = started or a == "started"
            ended_after = a == "last"
        elif a == "ended":
            if bleeding:
                ended_after = True
            else:
                ended = True
    if bleeding and ended_after:
        return "last"
    if started:
        return "started"
    if bleeding:
        return "yes"
    if ended:
        return "ended"
    return "no"


def periods_from_days(reports: dict[date, str]) -> list[Period]:
    """Build periods from per-day answers (one value per day, see collapse_day)."""
    out: list[Period] = []
    cur: Period | None = None
    last_bleed: date | None = None
    for d in sorted(reports):
        a = reports[d]
        bleeding = a in ("yes", "started", "last")
        if bleeding:
            new = (
                cur is None
                or last_bleed is None
                or (d - last_bleed).days > GAP_NEW_PERIOD
                or (a == "started" and (d - cur.start).days > 3)
            )
            if new:
                if cur is not None and cur.end is None:
                    cur.end = last_bleed or cur.start
                cur = Period(d, None)
                out.append(cur)
            elif cur is not None and cur.end is not None:
                cur.end = None          # „vorbei“ war zu früh gemeldet: Periode läuft weiter
            last_bleed = d
            if a == "last" and cur is not None:
                cur.end = d
        elif a in ("ended", "no") and cur is not None and cur.end is None and last_bleed is not None:
            cur.end = last_bleed
    return out


def _wstats(values: list[float]) -> tuple[float, float, float]:
    """Exponentially weighted mean/spread, newest last. Returns (mean, sd, weight sum)."""
    if not values:
        return 0.0, 0.0, 0.0
    ws = [WEIGHT_DECAY ** (len(values) - 1 - i) for i in range(len(values))]
    sw = sum(ws)
    m = sum(w * v for w, v in zip(ws, values)) / sw
    var = sum(w * (v - m) ** 2 for w, v in zip(ws, values)) / sw
    return m, math.sqrt(var), sw


def detect_temp_shift(temps: dict[date, float], since: date) -> date | None:
    """'3 over 6': first day of 3 consecutive values >= 0.2 °C above the max of the 6 before."""
    days = sorted(d for d in temps if d >= since)
    vals = [temps[d] for d in days]
    for i in range(6, len(vals) - 2):
        base = max(vals[i - 6:i])
        if all(vals[i + k] >= base + 0.2 for k in range(3)) and (days[i + 2] - days[i - 6]).days <= 12:
            return days[i]
    return None


@dataclass
class CyclePrediction:
    next_start: date | None
    next_end: date | None
    window_days: float          # ± Unsicherheit in Tagen
    cycle_len: float
    period_len: float
    active: bool
    current_day: int | None     # Zyklustag (1 = erster Blutungstag)
    phase: str | None           # menstrual | follicular | ovulation | luteal
    confidence: float           # 0..1
    cycles_learned: int
    temp_shift: date | None


def predict(reports: dict[date, str], today: date, *, age: int | None = None,
            temps: dict[date, float] | None = None) -> CyclePrediction:
    periods = periods_from_days(reports)
    starts = [p.start for p in periods]
    lengths = [(b - a).days for a, b in zip(starts, starts[1:]) if MIN_CYCLE <= (b - a).days <= MAX_CYCLE]
    plens = [((p.end - p.start).days + 1) for p in periods if p.end is not None and 1 <= (p.end - p.start).days + 1 <= 12]
    m, sd, sw = _wstats([float(x) for x in lengths[-12:]])
    k = min(1.0, sw / 4.0)      # nach ~4 Zyklen überwiegt das Gelernte
    cyc = (1 - k) * PRIOR_CYCLE + k * m if lengths else PRIOR_CYCLE
    spread = (1 - k) * prior_spread(age) + k * max(1.0, sd) if lengths else prior_spread(age)
    pm, _, psw = _wstats([float(x) for x in plens[-12:]])
    pk = min(1.0, psw / 3.0)
    plen = (1 - pk) * PRIOR_PERIOD + pk * pm if plens else PRIOR_PERIOD

    active = False
    if periods:
        last = periods[-1]
        if last.end is None and (today - last.start).days < MAX_OPEN_PERIOD:
            active = True
        elif last.end is not None and last.start <= today <= last.end:
            active = True
    if not starts:
        return CyclePrediction(None, None, spread, round(cyc, 1), round(plen, 1), active, None, None, 0.0, 0, None)

    last_start = starts[-1]
    # Lutealphase aus früheren Zyklen mit Temperaturanstieg lernen
    shift = None
    luteal = PRIOR_LUTEAL
    if temps:
        lut: list[float] = []
        for a, b in zip(starts, starts[1:]):
            s = detect_temp_shift({d: v for d, v in temps.items() if a <= d < b}, a)
            if s is not None:
                lut.append(float((b - s).days + 1))
        if lut:
            lm, _, lsw = _wstats(lut[-8:])
            lk = min(1.0, lsw / 3.0)
            luteal = (1 - lk) * PRIOR_LUTEAL + lk * lm
        shift = detect_temp_shift({d: v for d, v in temps.items() if d >= last_start}, last_start)

    if shift is not None:
        nxt = shift + timedelta(days=round(luteal) - 1)
        spread = min(spread, 2.0)
    else:
        nxt = last_start + timedelta(days=round(cyc))
        # schon überfällig? -> Prognose rollt mit (morgen), Unsicherheit wächst
        while nxt < today and not active:
            nxt = today
            spread += 1.0
            break
    if active and periods[-1].end is None:
        nxt_after = last_start + timedelta(days=round(cyc))
        nxt = nxt_after
    cday = (today - last_start).days + 1
    phase = _phase(cday, cyc, plen, luteal)
    conf = max(0.05, min(0.95, (1.0 - spread / 10.0) * (0.4 + 0.6 * k)))
    return CyclePrediction(
        next_start=nxt, next_end=nxt + timedelta(days=round(plen) - 1), window_days=round(spread, 1),
        cycle_len=round(cyc, 1), period_len=round(plen, 1), active=active, current_day=cday if cday <= 90 else None,
        phase=phase if cday <= 90 else None, confidence=round(conf, 2), cycles_learned=len(lengths), temp_shift=shift,
    )


def _phase(cday: int, cyc: float, plen: float, luteal: float) -> str:
    ovu = cyc - luteal
    if cday <= plen:
        return "menstrual"
    if cday < ovu - 1:
        return "follicular"
    if cday <= ovu + 1:
        return "ovulation"
    return "luteal"
