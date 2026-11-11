# Changelog

## 1.0.1 – 2026-11-11

- **Delete backups** in the admin area: a delete button per backup file with a confirmation (admins only, admin PIN if set). Automatic backups are still pruned to the configured number; manual backups, uploads and safety points are only removed by you.
- **Date fields as a code-style mask**: date of birth (profile and setup wizard) and "pause until" are entered as DD.MM.YYYY in eight single-digit boxes – jumps to the next box automatically, backspace goes back, arrow keys and pasting a whole date (e.g. `17.05.1990` or `1990-05-17`) work, invalid dates are marked. The year of the birthday stays optional. English uses DD/MM/YYYY.

## 1.0.0 – 2026-11-11

First release.

- **Persons, rights and privacy**: only persons with a linked user take part; an admin sets them up in the panel's admin area (wizard, children's mode, "may edit own data"). Complete rights matrix – admins manage configuration but never see contents. Entries encrypted at rest per person; optional **personal PIN** that protects texts cryptographically; optional **admin PIN**. Not set up yet? A preview with **"Request setup"** notifies the admins.
- **Check-ins** morning and evening with mood sliders and faces, energy, feeling of health, sleep quality, good and not-so-good things, intentions, journal, training, weight, period, muscle soreness, yesterday's intentions. Few mandatory fields, gentle shake for missing ones, encrypted drafts on the server, editing and deleting with an edit note, filling in later, evening entry from 14:00, pause mode.
- **Schedule**: fixed time per weekday, timestamp entity + offset, **sleep based** (one setting "gap to sleep", fine-tuned from answer times) or manual/automation.
- **Notifications** per device with deep link, "Check in now" and "Later (10 min)", reminders, child-friendly texts, nothing sensitive on the lock screen. **Android 14+**: a swiped-away notification is re-sent only to that device while the check-in is open (rate-limited). iOS time-sensitive. Scripts with freely mapped fields. Test button and platform guide in the profile.
- **Sleep detection** that learns: bed sensors (on/off, numeric with automatically learned baseline/direction/threshold), sleep apps, wearables, sleep confidence and helper signals; shared beds; naps; confirmation/correction by dragging in the morning check-in; live wizard with 48 h preview and draggable threshold; living model view. Tested on 8 synthetic scenarios.
- **Sleep score and sleepmaxing** with the personal optimum (learned from the next day's wellbeing within age-based recommendations).
- **Mood forecast** (local online ridge regression) with range, explanation and forecast-vs-actual.
- **Health score** per person and family (k-threshold for persons).
- **Insights**: mood chart, year in pixels, weekdays, distribution, morning → evening, sleep timeline, duration vs. optimum, weight trend, training ↔ energy, sleep ↔ mood, what does you good / drags you down, goals tracker, weekly and monthly report, on this day, happiness jar, protective hint with helplines.
- **History** with calendar, day detail, swipe, filters and a **local natural-language search** (rule parser + BM25 with stems and synonyms, German and English).
- **Training rhythm** (rest days, soreness, recommendation, overdue), **weight** (trend, weekly average, healthy optimum, safety rules, live tracking with sensor), **cycle** (documentation, learned forecast, optional basal temperature; only three sensors for admins), **birthdays** (several on one day, no year, 29 February, confetti).
- **Entities** per person and family hub, cleaned up when modules are switched off; services for check-ins, pause, backups, setup requests, test notifications.
- **Backup & restore**: Home Assistant backup platform (flush + pause writes) and own encrypted `.mhbackup` files (manual/automatic, preview, safety point, full / configuration / one person, format migration); personal JSON/Markdown export and import.
- **LLM beta** via AI task (capability check) or conversation agent – with admin warning, per-person consent, data minimisation, rate limit and fallback.
- **Cards**: person, family, check-in, sleep, weight, training, mood chart, birthdays (visual editors, sections grid), sidebar panel with mini guide and phone layout, **dashboard strategy** `custom:mental-health`.
- **Repairs** for missing sources and notification targets with a one-click fix; diagnostics without contents; computing load 1–3.
