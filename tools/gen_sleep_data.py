"""Synthetic sleep data for tests and tuning (deterministic).

Each scenario yields days of 24 h (14:00 -> 14:00) with per-minute values per source and the
ground truth (sleep onset, wake, naps). Run directly for a learning-curve report:

    python tools/gen_sleep_data.py            # all scenarios, 30 nights each
"""
from __future__ import annotations

import math
import random
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
import _path  # noqa: E402,F401  – lädt custom_components/mental_health/logic als Paket "logic"

from logic.sleep.detector import SleepModel  # noqa: E402
from logic.sleep.features import MinuteSeries  # noqa: E402
from logic.sleep.pipeline import build_window, feed_levels  # noqa: E402
from logic.sleep.sources import Source, binary_value  # noqa: E402

NAN = float("nan")
DAY = 1440
BASE_EPOCH_MIN = 29_000_000          # beliebige Epoche (Minuten), Start 14:00 lokal
WINDOW_FROM = 0                      # Fenster 14:00 -> 14:00 (ganzer Tag, Nickerchen inklusive)


@dataclass
class Truth:
    onset: int                         # Minute innerhalb des Tages (ab 14:00)
    wake: int
    naps: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Day:
    values: dict[str, list[float]]     # Quelle -> Minutenwerte (NaN = nicht verfügbar)
    ranges: dict[str, list[float]]
    truth: Truth
    weekday: int


def hm(h: float) -> int:
    """Time of day (hours, may exceed 24) -> minute since 14:00."""
    return int(round((h - 14.0) * 60)) % DAY if h >= 14 else int(round((h + 10.0) * 60))


def _noise(rng: random.Random, sd: float) -> float:
    return rng.gauss(0.0, sd)


def _jit(rng: random.Random, m: int, sd: float) -> int:
    return int(round(m + rng.gauss(0, sd)))


def _bed_numeric(rng, loaded, base, load_level, noise, drift, partial=None):
    """loaded: list of 0/1/2 (persons) or float load fraction per minute."""
    vals, rngs = [], []
    for i, ld in enumerate(loaded):
        target = base + drift
        if ld:
            target = base + (load_level - base) * ld
        v = target + _noise(rng, noise)
        if partial is not None and partial[i]:
            v = base + drift + _noise(rng, noise)
        r = abs(_noise(rng, noise * 2)) + (abs(_noise(rng, 0.25)) if (ld and rng.random() < 0.08) else 0.0)
        vals.append(v)
        rngs.append(r)
    return vals, rngs


# ------------------------------------------------------------------------- Szenarien
def scenario_kilian(n_days: int, seed: int = 1) -> tuple[list[Source], list[Day]]:
    """Bed sensor in volts, as in the screenshot: baseline 3.1 V, short evening dips without
    sleep, baseline during the night (sleeping beside the measuring point), morning trough."""
    rng = random.Random(seed)
    src = [Source.from_dict({"id": "bed", "entity": "sensor.esp_32_01_master_bed_sensor", "kind": "numeric"})]
    days = []
    for d in range(n_days):
        wd = (d + 2) % 7
        weekend = wd >= 5
        loaded = [0.0] * DAY
        # Abend-Einbrüche (setzen/legen, kurz) – kein Schlaf
        for h in (20.25, 20.67, 22.0):
            if rng.random() < 0.85:
                s = _jit(rng, hm(h), 10)
                for i in range(s, min(DAY, s + rng.randint(4, 14))):
                    loaded[i] = rng.uniform(0.75, 1.0)
        bed = _jit(rng, hm(23.0 + (0.5 if weekend else 0)), 20)
        onset = _jit(rng, bed + 55, 12)
        off_sensor = max(onset + 10, _jit(rng, hm(0.75 + (0.5 if weekend else 0)), 15))
        # kleine Einbrüche (Bewegung, Teilbelastung) bis ~00:45
        i = bed
        while i < off_sensor:
            if rng.random() < 0.25:
                for k in range(i, min(off_sensor, i + rng.randint(2, 8))):
                    loaded[k] = rng.uniform(0.12, 0.45)
            i += rng.randint(3, 9)
        # Morgen-Senke: wieder auf der Messstelle
        morning_on = _jit(rng, hm(6.5 + (1.0 if weekend else 0)), 15)
        wake = _jit(rng, hm(7.55 + (1.0 if weekend else 0)), 12)
        out = max(wake + 2, _jit(rng, wake + 6, 3))
        lvl = 0.35
        for k in range(morning_on, out):
            # ruhig liegend: Belastung ändert sich langsam (2,4 V -> 1,3 V), keine Sprünge je Minute
            lvl = min(1.0, max(0.3, lvl + rng.gauss(0.012, 0.02)))
            loaded[k] = lvl
        # kurze Erholung auf ~2,3 V
        rec = morning_on + rng.randint(25, 45)
        for k in range(rec, min(out, rec + 6)):
            loaded[k] = 0.4
        drift = 0.05 * math.sin(d / 5.0)
        vals, rngs = _bed_numeric(rng, loaded, 3.1, 1.0, 0.025, drift)
        days.append(Day({"bed": vals}, {"bed": rngs}, Truth(onset, wake), wd))
    return src, days


