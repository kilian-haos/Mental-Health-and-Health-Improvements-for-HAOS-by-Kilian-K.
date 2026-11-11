# Sleep sources

Mental Health detects per person: **in bed**, **asleep**, **awake in bed**, **nap**, **getting up**, **going to bed**, interruptions and sleep duration. Beds are also used during the day (reading, phone, rest) – that must not count as sleep. The detection works with whatever you have; more sources make it more confident.

## Source types

| Type | Channel | Examples |
|---|---|---|
| On/off (role *in bed*) | occupancy | bed sensor, pressure mat, `input_boolean` |
| On/off (role *asleep*) | sleep hint | iPhone focus "Sleep" (`binary_sensor.<iphone>_focus`), a "sleeping" helper |
| Numeric | occupancy + movement | pressure, force, voltage, weight in bed |
| States | sleep hint | Sleep as Android (`sleep_tracking_started` …), `sensor.<phone>_sleep_segment`, wearables |
| Probability | sleep hint | `sensor.<phone>_sleep_confidence` (Android, 0–100) |
| Helper: screen | phone in use | `binary_sensor.<phone>_interactive` |
| Helper: charging | phone charging | `binary_sensor.<phone>_is_charging`, `sensor.<phone>_charger_type` |
| Helper: light | bedroom light | `light.bedroom` |
| Helper: motion elsewhere | hallway, kitchen … | `binary_sensor.hallway_motion` |
| Helper: room presence | mmWave in the bedroom | `binary_sensor.bedroom_presence` |
| Helper: home | at home | `person.x`, `device_tracker.y` |

For on/off sources you choose whether **on** or **off** means "in bed"/"asleep". For numeric sources an optional **trigger level** and direction can be entered; left empty, the model finds level and direction itself. An entered value is used as a starting point and refined carefully (the profile shows "learned: 2.45 V").

## The model

1. **Levels** (numeric sources): a Gaussian mixture with 2 components (3 for a shared bed: 0/1/2 people) is fitted with EM over a decaying histogram (half-life 10 days). The component that dominates during the day (10–18 h) is the baseline (empty bed); the direction (falls or rises under load) and the threshold follow from the mixture. Drift (temperature, mattress settling) is followed automatically.
2. **Evidence per minute**: occupancy, movement (minute range relative to the load step), sleep hints and helper signals. Each has a learned probability per state (*away*, *awake in bed*, *asleep*) – Beta counts that start with sensible values and learn from confirmations. Evidence is tempered (neighbouring minutes are not independent).
3. **Time-of-day prior**: 48 half-hour bins learned from confirmed nights (cold start: night window 21–10 h, core 23:00–06:30). At night a quiet baseline between bedtime and getting up therefore stays "asleep" unless something clearly speaks against it – phone screen on, light on, motion in the hallway, not at home.
4. **Forward-backward** over the window gives a probability of sleep per minute.
5. **Post-processing**: minimum duration (30 min in the first nights, then 15), wake bouts shorter than 25 min count as interruptions, the end is anchored to the last bed exit after which the bed stays empty, naps are detected separately during the day (lying quietly ≥ 20 min without the phone).
6. **Learning**: confirming or correcting the night in the morning check-in updates the channel probabilities, the prior and a start/end bias. Very confident nights also teach the model a little on their own.
7. **Confidence** 0–100 % per night from how sharp the decision is, how much of the night the sensors themselves support and how much the model has learned. Low confidence → the morning check-in asks actively.

### Example: a voltage bed sensor

A bed sensor at roughly 3.1 V when the bed is empty, short deep dips in the evening (sitting/lying down briefly – not sleep), small dips while falling asleep, baseline for most of the night (the person lies beside the measuring point) and a long trough in the morning before getting up. A threshold per sample would get this wrong. The model treats the evening dips as "awake in bed" (low prior, short), keeps the quiet night as sleep (high prior, no contrary evidence) and anchors getting up to the last bed exit in the morning. Synthetic tests with exactly this pattern (`tools/gen_sleep_data.py`, scenario 1) reach a median error of about 15 min for falling asleep and 8 min for waking up after the learning phase. Confidence stays honestly lower for such a source, so the check-in asks for confirmation more often.

## Synthetic test scenarios

`python tools/gen_sleep_data.py` runs 30 nights for each of: (1) the voltage bed sensor above, (2a/2b) clean and inverted on/off sensor, (3) numeric sensor rising under load (kg), (4) shared bed with two people, (5) nap vs. reading in bed with the phone, (6) late-shift sleep times and weekends, (7) phone signals only (charging + screen), (8) sensor outages. It prints the median errors for nights 1–10 and 21–30 (learning curve), naps found, false naps and the confidence.
