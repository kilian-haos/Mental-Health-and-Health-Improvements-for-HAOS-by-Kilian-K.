# Notifications

How Mental Health notifies people about open check-ins – and why Android 14+ needs special care.

## Basics

- **One call per device.** Every target of a person is notified on its own, so a broken target (a phone that was reset, a removed script) never blocks the others. Broken targets raise a repair notice with a one-click fix.
- **The notification only opens the check-in.** Tapping it (Android `clickAction`, iOS `url`) or the action **"Check in now"** opens `/mental-health?checkin=morning` or `…=evening`. Optional action **"Later (10 min)"** re-sends to that device after ten minutes.
- **No text input in notifications.** `reply_text` answers travel over the Home Assistant event bus and end up in the recorder – unacceptable for journal texts. Entries are only ever made in the check-in page.
- **Nothing sensitive on the lock screen.** By default the text is just "Your morning check-in is ready." A person can enable *details on the lock screen* (sleep score, week comparison, training recommendation). Weight, cycle and mood values are never shown.
- **Reminders** while the window is open (default every 15 min, configurable); the window closes after 60 min (configurable) – then the notification is removed on all devices.
- **Children** get child-friendly texts.

## Targets

| Type | Example | Persistence |
|---|---|---|
| Companion App (`notify.mobile_app_*`) | `notify.mobile_app_s25` | Android: yes (re-send after swipe-away); iOS: time-sensitive |
| Notify entity | `notify.family_tablet` | text + link |
| Notify service (other) | `notify.telegram` | text + link |
| Script with mapped fields | `script.push_an_ein_gerat` | fields for title, message, data (tag, persistent …), target – persistence data is passed on |

The platform of a Companion App target is detected automatically from the mobile_app registration (`os_name`). For scripts you choose it.

## Android 14+: "persistent" is not persistent any more

Since **Android 14**, users can swipe away notifications even when they were sent with `persistent: true`. Android only prevents it on the locked screen and in a few system cases.

**What Mental Health does:**

1. Every check-in notification gets a **tag** that encodes the person, the slot and the device index: `mh_<person>_<morning|evening>_<index>`.
2. The Companion App fires `mobile_app_notification_cleared` (with title, message, tag and data of the cleared notification) when it is swiped away.
3. The integration listens for this event itself – **no automation needed**. If the tag belongs to an open check-in window, it **re-sends the notification only to that device** with `alert_once: true` (no new sound).
4. Loop protection: at most once every 10 s per device and at most 20 times per window.
5. When the check-in is done, cancelled or expired, `clear_notification` with the tag removes it on all devices.

The event does not contain a device ID (checked against the Home Assistant core source, `mobile_app/webhook.py → fire_event`); that is why the device is encoded in the tag and not in the visible text.

Data sent to Android devices:

```yaml
data:
  tag: mh_<person>_evening_0
  persistent: true        # only if "Android: come back after swipe-away" is on
  sticky: "true"
  alert_once: true
  channel: Mental Health – Check-in
  importance: high        # configurable per person
  priority: high
  ttl: 0
  clickAction: /mental-health?checkin=evening
  url: /mental-health?checkin=evening
  actions:
    - action: URI
      title: Check in now
      uri: /mental-health?checkin=evening
    - action: MH_LATER_<person>_evening_0
      title: Later (10 min)
```

**Settings on the phone (Companion App):**

- Notifications allowed, **notification access** granted.
- Battery **"Unrestricted"** for the Companion App – otherwise Android may delay or drop the cleared event.
- The channel **"Mental Health – Check-in"** appears after the first notification; sound, vibration and lock-screen display are set there.

## iOS / macOS

There is no persistent notification on Apple platforms. Mental Health uses:

- `push.interruption-level: time-sensitive` (configurable: active, passive, critical) – enable *Time Sensitive Notifications* for the Home Assistant app in the iOS settings,
- the tag to replace an older notification instead of stacking,
- reminders while the window is open,
- `clear_notification` to remove it when done,
- `url` to open the check-in.

Re-sends after a swipe-away are not done on iOS (the event does not exist there).

## Test

Profile → Notifications → **Send test notification**. Swipe the test away on Android – while a check-in is open it would come back; the test itself is not re-sent.