def scenario_binary(n_days: int, inverted: bool = False, seed: int = 2) -> tuple[list[Source], list[Day]]:
    rng = random.Random(seed)
    src = [Source.from_dict({"id": "mat", "entity": "binary_sensor.bed", "kind": "binary", "role": "in_bed",
                             "on_means": not inverted})]
    days = []
    for d in range(n_days):
        wd = (d + 2) % 7
        inbed = [0] * DAY
        # Lesen im Bett am Abend
        r = _jit(rng, hm(21.0), 15)
        for k in range(r, r + rng.randint(15, 35)):
            inbed[k] = 1
        bed = _jit(rng, hm(22.75 + (0.75 if wd >= 5 else 0)), 20)
        onset = _jit(rng, bed + 18, 6)
        wake = _jit(rng, hm(6.75 + (1.25 if wd >= 5 else 0)), 15)
        out = wake + rng.randint(3, 12)
        for k in range(bed, out):
            inbed[k] = 1
        # Toilette nachts
        t = rng.randint(onset + 120, max(onset + 121, wake - 60))
        for k in range(t, t + rng.randint(3, 7)):
            inbed[k] = 0
        vals = [float((1 - v) if inverted else v) for v in inbed]
        days.append(Day({"mat": vals}, {"mat": [0.0] * DAY}, Truth(onset, wake), wd))
    return src, days


def scenario_rising(n_days: int, seed: int = 3) -> tuple[list[Source], list[Day]]:
    """Load cell in kg: rises under load."""
    rng = random.Random(seed)
    src = [Source.from_dict({"id": "kg", "entity": "sensor.bed_weight", "kind": "numeric"})]
    days = []
    for d in range(n_days):
        wd = (d + 2) % 7
        loaded = [0.0] * DAY
        bed = _jit(rng, hm(23.25), 20)
        onset = _jit(rng, bed + 15, 6)
        wake = _jit(rng, hm(6.5 + (1.0 if wd >= 5 else 0)), 15)
        for k in range(bed, wake + rng.randint(2, 10)):
            loaded[k] = rng.uniform(0.92, 1.0)
        vals, rngs = _bed_numeric(rng, loaded, 2.0, 74.0, 0.4, 0.3 * math.sin(d / 4))
        days.append(Day({"kg": vals}, {"kg": rngs}, Truth(onset, wake), wd))
    return src, days


