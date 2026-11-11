"""Weight, cycle, birthdays, check-in rules, schedule, health score, mood model."""
import unittest
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import _path  # noqa: F401
from logic import birthday as B
from logic import checkin as C
from logic import cycle as Y
from logic import schedule as S
from logic import weight as W
from logic.analysis import health_score as H
from logic.analysis.mood_model import MIN_DAYS, MoodModel, features


class Weight(unittest.TestCase):
    def test_healthy_range_and_optimum(self):
        self.assertEqual(W.healthy_range(180, 30), (59.9, 80.7))
        opt, rng = W.optimum(180, 30)
        self.assertAlmostEqual(opt, 70.3, 1)
        self.assertEqual(W.healthy_range(180, 70), (71.3, 87.5))   # ab 65 leicht höher

    def test_target_clamped_to_healthy_range(self):
        self.assertEqual(W.clamp_target(50, 180, 30), 59.9)
        self.assertEqual(W.optimum(180, 30, target=95)[0], 80.7)
        self.assertEqual(W.optimum(180, 30, target=75)[0], 75.0)

    def test_no_height_no_optimum(self):
        self.assertEqual(W.optimum(None, 30), (None, None))
        s = W.summarize([date(2026, 11, 1)], [80.0], date(2026, 11, 1), height_cm=None, age=30, target=None, child=False)
        self.assertIsNone(s.optimum)
        self.assertEqual(s.hint, "add_height")

    def test_colour_four_cases(self):
        rng = (59.9, 80.7)
        opt = 70.0
        # unter dem Optimum: + grün, − rot
        self.assertEqual(W.color(+0.5, 64.0, opt, rng), W.GOOD)
        self.assertEqual(W.color(-0.5, 64.0, opt, rng), W.BAD)
        # über dem Optimum: + rot, − grün
        self.assertEqual(W.color(+0.5, 78.0, opt, rng), W.BAD)
        self.assertEqual(W.color(-0.5, 78.0, opt, rng), W.GOOD)
        # im optimalen Bereich: neutral
        self.assertEqual(W.color(-0.5, 70.4, opt, rng), W.NEUTRAL)

    def test_loss_below_healthy_range_never_green(self):
        self.assertEqual(W.color(-0.5, 55.0, 70.0, (59.9, 80.7)), W.BAD)
        days = [date(2026, 11, 1) + timedelta(days=i) for i in range(10)]
        s = W.summarize(days, [57.0] * 10, days[-1], height_cm=180, age=30, target=None, child=False)
        self.assertEqual(s.hint, "below_range")

    def test_fast_loss_hint(self):
        days = [date(2026, 10, 1) + timedelta(days=i) for i in range(21)]
        vals = [80.0 - i * 0.35 for i in range(21)]
        s = W.summarize(days, vals, days[-1], height_cm=180, age=30, target=None, child=False)
        self.assertEqual(s.hint, "fast_loss")

    def test_due_7_15_rule(self):
        self.assertEqual(W.due_state(6, False), "none")
        self.assertEqual(W.due_state(7, False), "warn")
        self.assertEqual(W.due_state(15, False), "required")
        last = date(2026, 10, 1)
        self.assertEqual(W.due_state(20, False, required_served=date(2026, 10, 20), last_value=last), "warn")

    def test_never_required_for_children(self):
        self.assertEqual(W.due_state(40, True), "none")
        s = W.summarize([date(2026, 11, 1)], [40.0], date(2026, 11, 20), height_cm=150, age=11, target=None, child=True)
        self.assertIsNone(s.optimum)
        self.assertEqual((s.color_week, s.color_opt, s.due), (W.NEUTRAL, W.NEUTRAL, "none"))

    def test_units_and_outliers(self):
        self.assertAlmostEqual(W.to_kg(176.4, "lb"), 80.0, 1)
        self.assertTrue(W.plausible(80.2, 80.0))
        self.assertFalse(W.plausible(95.0, 80.0))
        self.assertFalse(W.plausible(1.0))

    def test_trend_smooths(self):
        days = [date(2026, 11, 1) + timedelta(days=i) for i in range(4)]
        tr = W.WeightSeries(days, [80, 82, 80, 82]).trend()
        self.assertTrue(80 < tr[-1] < 81.5)


