"""Benchmark: CPU share and RAM per computing-load level for 1 / 7 / 10 persons with 3 years of data.

Measures the real code paths (no HA needed):
* RAM: tracemalloc peak of all persons loaded (decrypted numbers, encrypted text tokens, models,
  36 h sensor buffers) – i.e. what the runtime keeps in memory.
* CPU: one simulated day per person – a bed sensor reporting every 5 s (ESPHome-like), live
  sleep detection every n minutes (level 1: 5, 2: 2, 3: 1) over the 20 h window, plus the nightly
  job (mood model, optimum, level-model fit) and one dashboard/entity computation every 5 min.
  CPU share = CPU seconds / 86 400 s (average share of one core).

    python tools/bench.py            # full table
    python tools/bench.py --quick    # 1 person, level 2
"""
from __future__ import annotations

import random
import sys
import time
import tracemalloc
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT))
import ha_stub  # noqa: E402

ha_stub.install()
import types  # noqa: E402

for name, path in (("custom_components", ROOT / "custom_components"),
                   ("custom_components.mental_health", ROOT / "custom_components" / "mental_health")):
    m = types.ModuleType(name)
    m.__path__ = [str(path)]
    sys.modules.setdefault(name, m)

from custom_components.mental_health.logic.crypto import Keyring  # noqa: E402
from custom_components.mental_health.person import Clock, Person  # noqa: E402
from custom_components.mental_health.storage import PersonVault, normalize_person  # noqa: E402

TZ = ZoneInfo("Europe/Berlin")
STEP = {1: 5, 2: 2, 3: 1}
TEXTS = ["Spaziergang im Wald", "Kaffee mit Freunden", "Gutes Essen", "Stress auf der Arbeit", "Regen", "Training im Gym",
         "Musik gehört", "Lange geschlafen", "Streit mit dem Bruder", "Sonnenuntergang am See"]


def make_person(idx: int, years: int = 3, seed: int = 1) -> Person:
    rnd = random.Random(seed + idx)
    ring = Keyring()
    pid = f"p{idx}"
    ring.ensure_person(pid)
    prof = normalize_person({"name": f"Person {idx}", "sex": "female" if idx % 2 else "male", "birthdate": "1990-05-17",
                             "height_cm": 175, "modules": {"weight": True, "cycle": idx % 2 == 1},
                             "sleep_sources": [{"id": "bed", "entity": "sensor.bed", "kind": "numeric"}]}, pid)
    vault = PersonVault(ring.dek(pid))
    vault.tek = ring.tek_without_pin(pid)
    today = date(2026, 11, 11)
    for i in range(365 * years, 0, -1):
        d = (today - timedelta(days=i)).isoformat()
        mood = rnd.randint(3, 9)
        n = {"m": {"mood": mood, "energy": rnd.randint(3, 9), "sleep_quality": rnd.randint(4, 9), "_ts": d},
             "e": {"mood": mood, "energy": rnd.randint(3, 9), "health": rnd.randint(5, 9), "trained": {"done": rnd.random() < .3}, "_ts": d},
             "sleep": {"asleep": rnd.randint(330, 520), "score": rnd.randint(50, 95), "bed_tod": 1400 + rnd.randint(-40, 40) % 1440,
                       "wake_tod": 410 + rnd.randint(-30, 30), "conf": 0.7, "src": "auto"}}
        vault.set_numbers(d, n)
        vault.set_texts(d, {"e": {"good": rnd.sample(TEXTS, 2), "bad": [rnd.choice(TEXTS)],
                                  "journal": " ".join(rnd.choice(TEXTS) for _ in range(rnd.randint(0, 12))) or None}})
        if i % 3 == 0:
            vault.set_weight(d, 70 + rnd.random() * 3)
    vault.dump()                     # Tokens erzeugen (wie nach dem Laden aus dem Store)
    p = Person(prof, vault, {})
    p.tracking_since = (today - timedelta(days=365 * years)).isoformat()
    return p