def scenario_shared(n_days: int, seed: int = 4) -> tuple[list[Source], list[Day], list[Day]]:
    """Shared bed, levels 0/1/2 persons; person B goes to bed later, phone screen as hint."""
    rng = random.Random(seed)
    src = [Source.from_dict({"id": "bed", "entity": "sensor.master_bed", "kind": "numeric", "shared_with": ["b"]}),
           Source.from_dict({"id": "scr", "entity": "binary_sensor.a_interactive", "kind": "aux", "role": "screen"})]
    days_a, days_b = [], []
    for d in range(n_days):
        wd = (d + 2) % 7
        a_bed = _jit(rng, hm(22.5), 15)
        a_on = a_bed + _jit(rng, 15, 4)
        a_wake = _jit(rng, hm(6.25), 12)
        b_bed = _jit(rng, hm(23.75), 20)
        b_on = b_bed + 20
        b_wake = _jit(rng, hm(7.5), 15)
        persons = [0.0] * DAY
        for k in range(DAY):
            persons[k] = (1 if a_bed <= k < a_wake + 4 else 0) + (1 if b_bed <= k < b_wake + 4 else 0)
        vals, rngs = [], []
        for k in range(DAY):
            p = persons[k]
            v = {0: 3.1, 1: 1.9, 2: 0.9}[int(p)] + _noise(rng, 0.03)
            vals.append(v)
            rngs.append(abs(_noise(rng, 0.05)))
        scr_a = [1.0 if (a_bed - 30 <= k < a_on - 2 or a_wake + 1 <= k < a_wake + 20) else 0.0 for k in range(DAY)]
        scr_b = [1.0 if (b_bed - 10 <= k < b_on - 2 or b_wake <= k < b_wake + 15) else 0.0 for k in range(DAY)]
        days_a.append(Day({"bed": vals, "scr": scr_a}, {"bed": rngs, "scr": [0.0] * DAY}, Truth(a_on, a_wake), wd))
        days_b.append(Day({"bed": vals, "scr": scr_b}, {"bed": rngs, "scr": [0.0] * DAY}, Truth(b_on, b_wake), wd))
    return src, days_a, days_b


def scenario_nap(n_days: int, seed: int = 5) -> tuple[list[Source], list[Day]]:
    """Daytime: reading in bed with phone (no sleep) vs. a real nap."""
    rng = random.Random(seed)
    src = [Source.from_dict({"id": "bed", "entity": "sensor.bed", "kind": "numeric"}),
           Source.from_dict({"id": "scr", "entity": "binary_sensor.phone_interactive", "kind": "aux", "role": "screen"})]
    days = []
    for d in range(n_days):
        wd = (d + 2) % 7
        loaded = [0.0] * DAY
        scr = [0.0] * DAY
        rngs_extra = [0.0] * DAY
        # Lesen 14:30–15:10 mit Handy und Bewegung
        r0 = _jit(rng, hm(14.5), 5)
        for k in range(r0, r0 + rng.randint(30, 45)):
            loaded[k] = 1.0
            scr[k] = 1.0 if rng.random() < 0.7 else 0.0
            rngs_extra[k] = 0.4 if rng.random() < 0.3 else 0.0
        naps = []
        if d % 2 == 0:
            n0 = _jit(rng, hm(16.0), 10)
            n1 = n0 + rng.randint(30, 60)
            for k in range(n0 - 4, n1 + 3):
                loaded[k] = 1.0
            naps.append((n0, n1))
        bed = _jit(rng, hm(23.0), 15)
        onset = bed + 15
        wake = _jit(rng, hm(6.75), 15)
        for k in range(bed, wake + 5):
            loaded[k] = 1.0
        vals, rngs = _bed_numeric(rng, loaded, 3.0, 1.2, 0.02, 0.0)
        rngs = [a + b for a, b in zip(rngs, rngs_extra)]
        days.append(Day({"bed": vals, "scr": scr}, {"bed": rngs, "scr": [0.0] * DAY}, Truth(onset, wake, naps), wd))
    return src, days


def scenario_shift(n_days: int, seed: int = 6) -> tuple[list[Source], list[Day]]:
    """Late shift: weekdays 02:00–10:00, weekends 23:30–08:30 (binary bed sensor)."""
    rng = random.Random(seed)
    src = [Source.from_dict({"id": "mat", "entity": "binary_sensor.bed", "kind": "binary"})]
    days = []
    for d in range(n_days):
        wd = (d + 2) % 7
        if wd < 5:
            bed, wake = _jit(rng, hm(26.0), 15), _jit(rng, hm(10.0), 15)
        else:
            bed, wake = _jit(rng, hm(23.5), 15), _jit(rng, hm(8.5), 15)
        onset = bed + 12
        v = [1.0 if bed <= k < wake + 5 else 0.0 for k in range(DAY)]
        days.append(Day({"mat": v}, {"mat": [0.0] * DAY}, Truth(onset, wake), wd))
    return src, days