class Cycle(unittest.TestCase):
    def reports(self, starts, length=5):
        r = {}
        for s in starts:
            r[s] = "started"
            for k in range(1, length):
                r[s + timedelta(days=k)] = "yes"
            r[s + timedelta(days=length)] = "ended"
        return r

    def test_collapse_day(self):
        self.assertEqual(Y.collapse_day(["yes", "ended"]), "last")
        self.assertEqual(Y.collapse_day(["no", "started"]), "started")
        self.assertEqual(Y.collapse_day(["ended"]), "ended")
        self.assertEqual(Y.collapse_day(["no", "no"]), "no")

    def test_periods(self):
        s0 = date(2026, 1, 1)
        ps = Y.periods_from_days(self.reports([s0, s0 + timedelta(days=30)]))
        self.assertEqual(len(ps), 2)
        self.assertEqual(ps[0].end, s0 + timedelta(days=4))

    def test_prior_without_data(self):
        p = Y.predict({}, date(2026, 1, 10))
        self.assertIsNone(p.next_start)
        self.assertEqual(p.cycle_len, 28.0)

    def test_learns_cycle_length(self):
        s0 = date(2026, 1, 1)
        starts = [s0 + timedelta(days=31 * i) for i in range(8)]
        p = Y.predict(self.reports(starts), starts[-1] + timedelta(days=10), age=30)
        self.assertGreater(p.cycle_len, 30.0)
        self.assertEqual(p.next_start, starts[-1] + timedelta(days=round(p.cycle_len)))
        self.assertGreater(p.confidence, 0.4)
        self.assertFalse(p.active)

    def test_active_and_phase(self):
        s0 = date(2026, 1, 1)
        r = {s0: "started", s0 + timedelta(days=1): "yes"}
        p = Y.predict(r, s0 + timedelta(days=2))
        self.assertTrue(p.active)
        self.assertEqual(p.phase, "menstrual")

    def test_teen_spread_larger(self):
        self.assertGreater(Y.prior_spread(15), Y.prior_spread(30))

    def test_temperature_shift(self):
        s0 = date(2026, 3, 1)
        temps = {s0 + timedelta(days=i): 36.4 for i in range(14)}
        temps.update({s0 + timedelta(days=14 + i): 36.8 for i in range(8)})
        shift = Y.detect_temp_shift(temps, s0)
        self.assertEqual(shift, s0 + timedelta(days=14))
        p = Y.predict({s0: "started"}, s0 + timedelta(days=20), temps=temps)
        self.assertEqual(p.temp_shift, shift)
        self.assertEqual(p.next_start, shift + timedelta(days=13))


class Birthdays(unittest.TestCase):
    def test_parse_and_age(self):
        b = B.Birthdate.parse("2010-05-17")
        self.assertEqual(b.age(date(2026, 5, 16)), 15)
        self.assertEqual(b.age(date(2026, 5, 17)), 16)
        self.assertTrue(b.is_today(date(2026, 5, 17)))

    def test_without_year(self):
        b = B.Birthdate.parse("--12-24")
        self.assertIsNone(b.age(date(2026, 1, 1)))
        self.assertEqual(b.next_birthday(date(2026, 12, 25)), date(2027, 12, 24))
        self.assertEqual(b.to_str(), "--12-24")

    def test_leap_day(self):
        b = B.Birthdate.parse("2012-02-29")
        self.assertEqual(b.occurrence(2026), date(2026, 2, 28))
        self.assertTrue(b.is_today(date(2026, 2, 28)))
        self.assertTrue(b.is_today(date(2028, 2, 29)))
        self.assertEqual(b.age(date(2026, 2, 28)), 14)

    def test_several_same_day(self):
        ppl = {"a": B.Birthdate.parse("2000-06-01"), "b": B.Birthdate.parse("--06-01"), "c": B.Birthdate.parse("1990-07-01"),
               "d": None}
        self.assertEqual(B.family_today(ppl, date(2026, 6, 1)), ["a", "b"])
        nxt, who = B.family_next(ppl, date(2026, 5, 20))
        self.assertEqual((nxt, who), (date(2026, 6, 1), ["a", "b"]))
        nxt, who = B.family_next(ppl, date(2026, 6, 1))
        self.assertEqual(who, ["c"])

    def test_invalid(self):
        self.assertIsNone(B.Birthdate.parse("2026-02-30"))
        self.assertIsNone(B.Birthdate.parse("abc"))


