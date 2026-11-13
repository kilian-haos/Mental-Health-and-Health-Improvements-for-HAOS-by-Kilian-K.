"""Check-in forms and validation (pure Python).

The server builds the form (which fields, in which order, which are required) from the
person's modules and state. The card only renders it – so card, panel and automations always
agree, and the rules live in one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any

MORNING = "morning"
EVENING = "evening"
SLOTS = (MORNING, EVENING)

# Feldtypen
SCALE10 = "scale10"
SCALE3 = "scale3"          # Muskelkater 0–3
SCALE_PAIN = "scale_pain"  # 0–10
TEXTS = "texts"            # Liste kurzer Texte (min/max)
TEXT = "text"              # mehrzeilig
YESNO = "yesno"
CHOICE = "choice"
CHIPS = "chips"
NUMBER = "number"
SLEEP = "sleep"            # erkannte Schlafzeit bestätigen/korrigieren
GOALS_REVIEW = "goals_review"
INFO = "info"              # reine Anzeige (Prognose, Gewicht, Training, Geburtstag …)
DUMP = "dump"              # Brain Dump: neue Punkte (morgens/abends), abends zusätzlich Abhaken

FLOW = ("light", "medium", "heavy", "very_heavy")
SYMPTOMS = ("cramps", "headache", "fatigue", "mood", "bloating", "back_pain", "nausea", "tender_breasts", "acne", "cravings")
PERIOD_ANSWERS = ("no", "yes", "started", "ended")
GOAL_RESULTS = ("done", "partly", "not")
TRAINING_TYPES = ("strength", "cardio", "endurance", "mobility", "team", "other")
MAX_TEXT = 4000
MAX_SHORT = 200


@dataclass
class Field:
    key: str
    type: str
    required: bool = False
    opts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"key": self.key, "type": self.type, "required": self.required, **({"opts": self.opts} if self.opts else {})}


@dataclass
class FormContext:
    slot: str
    modules: dict[str, bool]
    child: bool = False
    has_sleep_source: bool = False
    sleep_detected: dict | None = None        # {"start": iso, "end": iso, "confidence": 0..1, "score": ..}
    forecast: dict | None = None              # Stimmungsprognose
    weight_card: dict | None = None
    weight_due: str = "none"                  # none | warn | required
    ask_soreness: bool = False
    training_card: dict | None = None
    cycle_enabled: bool = False
    goals_yesterday: list[dict] = field(default_factory=list)   # [{"id","text"}]
    birthdays: list[dict] = field(default_factory=list)
    weight_live: bool = False
    dump_open: list[dict] = field(default_factory=list)   # offene Brain-Dump-Punkte (nur abends)


def build_form(ctx: FormContext) -> list[Field]:
    m = ctx.modules
    out: list[Field] = []
    if ctx.slot == MORNING:
        out.append(Field("greeting", INFO, opts={"forecast": ctx.forecast}))
        if m.get("sleep_tracking") and ctx.has_sleep_source and ctx.sleep_detected:
            out.append(Field("sleep", SLEEP, opts=dict(ctx.sleep_detected)))
        if m.get("weight") and not ctx.child and ctx.weight_card:
            out.append(Field("weight_info", INFO, opts=ctx.weight_card))
        out.append(Field("mood", SCALE10, True))
        if m.get("energy"):
            out.append(Field("energy", SCALE10))
        if m.get("sleep_quality"):
            out.append(Field("sleep_quality", SCALE10))
        if m.get("health"):
            out.append(Field("health", SCALE10))
        if m.get("training"):
            if ctx.ask_soreness:
                out.append(Field("soreness", SCALE3, True))
            if ctx.training_card:
                out.append(Field("training_info", INFO, opts=ctx.training_card))
        if m.get("cycle") and ctx.cycle_enabled:
            out += _period_fields()
        if m.get("goals") and ctx.goals_yesterday:
            out.append(Field("goals_review", GOALS_REVIEW, opts={"goals": ctx.goals_yesterday}))
        if m.get("brain_dump"):
            out.append(Field("dump", DUMP, opts={"open": []}))
        if m.get("birthday") and ctx.birthdays:
            out.append(Field("birthday_info", INFO, opts={"people": ctx.birthdays}))
        return out

    out.append(Field("mood", SCALE10, True))
    if m.get("energy"):
        out.append(Field("energy", SCALE10))
    if m.get("health"):
        out.append(Field("health", SCALE10))
    if m.get("good_bad"):
        out.append(Field("good", TEXTS, True, {"min": 1, "max": 3, "maxlen": MAX_SHORT}))
        out.append(Field("bad", TEXTS, True, {"min": 1, "max": 2, "maxlen": MAX_SHORT}))
    if m.get("goals"):
        out.append(Field("goals", TEXTS, False, {"min": 0, "max": 3, "maxlen": MAX_SHORT}))
    if m.get("journal"):
        out.append(Field("journal", TEXT, False, {"maxlen": MAX_TEXT}))
    if m.get("brain_dump"):
        out.append(Field("dump", DUMP, opts={"open": ctx.dump_open}))
    if m.get("training"):
        out.append(Field("trained", YESNO, True, {"types": list(TRAINING_TYPES)}))
        if ctx.ask_soreness:
            out.append(Field("soreness", SCALE3, True))
    if m.get("weight") and not ctx.child:
        out.append(Field("weight", NUMBER, ctx.weight_due == "required",
                         {"min": 2, "max": 400, "step": 0.1, "unit": "kg", "due": ctx.weight_due}))
    if m.get("cycle") and ctx.cycle_enabled:
        out += _period_fields()
    return out


def _period_fields() -> list[Field]:
    return [Field("period", CHOICE, True, {"options": list(PERIOD_ANSWERS),
                                          "flow": list(FLOW), "symptoms": list(SYMPTOMS)})]


# ---------------------------------------------------------------- Validierung
def _scale(v: Any, lo: int, hi: int) -> int | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:
        return None
    i = int(round(f))
    return i if lo <= i <= hi else None


def _texts(v: Any, maxn: int, maxlen: int) -> list[str]:
    if not isinstance(v, list):
        return []
    out = []
    for t in v[:maxn]:
        s = str(t or "").strip()[:maxlen]
        if s:
            out.append(s)
    return out


def validate(form: list[Field], data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    """Clean submitted values against the form. Returns (clean, errors{key: code})."""
    clean: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for f in form:
        if f.type == INFO:
            continue
        raw = data.get(f.key)
        if f.type == SCALE10:
            v = _scale(raw, 1, 10)
        elif f.type == SCALE3:
            v = _scale(raw, 0, 3)
        elif f.type == SCALE_PAIN:
            v = _scale(raw, 0, 10)
        elif f.type == TEXTS:
            v = _texts(raw, int(f.opts.get("max", 3)), int(f.opts.get("maxlen", MAX_SHORT)))
            if len(v) < int(f.opts.get("min", 0)):
                errors[f.key] = "min_items"
                continue
            v = v or None
        elif f.type == TEXT:
            s = str(raw or "").strip()[: int(f.opts.get("maxlen", MAX_TEXT))]
            v = s or None
        elif f.type == YESNO:
            v = _yesno(raw)
            if v is not None and f.key == "trained":
                v = {"done": v["done"], **_training_detail(raw)}
        elif f.type == NUMBER:
            try:
                v = round(float(raw), 1) if raw not in (None, "") else None
            except (TypeError, ValueError):
                v = None
            if v is not None and not (f.opts.get("min", -1e9) <= v <= f.opts.get("max", 1e9)):
                errors[f.key] = "range"
                continue
        elif f.type == CHOICE and f.key == "period":
            v = _period(raw)
            if v is None and raw not in (None, "", {}):
                errors[f.key] = "period_details"
                continue
        elif f.type == SLEEP:
            v = _sleep(raw)
        elif f.type == GOALS_REVIEW:
            v = _goals_review(raw, {g["id"] for g in f.opts.get("goals", [])})
        elif f.type == DUMP:
            v = _dump(raw, _tree_ids(f.opts.get("open") or []))
        else:
            v = None
        if v is None:
            if f.required:
                errors[f.key] = "required"
            continue
        clean[f.key] = v
    return clean, errors


def _yesno(raw: Any) -> dict | None:
    if isinstance(raw, dict):
        d = raw.get("done")
    else:
        d = raw
    if d is True or d in ("yes", "true", 1):
        return {"done": True}
    if d is False or d in ("no", "false", 0):
        return {"done": False}
    return None


def _training_detail(raw: Any) -> dict:
    if not isinstance(raw, dict) or not raw.get("done"):
        return {}
    out: dict[str, Any] = {}
    if raw.get("type") in TRAINING_TYPES:
        out["type"] = raw["type"]
    mins = _scale(raw.get("minutes"), 1, 600)
    if mins:
        out["minutes"] = mins
    return out


def _period(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        raw = {"answer": raw}
    a = raw.get("answer")
    if a not in PERIOD_ANSWERS:
        return None
    out: dict[str, Any] = {"answer": a}
    if a in ("yes", "started"):
        if raw.get("flow") not in FLOW:
            return None
        pain = _scale(raw.get("pain"), 0, 10)
        if pain is None:
            return None
        out["flow"] = raw["flow"]
        out["pain"] = pain
        out["symptoms"] = [s for s in (raw.get("symptoms") or []) if s in SYMPTOMS][:10]
    return out


def _sleep(raw: Any) -> dict | None:
    if not isinstance(raw, dict):
        return None
    action = raw.get("action")
    if action not in ("confirm", "correct", "skip"):
        return None
    out: dict[str, Any] = {"action": action}
    if action == "correct":
        try:
            s = datetime.fromisoformat(str(raw["start"]))
            e = datetime.fromisoformat(str(raw["end"]))
        except (KeyError, ValueError, TypeError):
            return None
        if not (0 < (e - s).total_seconds() <= 20 * 3600):
            return None
        out["start"], out["end"] = s.isoformat(), e.isoformat()
    return out


def _tree_ids(items: list[dict]) -> set[str]:
    out: set[str] = set()
    for it in items:
        out.add(str(it.get("id")))
        out |= _tree_ids(it.get("children") or [])
    return out


def _dump(raw: Any, ids: set[str]) -> dict | None:
    """{"add": [{"text", "done"}], "done": [ids], "undone": [ids]} – only ids that were offered."""
    if not isinstance(raw, dict):
        return None
    add = []
    for it in (raw.get("add") or [])[:50]:
        if isinstance(it, str):
            it = {"text": it}
        if not isinstance(it, dict):
            continue
        t = " ".join(str(it.get("text") or "").split())[:300]
        if t:
            add.append({"text": t, "done": bool(it.get("done"))})
    done = [str(i) for i in (raw.get("done") or []) if str(i) in ids][:500]
    undone = [str(i) for i in (raw.get("undone") or []) if str(i) in ids and str(i) not in done][:500]
    if not add and not done and not undone:
        return None
    return {"add": add, "done": done, "undone": undone}


def _goals_review(raw: Any, ids: set[str]) -> dict | None:
    if not isinstance(raw, dict):
        return None
    out = {k: v for k, v in raw.items() if k in ids and v in GOAL_RESULTS}
    return out or None


# ---------------------------------------------------------------- Zeitregeln
@dataclass
class TimeRules:
    evening_from: time = time(14, 0)
    morning_until: time = time(14, 0)
    late_entry: str = "day_end"      # none | day_end | 3_days


def manual_allowed(slot: str, now_local: datetime, day: date, today: date, rules: TimeRules) -> tuple[bool, bool]:
    """(allowed, late) for a manual entry of `slot` on logical `day` at `now_local` (logical today)."""
    if day > today:
        return False, False
    if day == today:
        if slot == EVENING:
            # Nach Mitternacht (vor der Tagesgrenze) gehört es noch zu „heute“ -> immer erlaubt
            if now_local.date() > day or now_local.time() >= rules.evening_from:
                return True, False
            return False, False
        if slot == MORNING:
            if now_local.date() == day and now_local.time() < rules.morning_until:
                return True, False
            return (rules.late_entry != "none"), True
    age = (today - day).days
    if rules.late_entry == "3_days" and age <= 3:
        return True, True
    return False, False


def merge_entries(old: dict | None, new: dict) -> dict:
    """Editing an entry keeps an edit note (timestamps only, no content history)."""
    if not old:
        return new
    out = dict(new)
    edits = list(old.get("_edits") or [])
    edits.append(new.get("_ts"))
    out["_edits"] = edits[-20:]
    out["_created"] = old.get("_created") or old.get("_ts")
    return out