def scenario_phone(n_days: int, seed: int = 7) -> tuple[list[Source], list[Day]]:
    """No bed sensor: phone charging + screen on, plus home presence."""
    rng = random.Random(seed)
    src = [Source.from_dict({"id": "chg", "entity": "binary_sensor.phone_is_charging", "kind": "aux", "role": "charging"}),
           Source.from_dict({"id": "scr", "entity": "binary_sensor.phone_interactive", "kind": "aux", "role": "screen"})]
    days = []
    for d in range(n_days):
        wd = (d + 2) % 7
        onset = _jit(rng, hm(23.4), 20)
        wake = _jit(rng, hm(6.9 + (1.0 if wd >= 5 else 0)), 15)
        plug = onset - rng.randint(5, 30)
        chg = [1.0 if plug <= k < wake + rng.randint(5, 25) else 0.0 for k in range(DAY)]
        scr = [0.0] * DAY
        for k in range(DAY):
            if not (onset <= k < wake):
                if rng.random() < (0.35 if (k < onset and k > onset - 120) or (wake <= k < wake + 60) else 0.25):
                    scr[k] = 1.0
            elif rng.random() < 0.003:
                scr[k] = 1.0          # kurzer Blick aufs Handy nachts
        days.append(Day({"chg": chg, "scr": scr}, {"chg": [0.0] * DAY, "scr": [0.0] * DAY}, Truth(onset, wake), wd))
    return src, days


def with_outages(days: list[Day], seed: int = 8) -> list[Day]:
    rng = random.Random(seed)
    for d, day in enumerate(days):
        if d % 3 == 1:
            s = rng.randint(hm(1.0), hm(4.0))
            for name in day.values:
                for k in range(s, s + rng.randint(30, 120)):
                    day.values[name][k] = NAN
                    day.ranges[name][k] = NAN
    return days


# ------------------------------------------------------------------------- Simulation
@dataclass
class NightEval:
    onset_err: float | None
    wake_err: float | None
    detected: bool
    false_naps: int
    naps_found: int
    naps_true: int
    confidence: float


def tod_list(start_offset: int, n: int) -> list[float]:
    return [float((14 * 60 + start_offset + i) % DAY) for i in range(n)]


def run(sources: list[Source], days: list[Day], label_nights: int = 14, model: SleepModel | None = None,
        other: list[Day] | None = None) -> tuple[SleepModel, list[NightEval]]:
    """Feed day by day, detect night (18:00 -> 14:00), confirm with truth for the first nights."""
    model = model or SleepModel()
    series = {s.id: MinuteSeries(2 * DAY) for s in sources}
    out: list[NightEval] = []
    for d, day in enumerate(days):
        base = BASE_EPOCH_MIN + d * DAY
        for s in sources:
            vals, rngs = day.values[s.id], day.ranges[s.id]
            if s.kind == "binary" and not s.on_means:
                vals = [binary_value(s, "on" if v == 1.0 else "off") if v == v else NAN for v in vals]
            for i in range(DAY):
                series[s.id].add(base + i + 0.1, vals[i])
                if rngs[i] == rngs[i] and rngs[i] > 0:
                    series[s.id].add(base + i + 0.6, vals[i] + rngs[i])
                    series[s.id].add(base + i + 0.7, vals[i])
            series[s.id].roll(base + DAY)
            feed_levels(s, model.levels, *_minute_means(series[s.id], base, DAY), tod_list(0, DAY))
        for lm in model.levels.values():
            lm.fit()
        start = base + WINDOW_FROM
        n = DAY - WINDOW_FROM
        tod = tod_list(WINDOW_FROM, n)
        win_series = {s.id: series[s.id].window(start, start + n) for s in sources}
        other_fn = None
        if other is not None:
            od = other[d]
            ob = [1.0 if od.truth.onset - 20 <= WINDOW_FROM + i < od.truth.wake + 4 else 0.0 for i in range(n)]
            other_fn = lambda _sid, ob=ob: ob  # noqa: E731
        win = build_window(start, tod, sources, win_series, model.levels, other_fn)
        res = model.detect(win)
        t = day.truth
        ev_on = ev_wk = None
        if res.sleep:
            ev_on = (res.sleep.start - base) - t.onset
            ev_wk = (res.sleep.end - base) - t.wake
        nap_true = [(a, b) for a, b in t.naps]
        found = 0
        false = 0
        for nap in res.naps:
            a, b = nap.start - base, nap.end - base
            if any(min(b, y) - max(a, x) > 10 for x, y in nap_true):
                found += 1
            else:
                false += 1
        out.append(NightEval(ev_on, ev_wk, res.sleep is not None, false, found, len(nap_true), res.confidence))
        if d < label_nights:
            model.learn(win, base + t.onset, base + t.wake, 1.0, res)
        elif res.confidence >= 0.8 and res.sleep:
            model.learn(win, res.sleep.start, res.sleep.end, 0.2)
        model.night_done(res, f"d{d}")
    return model, out


