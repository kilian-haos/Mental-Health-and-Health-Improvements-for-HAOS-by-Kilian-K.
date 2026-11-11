"""Training rhythm (pure Python). Exact rules:

1. Evening check-in "Trained today?" – yes sets last_training = that day, a rest phase begins.
2. The two following days are rest days. From the first day after training, muscle soreness 0-3
   is asked every day (morning; if the morning was missed, in the evening).
3. Recommendation: on a day with at least two full rest days since the last training (day 3 or
   later) whose soreness is <= 1 -> "Today is a good day for a workout".
   Soreness > 1 -> no recommendation, check again the next morning.
4. Not trained on the recommendation day: "no" in the evening is fine. From the next day on the
   recommendation is highlighted ("due for X days") until a training is logged again.
5. Training during the rest phase is allowed; it starts a new rest phase (gentle hint).
6. States: pause / ready_soon / recommended / overdue.

Paused days of the person (holiday, illness) never become the recommendation day and do not
count towards "due for X days". Days on which no soreness was recorded cannot become the
recommendation day – except from day 5 on: muscle soreness rarely lasts longer than 3-4 days
(DOMS typically peaks after 24-72 h), so a missing answer no longer blocks the recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

PAUSE = "pause"
READY_SOON = "ready_soon"
RECOMMENDED = "recommended"
OVERDUE = "overdue"
STATES = (PAUSE, READY_SOON, RECOMMENDED, OVERDUE)

REST_DAYS = 2
SORENESS_OK = 1
SORENESS_FREE_FROM_DAY = 5


@dataclass
class TrainingInput:
    today: date
    last_training: date | None
    soreness: dict[date, int] = field(default_factory=dict)   # Tag -> 0..3 (letzter Wert des Tages)
    paused: set[date] = field(default_factory=set)
    morning_done: bool = False                                  # Morgen-Check-in heute erledigt/verpasst?
    tracking_since: date | None = None                          # erster Tag mit Modul aktiv


@dataclass
class TrainingState:
    status: str
    days_since: int | None
    last_soreness: int | None
    recommended_on: date | None
    overdue_days: int
    highlight: bool
    paused_today: bool

    @property
    def recommended(self) -> bool:
        return self.status in (RECOMMENDED, OVERDUE)


def _eligible(day: date, inp: TrainingInput, first_possible: date) -> bool:
    if day < first_possible or day in inp.paused:
        return False
    s = inp.soreness.get(day)
    if s is not None:
        return s <= SORENESS_OK
    if inp.last_training is not None and (day - inp.last_training).days >= SORENESS_FREE_FROM_DAY:
        return True
    return False


def evaluate(inp: TrainingInput) -> TrainingState:
    today = inp.today
    paused_today = today in inp.paused
    last_s = None
    for d in sorted(inp.soreness, reverse=True):
        if d <= today and (inp.last_training is None or d > inp.last_training):
            last_s = inp.soreness[d]
            break

    if inp.last_training is None:
        # Noch nie trainiert: ab Start der Erfassung empfohlen (keine Pause nötig)
        start = inp.tracking_since or today
        rec = None
        d = start
        while d <= today:
            if d not in inp.paused and inp.soreness.get(d, 0) <= SORENESS_OK:
                rec = d
                break
            d += timedelta(days=1)
        # Ohne erstes Training gibt es kein „überfällig“ (kein Druck für neue Personen)
        return TrainingState(RECOMMENDED if rec else READY_SOON, None, last_s, rec, 0, False, paused_today)

    days_since = (today - inp.last_training).days
    if days_since <= 0:
        return TrainingState(PAUSE, 0, last_s, None, 0, False, paused_today)
    first_possible = inp.last_training + timedelta(days=REST_DAYS + 1)
    rec = None
    d = first_possible
    while d <= today:
        if _eligible(d, inp, first_possible):
            rec = d
            break
        d += timedelta(days=1)
    if rec is None:
        status = PAUSE if days_since < REST_DAYS else READY_SOON
        return TrainingState(status, days_since, last_s, None, 0, False, paused_today)
    return _finish(inp, rec, days_since, last_s, paused_today)


def _finish(inp: TrainingInput, rec: date | None, days_since: int | None, last_s: int | None,
            paused_today: bool) -> TrainingState:
    today = inp.today
    if rec is None:
        return TrainingState(READY_SOON, days_since, last_s, None, 0, False, paused_today)
    if rec == today:
        return TrainingState(RECOMMENDED, days_since, last_s, rec, 0, False, paused_today)
    # überfällig: Tage seit der ersten Empfehlung, ohne Pause-Tage
    n = sum(1 for i in range(1, (today - rec).days + 1) if (rec + timedelta(days=i)) not in inp.paused)
    return TrainingState(OVERDUE, days_since, last_s, rec, n, True, paused_today)


def ask_soreness(inp: TrainingInput, slot: str) -> bool:
    """Should the check-in in `slot` ('morning'/'evening') ask for muscle soreness today?"""
    if inp.last_training is None or inp.today in inp.paused:
        return False
    if inp.today in inp.soreness:
        return False
    days_since = (inp.today - inp.last_training).days
    if days_since < 1:
        return False
    st = evaluate(inp)
    if st.status in (RECOMMENDED, OVERDUE):
        return False
    if slot == "morning":
        return True
    return bool(inp.morning_done)   # abends nur, wenn der Morgen verpasst/erledigt ohne Antwort ist


def early_training(last_training: date | None, day: date) -> bool:
    """Training logged during the rest phase -> gentle hint "recovery is part of training"."""
    return last_training is not None and 0 < (day - last_training).days <= REST_DAYS