def simulate_day(p: Person, level: int, start: datetime) -> float:
    """CPU seconds for one day of this person."""
    rnd = random.Random(3)
    t0 = time.process_time()
    tod_of = lambda m: (datetime.fromtimestamp(m * 60, tz=TZ).hour * 60 + datetime.fromtimestamp(m * 60, tz=TZ).minute)  # noqa: E731
    base = int(start.timestamp() // 60)
    step = STEP[level]
    for minute in range(base, base + 1440):
        local = datetime.fromtimestamp(minute * 60, tz=TZ)
        h = local.hour + local.minute / 60
        loaded = h >= 23 or h < 0.75 or 6.5 <= h < 7.9
        for k in range(12):                      # alle 5 s ein Wert
            v = (1.6 if loaded else 3.1) + rnd.gauss(0, 0.02)
            p.feed_sample("bed", minute + k / 12.0, v)
        if (minute - base) % step == 0:
            p.roll_series(minute, tod_of)
            p.detect_live(Clock(local), tod_of)
        if (minute - base) % 5 == 0:
            p.entity_state(Clock(local), {})
    # Nacht-Job
    day = (start + timedelta(hours=12)).date()
    p.learn_day(day)
    p.relearn_optimum(day)
    for lm in p.sleep.levels.values():
        lm.fit(40 if level >= 2 else 20)
    return time.process_time() - t0


def run(n_persons: int, level: int) -> tuple[float, float]:
    tracemalloc.start()
    persons = [make_person(i) for i in range(n_persons)]
    _, peak_load = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    # Wärmen (Puffer/Level-Modell aufbauen), dann messen
    start = datetime(2026, 11, 10, 12, 0, tzinfo=TZ)
    for p in persons:
        simulate_day(p, level, start - timedelta(days=1))
    tracemalloc.start()
    cpu = sum(simulate_day(p, level, start) for p in persons)
    _, peak_day = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    mem = sum(_size(p) for p in persons)
    del peak_day
    return cpu / 86400 * 100, max(mem, peak_load) / 1024 / 1024


def _size(p: Person) -> int:
    """Approximate retained size of a person (deep sizeof over its containers)."""
    seen: set[int] = set()

    def sz(o, depth=0) -> int:
        if id(o) in seen or depth > 12:
            return 0
        seen.add(id(o))
        s = sys.getsizeof(o)
        if isinstance(o, dict):
            s += sum(sz(k, depth + 1) + sz(v, depth + 1) for k, v in o.items())
        elif isinstance(o, (list, tuple, set)):
            s += sum(sz(x, depth + 1) for x in o)
        elif hasattr(o, "__dict__") and not isinstance(o, type):
            s += sz(vars(o), depth + 1)
        return s
    return sz(p)


def ram_only(n_persons: int) -> float:
    tracemalloc.start()
    persons = [make_person(i) for i in range(n_persons)]
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    start = datetime(2026, 11, 10, 12, 0, tzinfo=TZ)
    for p in persons:                      # Puffer und Modelle einmal aufbauen
        p.series["bed"] = p.series.get("bed") or __import__("custom_components.mental_health.logic.sleep.features",
                                                                   fromlist=["x"]).MinuteSeries()
    del start
    mem = sum(_size(p) for p in persons)
    return max(mem, 0) / 1024 / 1024, peak / 1024 / 1024


def main() -> None:
    """CPU per level is measured on one person (persons are computed independently -> linear);
    RAM is measured with 1, 7 and 10 real persons."""
    quick = "--quick" in sys.argv
    levels = [2] if quick else [1, 2, 3]
    print(f"{'level':>6} {'CPU % of one core (1 person)':>30} {'10 persons':>12}")
    for lvl in levels:
        cpu, _ = run(1, lvl)
        print(f"{lvl:>6} {cpu:>30.3f} {cpu * 10:>12.2f}")
    print()
    print(f"{'persons':>8} {'RAM MB (kept)':>14} {'peak while loading':>20}")
    for n in ([1] if quick else [1, 7, 10]):
        kept, peak = ram_only(n)
        print(f"{n:>8} {kept:>14.1f} {peak:>20.1f}")


if __name__ == "__main__":
    main()
