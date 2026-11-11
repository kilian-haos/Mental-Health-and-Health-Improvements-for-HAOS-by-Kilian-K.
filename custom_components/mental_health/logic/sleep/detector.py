"""Sleep detection: state logic over time (HMM-like) + signal fusion + learning (pure Python).

Why not a threshold per sample? Real bed sensors are ambiguous: a low value is not
automatically sleep (sitting on the bed in the evening), the baseline is not automatically
awake (sleeping next to the measuring point, shared bed). So:

1. Every minute has evidence from all channels (occupancy, movement, sleep hints, phone
   screen, light, motion elsewhere, presence, home). Each channel has a learned probability
   per state – a tiny naive-Bayes model with Beta counts (learned from confirmations).
2. A learned **time-of-day prior** (48 half-hour bins) says how likely sleep is right now.
   At night a "quiet baseline" between going to bed and getting up therefore stays "asleep"
   unless something clearly speaks against it (screen on, light on, motion in the hallway,
   not at home).
3. Forward-backward over the minutes of the night window gives a posterior per minute.
   Evidence is tempered (neighbouring minutes are not independent).
4. Post-processing: minimum durations, hysteresis, short wake bouts count as interruptions,
   naps during the day are separate, getting up is anchored to the last bed exit.
5. Confirmations/corrections in the morning check-in are the strongest labels: they update
   the channel probabilities, the prior and the start/end bias.

States: A = away/up (not in bed), W = in bed awake, S = asleep.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .mixture import LevelModel

NAN = float("nan")
A, W, S = 0, 1, 2
STATES = ("away", "in_bed", "asleep")
NSTATE = 3

# Startwerte der Kanal-Wahrscheinlichkeiten P(Kanal = 1 | Zustand) für A, W, S
CHANNEL_PRIORS: dict[str, tuple[float, float, float]] = {
    "occ": (0.03, 0.90, 0.55),       # schlafend oft neben der Messstelle -> nur 0,55
    "move": (0.45, 0.50, 0.08),
    "hint": (0.05, 0.15, 0.85),
    "screen": (0.30, 0.35, 0.01),
    "charging": (0.30, 0.50, 0.75),
    "light": (0.50, 0.50, 0.03),
    "away_motion": (0.40, 0.04, 0.02),
    "room": (0.20, 0.95, 0.90),
    "home": (0.60, 0.995, 0.995),
}
PRIOR_STRENGTH = 20.0               # Gewicht der Startwerte (Pseudo-Beobachtungen)
TAU = 6.0                           # Temperierung: ~6 Minuten zählen wie eine unabhängige Beobachtung

# Übergänge pro Minute
TRANS = (
    (0.980, 0.015, 0.005),
    (0.025, 0.950, 0.025),
    (0.002, 0.008, 0.990),
)

PRIOR_BINS = 48
PRIOR_HALF_LIFE_N = 30.0            # Nächte

COLD_NIGHT_START = 21 * 60
COLD_NIGHT_END = 10 * 60
COLD_MIN_SLEEP = 30
LEARNED_MIN_SLEEP = 15
MERGE_GAP = 25                      # kürzere Wachphasen = Unterbrechung, kein Ende
INTERRUPTION_MIN = 3
NAP_MIN = 20
NAP_FROM = 8 * 60                   # Nickerchen nur tagsüber
NAP_UNTIL = 20 * 60 + 30
NAP_MAX_PRIOR = 0.2
WAKE_ANCHOR_EMPTY = 60              # so lange leer nach dem letzten Verlassen -> aufgestanden
MATURE_NIGHTS = 14


def cold_prior(tod_min: float) -> float:
    """Conservative start: night window 21-10 h, core 23:00-06:30."""
    t = tod_min % 1440
    if 23 * 60 <= t or t < 6 * 60 + 30:
        return 0.9
    if 21 * 60 <= t < 23 * 60:
        return 0.1 + 0.8 * (t - 21 * 60) / 120.0
    if 6 * 60 + 30 <= t < 10 * 60:
        return 0.9 - 0.85 * (t - 390) / 210.0
    return 0.03


def in_cold_window(tod_min: float) -> bool:
    t = tod_min % 1440
    return t >= COLD_NIGHT_START or t < COLD_NIGHT_END


@dataclass
class Window:
    """Minutes [start, start+n) with local time of day and channel values (0..1 or NaN)."""

    start: int                                   # absolute Minute (Epoche)
    tod: list[float]                             # Minute des Tages (lokal) je Minute
    ch: dict[str, list[float]] = field(default_factory=dict)

    @property
    def n(self) -> int:
        return len(self.tod)

    def get(self, name: str, i: int) -> float:
        arr = self.ch.get(name)
        if arr is None:
            return NAN
        return arr[i]


@dataclass
class Segment:
    start: int                 # absolute Minute
    end: int                   # exklusiv
    kind: str                  # sleep | nap | interruption | in_bed

    @property
    def minutes(self) -> int:
        return self.end - self.start

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "kind": self.kind}


@dataclass
class NightResult:
    sleep: Segment | None
    interruptions: list[Segment]
    naps: list[Segment]
    in_bed: list[Segment]
    state_now: str             # away | in_bed | asleep | nap
    confidence: float          # 0..1
    p_sleep: list[float]
    bed_entry: int | None      # erstes Zubettgehen vor dem Einschlafen
    latency: int | None        # Einschlaflatenz (min), wenn messbar

    @property
    def asleep_minutes(self) -> int:
        if self.sleep is None:
            return 0
        return self.sleep.minutes - sum(i.minutes for i in self.interruptions)


class SleepModel:
    """Per person. Small and serialisable (a few kB)."""

    def __init__(self) -> None:
        self.counts: dict[str, list[list[float]]] = {
            c: [[p * PRIOR_STRENGTH, (1 - p) * PRIOR_STRENGTH] for p in ps] for c, ps in CHANNEL_PRIORS.items()
        }
        self.prior_s = [0.0] * PRIOR_BINS          # gelernte Schlaf-Häufigkeit je Halbstunde (gewichtet)
        self.prior_w = [0.0] * PRIOR_BINS          # Gewichte
        self.onset_bias = 0.0
        self.wake_bias = 0.0
        self.labels = 0
        self.nights = 0
        self.levels: dict[str, LevelModel] = {}
        self.history: list[dict] = []              # letzte Nächte (Zeiten, Konfidenz) für Ansicht/Prognose

    # ---------------------------------------------------------- Parameter
    @property
    def maturity(self) -> float:
        return min(1.0, (self.nights + 2 * self.labels) / (MATURE_NIGHTS * 1.5))

    @property
    def learning(self) -> bool:
        return self.maturity < 1.0

    @property
    def min_sleep(self) -> int:
        return COLD_MIN_SLEEP if (self.labels < 3 and self.nights < 7) else LEARNED_MIN_SLEEP

    def p(self, channel: str, state: int) -> float:
        a, b = self.counts[channel][state]
        return a / (a + b)

    def prior(self, tod_min: float) -> float:
        """P(asleep) at this time of day: learned bins blended with the cold prior."""
        i = int((tod_min % 1440) // 30)
        w = self.prior_w[i]
        cold = cold_prior(tod_min)
        if w <= 0:
            return cold
        learned = self.prior_s[i] / w
        k = min(0.85, w / 10.0)
        return (1 - k) * cold + k * learned

    # ---------------------------------------------------------- Inferenz
    def _emissions(self, win: Window) -> list[tuple[float, float, float]]:
        out = []
        ps = {c: [self.p(c, s) for s in range(NSTATE)] for c in self.counts}
        chans = [c for c in self.counts if c in win.ch]
        for i in range(win.n):
            q = self.prior(win.tod[i])
            p_s = 0.03 + 0.92 * q
            p_w = 0.06 + 0.06 * q
            p_a = max(0.01, 1.0 - p_s - p_w)
            ll = [math.log(p_a), math.log(p_w), math.log(p_s)]
            ev = [0.0, 0.0, 0.0]
            for c in chans:
                v = win.ch[c][i]
                if v != v:
                    continue
                pc = ps[c]
                for s in range(NSTATE):
                    lik = v * pc[s] + (1.0 - v) * (1.0 - pc[s])
                    ev[s] += math.log(max(lik, 1e-6))
            out.append(tuple((ll[s] + ev[s]) / TAU for s in range(NSTATE)))
        return out

    def posteriors(self, win: Window) -> list[list[float]]:
        n = win.n
        if n == 0:
            return []
        em = self._emissions(win)
        lt = [[math.log(TRANS[i][j]) / TAU * 3.0 for j in range(NSTATE)] for i in range(NSTATE)]
        # Vorwärts
        fw = [[0.0] * NSTATE for _ in range(n)]
        fw[0] = list(em[0])
        _norm(fw[0])
        for t in range(1, n):
            prev = fw[t - 1]
            for j in range(NSTATE):
                fw[t][j] = em[t][j] + _lse([prev[i] + lt[i][j] for i in range(NSTATE)])
            _norm(fw[t])
        # Rückwärts
        bw = [[0.0] * NSTATE for _ in range(n)]
        for t in range(n - 2, -1, -1):
            nxt = bw[t + 1]
            for i in range(NSTATE):
                bw[t][i] = _lse([lt[i][j] + em[t + 1][j] + nxt[j] for j in range(NSTATE)])
            _norm(bw[t])
        post = []
        for t in range(n):
            v = [fw[t][s] + bw[t][s] for s in range(NSTATE)]
            m = max(v)
            e = [math.exp(x - m) for x in v]
            z = sum(e)
            post.append([x / z for x in e])
        return post

    def detect(self, win: Window, night_mask: list[bool] | None = None, *, apply_bias: bool = True) -> NightResult:
        """Analyse a window (typically 18:00–14:00 or the live buffer)."""
        n = win.n
        post = self.posteriors(win)
        p_s = [p[S] for p in post]
        occ = win.ch.get("occ") or [NAN] * n
        if night_mask is None:
            night_mask = [self._in_night(t) for t in win.tod]
        asleep = [p_s[i] > 0.5 and night_mask[i] for i in range(n)]
        blocks = _runs(asleep)
        # Zusammenführen: kurze Wachphasen = Unterbrechungen
        merged: list[list[int]] = []
        for a, b in blocks:
            if merged and a - merged[-1][1] < MERGE_GAP:
                merged[-1][1] = b
            else:
                merged.append([a, b])
        merged = [m for m in merged if m[1] - m[0] >= self.min_sleep]
        sleep = None
        interruptions: list[Segment] = []
        bed_entry = latency = None
        if merged:
            a, b = max(merged, key=lambda m: m[1] - m[0])
            b = self._wake_anchor(a, b, occ, win)
            if apply_bias:
                a = max(0, min(b - 1, a + int(round(self.onset_bias))))
                b = max(a + 1, min(n, b + int(round(self.wake_bias))))
            sleep = Segment(win.start + a, win.start + b, "sleep")
            for x, y in _runs([not asleep[i] for i in range(a, b)]):
                if y - x >= INTERRUPTION_MIN:
                    interruptions.append(Segment(win.start + a + x, win.start + a + y, "interruption"))
            # Zubettgehen: Beginn der zusammenhängenden Belegung/Wach-im-Bett-Phase vor dem Einschlafen
            j = a
            while j > 0 and (post[j - 1][W] + post[j - 1][S] > 0.5) and a - j < 180:
                j -= 1
            if j < a:
                bed_entry = win.start + j
                latency = a - j
        naps = self._naps(win, post, night_mask, sleep)
        in_bed = [Segment(win.start + x, win.start + y, "in_bed")
                  for x, y in _runs([(occ[i] == occ[i] and occ[i] > 0.5) for i in range(n)]) if y - x >= 2]
        # aktueller Zustand (letzte Minute)
        last = n - 1
        state = "away"
        if last >= 0:
            if sleep and sleep.start <= win.start + last < sleep.end and not any(
                    s.start <= win.start + last < s.end for s in interruptions):
                state = "asleep"
            elif naps and naps[-1].end >= win.start + last:
                state = "nap"
            elif post[last][W] + post[last][S] > 0.5 or (occ[last] == occ[last] and occ[last] > 0.5):
                state = "in_bed"
        conf = self._confidence(post, sleep, win)
        return NightResult(sleep, interruptions, naps, in_bed, state, conf, p_s, bed_entry, latency)

    def _in_night(self, tod: float) -> bool:
        if self.maturity < 0.3:
            return in_cold_window(tod)
        return self.prior(tod) > 0.08 or in_cold_window(tod) and self.prior(tod) > 0.04

    def _wake_anchor(self, a: int, b: int, occ: list[float], win: Window) -> int:
        """Cut the sleep block at the last bed exit if the bed stays empty afterwards (getting up)."""
        last_loaded = None
        for i in range(b - 1, a - 1, -1):
            if occ[i] == occ[i] and occ[i] > 0.5:
                last_loaded = i
                break
        if last_loaded is None or last_loaded >= b - 1:
            return b
        tod = win.tod[last_loaded]
        if not (4 * 60 <= tod <= 13 * 60):
            return b
        empty_after = sum(1 for i in range(last_loaded + 1, min(win.n, last_loaded + 1 + 600))
                          if occ[i] == occ[i] and occ[i] < 0.3)
        if empty_after >= min(WAKE_ANCHOR_EMPTY, win.n - last_loaded - 1) and b - last_loaded > 10:
            return last_loaded + 1
        return b

    def _naps(self, win: Window, post: list[list[float]], night_mask: list[bool], sleep: Segment | None) -> list[Segment]:
        n = win.n
        occ = win.ch.get("occ") or [NAN] * n
        move = win.ch.get("move") or [NAN] * n
        screen = win.ch.get("screen") or [NAN] * n
        hint = win.ch.get("hint") or [NAN] * n
        cand = []
        for i in range(n):
            m = win.start + i
            if sleep and sleep.start - 30 <= m < sleep.end + 30:
                cand.append(False)
                continue
            t = win.tod[i] % 1440
            if self.prior(t) > NAP_MAX_PRIOR or not (NAP_FROM <= t < NAP_UNTIL):
                cand.append(False)
                continue
            lying = occ[i] == occ[i] and occ[i] > 0.5 and (move[i] != move[i] or move[i] < 0.35)
            asleep_hint = hint[i] == hint[i] and hint[i] > 0.6
            phone = screen[i] == screen[i] and screen[i] > 0.5
            cand.append((lying or asleep_hint) and not phone)
        # 2-Minuten-Ausreißer schließen
        for i in range(1, n - 2):
            if not cand[i] and cand[i - 1] and (cand[i + 1] or cand[i + 2]):
                cand[i] = True
        return [Segment(win.start + x, win.start + y, "nap") for x, y in _runs(cand) if y - x >= NAP_MIN]

    def _confidence(self, post: list[list[float]], sleep: Segment | None, win: Window) -> float:
        if sleep is None:
            return round(0.3 * self.maturity + 0.2, 2)
        a, b = sleep.start - win.start, sleep.end - win.start
        inner = [post[i][S] for i in range(max(0, a), min(win.n, b))]
        sharp = sum(inner) / len(inner) if inner else 0.5
        edge = []
        for k in (a, b):
            lo, hi = max(0, k - 10), min(win.n, k + 10)
            seg = [post[i][S] for i in range(lo, hi)]
            if seg:
                edge.append(max(seg) - min(seg))
        edges = sum(edge) / len(edge) if edge else 0.5
        nsrc = sum(1 for c in win.ch if c != "move" and any(v == v for v in win.ch[c]))
        src = min(1.0, 0.8 + 0.1 * nsrc)
        # Wie viel der Nacht stützen die Sensoren selbst (ohne Tageszeit-Prior)?
        cover = self._evidence_cover(win, a, b)
        c = (0.35 * sharp + 0.2 * edges + 0.2 * self.maturity + 0.25 * cover) * src * (0.6 + 0.4 * cover)
        return round(max(0.05, min(0.99, c)), 2)

    def _evidence_cover(self, win: Window, a: int, b: int) -> float:
        """Share of minutes in [a, b) where the sensors themselves favour 'asleep' over 'away'."""
        chans = [c for c in self.counts if c in win.ch]
        if not chans or b <= a:
            return 0.0
        pa = {c: self.p(c, A) for c in chans}
        ps = {c: self.p(c, S) for c in chans}
        good = known = 0
        for i in range(max(0, a), min(win.n, b), 2):
            llr = 0.0
            seen = False
            for c in chans:
                v = win.ch[c][i]
                if v != v:
                    continue
                seen = True
                ls = v * ps[c] + (1 - v) * (1 - ps[c])
                la = v * pa[c] + (1 - v) * (1 - pa[c])
                llr += math.log(max(ls, 1e-6)) - math.log(max(la, 1e-6))
            if seen:
                known += 1
                good += 1 if llr > 0 else 0
        return good / known if known else 0.0

    # ---------------------------------------------------------- Lernen
    def learn(self, win: Window, start: int, end: int, weight: float = 1.0, detected: NightResult | None = None) -> None:
        """Label: asleep in [start, end) (absolute minutes); everything else in the window not."""
        if end <= start:
            return
        occ = win.ch.get("occ") or [NAN] * win.n
        for i in range(win.n):
            m = win.start + i
            if start <= m < end:
                st = S
            else:
                o = occ[i]
                st = W if (o == o and o > 0.5) else A
            for c, arr in win.ch.items():
                if c not in self.counts:
                    continue
                v = arr[i]
                if v != v:
                    continue
                cnt = self.counts[c][st]
                cnt[0] += weight * v / TAU
                cnt[1] += weight * (1.0 - v) / TAU
        self._cap_counts()
        # Tageszeit-Prior: je Halbstunde Anteil Schlaf in dieser Nacht
        decay = math.pow(0.5, weight / PRIOR_HALF_LIFE_N)
        seen = [0.0] * PRIOR_BINS
        slept = [0.0] * PRIOR_BINS
        for i in range(win.n):
            b = int((win.tod[i] % 1440) // 30)
            seen[b] += 1
            if start <= win.start + i < end:
                slept[b] += 1
        for b in range(PRIOR_BINS):
            if seen[b] >= 10:
                self.prior_s[b] = self.prior_s[b] * decay + weight * slept[b] / seen[b]
                self.prior_w[b] = self.prior_w[b] * decay + weight
        # systematische Abweichung Beginn/Ende (Korrekturen sind das stärkste Label)
        if detected is not None and detected.sleep is not None and weight >= 0.99:
            raw_a = detected.sleep.start - int(round(self.onset_bias))
            raw_b = detected.sleep.end - int(round(self.wake_bias))
            self.onset_bias = _clamp(0.7 * self.onset_bias + 0.3 * (start - raw_a), -90, 90)
            self.wake_bias = _clamp(0.7 * self.wake_bias + 0.3 * (end - raw_b), -90, 90)
        if weight >= 0.99:
            self.labels += 1

    def _cap_counts(self, cap: float = 400.0) -> None:
        for per_state in self.counts.values():
            for cnt in per_state:
                s = cnt[0] + cnt[1]
                if s > cap:
                    f = cap / s
                    cnt[0] *= f
                    cnt[1] *= f

    def night_done(self, result: NightResult, day_key: str, extra: dict | None = None) -> None:
        self.nights += 1
        entry = {
            "day": day_key,
            "start": result.sleep.start if result.sleep else None,
            "end": result.sleep.end if result.sleep else None,
            "asleep": result.asleep_minutes, "conf": result.confidence,
            "int": len(result.interruptions), "naps": sum(s.minutes for s in result.naps),
            "lat": result.latency, **(extra or {}),
        }
        self.history = [h for h in self.history if h.get("day") != day_key][-59:] + [entry]

    def reset(self) -> None:
        levels = {k: LevelModel(v.lo, v.hi, v.k) for k, v in self.levels.items()}
        for k, v in self.levels.items():
            levels[k].user_threshold = v.user_threshold
            levels[k].user_direction = v.user_direction
        self.__init__()
        self.levels = levels

    # ---------------------------------------------------------- Speicher
    def to_dict(self) -> dict:
        return {
            "v": 1,
            "counts": {c: [[round(x, 3) for x in s] for s in v] for c, v in self.counts.items()},
            "prior_s": [round(x, 4) for x in self.prior_s], "prior_w": [round(x, 4) for x in self.prior_w],
            "onset_bias": round(self.onset_bias, 2), "wake_bias": round(self.wake_bias, 2),
            "labels": self.labels, "nights": self.nights,
            "levels": {k: v.to_dict() for k, v in self.levels.items()},
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, d: dict | None) -> SleepModel:
        m = cls()
        if not d:
            return m
        for c, v in (d.get("counts") or {}).items():
            if c in m.counts and isinstance(v, list) and len(v) == NSTATE:
                m.counts[c] = [[float(x[0]), float(x[1])] for x in v]
        for name in ("prior_s", "prior_w"):
            v = d.get(name)
            if isinstance(v, list) and len(v) == PRIOR_BINS:
                setattr(m, name, [float(x) for x in v])
        m.onset_bias = float(d.get("onset_bias", 0.0))
        m.wake_bias = float(d.get("wake_bias", 0.0))
        m.labels = int(d.get("labels", 0))
        m.nights = int(d.get("nights", 0))
        m.levels = {k: LevelModel.from_dict(v) for k, v in (d.get("levels") or {}).items()}
        m.history = list(d.get("history") or [])[-60:]
        return m

    def view(self) -> dict:
        """Model view without any content: levels, thresholds, prior ring, recent nights."""
        return {
            "maturity": round(self.maturity, 2), "learning": self.learning, "nights": self.nights,
            "labels": self.labels, "night_of": min(self.nights + 1, MATURE_NIGHTS), "nights_needed": MATURE_NIGHTS,
            "prior": [round(self.prior(b * 30 + 15), 3) for b in range(PRIOR_BINS)],
            "channels": {c: [round(self.p(c, s), 3) for s in range(NSTATE)] for c in self.counts},
            "bias": {"onset": round(self.onset_bias, 1), "wake": round(self.wake_bias, 1)},
            "levels": {k: v.summary() for k, v in self.levels.items()},
            "history": self.history[-14:],
        }


def shared_occupancy(persons: int, p_other_in_bed: float | None) -> tuple[float, float]:
    """Shared bed: (occupancy for this person, confidence factor).

    2 persons -> both in bed. 1 person -> whoever the other signals do not place in bed;
    without signals it is 50/50 and the confidence drops honestly.
    """
    if persons >= 2:
        return 1.0, 1.0
    if persons <= 0:
        return 0.0, 1.0
    if p_other_in_bed is None or p_other_in_bed != p_other_in_bed:
        return 0.5, 0.5
    return max(0.0, min(1.0, 1.0 - p_other_in_bed)), 0.5 + abs(p_other_in_bed - 0.5)


def _runs(flags: list[bool]) -> list[tuple[int, int]]:
    out = []
    start = None
    for i, f in enumerate(flags):
        if f and start is None:
            start = i
        elif not f and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(flags)))
    return out


def _lse(xs: list[float]) -> float:
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def _norm(v: list[float]) -> None:
    m = _lse(v)
    for i in range(len(v)):
        v[i] -= m


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
