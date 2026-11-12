"""Constants for Mental Health and Health Improvements for HAOS by Kilian K."""
from __future__ import annotations

DOMAIN = "mental_health"
NAME = "Mental Health and Health Improvements for HAOS by Kilian K."
SHORT_NAME = "Mental Health"
MANUFACTURER = "Kilian K."
VERSION = "1.0.2"

# Plattformen (als Strings, damit die reine Logik ohne HA importierbar bleibt)
PLATFORMS = ["sensor", "binary_sensor", "switch", "button", "select"]

# ---------------------------------------------------------------- Stores
CONFIG_STORE_VERSION = 1
PERSON_STORE_VERSION = 1
MODEL_STORE_VERSION = 1
KEY_STORE_VERSION = 1
STORE_CONFIG = f"{DOMAIN}.config"
STORE_KEYS = f"{DOMAIN}.keys"
STORE_PERSON = f"{DOMAIN}.person.{{pid}}"
STORE_MODEL = f"{DOMAIN}.model.{{pid}}"
BACKUP_DIR = "mental_health/backups"
BACKUP_EXT = ".mhbackup"
BACKUP_FORMAT = 1

# ---------------------------------------------------------------- Frontend
FRONTEND_DIR = "frontend"
CARD_FILE = "mental-health.js"
PANEL_FILE = "mental-health-panel.js"
URL_BASE = f"/{DOMAIN}_static"
CARD_URL = f"{URL_BASE}/{CARD_FILE}"
PANEL_URL = f"{URL_BASE}/{PANEL_FILE}"
PANEL_URL_PATH = "mental-health"
PANEL_COMPONENT = "mental-health-panel"
PANEL_ICON = "mdi:heart-pulse"

# ---------------------------------------------------------------- Module
MODULES = (
    "mood", "energy", "health", "sleep_quality", "sleep_tracking", "good_bad",
    "goals", "journal", "weight", "training", "cycle", "birthday", "suggestions", "llm",
)
MODULES_DEFAULT = {
    "mood": True, "energy": True, "health": True, "sleep_quality": True, "sleep_tracking": True,
    "good_bad": True, "goals": True, "journal": True, "weight": False, "training": True,
    "cycle": False, "birthday": True, "suggestions": True, "llm": False,
}
MODULES_LOCKED_ON = ("mood",)            # Pflichtkern

SEXES = ("female", "male", "other", "unspecified")

# ---------------------------------------------------------------- Zeiten/Standards
DEFAULT_MORNING = "07:30"
DEFAULT_EVENING = "21:00"
DEFAULT_DAY_BOUNDARY = "04:00"          # Ein Tag endet beim Aufstehen bzw. spätestens hier
DEFAULT_EVENING_FROM = "14:00"          # Abend-Eingabe manuell ab
DEFAULT_MORNING_UNTIL = "14:00"         # Morgen-Check-in manuell bis
DEFAULT_WINDOW_MIN = 60
DEFAULT_REMIND_MIN = 15
DEFAULT_SLEEP_GAP_MIN = 20              # „Abstand zum Schlaf“
DEFAULT_NIGHTLY = "03:30"
DEFAULT_LATE_ENTRY = "day_end"          # none | day_end | 3_days
DEFAULT_PIN_SESSION_MIN = 30
DEFAULT_FAMILY_K = 3
DEFAULT_LOW_MOOD_DAYS = 3
DEFAULT_LOW_MOOD_MAX = 3
DEFAULT_SETUP_REQUEST_COOLDOWN_H = 24
DEFAULT_LOAD_LEVEL = 2

PIN_MAX_FAILS = 3
PIN_LOCK_S = 300

# Benachrichtigungen
NOTIFY_CHANNEL = "Mental Health – Check-in"
NOTIFY_TAG = "mh_{pid}_{kind}_{idx}"
RESEND_MIN_GAP_S = 10
RESEND_MAX_PER_WINDOW = 20

# Live-Daten
PUSH_INTERVAL = 0.5

# Farben (Obsidian Teal + Paletten). Rot ist für Warnungen reserviert und wird nie automatisch vergeben.
COLOR_TEAL = "#2fd6b0"
COLOR_AMBER = "#f5b14c"
COLOR_RED = "#ef7b63"
COLOR_GOOD = "#4ade80"
MODULE_COLORS = {
    "mood": "#2fd6b0", "energy": "#f5b14c", "health": "#60a5fa", "sleep": "#a78bfa",
    "weight": "#22d3ee", "training": "#f472b6", "cycle": "#fb7185", "birthday": "#facc15",
}


def signal_person(entry_id: str, pid: str) -> str:
    return f"{DOMAIN}_person_{entry_id}_{pid}"


def signal_hub(entry_id: str) -> str:
    return f"{DOMAIN}_hub_{entry_id}"


def signal_entities(entry_id: str) -> str:
    return f"{DOMAIN}_entities_{entry_id}"
