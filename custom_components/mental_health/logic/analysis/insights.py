"""Gentle, concrete insights from one's own data – no diagnoses (pure Python).

Every insight is {"key", "params", "tone"} – the card translates the key (de/en).
Tone: good | info | care.
"""
from __future__ import annotations

import random
import statistics
from datetime import date, timedelta

from .text import content_stems, learned_terms, stem, topic_effects, topics

MIN_GROUP = 5


def _d(rec: dict) -> date:
    return date.fromisoformat(rec["day"])


def _texts(rec: dict) -> str:
    return " ".join(list(rec.get("good") or []) + list(rec.get("bad") or []) + [rec.get("journal") or ""])


def best_day_words(records: list[dict]) -> dict | None:
    rated = [r for r in records if r.get("mood") is not None and _texts(r).strip()]
    if len(rated) < 14:
        return None
    rated.sort(key=lambda r: r["mood"], reverse=True)
    top = rated[: max(4, len(rated) // 4)]
    rest = rated[len(top):]
    def freq(rs: list[dict]) -> dict[str, float]:
        c: dict[str, int] = {}
        for r in rs:
            for t in topics(_texts(r)) | {f"w:{s}" for s in set(content_stems(_texts(r)))}:
                c[t] = c.get(t, 0) + 1
        return {k: v / len(rs) for k, v in c.items()}
    ft, fr = freq(top), freq(rest)
    terms = {t["stem"]: t["word"] for t in learned_terms({r["day"]: _texts(r) for r in rated}, 3)}
    cand = []
    for k, v in ft.items():
        if v < 0.3:
            continue
        lift = v - fr.get(k, 0.0)
        if lift < 0.2:
            continue
        if k.startswith("w:"):
            word = terms.get(k[2:])
            if not word:
                continue
            cand.append((lift, {"word": word}))
        else:
            cand.append((lift + 0.05, {"topic": k}))
    if not cand:
        return None
    cand.sort(key=lambda x: x[0], reverse=True)
    return {"key": "i_best_days", "params": {"items": [c for _, c in cand[:2]]}, "tone": "good"}


def sleep_effect(records: list[dict], cut_h: float = 6.5) -> dict | None:
    short = [r["mood"] for r in records if r.get("sleep_h") is not None and r["sleep_h"] < cut_h and r.get("mood") is not None]
    ok = [r["mood"] for r in records if r.get("sleep_h") is not None and r["sleep_h"] >= cut_h and r.get("mood") is not None]
    if len(short) < MIN_GROUP or len(ok) < MIN_GROUP:
        return None
    diff = statistics.mean(ok) - statistics.mean(short)
    if diff < 0.8:
        return None
    return {"key": "i_sleep_mood", "params": {"hours": cut_h, "diff": round(diff, 1)}, "tone": "info"}


def training_energy(records: list[dict]) -> dict | None:
    by_day = {r["day"]: r for r in records}
    after, other = [], []
    for r in records:
        prev = by_day.get((_d(r) - timedelta(days=1)).isoformat())
        if r.get("energy") is None or prev is None or prev.get("trained") is None:
            continue
        (after if prev["trained"] else other).append(r["energy"])
    if len(after) < MIN_GROUP or len(other) < MIN_GROUP:
        return None
    diff = statistics.mean(after) - statistics.mean(other)
    if abs(diff) < 0.7:
        return None
    return {"key": "i_training_energy_up" if diff > 0 else "i_training_energy_down",
            "params": {"diff": round(abs(diff), 1)}, "tone": "info"}


def weekday_pattern(records: list[dict]) -> dict | None:
    by: dict[int, list[float]] = {}
    for r in records:
        if r.get("mood") is not None:
            by.setdefault(_d(r).weekday(), []).append(r["mood"])
    means = {k: statistics.mean(v) for k, v in by.items() if len(v) >= 3}
    if len(means) < 5:
        return None
    best = max(means, key=means.get)
    worst = min(means, key=means.get)
    if means[best] - means[worst] < 1.0:
        return None
    return {"key": "i_weekday", "params": {"best": best, "worst": worst, "diff": round(means[best] - means[worst], 1)},
            "tone": "info"}


def morning_evening(records: list[dict]) -> dict | None:
    d = [r["mood_e"] - r["mood_m"] for r in records if r.get("mood_m") is not None and r.get("mood_e") is not None]
    if len(d) < 10:
        return None
    m = statistics.mean(d)
    if abs(m) < 0.7:
        return None
    return {"key": "i_day_up" if m > 0 else "i_day_down", "params": {"diff": round(abs(m), 1)}, "tone": "info"}


def goals_tracker(records: list[dict]) -> list[dict]:
    """Recurring goals (by stem signature) with success rate."""
    groups: dict[str, dict] = {}
    for r in records:
        for g in r.get("goal_results") or []:
            sig = " ".join(sorted(set(content_stems(g.get("text") or ""))))[:60] or stem(g.get("text") or "")
            if not sig:
                continue
            e = groups.setdefault(sig, {"text": g.get("text"), "n": 0, "done": 0, "partly": 0, "not": 0, "last": r["day"]})
            e["n"] += 1
            res = g.get("result")
            if res in ("done", "partly", "not"):
                e[res] += 1
            e["last"] = max(e["last"], r["day"])
            e["text"] = g.get("text") or e["text"]
    out = []
    for e in groups.values():
        rate = (e["done"] + 0.5 * e["partly"]) / e["n"] if e["n"] else 0.0
        out.append({**e, "rate": round(rate, 2), "recurring": e["n"] >= 3})
    out.sort(key=lambda x: (-x["n"], x["text"] or ""))
    return out[:20]


def goal_insight(records: list[dict]) -> dict | None:
    rec = [g for g in goals_tracker(records) if g["recurring"]]
    if not rec:
        return None
    g = rec[0]
    return {"key": "i_goal", "params": {"text": g["text"], "done": g["done"], "n": g["n"]}, "tone": "good"}


def low_mood_alert(records: list[dict], today: date, days: int, max_mood: float) -> bool:
    """Protective hint: the last `days` days with data all have mood <= max_mood (only own dashboard)."""
    recent = []
    for i in range(days + 2):
        d = (today - timedelta(days=i)).isoformat()
        r = next((x for x in records if x["day"] == d), None)
        if r is not None and r.get("mood") is not None:
            recent.append(r["mood"])
        if len(recent) >= days:
            break
    return len(recent) >= days and all(m <= max_mood for m in recent)


def on_this_day(records: list[dict], today: date) -> list[dict]:
    out = []
    by = {r["day"]: r for r in records}
    for key, delta in (("month", _month_ago(today)), ("year", _year_ago(today))):
        r = by.get(delta.isoformat())
        if r and (r.get("good") or r.get("mood") is not None):
            out.append({"when": key, "day": r["day"], "mood": r.get("mood"), "good": (r.get("good") or [])[:3]})
    return out


def _month_ago(d: date) -> date:
    y, m = (d.year, d.month - 1) if d.month > 1 else (d.year - 1, 12)
    import calendar
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _year_ago(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:
        return d.replace(year=d.year - 1, day=28)


def happy_jar(records: list[dict], today: date) -> dict | None:
    """On a bad day: one good thing from an earlier good day (stable for the day)."""
    pool = [(r["day"], g) for r in records if (r.get("mood") or 0) >= 7 and r["day"] < today.isoformat()
            for g in (r.get("good") or [])]
    if not pool:
        return None
    rnd = random.Random(today.toordinal())
    day, text = rnd.choice(pool)
    return {"day": day, "text": text}


def period_report(records: list[dict], start: date, end: date, prev_start: date, prev_end: date) -> dict:
    def stats(a: date, b: date) -> dict:
        rs = [r for r in records if a <= _d(r) <= b]
        def avg(k: str) -> float | None:
            v = [r[k] for r in rs if r.get(k) is not None]
            return round(statistics.mean(v), 1) if v else None
        good = [g for r in rs for g in (r.get("good") or [])]
        return {
            "days": len(rs), "mood": avg("mood"), "energy": avg("energy"), "health": avg("health"),
            "sleep_h": avg("sleep_h"), "sleep_score": avg("sleep_score"),
            "trainings": sum(1 for r in rs if r.get("trained")),
            "best_day": max(rs, key=lambda r: r.get("mood") or 0)["day"] if rs else None,
            "good_count": len(good), "highlights": good[:5],
        }
    cur = stats(start, end)
    prev = stats(prev_start, prev_end)
    delta = {k: round(cur[k] - prev[k], 1) for k in ("mood", "energy", "health", "sleep_h")
             if cur.get(k) is not None and prev.get(k) is not None}
    return {"start": start.isoformat(), "end": end.isoformat(), "cur": cur, "prev": prev, "delta": delta}


def all_insights(records: list[dict], *, sleep: bool, training: bool, goals: bool) -> list[dict]:
    out = []
    for fn, on in ((best_day_words, True), (sleep_effect, sleep), (training_energy, training),
                   (weekday_pattern, True), (morning_evening, True), (goal_insight, goals)):
        if not on:
            continue
        try:
            r = fn(records)
        except (ValueError, ZeroDivisionError, statistics.StatisticsError):
            r = None
        if r:
            out.append(r)
    return out


def topic_lists(records: list[dict]) -> dict:
    """'What does you good' / 'what drags you down' (topics linked with mood)."""
    days = [(topics(_texts(r)), r["mood"]) for r in records if r.get("mood") is not None and _texts(r).strip()]
    eff = topic_effects(days)
    return {"good": [e for e in eff if e["effect"] >= 0.5][:5],
            "bad": [e for e in reversed(eff) if e["effect"] <= -0.5][:5]}
