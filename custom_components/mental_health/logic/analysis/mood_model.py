"""Mood forecast: tiny online ridge regression per person (pure Python).

Features (all optional, missing = neutral 0): sleep vs. optimum, sleep score, weekday
(sin/cos + weekend), recent trend, training yesterday, muscle soreness, cycle phase, energy and
health yesterday, outdoor temperature / daylight (if an admin shares such entities).
Forecasts are shown after ~10 days of data; before that "I'm still getting to know you".
"""
from __future__ import annotations

import math

FEATURES = (
    "bias", "sleep_dev", "sleep_score", "wd_sin", "wd_cos", "weekend", "trend", "trained_y", "soreness",
    "ph_menstrual", "ph_luteal", "energy_y", "health_y", "mood_y", "temp", "daylight",
)
D = len(FEATURES)
LAMBDA = 3.0
FORGET = 0.985          # ältere Tage zählen langsam weniger
MIN_DAYS = 10

# Erklärungs-Schlüssel (Frontend/Übersetzung) je Merkmal
EXPLAIN = {
    "sleep_dev": "x_sleep", "sleep_score": "x_sleep_score", "weekend": "x_weekend", "trend": "x_trend",
    "trained_y": "x_trained", "soreness": "x_soreness", "ph_menstrual": "x_period", "ph_luteal": "x_luteal",
    "energy_y": "x_energy", "health_y": "x_health", "mood_y": "x_mood_y", "temp": "x_temp", "daylight": "x_daylight",
    "wd_sin": "x_weekday", "wd_cos": "x_weekday",
}


def features(*, sleep_h: float | None, optimum_h: float | None, sleep_score: float | None, weekday: int,
             trend: float | None, trained_y: bool | None, soreness: int | None, phase: str | None,
             energy_y: float | None, health_y: float | None, mood_y: float | None,
             temp: float | None = None, daylight_h: float | None = None) -> list[float]:
    x = [0.0] * D
    x[0] = 1.0
    if sleep_h is not None and optimum_h:
        x[1] = max(-4.0, min(3.0, sleep_h - optimum_h))
    if sleep_score is not None:
        x[2] = (sleep_score - 70.0) / 20.0
    a = weekday / 7.0 * 2 * math.pi
    x[3], x[4] = math.sin(a), math.cos(a)
    x[5] = 1.0 if weekday >= 5 else 0.0
    if trend is not None:
        x[6] = max(-3.0, min(3.0, trend))
    if trained_y is not None:
        x[7] = 1.0 if trained_y else 0.0
    if soreness is not None:
        x[8] = soreness / 3.0
    if phase == "menstrual":
        x[9] = 1.0
    elif phase == "luteal":
        x[10] = 1.0
    if energy_y is not None:
        x[11] = (energy_y - 5.5) / 3.0
    if health_y is not None:
        x[12] = (health_y - 5.5) / 3.0
    if mood_y is not None:
        x[13] = (mood_y - 5.5) / 3.0
    if temp is not None:
        x[14] = max(-2.0, min(2.0, (temp - 15.0) / 10.0))
    if daylight_h is not None:
        x[15] = (daylight_h - 12.0) / 4.0
    return x


