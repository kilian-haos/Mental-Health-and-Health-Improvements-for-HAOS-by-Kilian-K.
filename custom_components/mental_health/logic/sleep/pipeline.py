"""Glue: per-minute source series -> channel window for the detector (pure Python)."""
from __future__ import annotations

from collections.abc import Callable

from .detector import NAN, Window, shared_occupancy
from .features import movement
from .mixture import LevelModel
from .sources import KIND_AUX, KIND_BINARY, KIND_ENUM, KIND_NUMERIC, KIND_PROB, Source

DAY_START = 10 * 60      # Tageswerte für die Grundlinie: 10–18 Uhr
DAY_END = 18 * 60


def level_model_for(src: Source, models: dict[str, LevelModel]) -> LevelModel:
    m = models.get(src.id)
    k = 3 if src.shared_with else 2
    if m is None or m.k != k:
        m = LevelModel(k=k)
        models[src.id] = m
    m.user_threshold = src.threshold
    m.user_direction = src.direction
    return m


def feed_levels(src: Source, models: dict[str, LevelModel], values: list[float], tod: list[float]) -> None:
    """Add finished minutes of a numeric source to its level histogram."""
    if src.kind != KIND_NUMERIC:
        return
    m = level_model_for(src, models)
    for v, t in zip(values, tod):
        if v == v:
            m.add(v, 1.0, DAY_START <= (t % 1440) < DAY_END)


def build_window(
    start: int,
    tod: list[float],
    sources: list[Source],
    series: dict[str, tuple[list[float], list[float]]],
    models: dict[str, LevelModel],
    other_in_bed: Callable[[str], list[float] | None] | None = None,
) -> Window:
    """series: source id -> (minute means, minute ranges). Enum/probability sources are already 0..1."""
    n = len(tod)
    ch: dict[str, list[float]] = {}

    def merge(name: str, vals: list[float], how: str) -> None:
        cur = ch.get(name)
        if cur is None:
            ch[name] = list(vals)
            return
        for i, v in enumerate(vals):
            if v != v:
                continue
            c = cur[i]
            if c != c:
                cur[i] = v
            elif how == "max":
                cur[i] = max(c, v)
            else:
                cur[i] = (c + v) / 2.0

    for src in sources:
        if src.kind == KIND_NUMERIC:
            means, rngs = series.get(src.id, ([NAN] * n, [NAN] * n))
            lm = level_model_for(src, models)
            if src.shared_with and lm.ready:
                others = other_in_bed(src.id) if other_in_bed else None
                occ = []
                for i, v in enumerate(means):
                    if v != v:
                        occ.append(NAN)
                        continue
                    persons = lm.persons(v)
                    o_other = others[i] if others else None
                    occ.append(shared_occupancy(persons, o_other)[0])
            else:
                occ = [lm.occupancy(v) if v == v else NAN for v in means]
            merge("occ", occ, "max")
            b, t = lm.baseline, lm.threshold()
            levels = lm.load_levels()
            if b is not None and levels:
                scale = abs(levels[0].mu - b)          # Bewegung relativ zur Belastungsstufe
            elif b is not None and t is not None:
                scale = abs(b - t) * 2.0
            else:
                scale = 0.6
            merge("move", movement(rngs, scale), "max")
        elif src.kind == KIND_BINARY:
            means, _ = series.get(src.id, ([NAN] * n, [NAN] * n))
            merge(src.channel or "occ", means, "max" if src.channel == "occ" else "mean")
        elif src.kind in (KIND_ENUM, KIND_PROB):
            means, _ = series.get(src.id, ([NAN] * n, [NAN] * n))
            merge("hint", means, "mean")
        elif src.kind == KIND_AUX and src.channel:
            means, _ = series.get(src.id, ([NAN] * n, [NAN] * n))
            merge(src.channel, means, "max")
    return Window(start, list(tod), ch)
