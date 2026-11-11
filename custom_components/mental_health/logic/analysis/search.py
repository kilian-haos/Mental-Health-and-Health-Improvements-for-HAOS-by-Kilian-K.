"""Local "AI" search: natural-language rule parser (de/en) -> filters, then BM25 full text.

Only ever runs over the person's own day records. Day record (dict):
  day, mood, mood_m, mood_e, energy, health, sleep_h, trained, period, slots,
  good [..], bad [..], goals [..], journal
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from .text import STOP, content_stems, stem, synonyms, tokens

MONTHS = {
    "januar": 1, "jänner": 1, "january": 1, "jan": 1, "februar": 2, "february": 2, "feb": 2, "märz": 3, "maerz": 3,
    "march": 3, "april": 4, "apr": 4, "mai": 5, "may": 5, "juni": 6, "june": 6, "juli": 7, "july": 7, "august": 8,
    "aug": 8, "september": 9, "sept": 9, "sep": 9, "oktober": 10, "october": 10, "okt": 10, "oct": 10, "november": 11,
    "nov": 11, "dezember": 12, "december": 12, "dez": 12, "dec": 12,
}
SEASONS = {
    "sommer": (6, 8), "summer": (6, 8), "winter": (12, 2), "frühling": (3, 5), "fruehling": (3, 5), "spring": (3, 5),
    "herbst": (9, 11), "autumn": (9, 11), "fall": (9, 11),
}

# Phrasen -> Filter (Reihenfolge wichtig: längere zuerst)
PHRASES: list[tuple[str, dict]] = [
    (r"\b(schlechte[nrsm]?|miese[nrsm]?|traurige[nrsm]?) tage?\b|\bbad days?\b|\bwhen i felt (bad|down|low)\b|"
     r"\bwo es mir (schlecht|mies) (ging|ging's)\b|\bnegative?\b", {"polarity": "negative"}),
    (r"\b(gute[nrsm]?|schöne[nrsm]?|tolle[nrsm]?|beste[nrsm]?) tage?\b|\bgood days?\b|\bbest days?\b|"
     r"\bwhen i felt (good|great|happy)\b|\bwo es mir gut ging\b|\bpositive?\b|\bglücklich\b", {"polarity": "positive"}),
    (r"\bneutral(e[nrsm]?)?( tage?)?\b|\bokay days?\b", {"polarity": "neutral"}),
    (r"\bmit training\b|\bnach dem training\b|\bwith (training|workout|exercise)\b|\btrainiert\b|\bworked out\b",
     {"trained": True}),
    (r"\bohne training\b|\bwithout (training|workout)\b", {"trained": False}),
    (r"\bwenig schlaf\b|\bschlecht geschlafen\b|\bkurze? nächte?\b|\blittle sleep\b|\bshort nights?\b|"
     r"\bpoor sleep\b|\bbad sleep\b|\bnot enough sleep\b", {"sleep": "short"}),
    (r"\bviel schlaf\b|\bgut geschlafen\b|\blange? nächte?\b|\blots of sleep\b|\bgood sleep\b|\bslept well\b",
     {"sleep": "long"}),
    (r"\bwährend (der|meiner) (periode|tage|menstruation)\b|\bperiode\b|\bduring (my )?period\b|\bperiod\b|"
     r"\bmenstruation\b", {"period": True}),
    (r"\bmit journal\b|\bjournal(einträge?n?)?\b|\bwith journal\b|\bjournal entries\b", {"journal": True}),
    (r"\bmit (zielen|vorsätzen)\b|\bwith goals\b|\bgoals?\b|\bvorsätze?n?\b|\bziele?n?\b", {"goals": True}),
    (r"\bmorgens\b|\bam morgen\b|\bmornings?\b", {"slot": "morning"}),
    (r"\babends\b|\bam abend\b|\bevenings?\b", {"slot": "evening"}),
    (r"\b(am )?wochenende?n?\b|\bweekends?\b", {"weekend": True}),
    (r"\bwerktags?\b|\bunter der woche\b|\bweekdays?\b", {"weekend": False}),
]


@dataclass
class Filters:
    start: date | None = None
    end: date | None = None
    months: set[int] = field(default_factory=set)
    polarity: str | None = None       # positive | neutral | negative
    trained: bool | None = None
    sleep: str | None = None          # short | long
    period: bool | None = None
    journal: bool | None = None
    goals: bool | None = None
    slot: str | None = None
    weekend: bool | None = None
    terms: list[str] = field(default_factory=list)

    def chips(self) -> list[dict]:
        out = []
        if self.start or self.end:
            out.append({"k": "range", "start": self.start.isoformat() if self.start else None,
                        "end": self.end.isoformat() if self.end else None})
        if self.months:
            out.append({"k": "months", "v": sorted(self.months)})
        for k in ("polarity", "trained", "sleep", "period", "journal", "goals", "slot", "weekend"):
            v = getattr(self, k)
            if v is not None:
                out.append({"k": k, "v": v})
        for t in self.terms:
            out.append({"k": "term", "v": t})
        return out

    @classmethod
    def from_chips(cls, chips: list[dict]) -> Filters:
        f = cls()
        for c in chips or []:
            k, v = c.get("k"), c.get("v")
            if k == "range":
                f.start = date.fromisoformat(c["start"]) if c.get("start") else None
                f.end = date.fromisoformat(c["end"]) if c.get("end") else None
            elif k == "months" and isinstance(v, list):
                f.months = {int(x) for x in v if 1 <= int(x) <= 12}
            elif k == "term" and isinstance(v, str):
                f.terms.append(v[:40])
            elif k in ("polarity", "sleep", "slot") and isinstance(v, str):
                setattr(f, k, v)
            elif k in ("trained", "period", "journal", "goals", "weekend") and isinstance(v, bool):
                setattr(f, k, v)
        return f


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def parse(query: str, today: date) -> Filters:
    q = " " + (query or "").lower().strip() + " "
    f = Filters()
    for pattern, values in PHRASES:
        if re.search(pattern, q):
            for k, v in values.items():
                if getattr(f, k) is None:
                    setattr(f, k, v)
            q = re.sub(pattern, " ", q)

    def rng(a: date, b: date) -> None:
        f.start, f.end = a, b

    if re.search(r"\bheute\b|\btoday\b", q):
        rng(today, today)
    elif re.search(r"\bgestern\b|\byesterday\b", q):
        rng(today - timedelta(days=1), today - timedelta(days=1))
    elif re.search(r"\b(letzte[nrm]?|vergangene[nrm]?) woche\b|\blast week\b", q):
        s = today - timedelta(days=today.weekday() + 7)
        rng(s, s + timedelta(days=6))
    elif re.search(r"\bdiese[nrm]? woche\b|\bthis week\b", q):
        rng(today - timedelta(days=today.weekday()), today)
    elif re.search(r"\b(letzte[nrm]?|vergangene[nrm]?) monat\b|\blast month\b", q):
        s = _add_months(_month_start(today), -1)
        rng(s, _month_start(today) - timedelta(days=1))
    elif re.search(r"\bdiese[nrm]? monat\b|\bthis month\b", q):
        rng(_month_start(today), today)
    elif re.search(r"\b(letzte[nrms]?|vergangene[nrms]?) jahr\b|\blast year\b", q):
        rng(date(today.year - 1, 1, 1), date(today.year - 1, 12, 31))
    elif re.search(r"\bdieses jahr\b|\bthis year\b", q):
        rng(date(today.year, 1, 1), today)
    m = re.search(r"\b(?:letzten|vergangenen|last|past)\s+(\d{1,3})\s+(tage?n?|days?|wochen|weeks?|monate?n?|months?)\b", q)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        days = n if unit.startswith(("tag", "day")) else n * 7 if unit.startswith(("woch", "week")) else n * 30
        rng(today - timedelta(days=days - 1), today)
        q = q.replace(m.group(0), " ")
    q = re.sub(r"\b(letzte[nrms]?|vergangene[nrms]?|diese[nrms]?|last|this|past) (woche|monat|jahr|week|month|year)\b",
               " ", q)
    q = re.sub(r"\b(heute|gestern|today|yesterday)\b", " ", q)
    for name, (a, b) in SEASONS.items():
        if re.search(rf"\b{name}\b", q):
            f.months |= set(range(a, b + 1)) if a <= b else {12, 1, 2}
            q = re.sub(rf"\b(im |in |in the )?{name}\b", " ", q)
    for name, mo in MONTHS.items():
        if len(name) > 3 and re.search(rf"\b{name}\b", q):
            f.months.add(mo)
            q = re.sub(rf"\b(im |in )?{name}\b", " ", q)
    y = re.search(r"\b(20\d\d)\b", q)
    if y:
        yr = int(y.group(1))
        f.start, f.end = date(yr, 1, 1), date(yr, 12, 31)
        q = q.replace(y.group(1), " ")
    filler = {"zeig", "zeige", "mir", "alle", "tage", "tag", "einträge", "eintrag", "wo", "wann", "ich", "show", "me",
              "all", "days", "day", "entries", "where", "when", "with", "mit", "an", "denen", "im", "in", "the", "at",
              "about", "über", "von", "find", "finde", "suche", "search", "es", "mir", "ging", "felt", "habe", "hatte"}
    f.terms = [t for t in tokens(q) if t not in STOP and t not in filler and len(t) > 2][:8]
    return f


def matches(rec: dict, f: Filters) -> bool:
    d = date.fromisoformat(rec["day"])
    if f.start and d < f.start or f.end and d > f.end:
        return False
    if f.months and d.month not in f.months:
        return False
    if f.weekend is not None and (d.weekday() >= 5) != f.weekend:
        return False
    mood = rec.get("mood_m") if f.slot == "morning" else rec.get("mood_e") if f.slot == "evening" else rec.get("mood")
    if f.slot and f.slot not in (rec.get("slots") or []):
        return False
    if f.polarity:
        if mood is None:
            return False
        if f.polarity == "positive" and mood < 7:
            return False
        if f.polarity == "negative" and mood > 4:
            return False
        if f.polarity == "neutral" and not (4 < mood < 7):
            return False
    if f.trained is not None and rec.get("trained") is not f.trained:
        return False
    if f.sleep == "short" and not (rec.get("sleep_h") is not None and rec["sleep_h"] < 6.5):
        return False
    if f.sleep == "long" and not (rec.get("sleep_h") is not None and rec["sleep_h"] >= 8.0):
        return False
    if f.period is not None and bool(rec.get("period")) != f.period:
        return False
    if f.journal is not None and bool(rec.get("journal")) != f.journal:
        return False
    if f.goals is not None and bool(rec.get("goals")) != f.goals:
        return False
    return True


def doc_text(rec: dict) -> str:
    parts = list(rec.get("good") or []) + list(rec.get("bad") or []) + list(rec.get("goals") or [])
    if rec.get("journal"):
        parts.append(rec["journal"])
    return "\n".join(parts)


class BM25:
    def __init__(self, docs: dict[str, str], k1: float = 1.4, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.tf: dict[str, dict[str, int]] = {}
        self.len: dict[str, int] = {}
        self.df: dict[str, int] = {}
        for key, text in docs.items():
            stems = content_stems(text)
            counts: dict[str, int] = {}
            for s in stems:
                counts[s] = counts.get(s, 0) + 1
            self.tf[key] = counts
            self.len[key] = len(stems)
            for s in counts:
                self.df[s] = self.df.get(s, 0) + 1
        self.n = len(docs)
        self.avg = (sum(self.len.values()) / self.n) if self.n else 0.0

    def score(self, key: str, query_stems: list[set[str]]) -> float:
        tf = self.tf.get(key, {})
        dl = self.len.get(key, 0)
        total = 0.0
        for group in query_stems:
            best = 0.0
            for s in group:
                f = tf.get(s, 0)
                if not f:
                    continue
                idf = math.log(1 + (self.n - self.df.get(s, 0) + 0.5) / (self.df.get(s, 0) + 0.5))
                w = 1.0 if s == next(iter(group)) else 0.6       # Synonyme zählen etwas weniger
                best = max(best, w * idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / (self.avg or 1))))
            total += best
        return total


def search(records: list[dict], f: Filters, limit: int = 200) -> list[dict]:
    """Filter, then rank by BM25 (if there are terms) or by date (newest first)."""
    cand = [r for r in records if matches(r, f)]
    if not f.terms:
        cand.sort(key=lambda r: r["day"], reverse=True)
        return [{"day": r["day"], "score": None, "hits": []} for r in cand[:limit]]
    qs = []
    for t in f.terms:
        st = stem(t)
        group = [st] + sorted(synonyms(st) - {st})
        qs.append(_ordered(group))
    index = BM25({r["day"]: doc_text(r) for r in cand})
    out = []
    for r in cand:
        sc = index.score(r["day"], qs)
        if sc > 0:
            hits = sorted({s for g in qs for s in g if s in index.tf.get(r["day"], {})})
            out.append({"day": r["day"], "score": round(sc, 3), "hits": hits})
    out.sort(key=lambda x: (-x["score"], x["day"]))
    return out[:limit]


class _ordered(set):
    """A set that remembers its first element (the original term) for weighting."""

    def __init__(self, items: list[str]) -> None:
        super().__init__(items)
        self._first = items[0] if items else None

    def __iter__(self):
        if self._first is not None:
            yield self._first
        for x in set.__iter__(self):
            if x != self._first:
                yield x