class MoodModel:
    def __init__(self) -> None:
        self.ata = [[LAMBDA if (i == j and i > 0) else (1e-3 if i == j else 0.0) for j in range(D)] for i in range(D)]
        self.aty = [0.0] * D
        self.n = 0.0
        self.days = 0
        self.res_ss = 4.0          # Residuen-Quadratsumme (für Bandbreite), Start ≈ sd 2
        self.res_n = 1.0
        self.mean_x = [0.0] * D
        self.history: list[dict] = []   # Prognose vs. tatsächlich (letzte 60)
        self._w: list[float] | None = None

    def update(self, x: list[float], y: float) -> None:
        pred = self.predict_raw(x) if self.days >= 3 else None
        for i in range(D):
            for j in range(D):
                self.ata[i][j] = self.ata[i][j] * FORGET + x[i] * x[j]
            self.aty[i] = self.aty[i] * FORGET + x[i] * y
        # Ridge-Anteil nach dem Vergessen wiederherstellen
        for i in range(1, D):
            self.ata[i][i] += LAMBDA * (1 - FORGET)
        self.n = self.n * FORGET + 1.0
        for i in range(D):
            self.mean_x[i] = self.mean_x[i] + (x[i] - self.mean_x[i]) / min(self.n, 30.0)
        if pred is not None:
            self.res_ss = self.res_ss * FORGET + (y - pred) ** 2
            self.res_n = self.res_n * FORGET + 1.0
        self.days += 1
        self._w = None

    def weights(self) -> list[float]:
        if self._w is None:
            self._w = _solve([row[:] for row in self.ata], self.aty[:])
        return self._w

    def predict_raw(self, x: list[float]) -> float:
        w = self.weights()
        if self.n < 1:
            return 5.5
        # Achsenabschnitt ohne Daten: Mittelwert
        return sum(wi * xi for wi, xi in zip(w, x))

    def forecast(self, x: list[float]) -> dict | None:
        if self.days < MIN_DAYS:
            return {"ready": False, "days": self.days, "needed": MIN_DAYS}
        p = max(1.0, min(10.0, self.predict_raw(x)))
        sd = math.sqrt(self.res_ss / max(self.res_n, 1.0))
        conf = max(0.1, min(0.95, 1.0 - sd / 4.0)) * min(1.0, self.days / 30.0 + 0.4)
        return {
            "ready": True, "value": round(p, 1), "low": round(max(1.0, p - sd), 1), "high": round(min(10.0, p + sd), 1),
            "confidence": round(conf, 2), "reasons": self.explain(x),
        }

    def explain(self, x: list[float], top: int = 2) -> list[dict]:
        w = self.weights()
        contrib = []
        for i in range(1, D):
            c = w[i] * (x[i] - self.mean_x[i])
            if abs(c) >= 0.25 and FEATURES[i] in EXPLAIN:
                contrib.append((abs(c), FEATURES[i], c))
        contrib.sort(reverse=True)
        out, seen = [], set()
        for _, f, c in contrib:
            key = EXPLAIN[f]
            if key in seen:
                continue
            seen.add(key)
            out.append({"key": key, "effect": round(c, 1), "value": round(x[FEATURES.index(f)], 2)})
            if len(out) >= top:
                break
        return out

    def record(self, day: str, predicted: float | None, actual: float | None) -> None:
        self.history = [h for h in self.history if h["day"] != day][-59:] + [
            {"day": day, "p": predicted, "a": actual}]

    def to_dict(self) -> dict:
        return {"ata": [[round(v, 5) for v in r] for r in self.ata], "aty": [round(v, 5) for v in self.aty],
                "n": round(self.n, 4), "days": self.days, "res_ss": round(self.res_ss, 4), "res_n": round(self.res_n, 4),
                "mean_x": [round(v, 4) for v in self.mean_x], "history": self.history, "features": list(FEATURES)}

    @classmethod
    def from_dict(cls, d: dict | None) -> MoodModel:
        m = cls()
        if not d or list(d.get("features") or []) != list(FEATURES):
            # Merkmalsliste geändert: neu lernen, Verlauf behalten
            if d:
                m.history = list(d.get("history") or [])
            return m
        m.ata = [[float(v) for v in r] for r in d["ata"]]
        m.aty = [float(v) for v in d["aty"]]
        m.n = float(d.get("n", 0))
        m.days = int(d.get("days", 0))
        m.res_ss = float(d.get("res_ss", 4.0))
        m.res_n = float(d.get("res_n", 1.0))
        m.mean_x = [float(v) for v in d.get("mean_x") or [0.0] * D]
        m.history = list(d.get("history") or [])
        return m


def _solve(a: list[list[float]], b: list[float]) -> list[float]:
    n = len(b)
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-12:
            continue
        a[col], a[piv] = a[piv], a[col]
        b[col], b[piv] = b[piv], b[col]
        for r in range(col + 1, n):
            f = a[r][col] / a[col][col]
            if f:
                for k in range(col, n):
                    a[r][k] -= f * a[col][k]
                b[r] -= f * b[col]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        if abs(a[i][i]) < 1e-12:
            continue
        x[i] = (b[i] - sum(a[i][k] * x[k] for k in range(i + 1, n))) / a[i][i]
    return x