class Checkin(unittest.TestCase):
    MODS = {"mood": True, "energy": True, "health": True, "sleep_quality": True, "good_bad": True, "goals": True,
            "journal": True, "training": True, "weight": True, "cycle": True, "birthday": True, "sleep_tracking": True}

    def test_evening_required_fields(self):
        form = C.build_form(C.FormContext("evening", self.MODS, cycle_enabled=True))
        req = {f.key for f in form if f.required}
        self.assertEqual(req, {"mood", "good", "bad", "trained", "period"})
        clean, err = C.validate(form, {})
        self.assertEqual(set(err), req)

    def test_evening_valid(self):
        form = C.build_form(C.FormContext("evening", self.MODS))
        clean, err = C.validate(form, {"mood": 7, "good": ["Spaziergang", " "], "bad": ["Regen"],
                                       "trained": {"done": True, "type": "cardio", "minutes": 30}, "journal": "  hi "})
        self.assertEqual(err, {})
        self.assertEqual(clean["good"], ["Spaziergang"])
        self.assertEqual(clean["trained"], {"done": True, "type": "cardio", "minutes": 30})
        self.assertEqual(clean["journal"], "hi")

    def test_disabled_modules_disappear(self):
        mods = {k: False for k in self.MODS} | {"mood": True}
        form = C.build_form(C.FormContext("evening", mods))
        self.assertEqual([f.key for f in form], ["mood"])

    def test_weight_required_by_rule_never_child(self):
        f = C.build_form(C.FormContext("evening", self.MODS, weight_due="required"))
        self.assertTrue(next(x for x in f if x.key == "weight").required)
        f = C.build_form(C.FormContext("evening", self.MODS, weight_due="required", child=True))
        self.assertFalse(any(x.key == "weight" for x in f))

    def test_period_details_required(self):
        form = C.build_form(C.FormContext("morning", self.MODS, cycle_enabled=True))
        _, err = C.validate(form, {"mood": 5, "period": {"answer": "yes"}})
        self.assertEqual(err.get("period"), "period_details")
        clean, err = C.validate(form, {"mood": 5, "period": {"answer": "yes", "flow": "medium", "pain": 4,
                                                             "symptoms": ["cramps", "x"]}})
        self.assertEqual(err, {})
        self.assertEqual(clean["period"]["symptoms"], ["cramps"])

    def test_morning_order_and_soreness(self):
        form = C.build_form(C.FormContext("morning", self.MODS, has_sleep_source=True, sleep_detected={"start": "x"},
                                          ask_soreness=True, goals_yesterday=[{"id": "g1", "text": "früh ins Bett"}]))
        keys = [f.key for f in form]
        self.assertLess(keys.index("sleep"), keys.index("mood"))
        self.assertIn("soreness", keys)
        self.assertIn("goals_review", keys)

    def test_scale_range(self):
        form = C.build_form(C.FormContext("morning", {"mood": True}))
        _, err = C.validate(form, {"mood": 11})
        self.assertEqual(err, {"mood": "required"})

    def test_sleep_correction(self):
        form = [C.Field("sleep", C.SLEEP)]
        clean, _ = C.validate(form, {"sleep": {"action": "correct", "start": "2026-11-10T23:40:00+01:00",
                                               "end": "2026-11-11T06:52:00+01:00"}})
        self.assertEqual(clean["sleep"]["action"], "correct")
        clean, _ = C.validate(form, {"sleep": {"action": "correct", "start": "2026-11-11T06:00:00", "end": "2026-11-10T06:00:00"}})
        self.assertNotIn("sleep", clean)

    def test_time_rules(self):
        r = C.TimeRules()
        d = date(2026, 11, 11)
        self.assertEqual(C.manual_allowed("evening", datetime(2026, 11, 11, 13, 59), d, d, r), (False, False))
        self.assertEqual(C.manual_allowed("evening", datetime(2026, 11, 11, 14, 0), d, d, r), (True, False))
        self.assertEqual(C.manual_allowed("evening", datetime(2026, 11, 12, 1, 0), d, d, r), (True, False))
        self.assertEqual(C.manual_allowed("morning", datetime(2026, 11, 11, 9, 0), d, d, r), (True, False))
        self.assertEqual(C.manual_allowed("morning", datetime(2026, 11, 11, 15, 0), d, d, r), (True, True))
        self.assertEqual(C.manual_allowed("evening", datetime(2026, 11, 12, 9, 0), d, d + timedelta(days=1), r), (False, False))
        r3 = C.TimeRules(late_entry="3_days")
        self.assertEqual(C.manual_allowed("evening", datetime(2026, 11, 13, 9, 0), d, d + timedelta(days=2), r3), (True, True))
        rn = C.TimeRules(late_entry="none")
        self.assertEqual(C.manual_allowed("morning", datetime(2026, 11, 11, 15, 0), d, d, rn), (False, True))

    def test_edit_note(self):
        e = C.merge_entries({"mood": 3, "_ts": "a"}, {"mood": 5, "_ts": "b"})
        self.assertEqual(e["_edits"], ["b"])
        self.assertEqual(e["_created"], "a")


