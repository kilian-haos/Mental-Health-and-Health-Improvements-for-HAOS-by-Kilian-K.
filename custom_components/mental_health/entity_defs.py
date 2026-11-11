"""Which entities exist – per person (depending on modules) and on the hub. No HA imports."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Def:
    key: str
    platform: str                 # sensor | binary_sensor | switch | button | select
    module: str | None = None     # Modul, das aktiv sein muss
    kind: str | None = None       # measurement | timestamp | date | enum | duration_h | percent | kg | days
    options: tuple[str, ...] = ()
    icon: str | None = None
    extra: str | None = None      # zusätzliche Bedingung


PERSON_DEFS: tuple[Def, ...] = (
    Def("mood_morning", "sensor", None, "measurement", icon="mdi:weather-sunset-up"),
    Def("mood_evening", "sensor", None, "measurement", icon="mdi:weather-night"),
    Def("mood_today", "sensor", None, "measurement", icon="mdi:emoticon-outline"),
    Def("mood_avg7", "sensor", None, "measurement", icon="mdi:chart-line"),
    Def("mood_avg30", "sensor", None, "measurement", icon="mdi:chart-line"),
    Def("mood_trend", "sensor", None, "measurement", icon="mdi:trending-up"),
    Def("mood_forecast", "sensor", "suggestions", "measurement", icon="mdi:crystal-ball"),
    Def("energy", "sensor", "energy", "measurement", icon="mdi:lightning-bolt-outline"),
    Def("health_feeling", "sensor", "health", "measurement", icon="mdi:heart-outline"),
    Def("sleep_quality", "sensor", "sleep_quality", "measurement", icon="mdi:bed-outline"),
    Def("health_score", "sensor", None, "measurement", icon="mdi:heart-pulse"),
    Def("sleep_state", "sensor", "sleep_tracking", "enum", ("away", "in_bed", "asleep", "nap"), icon="mdi:sleep"),
    Def("sleep_duration", "sensor", "sleep_tracking", "duration_h", icon="mdi:sleep"),
    Def("sleep_score", "sensor", "sleep_tracking", "measurement", icon="mdi:star-outline"),
    Def("sleep_week_pct", "sensor", "sleep_tracking", "percent", icon="mdi:percent-outline"),
    Def("sleep_opt_pct", "sensor", "sleep_tracking", "percent", icon="mdi:bullseye-arrow"),
    Def("sleep_optimum", "sensor", "sleep_tracking", "duration_h", icon="mdi:bullseye"),
    Def("last_bedtime", "sensor", "sleep_tracking", "timestamp", icon="mdi:bed-clock"),
    Def("last_wake", "sensor", "sleep_tracking", "timestamp", icon="mdi:alarm"),
    Def("predicted_bedtime", "sensor", "sleep_tracking", "timestamp", icon="mdi:bed-clock"),
    Def("predicted_wake", "sensor", "sleep_tracking", "timestamp", icon="mdi:alarm-check"),
    Def("sleep_regularity", "sensor", "sleep_tracking", "measurement", icon="mdi:calendar-sync"),
    Def("sleep_confidence", "sensor", "sleep_tracking", "percent", icon="mdi:check-decagram-outline"),
    Def("weight_profile", "sensor", "weight", "kg", icon="mdi:scale-bathroom", extra="weight_not_live"),
    Def("weight_days_since", "sensor", "weight", "days", icon="mdi:calendar-clock"),
    Def("training_status", "sensor", "training", "enum", ("pause", "ready_soon", "recommended", "overdue"), icon="mdi:dumbbell"),
    Def("training_days_since", "sensor", "training", "days", icon="mdi:calendar-clock"),
    Def("training_soreness", "sensor", "training", "measurement", icon="mdi:arm-flex-outline"),
    Def("last_training", "sensor", "training", "timestamp", icon="mdi:dumbbell"),
    Def("cycle_next_start", "sensor", "cycle", "date", icon="mdi:calendar-start"),
    Def("cycle_next_end", "sensor", "cycle", "date", icon="mdi:calendar-end"),
    Def("next_morning", "sensor", None, "timestamp", icon="mdi:weather-sunset-up"),
    Def("next_evening", "sensor", None, "timestamp", icon="mdi:weather-night"),
    Def("last_checkin", "sensor", None, "timestamp", icon="mdi:check-circle-outline"),
    Def("streak", "sensor", None, "days", icon="mdi:fire"),
    Def("age", "sensor", "birthday", "years", icon="mdi:cake-variant-outline", extra="has_year"),
    Def("next_birthday", "sensor", "birthday", "timestamp", icon="mdi:cake-variant"),
    # Binärsensoren
    Def("sleeping", "binary_sensor", "sleep_tracking", icon="mdi:sleep"),
    Def("in_bed", "binary_sensor", "sleep_tracking", icon="mdi:bed"),
    Def("weight_due", "binary_sensor", "weight", icon="mdi:scale-bathroom", extra="not_child"),
    Def("training_recommended", "binary_sensor", "training", icon="mdi:dumbbell"),
    Def("cycle_active", "binary_sensor", "cycle", icon="mdi:water-outline"),
    Def("morning_open", "binary_sensor", None, icon="mdi:weather-sunset-up"),
    Def("evening_open", "binary_sensor", None, icon="mdi:weather-night"),
    Def("birthday_today", "binary_sensor", "birthday", icon="mdi:party-popper"),
    # Steuerung
    Def("pause", "switch", None, icon="mdi:pause-circle-outline"),
    Def("start_morning", "button", None, icon="mdi:weather-sunset-up"),
    Def("start_evening", "button", None, icon="mdi:weather-night"),
)

HUB_DEFS: tuple[Def, ...] = (
    Def("family_mood", "sensor", None, "measurement", icon="mdi:home-heart"),
    Def("family_mood_avg7", "sensor", None, "measurement", icon="mdi:chart-line"),
    Def("family_trend", "sensor", None, "measurement", icon="mdi:trending-up"),
    Def("family_health", "sensor", None, "measurement", icon="mdi:heart-pulse"),
    Def("family_sleep", "sensor", None, "measurement", icon="mdi:sleep"),
    Def("participation", "sensor", None, "percent", icon="mdi:account-check-outline"),
    Def("birthdays_today", "sensor", None, "count", icon="mdi:cake-variant"),
    Def("next_birthday", "sensor", None, "timestamp", icon="mdi:cake-variant-outline"),
    Def("last_backup", "sensor", None, "timestamp", icon="mdi:backup-restore"),
    Def("load_level", "select", None, options=("1", "2", "3"), icon="mdi:speedometer"),
    Def("llm_beta", "switch", None, icon="mdi:robot-outline"),
    Def("create_backup", "button", None, icon="mdi:content-save-outline"),
)


def _active(d: Def, person: Any) -> bool:
    if d.module and not person.mod(d.module):
        return False
    if d.extra == "weight_not_live" and (person.profile.get("weight_live") or person.child):
        return False
    if d.extra == "not_child" and person.child:
        return False
    if d.extra == "has_year":
        b = person.birthdate
        if not b or b.year is None:
            return False
    return True


def person_defs(person: Any, platform: str | None = None) -> list[Def]:
    return [d for d in PERSON_DEFS if (platform is None or d.platform == platform) and _active(d, person)]


def person_entity_keys(person: Any) -> set[str]:
    return {d.key for d in person_defs(person)}


def hub_defs(platform: str | None = None) -> list[Def]:
    return [d for d in HUB_DEFS if platform is None or d.platform == platform]


def hub_entity_keys(_runtime: Any = None) -> set[str]:
    return {d.key for d in HUB_DEFS}
