"""LLM integration (beta): ai_task (HA ≥ 2025.8, capability check) or conversation agent.

Privacy: only with admin activation *and* the person's own consent (revocable). Only the
minimum is sent (time-limited excerpts, other household members' names are replaced).
Outputs are plain text (the card renders them with textContent – no HTML injection).
Timeouts, rate limit, fallback to the local analysis.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import date, timedelta
from typing import Any

from .logic.analysis import search as SE

_LOGGER = logging.getLogger(__name__)
TIMEOUT_S = 45
RATE_PER_HOUR = 20
MAX_OUT = 4000
_TAG = re.compile(r"<[^>]{0,200}>")


class LlmUnavailable(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def clean_output(text: Any) -> str:
    s = str(text or "")
    s = _TAG.sub("", s)
    s = s.replace("\r", "")
    return s.strip()[:MAX_OUT]


def anonymise(text: str, names: list[str]) -> str:
    out = text
    for n in sorted({n for n in names if n and len(n) >= 2}, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(n)}\b", "[person]", out, flags=re.IGNORECASE)
    return out


class Llm:
    def __init__(self, rt: Any) -> None:
        self.rt = rt
        self.calls: dict[str, list[float]] = {}

    # ---------------------------------------------------------- Fähigkeiten
    def capabilities(self) -> dict:
        hass = self.rt.hass
        return {
            "ai_task": hass.services.has_service("ai_task", "generate_data"),
            "conversation": hass.services.has_service("conversation", "process"),
            "ai_task_entities": sorted(s.entity_id for s in hass.states.async_all("ai_task")),
            "agents": sorted(s.entity_id for s in hass.states.async_all("conversation")),
        }

    def _check(self, person: Any) -> None:
        cfg = self.rt.settings["llm"]
        if not cfg.get("enabled") or not cfg.get("accepted"):
            raise LlmUnavailable("disabled")
        if not person.mod("llm"):
            raise LlmUnavailable("no_consent")
        now = time.time()
        lst = [t for t in self.calls.get(person.pid, []) if now - t < 3600]
        if len(lst) >= RATE_PER_HOUR:
            raise LlmUnavailable("rate_limited")
        lst.append(now)
        self.calls[person.pid] = lst

    async def _ask(self, task: str, instructions: str, structure: dict | None = None) -> Any:
        cfg = self.rt.settings["llm"]
        hass = self.rt.hass
        caps = self.capabilities()
        try:
            async with asyncio.timeout(TIMEOUT_S):
                if cfg.get("mode") == "ai_task" and caps["ai_task"]:
                    data: dict[str, Any] = {"task_name": task, "instructions": instructions}
                    if cfg.get("entity"):
                        data["entity_id"] = cfg["entity"]
                    if structure:
                        data["structure"] = structure
                    try:
                        res = await hass.services.async_call("ai_task", "generate_data", data, blocking=True,
                                                             return_response=True)
                    except Exception as err:  # noqa: BLE001 – ältere Versionen ohne "structure"
                        if structure and "structure" in str(err).lower():
                            data.pop("structure", None)
                            res = await hass.services.async_call("ai_task", "generate_data", data, blocking=True,
                                                                 return_response=True)
                        else:
                            raise
                    return (res or {}).get("data")
                if caps["conversation"]:
                    data = {"text": instructions}
                    if cfg.get("agent"):
                        data["agent_id"] = cfg["agent"]
                    res = await hass.services.async_call("conversation", "process", data, blocking=True,
                                                         return_response=True)
                    return (((res or {}).get("response") or {}).get("speech") or {}).get("plain", {}).get("speech")
        except TimeoutError as err:
            raise LlmUnavailable("timeout") from err
        except LlmUnavailable:
            raise
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Mental Health LLM call failed: %s", type(err).__name__)
            raise LlmUnavailable("error") from err
        raise LlmUnavailable("no_backend")

    # ---------------------------------------------------------- Funktionen
    async def search_filters(self, person: Any, query: str, today: date, lang: str) -> list[dict]:
        """Natural-language query -> filter chips. Sends only the query and today's date."""
        self._check(person)
        instr = (
            "Convert the user's search over their personal mood journal into JSON filters. Today is "
            f"{today.isoformat()}. Allowed keys: start (YYYY-MM-DD), end, months (list of 1-12), polarity "
            "(positive|neutral|negative), trained (bool), sleep (short|long), period (bool), journal (bool), "
            "goals (bool), slot (morning|evening), weekend (bool), terms (list of up to 5 search words in the "
            f"query's language). Only include keys that the query asks for. Query: {query[:300]}"
        )
        raw = await self._ask("Mental Health search", instr, None)
        obj = _json_from(raw)
        if not isinstance(obj, dict):
            raise LlmUnavailable("bad_output")
        chips: list[dict] = []
        if obj.get("start") or obj.get("end"):
            chips.append({"k": "range", "start": _date(obj.get("start")), "end": _date(obj.get("end"))})
        if isinstance(obj.get("months"), list):
            chips.append({"k": "months", "v": [int(m) for m in obj["months"] if str(m).isdigit() and 1 <= int(m) <= 12]})
        for k in ("polarity", "sleep", "slot"):
            if isinstance(obj.get(k), str):
                chips.append({"k": k, "v": obj[k]})
        for k in ("trained", "period", "journal", "goals", "weekend"):
            if isinstance(obj.get(k), bool):
                chips.append({"k": k, "v": obj[k]})
        for t in (obj.get("terms") or [])[:5]:
            if isinstance(t, str) and t.strip():
                chips.append({"k": "term", "v": t.strip()[:40]})
        return SE.Filters.from_chips(chips).chips()

    async def summary(self, person: Any, today: date, days: int, lang: str, other_names: list[str]) -> str:
        """Summary of a period (max. 31 days of excerpts)."""
        self._check(person)
        days = max(1, min(31, days))
        lines = []
        for i in range(days - 1, -1, -1):
            d = (today - timedelta(days=i)).isoformat()
            r = person.record(d, with_texts=True)
            if r.get("mood") is None and not r.get("good"):
                continue
            parts = [f"{d}: mood {r.get('mood')}", f"energy {r.get('energy')}"]
            if r.get("sleep_h"):
                parts.append(f"sleep {r['sleep_h']} h")
            if r.get("trained"):
                parts.append("trained")
            if r.get("good"):
                parts.append("good: " + "; ".join(x[:80] for x in r["good"][:3]))
            if r.get("bad"):
                parts.append("bad: " + "; ".join(x[:80] for x in r["bad"][:2]))
            if r.get("journal"):
                parts.append("journal: " + r["journal"][:240])
            lines.append(anonymise(" | ".join(parts), other_names))
        language = "German" if lang == "de" else "English"
        instr = (
            f"You are a warm, careful wellbeing companion (not a therapist, no diagnoses). Write a short summary "
            f"in {language} (max. 8 sentences, 'du'-form in German) of the person's last {days} days: patterns, "
            "what did them good, one or two gentle, concrete suggestions. No medical claims. Data:\n" + "\n".join(lines[-days:])
        )
        return clean_output(await self._ask("Mental Health summary", instr))


def _json_from(raw: Any) -> Any:
    if isinstance(raw, (dict, list)):
        return raw
    s = str(raw or "")
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except ValueError:
        return None


def _date(v: Any) -> str | None:
    try:
        return date.fromisoformat(str(v)[:10]).isoformat() if v else None
    except ValueError:
        return None