class Schedule(unittest.TestCase):
    tz = ZoneInfo("Europe/Berlin")

    def test_fixed_weekday(self):
        s = S.SlotSchedule.from_dict({"mode": "fixed", "times": ["07:00"] * 5 + ["09:00"] * 2}, "07:30")
        self.assertEqual(S.fixed_time(s, date(2026, 11, 14), self.tz, "07:30").hour, 9)
        self.assertEqual(S.fixed_time(s, date(2026, 11, 13), self.tz, "07:30").hour, 7)

    def test_from_dict_defaults(self):
        s = S.SlotSchedule.from_dict(None, "21:00")
        self.assertEqual(s.times, ["21:00"] * 7)
        self.assertEqual(s.mode, "fixed")

    def test_sleep_trigger_and_fallback(self):
        g = S.AdaptiveGap(20)
        woke = datetime(2026, 11, 11, 6, 50, tzinfo=self.tz)
        self.assertEqual(S.sleep_trigger("morning", g, woke_at=woke, predicted_bed=None, confidence=0.8, now=woke),
                         woke + timedelta(minutes=20))
        self.assertIsNone(S.sleep_trigger("morning", g, woke_at=woke, predicted_bed=None, confidence=0.2, now=woke))
        bed = datetime(2026, 11, 11, 23, 0, tzinfo=self.tz)
        self.assertEqual(S.sleep_trigger("evening", g, woke_at=None, predicted_bed=bed, confidence=0.8, now=bed),
                         bed - timedelta(minutes=30))

    def test_adaptive_gap_bounded(self):
        g = S.AdaptiveGap(20)
        for _ in range(100):
            g.learn("morning", None)
        self.assertEqual(g.morning_offset(), 60.0)
        for _ in range(200):
            g.learn("morning", 1.0)
        self.assertEqual(g.morning_offset(), 10.0)
        g2 = S.AdaptiveGap.from_dict(g.to_dict(), 25)
        self.assertIsNone(g2.morning)

    def test_entity_trigger(self):
        t = datetime(2026, 11, 11, 6, 30, tzinfo=self.tz)
        self.assertEqual(S.entity_trigger(t, 15), t + timedelta(minutes=15))

    def test_clamp(self):
        t = datetime(2026, 11, 11, 3, 0, tzinfo=self.tz)
        self.assertEqual(S.clamp_to_day(t, time(5, 0), time(12, 0)).hour, 5)


class HealthScore(unittest.TestCase):
    def test_components_and_redistribution(self):
        total, comps = H.compute(H.HealthInput([8, 8, 8], [7], [7], [80], "pause", modules={"sleep_tracking": True}))
        self.assertIn("sleep", comps)
        self.assertTrue(70 <= total <= 95)
        t2, c2 = H.compute(H.HealthInput([8, 8, 8], [7], [7], [80], "pause", modules={"sleep_tracking": False,
                                                                                       "training": False}))
        self.assertNotIn("sleep", c2)
        self.assertNotIn("training", c2)

    def test_no_mood_no_score(self):
        self.assertEqual(H.compute(H.HealthInput([], [], [], []))[0], None)

    def test_family_k_threshold(self):
        self.assertIsNone(H.family([70, 80], 3))
        self.assertEqual(H.family([70, 80, 90], 3), 80)
        self.assertEqual(H.family([70, 80], 3, admin=True), 75)
        self.assertIsNone(H.family([70], 1))          # min. 2 auch bei k=1

    def test_weather(self):
        self.assertEqual(H.family_weather(8.5), "sunny")
        self.assertEqual(H.family_weather(2.0), "storm")


class Mood(unittest.TestCase):
    def test_learns_sleep_effect_and_gates(self):
        m = MoodModel()
        import random
        rnd = random.Random(1)
        for i in range(60):
            sh = rnd.uniform(5, 9)
            x = features(sleep_h=sh, optimum_h=8, sleep_score=None, weekday=i % 7, trend=None, trained_y=None,
                         soreness=None, phase=None, energy_y=None, health_y=None, mood_y=None)
            y = 6.5 + 0.9 * (sh - 8) + rnd.gauss(0, 0.4)
            if i == MIN_DAYS - 2:
                self.assertFalse(m.forecast(x)["ready"])
            m.update(x, y)
        x_short = features(sleep_h=5.5, optimum_h=8, sleep_score=None, weekday=2, trend=None, trained_y=None,
                           soreness=None, phase=None, energy_y=None, health_y=None, mood_y=None)
        f = m.forecast(x_short)
        self.assertTrue(f["ready"])
        self.assertLess(f["value"], 5.5)
        self.assertEqual(f["reasons"][0]["key"], "x_sleep")
        m2 = MoodModel.from_dict(m.to_dict())
        self.assertAlmostEqual(m2.forecast(x_short)["value"], f["value"], 1)


if __name__ == "__main__":
    unittest.main()
