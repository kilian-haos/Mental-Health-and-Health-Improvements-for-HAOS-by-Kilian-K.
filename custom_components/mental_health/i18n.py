"""Language – follows Home Assistant automatically, there is no manual setting.

* Setup/options dialogs, entity names, states and services use the translation files
  (`translations/en.json`, `de.json`); other languages fall back to English.
* Texts the integration writes itself (device models, notifications, panel title) exist in
  English and German: German only if the Home Assistant *system* language is German.
* The card/panel follows the language of the viewing user.
"""
from __future__ import annotations

from typing import Any

LANGUAGES = ("en", "de")
DEFAULT_LANGUAGE = "en"

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "panel_title": "Mental Health",
        "hub_name": "Mental Health",
        "model_hub": "Family hub",
        "model_person": "Personal companion",
        "device_person": "{name} – Mental Health",
        # Check-in-Benachrichtigungen (keine sensiblen Inhalte auf dem Sperrbildschirm)
        "n_morning_title": "Good morning ☀️",
        "n_morning_title_child": "Good morning, {name}! ☀️",
        "n_evening_title": "How was your day? 🌙",
        "n_evening_title_child": "Hey {name}, how was your day? 🌙",
        "n_morning_msg": "Your morning check-in is ready.",
        "n_morning_msg_child": "Tap here and tell me how you feel 😊",
        "n_evening_msg": "Take a minute for your evening check-in.",
        "n_evening_msg_child": "Tap here – it only takes a minute 🌟",
        "n_sleep_score": "Sleep score {score}",
        "n_week": "{pct} % vs. week",
        "n_training": "Good day for a workout 💪",
        "n_training_child": "Good day for some exercise 🏃",
        "n_action_open": "Check in now",
        "n_action_later": "Later (10 min)",
        "n_test_title": "Mental Health – test",
        "n_test_msg": "Notifications work 👍 Swipe me away: on Android I come back while a check-in is open.",
        "n_channel": "Mental Health – Check-in",
        "n_weekly_title": "Your week 🌿",
        "n_weekly_msg": "Your weekly review is ready.",
        # Admins
        "n_setup_title": "Mental Health – setup request",
        "n_setup_msg": "{name} would like to use Mental Health.",
        "n_setup_action": "Set up now",
        "n_admin_title": "Mental Health",
        "n_backup_failed": "The automatic backup failed: {error}",
        "n_notify_failed": "Check-in notifications for {name} could not be delivered to {target}.",
        "default_person": "Person",
    },
    "de": {
        "panel_title": "Mental Health",
        "hub_name": "Mental Health",
        "model_hub": "Familien-Hub",
        "model_person": "Persönlicher Begleiter",
        "device_person": "{name} – Mental Health",
        "n_morning_title": "Guten Morgen ☀️",
        "n_morning_title_child": "Guten Morgen, {name}! ☀️",
        "n_evening_title": "Wie war dein Tag? 🌙",
        "n_evening_title_child": "Hey {name}, wie war dein Tag? 🌙",
        "n_morning_msg": "Dein Morgen-Check-in ist bereit.",
        "n_morning_msg_child": "Tipp hier und erzähl mir, wie es dir geht 😊",
        "n_evening_msg": "Nimm dir kurz Zeit für deinen Abend-Check-in.",
        "n_evening_msg_child": "Tipp hier – dauert nur eine Minute 🌟",
        "n_sleep_score": "Schlaf-Score {score}",
        "n_week": "{pct} % ggü. Woche",
        "n_training": "Guter Tag für ein Training 💪",
        "n_training_child": "Guter Tag für Bewegung 🏃",
        "n_action_open": "Jetzt eintragen",
        "n_action_later": "Später (10 min)",
        "n_test_title": "Mental Health – Test",
        "n_test_msg": "Benachrichtigungen funktionieren 👍 Wisch mich weg: Auf Android komme ich zurück, solange ein Check-in offen ist.",
        "n_channel": "Mental Health – Check-in",
        "n_weekly_title": "Deine Woche 🌿",
        "n_weekly_msg": "Dein Wochenrückblick ist da.",
        "n_setup_title": "Mental Health – Einrichtungsanfrage",
        "n_setup_msg": "{name} möchte Mental Health nutzen.",
        "n_setup_action": "Jetzt einrichten",
        "n_admin_title": "Mental Health",
        "n_backup_failed": "Das automatische Backup ist fehlgeschlagen: {error}",
        "n_notify_failed": "Check-in-Benachrichtigungen für {name} konnten nicht an {target} zugestellt werden.",
        "default_person": "Person",
    },
}


def norm_lang(value: Any) -> str:
    v = str(value or "").lower().replace("_", "-").split("-")[0]
    return v if v in LANGUAGES else DEFAULT_LANGUAGE


def system_lang(hass: Any) -> str:
    return norm_lang(getattr(getattr(hass, "config", None), "language", None))


def tr(lang: str, key: str, **kw: Any) -> str:
    text = STRINGS[norm_lang(lang)].get(key) or STRINGS[DEFAULT_LANGUAGE][key]
    return text.format(**kw) if kw else text
