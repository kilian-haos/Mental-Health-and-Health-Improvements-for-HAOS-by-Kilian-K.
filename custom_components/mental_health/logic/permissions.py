"""Central permission matrix (pure Python, no Home Assistant import).

Admin rights never grant access to another person's *content* (entries, texts, analyses,
personal dashboards, cycle details). Admins manage configuration; persons own their data.
"""
from __future__ import annotations

from dataclasses import dataclass

# Aktionen
MANAGE_PERSONS = "manage_persons"        # anlegen/löschen, Kindermodus, Bearbeitungsrecht vergeben
PROFILE_VIEW = "profile_view"
PROFILE_EDIT = "profile_edit"            # Alter, Geschlecht, Größe, Quellen …
WEIGHT_VIEW = "weight_view"              # Profilwert Gewicht sehen
WEIGHT_EDIT = "weight_edit"              # Profilwert Gewicht ändern
TARGET_WEIGHT_EDIT = "target_weight_edit"
MODULES_EDIT = "modules_edit"
SCHEDULE_EDIT = "schedule_edit"          # Check-in-Zeiten, Benachrichtigungsziele
PAUSE = "pause"
OWN_PIN = "own_pin"                      # eigene Personen-PIN setzen/ändern/entfernen
RESET_PIN = "reset_pin"                  # Admin: PIN zurücksetzen (Texte gehen verloren)
CONTENT = "content"                      # Einträge, Journal, Auswertungen, Zyklus-Details
CHECKIN = "checkin"                      # eigenen Check-in ausfüllen
LLM_CONSENT = "llm_consent"
ADMIN_AREA = "admin_area"
BACKUP = "backup"

ALL_ACTIONS = (
    MANAGE_PERSONS, PROFILE_VIEW, PROFILE_EDIT, WEIGHT_VIEW, WEIGHT_EDIT, TARGET_WEIGHT_EDIT,
    MODULES_EDIT, SCHEDULE_EDIT, PAUSE, OWN_PIN, RESET_PIN, CONTENT, CHECKIN, LLM_CONSENT,
    ADMIN_AREA, BACKUP,
)

# Gründe (Übersetzungsschlüssel im Frontend)
R_OK = ""
R_ADMIN_MANAGED = "admin_managed"        # „Wird von einem Admin verwaltet“
R_ADMIN_ONLY = "admin_only"
R_OWN_ONLY = "own_only"                  # Inhalte nur für die Person selbst
R_LIVE_WEIGHT = "live_weight"            # „Nur für <Name> sichtbar“
R_CHILD = "child"
R_NOT_SET_UP = "not_set_up"


@dataclass(frozen=True)
class Viewer:
    user_id: str | None
    is_admin: bool


@dataclass(frozen=True)
class PersonRights:
    user_id: str | None
    child: bool = False
    can_edit_own: bool = False
    weight_live: bool = False
    llm_child_allowed: bool = False


def check(viewer: Viewer, action: str, person: PersonRights | None = None) -> tuple[bool, str]:
    """Return (allowed, reason). `person` is None for global actions."""
    admin = bool(viewer.is_admin)
    if action in (MANAGE_PERSONS, ADMIN_AREA, BACKUP, RESET_PIN):
        return (True, R_OK) if admin else (False, R_ADMIN_ONLY)
    if person is None:
        return False, R_NOT_SET_UP
    is_self = bool(viewer.user_id) and viewer.user_id == person.user_id
    adult_editor = is_self and not person.child and person.can_edit_own

    if action == CONTENT or action == CHECKIN:
        return (True, R_OK) if is_self else (False, R_OWN_ONLY)
    if action == OWN_PIN:
        return (True, R_OK) if is_self else (False, R_OWN_ONLY)
    if action == PROFILE_VIEW:
        return (True, R_OK) if (is_self or admin) else (False, R_OWN_ONLY)
    if action in (PROFILE_EDIT, MODULES_EDIT, TARGET_WEIGHT_EDIT):
        if admin or adult_editor:
            return True, R_OK
        return False, (R_CHILD if is_self and person.child else R_ADMIN_MANAGED)
    if action == WEIGHT_VIEW:
        if is_self:
            return True, R_OK
        if admin and not person.weight_live:
            return True, R_OK
        return False, (R_LIVE_WEIGHT if admin else R_OWN_ONLY)
    if action == WEIGHT_EDIT:
        if adult_editor:
            return True, R_OK
        if admin and not person.weight_live and not is_self:
            return True, R_OK
        if admin and is_self:
            # Admin als Person: eigenes Gewicht darf er immer pflegen
            return True, R_OK
        if admin and person.weight_live:
            return False, R_LIVE_WEIGHT
        return False, (R_CHILD if is_self and person.child else R_ADMIN_MANAGED)
    if action in (SCHEDULE_EDIT, PAUSE):
        if admin or (is_self and not person.child):
            return True, R_OK
        return False, (R_CHILD if is_self else R_ADMIN_MANAGED)
    if action == LLM_CONSENT:
        if not is_self:
            return False, R_OWN_ONLY
        if person.child and not person.llm_child_allowed:
            return False, R_CHILD
        return True, R_OK
    return False, R_ADMIN_MANAGED


def allowed(viewer: Viewer, action: str, person: PersonRights | None = None) -> bool:
    return check(viewer, action, person)[0]


def rights_map(viewer: Viewer, person: PersonRights | None) -> dict[str, dict]:
    """All actions with result + reason (for the UI: grey out with a reason, never hide)."""
    out = {}
    for a in ALL_ACTIONS:
        ok, why = check(viewer, a, person)
        out[a] = {"ok": ok, "why": why}
    return out
