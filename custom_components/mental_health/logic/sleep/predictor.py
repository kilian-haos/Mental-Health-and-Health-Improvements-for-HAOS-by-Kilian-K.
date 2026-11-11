"""Bedtime / wake-up prediction per person (pure Python).

Weighted circular mean with spread, separately for workdays and days off (once there are
enough nights of each), corrected by an alarm entity when one is set.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from ..daymath import circ_diff, circ_mean_minutes

HALF_LIFE_NIGHTS = 14.0
MIN_PER_GROUP = 3


@dataclass
class NightTimes:
    bed: float | None          # Minute des Tages (lokal)
    wake: float | None
    workday: bool
    age: int                   # Nächte zurück (0 = letzte Nacht)
    alarm: float | None = None


@dataclass
class Prediction:
    bed: float | None
    wake: float | None
    bed_spread: float
    wake_spread: float
    confidence: float
    n: int


def predict(history: list[NightTimes], workday: bool, alarm_tod: float | None = None) -> Prediction:
    same = [h for h in history if h.workday == workday]
    group = same if len(same) >= MIN_PER_GROUP else history
    if not group:
        return Prediction(None, None, 0.0, 0.0, 0.0, 0)
    w = [math.pow(0.5, h.age / HALF_LIFE_NIGHTS) for h in group]
    beds = [(h.bed, wi) for h, wi in zip(group, w) if h.bed is not None]
    wakes = [(h.wake, wi) for h, wi in zip(group, w) if h.wake is not None]
    bed, bsp = circ_mean_minutes([b for b, _ in beds], [x for _, x in beds]) if beds else (None, 0.0)
    wake, wsp = circ_mean_minutes([b for b, _ in wakes], [x for _, x in wakes]) if wakes else (None, 0.0)
    if alarm_tod is not None and wake is not None and -150 <= circ_diff(alarm_tod, wake) <= 90:
        # Abstand Wecker -> Aufstehen lernen (Schlummern)
        deltas = [circ_diff(h.wake, h.alarm) for h in group if h.alarm is not None and h.wake is not None]
        snooze = sum(deltas) / len(deltas) if deltas else 5.0
        wake = (alarm_tod + max(0.0, min(60.0, snooze))) % 1440
        wsp = min(wsp, 15.0)
    n = len(group)
    conf = max(0.0, min(1.0, (n / 10.0) * (1.0 - min(1.0, (bsp + wsp) / 240.0))))
    return Prediction(bed, wake, round(bsp, 1), round(wsp, 1), round(conf, 2), n)
