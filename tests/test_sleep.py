"""Sleep detection with synthetic data (tools/gen_sleep_data.py), learning curve and level model."""
import math
import unittest

import _path  # noqa: F401
import gen_sleep_data as G
from logic.sleep import score as SC
from logic.sleep.detector import SleepModel
from logic.sleep.features import MinuteSeries
from logic.sleep.mixture import LevelModel
from logic.sleep.predictor import NightTimes, predict
from logic.sleep.sources import Source, binary_value, enum_value, prob_value, suggest_mapping

N = 30


def run(name):
    src, days = G.SCENARIOS[name](N)
    return G.run(src, days)


class Scenarios(unittest.TestCase):
    """Median errors after the learning phase (nights 15-30)."""

    def check(self, name, onset, wake, min_conf=None, max_conf=None):
        model, ev = run(name)
        s = G.summary(ev, skip=14)
        self.assertEqual(s["detected"], s["nights"], name)
        self.assertLessEqual(s["onset_median"], onset, f"{name}: {s}")
        self.assertLessEqual(s["wake_median"], wake, f"{name}: {s}")
        if min_conf is not None:
            self.assertGreaterEqual(s["confidence"], min_conf, f"{name}: {s}")
        if max_conf is not None:
            self.assertLessEqual(s["confidence"], max_conf, f"{name}: {s}")
        return model, ev, s

    def test_1_kilian_volt_sensor(self):
        model, ev, s = self.check("1_kilian_volt", 25, 15, max_conf=0.6)   # mehrdeutig -> ehrlich niedrige Konfidenz
        self.assertEqual(s["false_naps"], 0)
        lv = model.levels["bed"].summary()
        self.assertEqual(lv["direction"], -1)
        self.assertAlmostEqual(lv["baseline"], 3.1, delta=0.1)
        self.assertTrue(2.0 < lv["threshold"] < 3.05)
        # Abend-Einbrüche ohne Schlaf: erkannter Schlaf beginnt nie vor 22:30
        for e in ev:
            if e.onset_err is not None:
                self.assertGreater(e.onset_err, -150)

    def test_2a_binary(self):
        self.check("2a_binary", 15, 10, min_conf=0.6)

    def test_2b_binary_inverted(self):
        _, ev_a, _ = self.check("2b_binary_inverted", 15, 10, min_conf=0.6)
        _, ev_b = run("2a_binary")
        self.assertEqual([e.onset_err for e in ev_a], [e.onset_err for e in ev_b])

    def test_3_numeric_rising(self):
        model, _, _ = self.check("3_numeric_rising", 15, 10, min_conf=0.6)
        self.assertEqual(model.levels["kg"].summary()["direction"], 1)

    def test_4_shared_bed(self):
        src, da, db = G.scenario_shared(N)
        model, ev = G.run(src, da, other=db)
        s = G.summary(ev, skip=14)
        self.assertLessEqual(s["onset_median"], 10)
        self.assertLessEqual(s["wake_median"], 10)
        self.assertEqual(len(model.levels["bed"].load_levels()), 2)      # 1 und 2 Personen

    def test_5_nap_vs_reading(self):
        _, ev, _ = self.check("5_nap_vs_reading", 10, 10)
        s = G.summary(ev)
        self.assertGreaterEqual(s["naps_found"], s["naps_true"] - 2)
        self.assertLessEqual(s["false_naps"], 2)

    def test_6_shift_work(self):
        self.check("6_shift_work", 15, 15)

    def test_7_phone_only(self):
        self.check("7_phone_only", 15, 10)

    def test_8_outages(self):
        self.check("8_outages", 40, 20, max_conf=0.6)

    def test_learning_curve_improves(self):
        src, days = G.scenario_kilian(N, seed=11)
        _, ev = G.run(src, days)
        early = G.summary(ev[:7])
        late = G.summary(ev[-10:])
        self.assertLessEqual(late["onset_median"] + late["wake_median"], early["onset_median"] + early["wake_median"] + 5)

    def test_model_serialisation(self):
        model, _ = run("2a_binary")
        m2 = SleepModel.from_dict(model.to_dict())
        self.assertEqual(m2.to_dict()["counts"], model.to_dict()["counts"])
        self.assertEqual(m2.labels, model.labels)
        v = m2.view()
        self.assertEqual(len(v["prior"]), 48)
        self.assertFalse(v["learning"])
        m2.reset()
        self.assertEqual(m2.labels, 0)
        self.assertTrue(m2.view()["learning"])