def _minute_means(series: MinuteSeries, base: int, n: int) -> tuple[list[float]]:
    m, _ = series.window(base, base + n)
    return (m,)


def summary(evals: list[NightEval], skip: int = 0) -> dict:
    ev = evals[skip:]
    on = [abs(e.onset_err) for e in ev if e.onset_err is not None]
    wk = [abs(e.wake_err) for e in ev if e.wake_err is not None]
    return {
        "nights": len(ev),
        "detected": sum(e.detected for e in ev),
        "onset_median": round(statistics.median(on), 1) if on else None,
        "wake_median": round(statistics.median(wk), 1) if wk else None,
        "false_naps": sum(e.false_naps for e in ev),
        "naps_found": sum(e.naps_found for e in ev),
        "naps_true": sum(e.naps_true for e in ev),
        "confidence": round(statistics.mean(e.confidence for e in ev), 2) if ev else None,
    }


SCENARIOS = {
    "1_kilian_volt": lambda n: scenario_kilian(n),
    "2a_binary": lambda n: scenario_binary(n),
    "2b_binary_inverted": lambda n: scenario_binary(n, inverted=True),
    "3_numeric_rising": lambda n: scenario_rising(n),
    "5_nap_vs_reading": lambda n: scenario_nap(n),
    "6_shift_work": lambda n: scenario_shift(n),
    "7_phone_only": lambda n: scenario_phone(n),
    "8_outages": lambda n: (lambda s, d: (s, with_outages(d)))(*scenario_kilian(n, seed=9)),
}


def main() -> None:
    n = 30
    print(f"{'scenario':22} {'det':>4} {'on 1-10':>8} {'on 21-30':>9} {'wk 1-10':>8} {'wk 21-30':>9} {'naps':>7} {'false':>6} {'conf':>5}")
    for name, fn in SCENARIOS.items():
        src, days = fn(n)
        _, ev = run(src, days)
        a = summary(ev[:10])
        b = summary(ev[20:])
        tot = summary(ev)
        print(f"{name:22} {tot['detected']:>4} {a['onset_median']!s:>8} {b['onset_median']!s:>9} "
              f"{a['wake_median']!s:>8} {b['wake_median']!s:>9} {tot['naps_found']}/{tot['naps_true']:<5} "
              f"{tot['false_naps']:>6} {b['confidence']!s:>5}")
    src, da, db = scenario_shared(n)
    _, ea = run(src, da, other=db)
    a = summary(ea[:10])
    b = summary(ea[20:])
    print(f"{'4_shared_bed (A)':22} {summary(ea)['detected']:>4} {a['onset_median']!s:>8} {b['onset_median']!s:>9} "
          f"{a['wake_median']!s:>8} {b['wake_median']!s:>9} {'-':>7} {summary(ea)['false_naps']:>6} {b['confidence']!s:>5}")


if __name__ == "__main__":
    main()
