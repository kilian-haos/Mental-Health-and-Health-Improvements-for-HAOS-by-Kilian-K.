"""Text analysis, search parser (de/en) + BM25, insights."""
import random
import unittest
from datetime import date, timedelta

import _path  # noqa: F401
from logic.analysis import insights as I
from logic.analysis import search as Q
from logic.analysis import text as T

TODAY = date(2026, 11, 11)


def records(n=60, seed=3):
    rnd = random.Random(seed)
    out = []
    for i in range(n):
        d = TODAY - timedelta(days=n - 1 - i)
        walk = rnd.random() < 0.35
        sleep_h = rnd.uniform(5.0, 9.0)
        mood = min(10, max(1, round(5 + (2 if walk else 0) + (sleep_h - 7) * 0.8 + rnd.gauss(0, 0.6))))
        out.append({
            "day": d.isoformat(), "mood": mood, "mood_m": mood - 1, "mood_e": mood, "energy": rnd.randint(3, 9),
            "health": 7, "sleep_h": round(sleep_h, 1), "trained": rnd.random() < 0.3, "period": False,
            "slots": ["morning", "evening"],
            "good": (["Spaziergang im Wald mit Freunden"] if walk else ["Gutes Essen"]),
            "bad": (["Stress auf der Arbeit"] if mood < 5 else ["Regen"]),
            "goals": ["früher ins Bett"] if i % 2 else [],
            "goal_results": [{"text": "früher ins Bett", "result": "done" if i % 4 == 1 else "not"}] if i % 2 else [],
            "journal": "Heute war ein schöner Tag am See." if mood >= 7 else ("Ich war sehr müde." if mood <= 4 else None),
        })
    return out


class Text(unittest.TestCase):
    def test_stem_and_topics(self):
        self.assertEqual(T.stem("Spaziergänge"), T.stem("spaziergange"))
        self.assertIn("nature", T.topics("Langer Spaziergang im Wald"))
        self.assertIn("friends", T.topics("met my friends"))
        self.assertIn("work", T.topics("Stress im Büro"))

    def test_tone_negation(self):
        self.assertGreater(T.tone("Heute war ein toller, glücklicher Tag"), 0.3)
        self.assertLess(T.tone("Ich bin traurig und einsam"), -0.3)
        self.assertLess(T.tone("Das war nicht gut"), 0)
        self.assertIsNone(T.tone("Bus fuhr um acht"))
        self.assertGreater(T.tone("not bad at all"), 0)

    def test_learned_terms(self):
        texts = {str(i): "Probe mit dem Chor in Liptingen" for i in range(4)}
        words = [t["word"] for t in T.learned_terms(texts)]
        self.assertIn("liptingen", words)


class Search(unittest.TestCase):
    def test_parse_de(self):
        f = Q.parse("schlechte Tage letzten Monat mit Training", TODAY)
        self.assertEqual(f.polarity, "negative")
        self.assertTrue(f.trained)
        self.assertEqual((f.start, f.end), (date(2026, 10, 1), date(2026, 10, 31)))
        self.assertEqual(f.terms, [])

    def test_parse_en(self):
        f = Q.parse("good days in summer with little sleep walk", TODAY)
        self.assertEqual(f.polarity, "positive")
        self.assertEqual(f.months, {6, 7, 8})
        self.assertEqual(f.sleep, "short")
        self.assertEqual(f.terms, ["walk"])

    def test_parse_misc(self):
        self.assertTrue(Q.parse("am Wochenende", TODAY).weekend)
        self.assertTrue(Q.parse("während der Periode", TODAY).period)
        f = Q.parse("letzten 14 Tage", TODAY)
        self.assertEqual(f.start, TODAY - timedelta(days=13))
        self.assertEqual(Q.parse("im März 2025", TODAY).months, {3})
        self.assertEqual(Q.parse("im März 2025", TODAY).start, date(2025, 1, 1))
        self.assertEqual(Q.parse("wo es mir gut ging", TODAY).polarity, "positive")

    def test_chips_roundtrip(self):
        f = Q.parse("schlechte Tage letzte Woche Arbeit", TODAY)
        g = Q.Filters.from_chips(f.chips())
        self.assertEqual((g.polarity, g.start, g.end, g.terms), (f.polarity, f.start, f.end, f.terms))

    def test_search_bm25_with_synonyms(self):
        recs = records()
        res = Q.search(recs, Q.parse("wald", TODAY))
        self.assertTrue(res)
        self.assertTrue(all("Wald" in Q.doc_text(next(r for r in recs if r["day"] == x["day"])) for x in res[:3]))
        res2 = Q.search(recs, Q.parse("forest", TODAY))     # Synonym (Thema Natur)
        self.assertTrue(res2)

    def test_search_filters_only(self):
        recs = records()
        res = Q.search(recs, Q.parse("schlechte Tage", TODAY))
        self.assertTrue(all(next(r for r in recs if r["day"] == x["day"])["mood"] <= 4 for x in res))
        days = [x["day"] for x in res]
        self.assertEqual(days, sorted(days, reverse=True))


class Insights(unittest.TestCase):
    def test_best_days_and_sleep(self):
        recs = records(90)
        ins = I.all_insights(recs, sleep=True, training=True, goals=True)
        keys = {i["key"] for i in ins}
        self.assertIn("i_best_days", keys)
        self.assertIn("i_sleep_mood", keys)
        self.assertIn("i_goal", keys)

    def test_disabled_modules(self):
        ins = I.all_insights(records(90), sleep=False, training=False, goals=False)
        self.assertFalse({i["key"] for i in ins} & {"i_sleep_mood", "i_goal"})

    def test_low_mood_alert(self):
        recs = [{"day": (TODAY - timedelta(days=i)).isoformat(), "mood": 2} for i in range(3)]
        self.assertTrue(I.low_mood_alert(recs, TODAY, 3, 3))
        recs[1]["mood"] = 5
        self.assertFalse(I.low_mood_alert(recs, TODAY, 3, 3))
        self.assertFalse(I.low_mood_alert(recs[:2], TODAY, 3, 3))

    def test_on_this_day_and_jar(self):
        recs = records(400)
        otd = I.on_this_day(recs, TODAY)
        self.assertEqual({o["when"] for o in otd}, {"month", "year"})
        jar = I.happy_jar(recs, TODAY)
        self.assertEqual(jar, I.happy_jar(recs, TODAY))     # stabil für den Tag

    def test_goals_tracker(self):
        g = I.goals_tracker(records(40))
        self.assertTrue(g[0]["recurring"])
        self.assertTrue(0 < g[0]["rate"] < 1)

    def test_reports(self):
        recs = records(30)
        rep = I.period_report(recs, TODAY - timedelta(days=6), TODAY, TODAY - timedelta(days=13), TODAY - timedelta(days=7))
        self.assertEqual(rep["cur"]["days"], 7)
        self.assertIn("mood", rep["delta"])

    def test_topic_lists(self):
        tl = I.topic_lists(records(90))
        self.assertIn("nature", [x["topic"] for x in tl["good"]])


if __name__ == "__main__":
    unittest.main()