class Parts(unittest.TestCase):
    def test_minute_series_hold_and_range(self):
        s = MinuteSeries(60)
        s.add(100.2, 3.1)
        s.add(100.8, 2.9)
        s.add(103.5, 3.0)
        s.roll(106)
        m, r = s.window(100, 106)
        self.assertAlmostEqual(m[0], 3.0, 3)
        self.assertAlmostEqual(r[0], 0.2, 3)
        self.assertAlmostEqual(m[1], 2.9, 3)          # Wert gehalten
        self.assertAlmostEqual(m[5], 3.0, 3)
        s.add(106.1, float("nan"))
        s.roll(108)
        self.assertTrue(math.isnan(s.window(107, 108)[0][0]))
        s2 = MinuteSeries.from_dict(s.to_dict(), 60)
        self.assertEqual(s2.head, s.head)

    def test_level_model_persistence(self):
        lm = LevelModel()
        for i in range(2000):
            lm.add(3.1 if i % 3 else 1.5, 1.0, daytime=i % 3 != 0)
        lm.fit()
        self.assertEqual(lm.direction, -1)
        self.assertGreater(lm.occupancy(1.5), 0.9)
        self.assertLess(lm.occupancy(3.1), 0.1)
        lm2 = LevelModel.from_dict(lm.to_dict())
        self.assertAlmostEqual(lm2.threshold(), lm.threshold(), 4)
        lm2.user_threshold = 2.5
        self.assertNotEqual(lm2.threshold(), lm.threshold())

    def test_source_mappings(self):
        inv = Source.from_dict({"id": "b", "entity": "binary_sensor.x", "kind": "binary", "on_means": False})
        self.assertEqual(binary_value(inv, "off"), 1.0)
        self.assertTrue(math.isnan(binary_value(inv, "unavailable")))
        en = Source.from_dict({"id": "e", "entity": "sensor.sleep", "kind": "enum", "mapping": {"Deep": "asleep"}})
        self.assertEqual(enum_value(en, "Deep")[0], 1.0)
        self.assertEqual(enum_value(en, "awake")[0], 0.0)
        self.assertEqual(prob_value("85"), 0.85)
        self.assertEqual(suggest_mapping(["sleep_tracking_started", "foo"]),
                         {"sleep_tracking_started": "asleep", "foo": "ignore"})
        chg = Source.from_dict({"id": "c", "entity": "sensor.phone_charger_type", "kind": "aux", "role": "charging"})
        self.assertEqual(binary_value(chg, "none"), 0.0)
        self.assertEqual(binary_value(chg, "ac"), 1.0)

    def test_predictor_and_alarm(self):
        hist = [NightTimes(23 * 60 + (i % 3) * 10, 6 * 60 + 45, True, i) for i in range(10)]
        hist += [NightTimes(0 * 60 + 30, 9 * 60, False, i) for i in range(4)]
        p = predict(hist, True)
        self.assertAlmostEqual(p.bed, 23 * 60 + 10, delta=5)
        q = predict(hist, False)
        self.assertAlmostEqual(q.wake, 9 * 60, delta=2)
        a = predict(hist, True, alarm_tod=6 * 60)
        self.assertAlmostEqual(a.wake, 6 * 60 + 5, delta=1)

    def test_score_and_optimum(self):
        self.assertEqual(SC.recommended_range(10), (9.0, 11.0))
        self.assertEqual(SC.recommended_range(70), (7.0, 8.0))
        opt, conf = SC.learn_optimum(30, None, [])
        self.assertEqual(opt, 8.0)
        import random
        rnd = random.Random(2)
        pairs = [(d, 8 - (d - 7.4) ** 2 + rnd.gauss(0, 0.3)) for d in [rnd.uniform(5.5, 9.5) for _ in range(120)]]
        opt, conf = SC.learn_optimum(30, None, pairs)
        self.assertTrue(7.3 <= opt <= 7.9, opt)
        opt_kid, _ = SC.learn_optimum(10, None, pairs)
        self.assertGreaterEqual(opt_kid, 9.0)                     # immer in der Empfehlung
        total, comps = SC.score(SC.ScoreInput(asleep_min=480, optimum_h=8, bed_dev_min=5, wake_dev_min=5, subjective=9))
        self.assertGreater(total, 85)
        low, _ = SC.score(SC.ScoreInput(asleep_min=300, optimum_h=8, interruptions=4, interruption_min=40))
        self.assertLess(low, 50)
        self.assertNotIn("latency", comps)

    def test_sleepmaxing_colours(self):
        m = SC.sleepmaxing(450, 420, 7.75)           # näher am Optimum als die Woche
        self.assertEqual(m["week_color"], "good")
        self.assertEqual(m["week_pct"], 7)
        m = SC.sleepmaxing(560, 470, 7.75)           # zu viel Schlaf, weg vom Optimum
        self.assertEqual(m["week_color"], "bad")
        self.assertEqual(m["opt_color"], "bad")
        self.assertEqual(SC.sleepmaxing(470, None, 7.75)["opt_color"], "good")


if __name__ == "__main__":
    unittest.main()
