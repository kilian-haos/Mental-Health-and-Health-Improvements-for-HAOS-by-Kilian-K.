"""Health score 0-100 per person and for the family (pure Python).

Components from the active modules only; weights are transparent and re-distributed when a
module is off or has no data. The cycle is context only (never a deduction).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

WEIGHTS = {
    "mood": 30, "stability": 10, "energy": 12, "health": 12, "sleep": 18, "training": 8, "weight": 5, "regularity": 5,
}


@dataclass
class HealthInput:
    moods: list[float]                 # Tageswerte (letzte 7 Tage)
    energy: list[float]
    health: list[float]
    sleep_scores: list[float]
    training_status: str | None = None  # pause | ready_soon | recommended | overdue
    overdue_days: int = 0
    weight_dist_kg: float | None = None  # |Trend - Optimum| (nur Erwachsene mit Optimum)
    checkin_rate: float | None = None    # 0..1 erledigte Check-ins (14 Tage)
    modules: dict[str, bool] | None = None


def _scale10(vals: list[float]) -> float | None:
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return (statistics.mean(v) - 1.0) / 9.0 * 100.0


def compute(inp: HealthInput) -> tuple[int | None, dict[str, int]]:
    m = inp.modules or {}
    comps: dict[str, float] = {}
    mood = _scale10(inp.moods)
    if mood is not None:
        comps["mood"] = mood
        if len([x for x in inp.moods if x is not None]) >= 3:
            sd = statistics.pstdev([x for x in inp.moods if x is not None])
            comps["stability"] = max(0.0, 100.0 - sd * 30.0)
    if m.get("energy", True):
        e = _scale10(inp.energy)
        if e is not None:
            comps["energy"] = e
    if m.get("health", True):
        h = _scale10(inp.health)
        if h is not None:
            comps["health"] = h
    if m.get("sleep_tracking", True) and inp.sleep_scores:
        comps["sleep"] = statistics.mean(inp.sleep_scores)
    if m.get("training", True) and inp.training_status:
        comps["training"] = {"pause": 100.0, "ready_soon": 95.0, "recommended": 85.0}.get(
            inp.training_status, max(30.0, 80.0 - 8.0 * inp.overdue_days))
    if m.get("weight", False) and inp.weight_dist_kg is not None:
        comps["weight"] = max(0.0, 100.0 - max(0.0, inp.weight_dist_kg - 1.0) * 8.0)
    if inp.checkin_rate is not None:
        comps["regularity"] = inp.checkin_rate * 100.0
    if "mood" not in comps:
        return None, {}
    tw = sum(WEIGHTS[k] for k in comps)
    total = sum(comps[k] * WEIGHTS[k] for k in comps) / tw
    return int(round(total)), {k: int(round(v)) for k, v in comps.items()}


def family(scores: list[int | None], k_min: int, admin: bool = False) -> int | None:
    """Mean of participating persons (equal weight). Persons only see it with >= k values."""
    vals = [s for s in scores if s is not None]
    if not vals:
        return None
    if not admin and len(vals) < max(2, k_min):
        return None
    return int(round(statistics.mean(vals)))


def family_weather(mood_mean: float | None) -> str | None:
    """Family "weather" from the family mood (1..10)."""
    if mood_mean is None:
        return None
    if mood_mean >= 8.0:
        return "sunny"
    if mood_mean >= 6.5:
        return "mostly_sunny"
    if mood_mean >= 5.0:
        return "cloudy"
    if mood_mean >= 3.5:
        return "rain"
    return "storm"
