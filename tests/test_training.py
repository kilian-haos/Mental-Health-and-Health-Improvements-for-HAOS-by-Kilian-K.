"""Training rhythm: every transition (section 11)."""
import unittest
from datetime import date, timedelta

import _path  # noqa: F401
from logic.training import (
    OVERDUE, PAUSE, READY_SOON, RECOMMENDED, TrainingInput, ask_soreness, early_training, evaluate,
)

T0 = date(2026, 11, 2)   # Montag: Training


def day(n: int) -> date:
    return T0 + timedelta(days=n)


def ev(today: int, soreness=None, paused=(), last=0, morning_done=False):
    return TrainingInput(day(today), day(last) if last is not None else None,
                         {day(k): v for k, v in (soreness or {}).items()}, {day(p) for p in paused}, morning_done)


class TrainingTransitions(unittest.TestCase):
    def test_training_day_is_pause(self):
        st = evaluate(ev(0))
        self.assertEqual(st.status, PAUSE)
        self.assertEqual(st.days_since, 0)

    def test_first_rest_day_pause(self):
        self.assertEqual(evaluate(ev(1, {1: 3})).status, PAUSE)

    def test_second_rest_day_ready_soon(self):
        self.assertEqual(evaluate(ev(2, {1: 3, 2: 2})).status, READY_SOON)

    def test_day3_low_soreness_recommended(self):
        st = evaluate(ev(3, {1: 2, 2: 1, 3: 1}))
        self.assertEqual(st.status, RECOMMENDED)
        self.assertEqual(st.recommended_on, day(3))
        self.assertFalse(st.highlight)

    def test_day3_soreness_zero_recommended(self):
        self.assertEqual(evaluate(ev(3, {3: 0})).status, RECOMMENDED)

    def test_day3_high_soreness_no_recommendation(self):
        self.assertEqual(evaluate(ev(3, {3: 2})).status, READY_SOON)

    def test_day3_soreness_not_yet_answered(self):
        self.assertEqual(evaluate(ev(3, {})).status, READY_SOON)

    def test_day2_low_soreness_still_no_recommendation(self):
        # zwei volle Pausentage sind Pflicht, auch ohne Muskelkater
        self.assertEqual(evaluate(ev(2, {1: 0, 2: 0})).status, READY_SOON)

    def test_high_then_low_next_morning(self):
        st = evaluate(ev(4, {3: 3, 4: 1}))
        self.assertEqual(st.status, RECOMMENDED)
        self.assertEqual(st.recommended_on, day(4))

    def test_not_trained_on_recommendation_day_becomes_overdue(self):
        st = evaluate(ev(4, {3: 0}))
        self.assertEqual(st.status, OVERDUE)
        self.assertTrue(st.highlight)
        self.assertEqual(st.overdue_days, 1)

    def test_overdue_counts_up_until_training(self):
        st = evaluate(ev(8, {3: 0}))
        self.assertEqual(st.status, OVERDUE)
        self.assertEqual(st.overdue_days, 5)

    def test_new_training_restarts(self):
        st = evaluate(ev(9, {3: 0}, last=9))
        self.assertEqual(st.status, PAUSE)
        self.assertEqual(st.overdue_days, 0)

    def test_training_during_pause_restarts_and_hints(self):
        self.assertTrue(early_training(day(0), day(1)))
        self.assertTrue(early_training(day(0), day(2)))
        self.assertFalse(early_training(day(0), day(3)))
        self.assertFalse(early_training(None, day(3)))
        self.assertEqual(evaluate(ev(1, last=1)).status, PAUSE)

    def test_missed_checkins_no_soreness_until_day5(self):
        self.assertEqual(evaluate(ev(4, {})).status, READY_SOON)
        st = evaluate(ev(5, {}))
        self.assertEqual(st.status, RECOMMENDED)
        self.assertEqual(st.recommended_on, day(5))

    def test_missed_morning_soreness_asked_evening(self):
        inp = ev(1, {}, morning_done=True)
        self.assertTrue(ask_soreness(inp, "evening"))
        self.assertTrue(ask_soreness(ev(1, {}), "morning"))
        self.assertFalse(ask_soreness(ev(1, {}, morning_done=False), "evening"))

    def test_soreness_not_asked_on_training_day_or_when_answered(self):
        self.assertFalse(ask_soreness(ev(0), "morning"))
        self.assertFalse(ask_soreness(ev(1, {1: 2}), "morning"))

    def test_soreness_not_asked_when_recommended_or_overdue(self):
        self.assertFalse(ask_soreness(ev(4, {3: 0}), "morning"))

    def test_person_pause_days_not_recommended_and_not_counted(self):
        # Tag 3 und 4 Pause (Urlaub): Empfehlung erst Tag 5
        st = evaluate(ev(5, {5: 1}, paused=(3, 4)))
        self.assertEqual(st.recommended_on, day(5))
        st = evaluate(ev(9, {5: 1}, paused=(3, 4, 7, 8)))
        self.assertEqual(st.status, OVERDUE)
        self.assertEqual(st.overdue_days, 2)       # Tag 6 und 9 zählen, 7/8 sind Pause

    def test_paused_today_flag_and_no_soreness_question(self):
        st = evaluate(ev(2, paused=(2,)))
        self.assertTrue(st.paused_today)
        self.assertFalse(ask_soreness(ev(2, paused=(2,)), "morning"))

    def test_never_trained_is_recommended_not_overdue(self):
        inp = TrainingInput(day(10), None, {}, set(), tracking_since=day(0))
        st = evaluate(inp)
        self.assertEqual(st.status, RECOMMENDED)
        self.assertFalse(st.highlight)

    def test_day_change_and_timezone_via_logical_days(self):
        # Logische Tage (Tagesgrenze) werden vorher berechnet; Training spät am Abend zählt zum Abendtag
        from datetime import datetime
        from zoneinfo import ZoneInfo

        from logic.daymath import logical_day, parse_hhmm
        tz = ZoneInfo("Europe/Berlin")
        late = datetime(2026, 11, 3, 0, 40, tzinfo=tz)
        self.assertEqual(logical_day(late, parse_hhmm("04:00")), date(2026, 11, 2))
        # Sommerzeitwechsel: 29.03.2026 02:30 existiert nicht
        from logic.daymath import local_at
        t = local_at(date(2026, 3, 29), parse_hhmm("02:30"), tz)
        self.assertEqual(t.hour, 3)


if __name__ == "__main__":
    unittest.main()
