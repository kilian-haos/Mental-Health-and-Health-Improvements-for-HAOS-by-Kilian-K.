# Privacy

Mental Health is built for families. Admins are trusted, but they are usually family members, too – so contents belong to the person alone.

## What is stored where

| Store (`<config>/.storage/`) | Content | Protection |
|---|---|---|
| `mental_health.config` | persons and profiles (name, date of birth, height, modules, sources, schedules, targets), settings | structure only, no entries |
| `mental_health.keys` | master key, each person's wrapped data key and text key | text key wrapped with the master key – or only with the PIN-derived key |
| `mental_health.person.<id>` | entries per day: numbers (mood, energy, sleep, training, period yes/no …), texts (good/bad things, goals, journal, cycle details), weights, drafts, cached text analysis | numbers: data key; texts, drafts, analysis: text key (Fernet = AES-128-CBC + HMAC-SHA256) |
| `mental_health.model.<id>` | learned models, 36 h sensor buffer | data key |

Nothing personal is written to entities, attributes, the logbook, the recorder or the event bus. Diagnostics contain structure, counters, model state and versions only.

## Who can see what

- **The person**: everything of their own – entries, texts, analyses, model view with recent nights, export.
- **Admins**: configuration of all persons, the sensors of all persons (needed for automations), the model state without contents. Not: entries, texts, goals, good/bad things, weight history with live tracking, cycle details, personal analyses. The weight profile value is hidden from admins while live tracking is on.
- **Other family members**: only the family view – averages without names, only when at least *k* people (default 3, minimum 2) have data for that day.

Every websocket command that returns contents resolves the person from the logged-in user. There is no parameter to ask for another person's contents and no admin bypass.

## Personal PIN – the design

The analysis needs plain numbers (sensors, forecasts, health score), but texts are the most sensitive part. Therefore:

- **Without a PIN** the text key is wrapped with the master key – the server can read texts for the local text analysis and search.
- **With a PIN** the text key is wrapped **only** with a key derived from the PIN (scrypt, N = 2¹⁴, r = 8, p = 1). It is kept in memory only while the person has an unlocked session (duration set by the person, default 30 min) and dropped afterwards. Text analysis catches up after unlocking.
- **Numbers keep working** with a PIN – sensors, forecasts and the health score don't stop.
- **PIN changes** re-wrap the same text key (no data rewrite).
- **Forgotten PIN**: an admin can reset it. A new text key is created; texts protected by the old PIN can no longer be decrypted and are removed. Numbers are kept. The admin area says so before resetting.
- PIN checks happen on the server, with a lockout after three wrong tries (5 minutes).

The optional **admin PIN** is separate: it only gates the admin area (stored as a scrypt hash) and has nothing to do with person data.

## Honest limits

- Whoever has file-system or code access to Home Assistant *and* the master key can decrypt everything that is not PIN-protected. The master key is part of Home Assistant backups and of the integration's own backups (that is what makes restoring possible). Home Assistant encrypts its own backups; `.mhbackup` files are encrypted with the backup password.
- An admin could modify the code of the integration. The UI separation protects against curiosity, not against a determined administrator.
- Python cannot reliably wipe keys from memory.
- Home Assistant cannot fully hide entities from non-admin users.

## LLM beta

Off by default. It needs (1) an admin who enables it after reading a warning and (2) the consent of each person (revocable at any time; children are locked unless an admin explicitly allows it). Only excerpts are sent (at most 31 days, truncated texts), other household members' names are replaced by "[person]", outputs are shown as plain text. If the selected agent is a cloud service, these texts leave your home.
