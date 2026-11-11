"""One participating person: profile, encrypted vault, models and all derived values.

No Home Assistant imports – the runtime feeds time, sensor samples and settings in. This keeps
the whole personal logic testable and guarantees that cards, panel and entities show the same
server-side results.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date, datetime, timedelta, tzinfo
from typing import Any

from .logic import checkin as CI
from .logic import cycle as CY
from .logic import training as TR
from .logic import weight as WT
from .logic.analysis import health_score as HS
from .logic.analysis import insights as INS
from .logic.analysis import search as SE
from .logic.analysis import text as TX
from .logic.analysis.mood_model import MoodModel, features
from .logic.birthday import Birthdate
from .logic.daymath import day_key, local_at, logical_day, minutes_of_day, parse_day, parse_hhmm
from .logic.permissions import PersonRights
from .logic.schedule import AdaptiveGap
from .logic.sleep import score as SC
from .logic.sleep.detector import NightResult, SleepModel
from .logic.sleep.features import MinuteSeries
from .logic.sleep.pipeline import build_window, feed_levels
from .logic.sleep.predictor import NightTimes, predict
from .logic.sleep.sources import Source
from .storage import Locked, PersonVault, new_id

LIVE_WINDOW_MIN = 20 * 60          # Live-Erkennung über die letzten 20 h


@dataclass
class Clock:
    now: datetime                    # lokal, mit Zeitzone
    boundary: str = "04:00"

    @property
    def tz(self) -> tzinfo:
        return self.now.tzinfo       # type: ignore[return-value]

    @property
    def today(self) -> date:
        return logical_day(self.now, parse_hhmm(self.boundary, "04:00"))

    @property
    def minute(self) -> int:
        return int(self.now.timestamp() // 60)


def _mean(vals: list[float | None]) -> float | None:
    v = [x for x in vals if x is not None]
    return statistics.mean(v) if v else None


class Person:
    def __init__(self, profile: dict, vault: PersonVault, model: dict | None = None) -> None:
        self.profile = profile
        self.vault = vault
        model = model or {}
        self.sleep = SleepModel.from_dict(model.get("sleep"))
        self.mood = MoodModel.from_dict(model.get("mood"))
        self.gap = AdaptiveGap.from_dict(model.get("gap"), self.profile["schedule"]["sleep_gap_min"])
        self.optimum = model.get("optimum") or None           # {"h", "conf"}
        self.series: dict[str, MinuteSeries] = {
            k: MinuteSeries.from_dict(v) for k, v in (model.get("series") or {}).items()}
        self.temps: dict[str, float] = dict(model.get("temps") or {})
        self.live: NightResult | None = None
        self.live_at = 0
        self.requests_sent: dict = {}
        self.weight_required_served: str | None = model.get("weight_required_served")
        self.tracking_since: str | None = model.get("since")

    # ---------------------------------------------------------- Basis
    @property
    def pid(self) -> str:
        return self.profile["id"]

    @property
    def name(self) -> str:
        return self.profile.get("name") or ""

    @property
    def user_id(self) -> str | None:
        return self.profile.get("user_id")

    @property
    def child(self) -> bool:
        return bool(self.profile.get("child"))

    @property
    def modules(self) -> dict[str, bool]:
        return self.profile["modules"]

    def mod(self, key: str) -> bool:
        m = self.modules
        if key == "sleep_tracking":
            return bool(m.get("sleep_tracking")) and bool(self.sources)
        if key == "cycle":
            return bool(m.get("cycle")) and self.profile.get("sex") in ("female", "other") and (
                not self.child or self.profile.get("cycle_child_allowed"))
        if key == "weight":
            return bool(m.get("weight"))
        if key == "birthday":
            return bool(m.get("birthday")) and bool(self.profile.get("birthdate"))
        if key == "llm":
            return bool(m.get("llm")) and bool(self.profile.get("llm_consent"))
        return bool(m.get(key))

    @property
    def sources(self) -> list[Source]:
        return [Source.from_dict(s) for s in self.profile.get("sleep_sources") or []]

    @property
    def rights(self) -> PersonRights:
        p = self.profile
        return PersonRights(p.get("user_id"), bool(p.get("child")), bool(p.get("can_edit_own")),
                            bool(p.get("weight_live")), bool(p.get("llm_child_allowed")))

    @property
    def birthdate(self) -> Birthdate | None:
        return Birthdate.parse(self.profile.get("birthdate"))

    def age(self, today: date) -> int | None:
        b = self.birthdate
        return b.age(today) if b else None

    def missing_profile(self) -> list[str]:
        out = []
        for k in ("birthdate", "sex", "height_cm"):
            v = self.profile.get(k)
            if not v or v == "unspecified":
                out.append(k)
        if self.mod("weight") and not self.profile.get("height_cm"):
            out.append("height_for_weight")
        return out

    # ---------------------------------------------------------- Pause
    def paused_on(self, day: date) -> bool:
        p = self.profile.get("pause")
        if p and p.get("from"):
            start = parse_day(p["from"])
            until = parse_day(p["until"]) if p.get("until") else None
            if start <= day and (until is None or day <= until):
                return True
        return bool(self.vault.numbers(day_key(day)).get("paused"))

    def paused_days(self) -> set[date]:
        return {parse_day(d) for d, n in self.vault.days.items() if n.get("paused")}

    # ---------------------------------------------------------- Tageswerte
    def day_numbers(self, day: date) -> dict:
        return self.vault.numbers(day_key(day))

    def day_mood(self, n: dict) -> float | None:
        return _mean([(n.get("m") or {}).get("mood"), (n.get("e") or {}).get("mood")])

    def record(self, day: str, with_texts: bool = False) -> dict:
        """Flat day record for analysis/search (texts only if requested and unlocked)."""
        n = self.vault.numbers(day)
        m, e = n.get("m") or {}, n.get("e") or {}
        sl = n.get("sleep") or {}
        trained = (e.get("trained") or {}).get("done") if e.get("trained") is not None else None
        period = any((x.get("period") or {}).get("answer") in ("yes", "started") for x in (m, e))
        rec = {
            "day": day, "mood": self.day_mood(n), "mood_m": m.get("mood"), "mood_e": e.get("mood"),
            "energy": _mean([m.get("energy"), e.get("energy")]), "health": _mean([m.get("health"), e.get("health")]),
            "sleep_quality": m.get("sleep_quality"),
            "sleep_h": round(sl["asleep"] / 60.0, 2) if sl.get("asleep") else None, "sleep_score": sl.get("score"),
            "trained": trained, "soreness": m.get("soreness", e.get("soreness")), "period": period,
            "slots": [s for s in ("morning", "evening") if n.get(s[0])], "late": bool(m.get("late") or e.get("late")),
            "weight": self.vault.weights.get(day), "edited": bool(m.get("_edits") or e.get("_edits")),
            "goal_res": n.get("goal_res") or {},
        }
        if with_texts:
            t = self.vault.texts(day) or {}
            te = t.get("e") or {}
            rec.update({"good": te.get("good") or [], "bad": te.get("bad") or [], "journal": te.get("journal"),
                        "goals": [g.get("text") for g in te.get("goals") or []],
                        "period_detail": {"m": (t.get("m") or {}).get("period"), "e": te.get("period")}})
            # Vorsätze von gestern -> Ergebnisse von heute
            prev = (parse_day(day) - timedelta(days=1)).isoformat()
            pt = self.vault.texts(prev) if self.vault.has_texts(prev) else None
            goals_prev = {g["id"]: g["text"] for g in ((pt or {}).get("e") or {}).get("goals") or []}
            rec["goal_results"] = [{"text": goals_prev[g], "result": r} for g, r in rec["goal_res"].items() if g in goals_prev]
        else:
            rec["journal"] = bool(self.vault.has_texts(day))
        return rec

    def records(self, with_texts: bool = False) -> list[dict]:
        return [self.record(d, with_texts) for d in sorted(self.vault.days)]

    # ---------------------------------------------------------- Training
    def training_input(self, today: date) -> TR.TrainingInput:
        last = None
        sore: dict[date, int] = {}
        morning_done = False
        for d, n in self.vault.days.items():
            e = n.get("e") or {}
            m = n.get("m") or {}
            if (e.get("trained") or {}).get("done"):
                dd = parse_day(d)
                if last is None or dd > last:
                    last = dd
            s = m.get("soreness", e.get("soreness"))
            if s is not None:
                sore[parse_day(d)] = int(s)
        t = self.day_numbers(today)
        morning_done = bool(t.get("m")) or (t.get("status") or {}).get("morning") == "missed"
        since = parse_day(self.tracking_since) if self.tracking_since else None
        return TR.TrainingInput(today, last, sore, self.paused_days() | ({today} if self.paused_on(today) else set()),
                                morning_done, since)

    def training(self, today: date) -> TR.TrainingState | None:
        if not self.mod("training"):
            return None
        return TR.evaluate(self.training_input(today))

    # ---------------------------------------------------------- Gewicht
    def weight_summary(self, today: date) -> WT.WeightSummary | None:
        if not self.mod("weight"):
            return None
        days = sorted(self.vault.weights)
        vals = [self.vault.weights[d] for d in days]
        if not days and self.profile.get("weight_kg") and not self.profile.get("weight_live"):
            days, vals = [today.isoformat()], [self.profile["weight_kg"]]
        p = self.profile
        served = parse_day(self.weight_required_served) if self.weight_required_served else None
        since = parse_day(self.tracking_since) if self.tracking_since else None
        return WT.summarize([parse_day(d) for d in days], vals, today, height_cm=p.get("height_cm"),
                            age=self.age(today), target=p.get("target_weight"), child=self.child,
                            required_served=served, tracking_since=since)

    def weight_due(self, today: date) -> str:
        if not self.mod("weight") or self.child or self.profile.get("weight_entity"):
            return "none"
        s = self.weight_summary(today)
        return s.due if s else "none"

    # ---------------------------------------------------------- Zyklus
    def cycle(self, today: date) -> CY.CyclePrediction | None:
        if not self.mod("cycle"):
            return None
        reports: dict[date, str] = {}
        for d, n in self.vault.days.items():
            answers = [x.get("period", {}).get("answer") for x in (n.get("m") or {}, n.get("e") or {})
                       if isinstance(x.get("period"), dict)]
            if answers:
                reports[parse_day(d)] = CY.collapse_day(answers)
        temps = {parse_day(d): v for d, v in self.temps.items()}
        return CY.predict(reports, today, age=self.age(today), temps=temps or None)

    # ---------------------------------------------------------- Schlaf
    def optimum_h(self, today: date) -> float:
        if self.optimum and self.optimum.get("h"):
            return float(self.optimum["h"])
        return SC.start_optimum(self.age(today), self.profile.get("sex"))

    def relearn_optimum(self, today: date) -> None:
        pairs = []
        for d in sorted(self.vault.days)[-180:]:
            n = self.vault.days[d]
            sl = n.get("sleep") or {}
            r = self.record(d)
            wb = _mean([r["mood"], r["energy"], r["health"]])
            if sl.get("asleep") and wb is not None:
                pairs.append((sl["asleep"] / 60.0, wb))
        h, conf = SC.learn_optimum(self.age(today), self.profile.get("sex"), pairs)
        self.optimum = {"h": h, "conf": conf}

    def feed_sample(self, source_id: str, minute_f: float, value: float) -> None:
        s = self.series.get(source_id)
        if s is None:
            s = self.series[source_id] = MinuteSeries()
        s.add(minute_f, value)

    def roll_series(self, minute: int, tod_of: callable) -> None:
        """Finish minutes; feed numeric level models with finished minutes."""
        for src in self.sources:
            s = self.series.get(src.id)
            if s is None:
                continue
            before = s.head
            s.roll(minute)
            if src.kind == "numeric" and s.head is not None and before is not None and s.head > before:
                start = max(before + 1, s.head - 600)
                vals, _ = s.window(start, s.head + 1)
                feed_levels(src, self.sleep.levels, vals, [tod_of(m) for m in range(start, s.head + 1)])

    def window(self, start: int, end: int, tod_of: callable, other_in_bed: callable | None = None):
        srcs = self.sources
        series = {s.id: (self.series[s.id].window(start, end) if s.id in self.series else
                         ([float("nan")] * (end - start), [float("nan")] * (end - start))) for s in srcs}
        return build_window(start, [tod_of(m) for m in range(start, end)], srcs, series, self.sleep.levels, other_in_bed)

    def detect_live(self, clock: Clock, tod_of: callable, other_in_bed: callable | None = None) -> NightResult | None:
        if not self.sources:
            self.live = None
            return None
        end = clock.minute
        win = self.window(end - LIVE_WINDOW_MIN, end, tod_of, other_in_bed)
        self.live = self.sleep.detect(win)
        self.live_at = end
        return self.live

    def night_for_morning(self, clock: Clock) -> dict | None:
        """Detected night ending today (for the morning check-in), or the stored one."""
        today = clock.today
        stored = self.day_numbers(today).get("sleep")
        if stored and stored.get("src") in ("confirmed", "corrected"):
            return stored
        r = self.live
        if r is None or r.sleep is None:
            return stored
        end_local = datetime.fromtimestamp(r.sleep.end * 60, tz=clock.tz)
        if logical_day(end_local, parse_hhmm("12:00")) != today and end_local.date() != today:
            return stored
        return self._night_dict(r, clock, "auto")

    def _night_dict(self, r: NightResult, clock: Clock, src: str, start_m: int | None = None,
                    end_m: int | None = None) -> dict:
        today = clock.today
        start_m = start_m if start_m is not None else r.sleep.start
        end_m = end_m if end_m is not None else r.sleep.end
        inter = [i for i in r.interruptions if start_m <= i.start < end_m]
        asleep = (end_m - start_m) - sum(i.minutes for i in inter)
        bed_tod = minutes_of_day(datetime.fromtimestamp(start_m * 60, tz=clock.tz))
        wake_tod = minutes_of_day(datetime.fromtimestamp(end_m * 60, tz=clock.tz))
        workday = today.weekday() < 5
        hist = self._night_times(today)
        usual = predict(hist, workday)
        from .logic.daymath import circ_diff
        bed_dev = circ_diff(bed_tod, usual.bed) if usual.bed is not None else None
        wake_dev = circ_diff(wake_tod, usual.wake) if usual.wake is not None else None
        subj = (self.day_numbers(today).get("m") or {}).get("sleep_quality")
        naps = sum(s.minutes for s in r.naps)
        total, comps = SC.score(SC.ScoreInput(asleep, self.optimum_h(today), bed_dev, wake_dev, len(inter),
                                              sum(i.minutes for i in inter), r.latency, subj, naps))
        return {
            "start": datetime.fromtimestamp(start_m * 60, tz=clock.tz).isoformat(),
            "end": datetime.fromtimestamp(end_m * 60, tz=clock.tz).isoformat(),
            "start_m": start_m, "end_m": end_m, "asleep": int(asleep), "score": total, "comps": comps,
            "conf": r.confidence if src == "auto" else 1.0, "int": len(inter), "int_min": sum(i.minutes for i in inter),
            "naps": naps, "lat": r.latency, "src": src, "bed_tod": round(bed_tod), "wake_tod": round(wake_tod),
            "segments": [{"s": i.start, "e": i.end} for i in inter][:20],
        }

    def _night_times(self, before: date) -> list[NightTimes]:
        out = []
        for d in sorted(self.vault.days, reverse=True)[:60]:
            dd = parse_day(d)
            if dd >= before:
                continue
            sl = (self.vault.days[d].get("sleep") or {})
            if sl.get("bed_tod") is None:
                continue
            out.append(NightTimes(sl.get("bed_tod"), sl.get("wake_tod"), dd.weekday() < 5, (before - dd).days - 1,
                                  sl.get("alarm_tod")))
        return out

    def sleep_prediction(self, clock: Clock, workday: bool | None = None, alarm_tod: float | None = None):
        today = clock.today
        wd = workday if workday is not None else (today + timedelta(days=1)).weekday() < 5
        return predict(self._night_times(today + timedelta(days=1)), wd, alarm_tod)

    def sleepmaxing(self, today: date) -> dict | None:
        sl = self.day_numbers(today).get("sleep")
        if not sl or not sl.get("asleep"):
            return None
        prev = [self.vault.numbers((today - timedelta(days=i)).isoformat()).get("sleep") or {} for i in range(1, 8)]
        wk = _mean([p.get("asleep") for p in prev])
        return SC.sleepmaxing(sl["asleep"], wk, self.optimum_h(today))

    def store_night(self, clock: Clock, night: dict) -> None:
        n = dict(self.day_numbers(clock.today))
        n["sleep"] = night
        self.vault.set_numbers(clock.today.isoformat(), n)

    def label_night(self, clock: Clock, start_m: int, end_m: int, src: str, tod_of: callable) -> dict | None:
        """Confirmation/correction from the morning check-in = strongest training label."""
        if not self.sources:
            return None
        win_start = start_m - 6 * 60
        win_end = min(clock.minute, end_m + 4 * 60)
        win = self.window(win_start, win_end, tod_of)
        detected = self.sleep.detect(win)
        self.sleep.learn(win, start_m, end_m, 1.0, detected)
        r = detected if detected.sleep else self.live
        if r is None or r.sleep is None:
            from .logic.sleep.detector import Segment
            r = NightResult(Segment(start_m, end_m, "sleep"), [], [], [], "away", 1.0, [], None, None)
        night = self._night_dict(r, clock, src, start_m, end_m)
        self.store_night(clock, night)
        self.sleep.night_done(r, clock.today.isoformat(), {"src": src})
        return night

    # ---------------------------------------------------------- Prognose
    def _features_for(self, day: date, extra: dict | None = None) -> list[float]:
        extra = extra or {}
        n = self.day_numbers(day)
        y = self.day_numbers(day - timedelta(days=1))
        sl = n.get("sleep") or {}
        recent = [self.day_mood(self.day_numbers(day - timedelta(days=i))) for i in range(1, 15)]
        r3 = _mean(recent[:3])
        r14 = _mean(recent)
        trend = (r3 - r14) if (r3 is not None and r14 is not None) else None
        cyc = self.cycle(day)
        ye = y.get("e") or {}
        return features(
            sleep_h=sl["asleep"] / 60.0 if sl.get("asleep") else None, optimum_h=self.optimum_h(day),
            sleep_score=sl.get("score"), weekday=day.weekday(), trend=trend,
            trained_y=(ye.get("trained") or {}).get("done") if ye.get("trained") is not None else None,
            soreness=(n.get("m") or {}).get("soreness"), phase=cyc.phase if cyc else None,
            energy_y=_mean([(y.get("m") or {}).get("energy"), ye.get("energy")]),
            health_y=_mean([(y.get("m") or {}).get("health"), ye.get("health")]),
            mood_y=self.day_mood(y), temp=extra.get("temp"), daylight_h=extra.get("daylight"))

    def forecast(self, day: date, extra: dict | None = None) -> dict | None:
        if not self.mod("suggestions"):
            return None
        if self.paused_on(day):
            return {"ready": False, "paused": True}
        x = self._features_for(day, extra)
        f = self.mood.forecast(x)
        if f and f.get("ready"):
            n = dict(self.day_numbers(day))
            if n.get("fx") is None:
                n["fx"] = [round(v, 4) for v in x]
                n["fp"] = f["value"]
                self.vault.set_numbers(day.isoformat(), n)
        return f

    def forecast_tomorrow(self, today: date, extra: dict | None = None) -> dict | None:
        if not self.mod("suggestions"):
            return None
        return self.mood.forecast(self._features_for(today + timedelta(days=1), extra))

    def learn_day(self, day: date, extra: dict | None = None) -> None:
        """End of day: train the mood model with the day's mood (once per day)."""
        n = dict(self.day_numbers(day))
        mood = self.day_mood(n)
        if mood is None or n.get("learned"):
            return
        x = n.get("fx") or self._features_for(day, extra)
        self.mood.update(list(x), mood)
        self.mood.record(day.isoformat(), n.get("fp"), round(mood, 1))
        n["learned"] = True
        self.vault.set_numbers(day.isoformat(), n)

    # ---------------------------------------------------------- Health Score
    def health(self, today: date) -> tuple[int | None, dict[str, int]]:
        last7 = [self.record((today - timedelta(days=i)).isoformat()) for i in range(7)]
        tr = self.training(today)
        ws = self.weight_summary(today)
        rate = self.checkin_rate(today)
        mods = {k: self.mod(k) for k in ("energy", "health", "sleep_tracking", "training", "weight")}
        return HS.compute(HS.HealthInput(
            [r["mood"] for r in last7], [r["energy"] for r in last7], [r["health"] for r in last7],
            [r["sleep_score"] for r in last7 if r["sleep_score"] is not None],
            tr.status if tr else None, tr.overdue_days if tr else 0,
            abs(ws.delta_opt) if (ws and ws.delta_opt is not None and not self.child) else None, rate, mods))

    def checkin_rate(self, today: date, days: int = 14) -> float | None:
        exp = done = 0
        for i in range(1, days + 1):
            d = today - timedelta(days=i)
            if self.tracking_since and d.isoformat() < self.tracking_since:
                continue
            if self.paused_on(d):
                continue
            n = self.day_numbers(d)
            exp += 2
            done += (1 if n.get("m") else 0) + (1 if n.get("e") else 0)
        return done / exp if exp else None

    def streak(self, today: date) -> int:
        s = 0
        d = today if self.day_numbers(today).get("m") or self.day_numbers(today).get("e") else today - timedelta(days=1)
        for _ in range(3650):
            n = self.day_numbers(d)
            if n.get("m") or n.get("e"):
                s += 1
            elif not self.paused_on(d):
                break
            d -= timedelta(days=1)
        return s

    def trends(self, today: date) -> dict:
        def avg(days: int) -> float | None:
            return _mean([self.day_mood(self.day_numbers(today - timedelta(days=i))) for i in range(days)])
        a7, a30 = avg(7), avg(30)
        return {"avg7": round(a7, 1) if a7 is not None else None, "avg30": round(a30, 1) if a30 is not None else None,
                "trend": round(a7 - a30, 1) if (a7 is not None and a30 is not None) else None}

    # ---------------------------------------------------------- Check-in
    def form(self, slot: str, clock: Clock, family_birthdays: list[dict] | None = None,
             extra: dict | None = None) -> list[CI.Field]:
        today = clock.today
        tin = self.training_input(today)
        tst = self.training(today)
        ask = bool(tst) and TR.ask_soreness(tin, slot)
        sleep_det = None
        if slot == "morning" and self.mod("sleep_tracking"):
            night = self.night_for_morning(clock)
            if night:
                sleep_det = {**night, "maxing": self.sleepmaxing(today) if night is not None else None,
                             "optimum_h": self.optimum_h(today), "ask": (night.get("conf") or 0) < 0.6,
                             "learning": self.sleep.view()["night_of"] if self.sleep.learning else None}
        wcard = None
        if slot == "morning" and self.mod("weight") and not self.child:
            ws = self.weight_summary(today)
            if ws and ws.trend is not None:
                wcard = _weight_card(ws)
        goals = []
        if slot == "morning" and self.mod("goals"):
            y = (today - timedelta(days=1)).isoformat()
            try:
                t = self.vault.texts(y) if self.vault.has_texts(y) else None
            except Locked:
                t = None
            goals = [{"id": g["id"], "text": g["text"]} for g in ((t or {}).get("e") or {}).get("goals") or []]
        tcard = None
        if tst and tst.status in (TR.RECOMMENDED, TR.OVERDUE):
            tcard = {"status": tst.status, "overdue": tst.overdue_days, "child": self.child}
        ctx = CI.FormContext(
            slot=slot, modules={k: self.mod(k) for k in self.modules}, child=self.child,
            has_sleep_source=bool(self.sources), sleep_detected=sleep_det,
            forecast=self.forecast(today, extra) if slot == "morning" else None, weight_card=wcard,
            weight_due=self.weight_due(today), ask_soreness=ask, training_card=tcard,
            cycle_enabled=self.mod("cycle"), goals_yesterday=goals, birthdays=family_birthdays or [],
            weight_live=bool(self.profile.get("weight_live")))
        return CI.build_form(ctx)

    def submit(self, slot: str, day: date, data: dict, clock: Clock, late: bool, tod_of: callable,
               family_birthdays: list[dict] | None = None, form: list[CI.Field] | None = None) -> tuple[dict, dict]:
        """Validate + store a check-in. Returns (errors, info). Requires the text key (unlocked)."""
        if self.vault.tek is None:
            raise Locked()
        form = form or self.form(slot, clock, family_birthdays)
        clean, errors = CI.validate(form, data)
        if errors:
            return errors, {}
        key = day.isoformat()
        n = dict(self.vault.numbers(key))
        try:
            t = dict(self.vault.texts(key) or {})
        except Locked:
            t = {}
        s = slot[0]
        ts = clock.now.isoformat()
        num: dict[str, Any] = {"_ts": ts}
        txt: dict[str, Any] = {}
        info: dict[str, Any] = {}
        for k in ("mood", "energy", "health", "sleep_quality", "soreness"):
            if k in clean:
                num[k] = clean[k]
        if "trained" in clean:
            num["trained"] = clean["trained"]
            if clean["trained"]["done"]:
                info["early_training"] = TR.early_training(self.training_input(day).last_training, day)
        if "period" in clean:
            p = clean["period"]
            num["period"] = {"answer": p["answer"]}
            if p["answer"] in ("yes", "started"):
                txt["period"] = {k: p[k] for k in ("flow", "pain", "symptoms") if k in p}
        if "weight" in clean:
            self.vault.set_weight(key, clean["weight"])
            num["weight"] = True
            if self.weight_due(day) == "required":
                self.weight_required_served = key
        for k in ("good", "bad", "journal"):
            if k in clean:
                txt[k] = clean[k]
        if "goals" in clean:
            txt["goals"] = [{"id": new_id()[:8], "text": g} for g in clean["goals"]]
        if "goals_review" in clean:
            n["goal_res"] = {**(n.get("goal_res") or {}), **clean["goals_review"]}
        if late:
            num["late"] = True
        old = n.get(s)
        num = CI.merge_entries(old, num)
        n[s] = num
        st = dict(n.get("status") or {})
        st[slot] = "done"
        n["status"] = st
        if "sleep" in clean and self.mod("sleep_tracking"):
            sl = clean["sleep"]
            night = self.night_for_morning(clock)
            if sl["action"] == "confirm" and night and night.get("start_m"):
                n["sleep"] = self.label_night(clock, night["start_m"], night["end_m"], "confirmed", tod_of) or night
            elif sl["action"] == "correct":
                sm = int(datetime.fromisoformat(sl["start"]).timestamp() // 60)
                em = int(datetime.fromisoformat(sl["end"]).timestamp() // 60)
                n["sleep"] = self.label_night(clock, sm, em, "corrected", tod_of) or night
            elif night and not n.get("sleep"):
                n["sleep"] = night
            if n.get("sleep") and "sleep_quality" in clean:
                n["sleep"]["subjective"] = clean["sleep_quality"]
        self.vault.set_numbers(key, n)
        if txt or t.get(s):
            t[s] = {**(t.get(s) or {}), **txt} if txt else t.get(s)
            self.vault.set_texts(key, t)
        self.vault.set_draft(slot, None)
        if not self.tracking_since:
            self.tracking_since = key
        if slot == "evening":
            self.learn_day(day)
        return {}, info

    def delete_entry(self, day: date, slot: str | None) -> None:
        key = day.isoformat()
        if slot is None:
            self.vault.delete_day(key)
            self.vault.set_weight(key, None)
            return
        n = dict(self.vault.numbers(key))
        n.pop(slot[0], None)
        st = dict(n.get("status") or {})
        st.pop(slot, None)
        n["status"] = st
        n.pop("learned", None)
        self.vault.set_numbers(key, n)
        try:
            t = dict(self.vault.texts(key) or {})
            t.pop(slot[0], None)
            self.vault.set_texts(key, t)
        except Locked:
            pass

    # ---------------------------------------------------------- Zusammenfassungen
    def entity_state(self, clock: Clock, status: dict) -> dict:
        """Values for this person's entities. Never contains texts or cycle details."""
        today = clock.today
        n = self.day_numbers(today)
        rec = self.record(today.isoformat())
        tr = self.training(today)
        ws = self.weight_summary(today)
        cy = self.cycle(today)
        hs, _ = self.health(today)
        trends = self.trends(today)
        sl = n.get("sleep") or {}
        fc = self.mood.forecast(self._features_for(today)) if self.mod("suggestions") else None
        pred = self.sleep_prediction(clock) if self.mod("sleep_tracking") else None
        b = self.birthdate
        mx = self.sleepmaxing(today)

        def at(tod: float | None, add_day: int) -> str | None:
            if tod is None:
                return None
            t = local_at(today + timedelta(days=add_day), datetime.min.time(), clock.tz) + timedelta(minutes=tod)
            return t.isoformat()
        last_ci = None
        for d in sorted(self.vault.days, reverse=True)[:5]:
            for s in ("e", "m"):
                ts = (self.vault.days[d].get(s) or {}).get("_ts")
                if ts and (last_ci is None or ts > last_ci):
                    last_ci = ts
        last_tr = self.training_input(today).last_training
        return {
            "mood_morning": rec["mood_m"], "mood_evening": rec["mood_e"],
            "mood_today": round(rec["mood"], 1) if rec["mood"] is not None else None,
            "mood_avg7": trends["avg7"], "mood_avg30": trends["avg30"], "mood_trend": trends["trend"],
            "mood_forecast": fc.get("value") if fc and fc.get("ready") else None,
            "forecast_confidence": round(fc["confidence"] * 100) if fc and fc.get("ready") else None,
            "energy": rec["energy"], "health_feeling": rec["health"], "sleep_quality": rec["sleep_quality"],
            "health_score": hs,
            "sleep_state": (self.live.state_now if self.live else None) if self.mod("sleep_tracking") else None,
            "sleep_duration": round(sl["asleep"] / 60.0, 2) if sl.get("asleep") else None,
            "sleep_score": sl.get("score"), "sleep_week_pct": mx.get("week_pct") if mx else None,
            "sleep_opt_pct": mx.get("opt_pct") if mx else None, "sleep_optimum": round(self.optimum_h(today), 2),
            "last_bedtime": sl.get("start"), "last_wake": sl.get("end"),
            "predicted_bedtime": at(pred.bed, 0 if (pred and pred.bed is not None and pred.bed > 12 * 60) else 1) if pred else None,
            "predicted_wake": at(pred.wake, 1) if pred else None,
            "sleep_regularity": (sl.get("comps") or {}).get("regularity"),
            "sleep_confidence": round((self.live.confidence if self.live else 0) * 100) if self.mod("sleep_tracking") else None,
            "weight_due": (ws.due != "none") if ws else None, "weight_days_since": ws.days_since if ws else None,
            "weight_profile": self.profile.get("weight_kg") if not self.profile.get("weight_live") else None,
            "training_status": tr.status if tr else None, "training_days_since": tr.days_since if tr else None,
            "training_soreness": tr.last_soreness if tr else None, "training_recommended": tr.recommended if tr else None,
            "last_training": local_at(last_tr, datetime.min.time(), clock.tz).isoformat() if (tr and last_tr) else None,
            "cycle_next_start": cy.next_start.isoformat() if (cy and cy.next_start) else None,
            "cycle_next_end": cy.next_end.isoformat() if (cy and cy.next_end) else None,
            "cycle_active": cy.active if cy else None,
            "checkin_morning_open": status.get("morning") == "open", "checkin_evening_open": status.get("evening") == "open",
            "next_morning": status.get("next_morning"), "next_evening": status.get("next_evening"),
            "last_checkin": last_ci, "streak": self.streak(today),
            "age": b.age(today) if b else None,
            "next_birthday": local_at(b.next_birthday(today), datetime.min.time(), clock.tz).isoformat() if b else None,
            "birthday_today": b.is_today(today) if b else None,
            "paused": self.paused_on(today),
        }


def _weight_card(ws: WT.WeightSummary) -> dict:
    return {"trend": ws.trend, "week_avg": ws.week_avg, "delta_week": ws.delta_week, "delta_opt": ws.delta_opt,
            "optimum": ws.optimum, "range": list(ws.range) if ws.range else None, "color_week": ws.color_week,
            "color_opt": ws.color_opt, "hint": ws.hint, "due": ws.due, "days_since": ws.days_since}


def weight_card(ws: WT.WeightSummary | None) -> dict | None:
    return _weight_card(ws) if ws else None


def search_records(person: Person, query: str | None, chips: list[dict] | None, today: date) -> tuple[list[dict], list[dict]]:
    f = SE.Filters.from_chips(chips) if chips is not None else SE.parse(query or "", today)
    recs = person.records(with_texts=True)
    return SE.search(recs, f), f.chips()


def analysis(person: Person, today: date) -> dict:
    """Insights for the person (needs texts -> unlocked)."""
    recs = person.records(with_texts=True)
    low = INS.low_mood_alert(recs, today, 3, 3)
    return {
        "insights": INS.all_insights(recs, sleep=person.mod("sleep_tracking"), training=person.mod("training"),
                                     goals=person.mod("goals")),
        "topics": INS.topic_lists(recs), "goals": INS.goals_tracker(recs) if person.mod("goals") else [],
        "on_this_day": INS.on_this_day(recs, today), "low": low,
        "jar": INS.happy_jar(recs, today) if (recs and (recs[-1].get("mood") or 10) <= 4) else None,
        "learned": TX.learned_terms({r["day"]: " ".join((r.get("good") or []) + (r.get("bad") or []) + [r.get("journal") or ""])
                                     for r in recs}),
    }
