/* Mental Health – sidebar panel (personal dashboard, insights, history, family, profile, admin).
 * Loaded only when the panel opens. Uses the shared core from mental-health.js (window.__MH).
 */
const _self = new URL(import.meta.url);
const _core = new URL("mental-health.js", _self);
_core.searchParams.set("v", _self.searchParams.get("c") || _self.searchParams.get("v") || "1");
if (!window.__MH) await import(_core.href);
const M = window.__MH;
const { esc, clamp, reduced, fmtNum, fmtTime, fmtDate, fmtDur, sign, moodEmoji, moodColor, ring, lineChart, smooth, attachTips,
  countUp, confetti, toast, shake, pinDialog, weightTile, protectHtml, nightRow, previewHtml, bindPreview, lsGet, lsSet, Api, CSS } = M;

/* ============================================================ Texte (Panel) */
Object.assign(M.I18N.en, {
  pin_sub_both: "Your personal PIN – or the admin PIN for admin access in this session.", pin_sub_admin: "Enter the admin PIN for admin access in this session.",
  admin_in: "Signed in as admin for this session", admin_in_short: "Admin", admin_in_hint: "Admin rights via the admin PIN – only for this session.",
  admin_end: "End admin", enter_code: "Enter code", lock_now: "Lock now", locked_now: "Locked",
  s_pick_entity: "Choose an entity above – the last 48 h appear here with the model's detection.",
  dump_open_n: "{n} open", dump_done_n: "{n} done", dump_oldest: "Oldest", dump_newest: "Newest", dump_all: "Show all",
  dump_empty: "Still empty – add something in the check-in or here.", dump_page_hint: "Tap ⋯ for sub-items, editing, sorting and deleting. Ticking an item ticks all of its sub-items.",
  dump_actions: "Actions", dump_subitem: "Sub-item", dump_up: "Up", dump_down: "Down", dump_indent: "Indent (under the item above)",
  dump_outdent: "Outdent", dump_show_done: "Show done", dump_hide_done: "Hide done", dump_too_deep: "At most three levels.",
  dump_delete_confirm: "Delete this item including all of its sub-items?", m_brain_dump: "Brain dump",
  tab_today: "Today", tab_insights: "Insights", tab_history: "History", tab_family: "Family", tab_profile: "Profile", tab_admin: "Admin",
  guide: "Guide", guide_title: "How it works",
  g_1: "<b>Check-in</b>: morning and evening, under a minute. Mandatory fields are marked with a dot.",
  g_2: "<b>Sliders</b>: drag – the face changes with your mood.", g_3: "<b>Sleep</b>: confirm or correct the detected night – drag the ends. This teaches the model most.",
  g_4: "<b>Charts</b>: tap a point for details. Choose the period at the top right.",
  g_5: "<b>History</b>: swipe left/right or use the arrows to flip through days. Search in your own words, e.g. “bad days last month”.",
  g_6: "<b>Privacy</b>: only you see your entries – admins neither. A PIN protects your texts even more.",
  g_7: "<b>Pause</b> (holiday, illness) in the profile: no questions, streaks don't break.",
  not_medical: "Orientation only – not a medical device. The cycle forecast is not a contraceptive method.",
  open_checkin: "Check in", evening_from: "Evening entry from {t}", yesterday_goals: "Yesterday's intentions",
  on_this_day: "On this day", month_ago: "1 month ago", year_ago: "1 year ago", jar: "From your happiness jar",
  sleep_nights: "Nights", score_trend: "Sleep score", duration_vs_opt: "Duration vs. optimum", regularity: "Regularity",
  components: "Components", c_mood: "Mood", c_stability: "Stability", c_energy: "Energy", c_health: "Health feeling", c_sleep: "Sleep",
  c_training: "Training rhythm", c_weight: "Weight", c_regularity: "Check-in regularity", c_duration: "Duration", c_interruptions: "Interruptions",
  c_latency: "Falling asleep", c_subjective: "Own rating",
  year_pixels: "Year in pixels", weekday_pattern: "Weekdays", me_delta: "Morning → evening", distribution: "Distribution",
  correlations: "Connections", sleep_mood: "Sleep ↔ mood", training_energy: "Training ↔ energy next day",
  good_for_you: "What does you good", drags_down: "What drags you down", goals_tracker: "Goals tracker",
  week_report: "Weekly review", month_report: "Monthly report", vs_prev: "vs. previous", trainings: "trainings", good_things: "good things",
  best_day: "Best day", llm_summary: "AI summary (beta)", llm_hint: "Sends excerpts of your entries to {b}. If that is a cloud service, they leave your home.",
  llm_run: "Create summary", llm_off: "Not enabled – an admin turns it on, then you agree in your profile.",
  forecast_vs: "Forecast vs. actual", insights_locked: "Unlock with your PIN to see text-based insights.",
  i_best_days: "On your best days {items} come up often.", i_sleep_mood: "After nights under {hours} h your mood is {diff} points lower on average.",
  i_training_energy_up: "The day after training your energy is {diff} points higher.", i_training_energy_down: "The day after training your energy is {diff} points lower – maybe plan more rest.",
  i_weekday: "{best} tends to be your best day, {worst} the hardest (difference {diff}).", i_day_up: "Your mood usually rises by {diff} during the day.",
  i_day_down: "Your mood usually drops by {diff} during the day.", i_goal: "Your intention “{text}” worked {done} of {n} times.",
  tp_family: "family", tp_friends: "friends", tp_partner: "partner", tp_work: "work", tp_school: "school", tp_sport: "sport", tp_nature: "nature & walks",
  tp_sleep: "sleep", tp_food: "food", tp_illness: "illness", tp_stress: "stress", tp_conflict: "arguments", tp_music: "music", tp_games: "games",
  tp_screen: "screen time", tp_pets: "pets", tp_rest: "rest", tp_achievement: "achievements", tp_learning: "learning", tp_creative: "creativity",
  tp_travel: "travel", tp_money: "money", tp_weather: "weather",
  x_sleep: "sleep vs. optimum", x_sleep_score: "sleep score", x_weekend: "weekend", x_trend: "recent trend", x_trained: "training yesterday",
  x_soreness: "muscle soreness", x_period: "period", x_luteal: "before your period", x_energy: "energy yesterday", x_health: "health yesterday",
  x_mood_y: "mood yesterday", x_temp: "temperature", x_daylight: "daylight", x_weekday: "weekday",
  search_ph: "Search, e.g. “bad days last month with training”", search_llm: "AI", results: "{n} days", no_results: "Nothing found.",
  flt_positive: "Positive", flt_neutral: "Neutral", flt_negative: "Negative", flt_journal: "With journal", flt_goals: "With goals", flt_training: "With training",
  flt_period: "During period", flt_morning: "Morning", flt_evening: "Evening", calendar: "Calendar", list: "List",
  day_empty: "No entries on this day.", add_entry: "Add entry", edit_entry: "Edit", delete_entry: "Delete entry",
  delete_confirm: "Delete this entry? Statistics and models will recalculate.", edited: "edited", chip_range: "{a} – {b}",
  ch_polarity: "{v}", ch_trained: "training", ch_sleep_short: "little sleep", ch_sleep_long: "lots of sleep", ch_period: "period",
  ch_journal: "journal", ch_goals: "goals", ch_weekend: "weekend", ch_weekdays: "weekdays", ch_morning: "morning", ch_evening: "evening",
  family_hist: "Family mood", members: "{n} people",
  // Profil
  p_basics: "About you", p_name: "Display name", p_birthdate: "Date of birth", p_birth_noyear: "The year is optional – leave it empty for a birthday without a year.", p_sex: "Sex",
  sex_female: "female", sex_male: "male", sex_other: "other", sex_unspecified: "not specified", p_height: "Height (cm)",
  p_weight: "Weight (kg)", p_weight_live: "Live weight tracking", p_weight_live_hint: "Values stay visible only to you. Without a sensor you'll be asked in the evening.",
  p_weight_entity: "Weight sensor (optional)", p_weight_entity_hint: "Admins can see the values of this sensor in Home Assistant.",
  p_target: "Target weight (optional)", p_target_hint: "Kept within the healthy range.", p_weight_hidden: "Only visible to {name}",
  p_missing: "With {what} the analysis becomes much more accurate.", p_missing_admin: "Ask an admin to add it.",
  mf_birthdate: "your date of birth", mf_sex: "sex", mf_height_cm: "your height", mf_height_for_weight: "your height (for a weight optimum)",
  p_modules: "Modules", m_mood: "Mood", m_energy: "Energy", m_health: "Health feeling", m_sleep_quality: "Sleep quality (own)",
  m_sleep_tracking: "Sleep tracking (sensors)", m_good_bad: "Good & bad things", m_goals: "Intentions & goals", m_journal: "Journal",
  m_weight: "Weight", m_training: "Training", m_training_child: "Exercise", m_cycle: "Cycle", m_birthday: "Birthday", m_suggestions: "Local suggestions",
  m_llm: "LLM features (beta)", m_core: "always on", m_cycle_hint: "Only with sex female or other.",
  p_times: "Check-in times", t_mode: "Trigger", mode_fixed: "Time", mode_entity: "Entity", mode_sleep: "Sleep", mode_manual: "Manual",
  mh_fixed: "At a fixed time – the same every day or per weekday.", mh_entity: "At the time of an entity, e.g. your alarm, plus an offset.",
  mh_sleep: "Follows your sleep: in the morning after you get up, in the evening before bedtime. Without sleep data the fixed time applies.",
  mh_manual: "No automatic reminder – start the check-in yourself or from an automation.", mh_sleep_need: "Needs a sleep source first.",
  t_every_day: "Every day", t_per_day: "Per weekday", t_offset_hint: "Minutes before (−) or after (+) the entity's time.",
  t_entity: "Timestamp entity (e.g. alarm)", t_offset: "Offset", t_gap: "Gap to sleep", t_gap_hint: "Morning ≈ this after getting up, evening ≈ 1.5 × before bedtime – fine-tuned by your answer times.",
  t_same: "Same every day", weekdays: "Mon,Tue,Wed,Thu,Fri,Sat,Sun", p_pause: "Pause", pause_on: "Pause now", pause_off: "End pause",
  pause_until: "Until (optional)", p_pin: "Personal PIN", pin_on: "Set PIN", pin_change: "Change PIN", pin_off: "Remove PIN",
  pin_hint: "Protects your texts (journal, good/bad things, goals, cycle details) with a key derived from your PIN. Without the PIN nobody can read them – not even admins. If you forget it, an admin can reset it, but these texts are then lost for good. Numbers (mood, sleep …) keep working.",
  pin_session: "Stay unlocked for (min)", pin_new: "New PIN", pin_old: "Current PIN", pin_set_ok: "PIN saved ✓", pin_removed: "PIN removed",
  p_notify: "Notifications", n_targets: "Devices & targets", n_add: "Add target", n_kind_service: "Companion App / notify service",
  n_kind_entity: "Notify entity", n_kind_script: "Script", n_test: "Send test notification", n_sent: "Sent to {n} of {m} targets",
  n_details: "Details on the lock screen (sleep score, training)", n_details_hint: "Never weight, cycle or mood values unless you turn this on.",
  n_remind: "Reminders while open", n_later: "“Later (10 min)” button", n_persist: "Android: come back after swipe-away",
  n_importance: "Android importance", n_ios: "iOS level", n_weekly: "Weekly review on Sunday",
  n_fields: "Script fields", n_f_title: "Field for title", n_f_message: "Field for message", n_f_data: "Field for data (optional)",
  n_f_target: "Field for target (optional)", n_target_value: "Target value", n_platform: "Platform",
  n_guide_android: "Android (Companion App): allow notifications and notification access, battery “Unrestricted” (otherwise the swipe-away event does not arrive reliably). Since Android 14, “persistent” notifications can be swiped away – Mental Health then re-sends to that device while your check-in is open. Sound and lock-screen display are set per channel “Mental Health – Check-in” in Android.",
  n_guide_ios: "iOS/macOS: there are no persistent notifications. Mental Health uses “time-sensitive” (enable Time Sensitive Notifications for the Home Assistant app in iOS settings), replaces the notification via its tag and reminds you while the check-in is open.",
  n_guide_other: "Other targets (e.g. Telegram, scripts) get text and a link, without persistence.",
  p_sleep: "Sleep sources", s_add: "Add source", s_entity: "Entity", s_kind: "Type", k_binary: "On/off", k_numeric: "Numeric (pressure, voltage, weight …)",
  k_enum: "States (sleep apps, wearables)", k_probability: "Probability (0–100)", k_aux: "Helper signal",
  s_role: "Meaning", r_in_bed: "in bed", r_asleep: "asleep", s_on_means: "“on” means", s_off_means: "“off” means",
  r_screen: "Phone screen on", r_charging: "Phone charging", r_light: "Bedroom light", r_away_motion: "Motion elsewhere", r_room: "Presence in bedroom", r_home: "At home",
  s_threshold: "Trigger level (optional)", s_threshold_hint: "Empty = the model finds level and direction itself. A value is used as a starting point and refined carefully.",
  s_direction: "Under load the value", dir_auto: "learn", dir_down: "falls", dir_up: "rises", s_shared: "Bed shared with",
  s_mapping: "Map states", s_preview: "Last 48 h with detection", s_learned: "learned: {v}", s_save: "Save source",
  s_no_sources: "No sleep source – all sleep features are hidden.", s_alarm: "Alarm entity (optional)",
  model_title: "Sleep model", model_reset: "Reset learned", model_reset_confirm: "Forget everything the sleep model learned (levels, times, confirmations)?",
  model_levels: "Levels", model_prior: "Time-of-day prior", model_maturity: "Learned", model_baseline: "Baseline", model_threshold: "Threshold",
  p_data: "Your data", export_json: "Export (JSON)", export_md: "Export (Markdown)", import: "Import", imported: "{n} days imported",
  p_llm: "LLM (beta)", llm_consent: "I agree that my texts may be sent to the configured AI service.", llm_revoke: "Revoke",
  llm_blocked: "Locked for children unless an admin explicitly allows it.", saved_short: "Saved",
  why_admin_managed: "Managed by an admin", why_admin_only: "Admins only", why_own_only: "Only the person themselves",
  why_live_weight: "Only visible to the person", why_child: "Managed by an admin",
  // Admin
  a_persons: "Persons", a_add: "Add person", a_requests: "Setup requests", a_settings: "Settings", a_notify: "Admin notifications",
  a_pin: "Admin PIN", a_pin_hint: "Optional, 4 digits, completely separate from personal PINs.", a_llm: "LLM (beta)", a_backup: "Backup & restore",
  a_status: "Status", a_choose_person: "Choose a person (only persons with a linked user)", a_no_user: "no user", a_taken: "set up",
  a_child: "Child mode", a_child_hint: "Guide value: up to about 12 years. Simpler language, emoji scale, no weight rating.",
  a_child_suggest: "Age {n} – child mode suggested.", a_can_edit: "May edit own data", a_create: "Create", a_created: "{name} is set up ✓",
  a_delete_person: "Remove person", a_delete_confirm: "Remove {name} from Mental Health? All entries of this person are deleted (backups stay).",
  a_reset_pin: "Reset PIN", a_reset_confirm: "Reset {name}'s PIN? Texts protected by the PIN (journal, good/bad things, goals, cycle details) are lost for good. Numbers are kept.",
  a_pin_lost: "{n} days of protected texts removed.", a_llm_child: "Allow LLM for this child", a_cycle_child: "Allow cycle for this child",
  st_day_boundary: "Day boundary", st_evening_from: "Evening entry from", st_morning_until: "Morning entry until", st_window: "Answer window (min)",
  st_remind: "Reminder every (min, 0 = off)", st_late: "Late entry", late_none: "not allowed", late_day_end: "until the end of the day", late_3_days: "up to 3 days",
  st_nightly: "Nightly analysis at", st_load: "Computing load", st_family_k: "Family values from (people)", st_low_days: "Protective hint after (days)",
  st_low_max: "… with mood at most", st_weekly: "Weekly review notification", st_workday: "Workday sensor (optional)",
  st_weather: "Outdoor temperature (optional)", st_daylight: "Daylight (sun.sun, optional)", st_cooldown: "Request cooldown (h)",
  load_1: "1 – light", load_2: "2 – balanced", load_3: "3 – thorough",
  llm_warn_title: "Before you enable the LLM beta", llm_warn: "With the LLM beta, excerpts of entries of persons who agree are sent to the selected agent. If it is a cloud service (OpenAI, Google …), these texts leave your home. Every person must agree separately; children are locked by default.",
  llm_accept: "I understand – enable", llm_mode: "Backend", llm_entity: "AI task entity", llm_agent: "Conversation agent", llm_caps: "Available: {a}",
  b_password: "Backup password", b_password_hint: "Without a password there is no export. Whoever has the backup and the password can restore it.",
  b_password_set: "Password is set", b_create: "Create backup now", b_auto: "Automatic", b_off: "off", b_daily: "daily", b_weekly: "weekly",
  b_keep: "Keep", b_list: "Backups", b_download: "Download", b_restore: "Restore", b_upload: "Upload file", b_preview: "Preview",
  b_scope: "What", b_all: "Everything", b_config: "Configuration only", b_person: "One person", b_restore_go: "Restore now",
  b_restore_hint: "A safety backup of the current state is created first. Afterwards the integration reloads.", b_restored: "Restored – reloading …",
  b_created: "Backup created ✓", b_delete: "Delete", b_deleted: "Backup deleted", b_delete_confirm: "Delete the backup {name} for good? This cannot be undone – download it first if you might need it.", b_enter_pw: "Password of the backup", b_none: "No backups yet.",
  ha_backup_hint: "Home Assistant backups include Mental Health automatically.",
  model_state: "Model", participation_14: "Participation (14 days)", nights_learned: "{n} nights · {l} confirmations",
  dismiss: "Dismiss", setup_for: "Set up", no_persons: "No persons yet – add the first one.",
});
Object.assign(M.I18N.de, {
  pin_sub_both: "Deine persönliche PIN – oder die Admin-PIN für Admin-Zugriff in dieser Sitzung.", pin_sub_admin: "Admin-PIN eingeben für Admin-Zugriff in dieser Sitzung.",
  admin_in: "Für diese Sitzung als Admin angemeldet", admin_in_short: "Als Admin drin", admin_in_hint: "Admin-Rechte über die Admin-PIN – nur für diese Sitzung.",
  admin_end: "Admin beenden", enter_code: "Code eingeben", lock_now: "Jetzt sperren", locked_now: "Gesperrt",
  s_pick_entity: "Wähle oben eine Entität – hier erscheinen dann die letzten 48 h mit der Erkennung des Modells.",
  dump_open_n: "{n} offen", dump_done_n: "{n} erledigt", dump_oldest: "Älteste", dump_newest: "Neueste", dump_all: "Alle anzeigen",
  dump_empty: "Noch leer – füge im Check-in oder hier etwas hinzu.", dump_page_hint: "Tippe auf ⋯ für Unterpunkte, Bearbeiten, Sortieren und Löschen. Ein Haken gilt für alle Unterpunkte.",
  dump_actions: "Aktionen", dump_subitem: "Unterpunkt", dump_up: "Nach oben", dump_down: "Nach unten", dump_indent: "Einrücken (unter den Punkt darüber)",
  dump_outdent: "Ausrücken", dump_show_done: "Erledigte zeigen", dump_hide_done: "Erledigte ausblenden", dump_too_deep: "Höchstens drei Ebenen.",
  dump_delete_confirm: "Diesen Punkt samt allen Unterpunkten löschen?", m_brain_dump: "Brain Dump",
  tab_today: "Heute", tab_insights: "Insights", tab_history: "Verlauf", tab_family: "Familie", tab_profile: "Profil", tab_admin: "Admin",
  guide: "Anleitung", guide_title: "So funktioniert's",
  g_1: "<b>Check-in</b>: morgens und abends, unter einer Minute. Pflichtfelder haben einen Punkt.",
  g_2: "<b>Regler</b>: ziehen – das Gesicht verändert sich mit deiner Stimmung.", g_3: "<b>Schlaf</b>: erkannte Nacht bestätigen oder korrigieren – an den Enden ziehen. Davon lernt das Modell am meisten.",
  g_4: "<b>Diagramme</b>: Punkt antippen für Details. Zeitraum oben rechts wählen.",
  g_5: "<b>Verlauf</b>: nach links/rechts wischen oder Pfeile nutzen. Suche in eigenen Worten, z. B. „schlechte Tage letzten Monat“.",
  g_6: "<b>Privatsphäre</b>: Nur du siehst deine Einträge – auch Admins nicht. Eine PIN schützt deine Texte zusätzlich.",
  g_7: "<b>Pause</b> (Urlaub, krank) im Profil: keine Abfragen, Serien reißen nicht.",
  not_medical: "Nur Orientierung – kein Medizinprodukt. Die Zyklusprognose ist keine Verhütungsmethode.",
  open_checkin: "Eintragen", evening_from: "Abend-Eintrag ab {t}", yesterday_goals: "Vorsätze von gestern",
  on_this_day: "Heute vor …", month_ago: "1 Monat", year_ago: "1 Jahr", jar: "Aus deinem Glücksglas",
  sleep_nights: "Nächte", score_trend: "Schlaf-Score", duration_vs_opt: "Dauer ggü. Optimum", regularity: "Regelmäßigkeit",
  components: "Komponenten", c_mood: "Stimmung", c_stability: "Stabilität", c_energy: "Energie", c_health: "Gesundheitsgefühl", c_sleep: "Schlaf",
  c_training: "Trainingsrhythmus", c_weight: "Gewicht", c_regularity: "Check-in-Regelmäßigkeit", c_duration: "Dauer", c_interruptions: "Unterbrechungen",
  c_latency: "Einschlafen", c_subjective: "Eigene Einschätzung",
  year_pixels: "Year in Pixels", weekday_pattern: "Wochentage", me_delta: "Morgen → Abend", distribution: "Verteilung",
  correlations: "Zusammenhänge", sleep_mood: "Schlaf ↔ Stimmung", training_energy: "Training ↔ Energie am Folgetag",
  good_for_you: "Was dir gut tut", drags_down: "Was dich runterzieht", goals_tracker: "Ziele-Tracker",
  week_report: "Wochenrückblick", month_report: "Monatsbericht", vs_prev: "ggü. vorher", trainings: "Trainings", good_things: "gute Dinge",
  best_day: "Bester Tag", llm_summary: "KI-Zusammenfassung (Beta)", llm_hint: "Sendet Ausschnitte deiner Einträge an {b}. Ist das ein Cloud-Dienst, verlassen sie dein Zuhause.",
  llm_run: "Zusammenfassung erstellen", llm_off: "Nicht aktiv – ein Admin schaltet es ein, dann stimmst du im Profil zu.",
  forecast_vs: "Prognose vs. tatsächlich", insights_locked: "Mit deiner PIN entsperren, um textbasierte Einblicke zu sehen.",
  i_best_days: "An deinen besten Tagen tauchen {items} oft auf.", i_sleep_mood: "Nach Nächten unter {hours} h ist deine Stimmung im Schnitt {diff} Punkte niedriger.",
  i_training_energy_up: "Am Tag nach dem Training ist deine Energie {diff} Punkte höher.", i_training_energy_down: "Am Tag nach dem Training ist deine Energie {diff} Punkte niedriger – vielleicht mehr Erholung einplanen.",
  i_weekday: "{best} ist meist dein bester Tag, {worst} der schwerste (Unterschied {diff}).", i_day_up: "Deine Stimmung steigt im Laufe des Tages meist um {diff}.",
  i_day_down: "Deine Stimmung sinkt im Laufe des Tages meist um {diff}.", i_goal: "Dein Vorsatz „{text}“ hat {done} von {n} Mal geklappt.",
  tp_family: "Familie", tp_friends: "Freunde", tp_partner: "Partnerschaft", tp_work: "Arbeit", tp_school: "Schule", tp_sport: "Sport", tp_nature: "Natur & Spaziergänge",
  tp_sleep: "Schlaf", tp_food: "Essen", tp_illness: "Krankheit", tp_stress: "Stress", tp_conflict: "Streit", tp_music: "Musik", tp_games: "Spiele",
  tp_screen: "Bildschirmzeit", tp_pets: "Haustiere", tp_rest: "Ruhe", tp_achievement: "Erfolge", tp_learning: "Lernen", tp_creative: "Kreatives",
  tp_travel: "Reisen", tp_money: "Geld", tp_weather: "Wetter",
  x_sleep: "Schlaf ggü. Optimum", x_sleep_score: "Schlaf-Score", x_weekend: "Wochenende", x_trend: "Trend der letzten Tage", x_trained: "Training gestern",
  x_soreness: "Muskelkater", x_period: "Periode", x_luteal: "vor der Periode", x_energy: "Energie gestern", x_health: "Gesundheit gestern",
  x_mood_y: "Stimmung gestern", x_temp: "Temperatur", x_daylight: "Tageslicht", x_weekday: "Wochentag",
  search_ph: "Suchen, z. B. „schlechte Tage letzten Monat mit Training“", search_llm: "KI", results: "{n} Tage", no_results: "Nichts gefunden.",
  flt_positive: "Positiv", flt_neutral: "Neutral", flt_negative: "Negativ", flt_journal: "Mit Journal", flt_goals: "Mit Zielen", flt_training: "Mit Training",
  flt_period: "Während der Periode", flt_morning: "Morgens", flt_evening: "Abends", calendar: "Kalender", list: "Liste",
  day_empty: "An diesem Tag gibt es keine Einträge.", add_entry: "Eintrag hinzufügen", edit_entry: "Bearbeiten", delete_entry: "Eintrag löschen",
  delete_confirm: "Diesen Eintrag löschen? Statistik und Modelle rechnen neu.", edited: "bearbeitet", chip_range: "{a} – {b}",
  ch_polarity: "{v}", ch_trained: "Training", ch_sleep_short: "wenig Schlaf", ch_sleep_long: "viel Schlaf", ch_period: "Periode",
  ch_journal: "Journal", ch_goals: "Ziele", ch_weekend: "Wochenende", ch_weekdays: "werktags", ch_morning: "morgens", ch_evening: "abends",
  family_hist: "Familienstimmung", members: "{n} Personen",
  p_basics: "Über dich", p_name: "Anzeigename", p_birthdate: "Geburtsdatum", p_birth_noyear: "Das Jahr ist optional – leer lassen für einen Geburtstag ohne Jahr.", p_sex: "Geschlecht",
  sex_female: "weiblich", sex_male: "männlich", sex_other: "anderes", sex_unspecified: "keine Angabe", p_height: "Größe (cm)",
  p_weight: "Gewicht (kg)", p_weight_live: "Live-Gewichtstracking", p_weight_live_hint: "Werte bleiben nur für dich sichtbar. Ohne Sensor wirst du abends gefragt.",
  p_weight_entity: "Gewichts-Sensor (optional)", p_weight_entity_hint: "Admins können die Werte dieses Sensors in Home Assistant sehen.",
  p_target: "Zielgewicht (optional)", p_target_hint: "Wird auf den gesunden Bereich begrenzt.", p_weight_hidden: "Nur für {name} sichtbar",
  p_missing: "Mit {what} wird die Auswertung deutlich genauer.", p_missing_admin: "Bitte einen Admin, es zu ergänzen.",
  mf_birthdate: "deinem Geburtsdatum", mf_sex: "Geschlecht", mf_height_cm: "deiner Größe", mf_height_for_weight: "deiner Größe (für ein Gewichts-Optimum)",
  p_modules: "Module", m_mood: "Stimmung", m_energy: "Energie", m_health: "Gesundheitsgefühl", m_sleep_quality: "Schlafqualität (eigene)",
  m_sleep_tracking: "Schlaf-Tracking (Sensoren)", m_good_bad: "Gute & schlechte Dinge", m_goals: "Vorsätze & Ziele", m_journal: "Journal",
  m_weight: "Gewicht", m_training: "Training", m_training_child: "Bewegung", m_cycle: "Zyklus", m_birthday: "Geburtstag", m_suggestions: "Lokale Vorschläge",
  m_llm: "LLM-Funktionen (Beta)", m_core: "immer an", m_cycle_hint: "Nur bei Geschlecht weiblich oder anderes.",
  p_times: "Check-in-Zeiten", t_mode: "Auslöser", mode_fixed: "Uhrzeit", mode_entity: "Entität", mode_sleep: "Schlaf", mode_manual: "Manuell",
  mh_fixed: "Zu einer festen Uhrzeit – jeden Tag gleich oder pro Wochentag.", mh_entity: "Zur Zeit einer Entität, z. B. deinem Wecker, plus Versatz.",
  mh_sleep: "Richtet sich nach deinem Schlaf: morgens nach dem Aufstehen, abends vor dem Zubettgehen. Ohne Schlafdaten gilt die feste Uhrzeit.",
  mh_manual: "Keine automatische Erinnerung – starte den Check-in selbst oder per Automation.", mh_sleep_need: "Braucht zuerst eine Schlafquelle.",
  t_every_day: "Jeden Tag", t_per_day: "Pro Wochentag", t_offset_hint: "Minuten vor (−) oder nach (+) der Zeit der Entität.",
  t_entity: "Zeitstempel-Entität (z. B. Wecker)", t_offset: "Versatz", t_gap: "Abstand zum Schlaf", t_gap_hint: "Morgens ≈ so lange nach dem Aufstehen, abends ≈ 1,5 × vor dem Zubettgehen – verfeinert anhand deiner Antwortzeiten.",
  t_same: "Jeden Tag gleich", weekdays: "Mo,Di,Mi,Do,Fr,Sa,So", p_pause: "Pause", pause_on: "Jetzt pausieren", pause_off: "Pause beenden",
  pause_until: "Bis (optional)", p_pin: "Persönliche PIN", pin_on: "PIN festlegen", pin_change: "PIN ändern", pin_off: "PIN entfernen",
  pin_hint: "Schützt deine Texte (Journal, gute/schlechte Dinge, Ziele, Zyklus-Details) mit einem Schlüssel aus deiner PIN. Ohne PIN kann sie niemand lesen – auch Admins nicht. Vergisst du sie, kann ein Admin sie zurücksetzen, die Texte sind dann aber endgültig verloren. Zahlen (Stimmung, Schlaf …) laufen weiter.",
  pin_session: "Entsperrt bleiben für (min)", pin_new: "Neue PIN", pin_old: "Aktuelle PIN", pin_set_ok: "PIN gespeichert ✓", pin_removed: "PIN entfernt",
  p_notify: "Benachrichtigungen", n_targets: "Geräte & Ziele", n_add: "Ziel hinzufügen", n_kind_service: "Companion App / notify-Dienst",
  n_kind_entity: "Notify-Entität", n_kind_script: "Skript", n_test: "Testbenachrichtigung senden", n_sent: "An {n} von {m} Zielen gesendet",
  n_details: "Details auf dem Sperrbildschirm (Schlaf-Score, Training)", n_details_hint: "Nie Gewicht, Zyklus oder Stimmungswerte, außer du schaltest das ein.",
  n_remind: "Erinnerungen, solange offen", n_later: "Knopf „Später (10 min)“", n_persist: "Android: nach Wegwischen zurückkommen",
  n_importance: "Android-Wichtigkeit", n_ios: "iOS-Stufe", n_weekly: "Wochenrückblick am Sonntag",
  n_fields: "Skript-Felder", n_f_title: "Feld für den Titel", n_f_message: "Feld für die Nachricht", n_f_data: "Feld für Daten (optional)",
  n_f_target: "Feld für das Ziel (optional)", n_target_value: "Zielwert", n_platform: "Plattform",
  n_guide_android: "Android (Companion App): Benachrichtigungen erlauben, Benachrichtigungszugriff erteilen, Akku „Nicht eingeschränkt“ (sonst kommt das Wegwisch-Ereignis nicht zuverlässig an). Seit Android 14 lassen sich auch „persistente“ Meldungen wegwischen – Mental Health sendet sie dann an genau dieses Gerät erneut, solange dein Check-in offen ist. Ton und Sperrbildschirm stellst du in Android pro Kanal „Mental Health – Check-in“ ein.",
  n_guide_ios: "iOS/macOS: Feste Benachrichtigungen gibt es dort nicht. Mental Health nutzt „Time Sensitive“ (in den iOS-Einstellungen für die Home-Assistant-App „Dringende Mitteilungen“ erlauben), ersetzt die Meldung über ihren Tag und erinnert, solange der Check-in offen ist.",
  n_guide_other: "Andere Ziele (z. B. Telegram, Skripte) bekommen Text und Link, ohne Persistenz.",
  p_sleep: "Schlafquellen", s_add: "Quelle hinzufügen", s_entity: "Entität", s_kind: "Art", k_binary: "An/Aus", k_numeric: "Numerisch (Druck, Spannung, Gewicht …)",
  k_enum: "Zustände (Schlaf-Apps, Wearables)", k_probability: "Wahrscheinlichkeit (0–100)", k_aux: "Hilfssignal",
  s_role: "Bedeutung", r_in_bed: "im Bett", r_asleep: "schläft", s_on_means: "„an“ bedeutet", s_off_means: "„aus“ bedeutet",
  r_screen: "Handy-Display an", r_charging: "Handy lädt", r_light: "Licht im Schlafzimmer", r_away_motion: "Bewegung anderswo", r_room: "Präsenz im Schlafzimmer", r_home: "Zuhause",
  s_threshold: "Triggerlevel (optional)", s_threshold_hint: "Leer = das Modell findet Schwelle und Richtung selbst. Ein Wert dient als Startwert und wird vorsichtig verfeinert.",
  s_direction: "Bei Belastung", dir_auto: "lernen", dir_down: "fällt der Wert", dir_up: "steigt der Wert", s_shared: "Bett geteilt mit",
  s_mapping: "Zustände zuordnen", s_preview: "Letzte 48 h mit Erkennung", s_learned: "gelernt: {v}", s_save: "Quelle speichern",
  s_no_sources: "Keine Schlafquelle – alle Schlaf-Funktionen sind ausgeblendet.", s_alarm: "Wecker-Entität (optional)",
  model_title: "Schlafmodell", model_reset: "Gelerntes zurücksetzen", model_reset_confirm: "Alles vergessen, was das Schlafmodell gelernt hat (Niveaus, Zeiten, Bestätigungen)?",
  model_levels: "Niveaus", model_prior: "Tageszeit-Prior", model_maturity: "Gelernt", model_baseline: "Grundlinie", model_threshold: "Schwelle",
  p_data: "Deine Daten", export_json: "Exportieren (JSON)", export_md: "Exportieren (Markdown)", import: "Importieren", imported: "{n} Tage importiert",
  p_llm: "LLM (Beta)", llm_consent: "Ich stimme zu, dass meine Texte an den eingestellten KI-Dienst gesendet werden dürfen.", llm_revoke: "Widerrufen",
  llm_blocked: "Für Kinder gesperrt, außer ein Admin erlaubt es ausdrücklich.", saved_short: "Gespeichert",
  why_admin_managed: "Wird von einem Admin verwaltet", why_admin_only: "Nur für Admins", why_own_only: "Nur für die Person selbst",
  why_live_weight: "Nur für die Person sichtbar", why_child: "Wird von einem Admin verwaltet",
  a_persons: "Personen", a_add: "Person anlegen", a_requests: "Einrichtungs-Anfragen", a_settings: "Einstellungen", a_notify: "Admin-Benachrichtigungen",
  a_pin: "Admin-PIN", a_pin_hint: "Optional, 4-stellig, völlig getrennt von den Personen-PINs.", a_llm: "LLM (Beta)", a_backup: "Backup & Wiederherstellen",
  a_status: "Status", a_choose_person: "Person wählen (nur Personen mit verknüpftem Benutzer)", a_no_user: "kein Benutzer", a_taken: "eingerichtet",
  a_child: "Kindermodus", a_child_hint: "Richtwert: bis ca. 12 Jahre. Einfachere Sprache, Emoji-Skala, keine Gewichtswertung.",
  a_child_suggest: "Alter {n} – Kindermodus empfohlen.", a_can_edit: "Darf eigene Daten bearbeiten", a_create: "Anlegen", a_created: "{name} ist eingerichtet ✓",
  a_delete_person: "Person entfernen", a_delete_confirm: "{name} aus Mental Health entfernen? Alle Einträge dieser Person werden gelöscht (Backups bleiben).",
  a_reset_pin: "PIN zurücksetzen", a_reset_confirm: "PIN von {name} zurücksetzen? Mit der PIN geschützte Texte (Journal, gute/schlechte Dinge, Ziele, Zyklus-Details) sind dann endgültig verloren. Zahlen bleiben erhalten.",
  a_pin_lost: "{n} Tage geschützter Texte entfernt.", a_llm_child: "LLM für dieses Kind erlauben", a_cycle_child: "Zyklus für dieses Kind erlauben",
  st_day_boundary: "Tagesgrenze", st_evening_from: "Abend-Eintrag ab", st_morning_until: "Morgen-Eintrag bis", st_window: "Antwortfenster (min)",
  st_remind: "Erinnerung alle (min, 0 = aus)", st_late: "Nachtragen", late_none: "nicht erlaubt", late_day_end: "bis Tagesende", late_3_days: "bis zu 3 Tage",
  st_nightly: "Nächtliche Auswertung um", st_load: "Rechenlast", st_family_k: "Familienwerte ab (Personen)", st_low_days: "Schutzhinweis nach (Tagen)",
  st_low_max: "… mit Stimmung höchstens", st_weekly: "Wochenrückblick-Benachrichtigung", st_workday: "Arbeitstag-Sensor (optional)",
  st_weather: "Außentemperatur (optional)", st_daylight: "Tageslicht (sun.sun, optional)", st_cooldown: "Sperrzeit für Anfragen (h)",
  load_1: "1 – leicht", load_2: "2 – ausgewogen", load_3: "3 – gründlich",
  llm_warn_title: "Bevor du die LLM-Beta einschaltest", llm_warn: "Mit der LLM-Beta werden Ausschnitte der Einträge von Personen, die zustimmen, an den gewählten Agenten gesendet. Ist das ein Cloud-Dienst (OpenAI, Google …), verlassen diese Texte dein Zuhause. Jede Person muss einzeln zustimmen; Kinder sind standardmäßig gesperrt.",
  llm_accept: "Verstanden – einschalten", llm_mode: "Backend", llm_entity: "AI-Task-Entität", llm_agent: "Konversations-Agent", llm_caps: "Verfügbar: {a}",
  b_password: "Backup-Passwort", b_password_hint: "Ohne Passwort kein Export. Wer Backup und Passwort hat, kann wiederherstellen.",
  b_password_set: "Passwort ist gesetzt", b_create: "Jetzt Backup erstellen", b_auto: "Automatisch", b_off: "aus", b_daily: "täglich", b_weekly: "wöchentlich",
  b_keep: "Behalten", b_list: "Backups", b_download: "Herunterladen", b_restore: "Wiederherstellen", b_upload: "Datei hochladen", b_preview: "Vorschau",
  b_scope: "Was", b_all: "Alles", b_config: "Nur Konfiguration", b_person: "Eine Person", b_restore_go: "Jetzt wiederherstellen",
  b_restore_hint: "Vorher wird automatisch ein Sicherungspunkt des aktuellen Stands erstellt. Danach lädt die Integration neu.", b_restored: "Wiederhergestellt – lädt neu …",
  b_created: "Backup erstellt ✓", b_delete: "Löschen", b_deleted: "Backup gelöscht", b_delete_confirm: "Backup {name} endgültig löschen? Das lässt sich nicht rückgängig machen – lade es vorher herunter, falls du es noch brauchen könntest.", b_enter_pw: "Passwort des Backups", b_none: "Noch keine Backups.",
  ha_backup_hint: "Home-Assistant-Backups enthalten Mental Health automatisch.",
  model_state: "Modell", participation_14: "Teilnahme (14 Tage)", nights_learned: "{n} Nächte · {l} Bestätigungen",
  dismiss: "Verwerfen", setup_for: "Einrichten", no_persons: "Noch keine Personen – leg die erste an.",
});

const PCSS = `
:host{ display:block; min-height:100vh; background:var(--c-bg); }
.app{ max-width:1280px; margin:0 auto; padding:14px 16px 96px; }
.top{ display:flex; align-items:center; gap:10px; padding:4px 2px 12px; }
.top .menu{ padding:9px 12px; font-size:18px; }
.top .h1{ font-size:22px; font-weight:600; }
.tabs{ display:flex; gap:6px; flex-wrap:wrap; }
.tab{ padding:8px 15px; font-size:14px; color:var(--c-muted); background:transparent; }
.tab.on{ background:var(--c-active); color:var(--c-teal); font-weight:600; }
.layout{ display:flex; gap:14px; align-items:flex-start; }
.guide{ width:280px; flex:0 0 280px; background:var(--c-surface); border-radius:var(--rad); padding:16px; position:sticky; top:12px; transition:width .3s var(--ease), flex-basis .3s var(--ease); overflow:hidden; }
.guide.collapsed{ width:52px; flex-basis:52px; padding:12px 8px; }
.guide.collapsed .gbody{ opacity:0; pointer-events:none; height:0; }
.guide .gbody{ transition:opacity .25s var(--ease); }
.guide p{ font-size:13px; color:var(--c-muted); line-height:1.5; margin:9px 0; }
.guide b{ color:var(--c-text); }
.main{ flex:1; min-width:0; display:grid; gap:14px; grid-template-columns:repeat(auto-fill,minmax(min(100%,360px),1fr)); align-content:start; }
.main > .wide{ grid-column:1 / -1; }
.sec{ background:var(--c-surface); border-radius:var(--rad); padding:18px; position:relative; overflow:hidden; }
.sec h3{ margin:0 0 12px; font-size:16px; font-weight:600; display:flex; align-items:center; gap:8px; }
.sec h4{ margin:16px 0 8px; font-size:13px; color:var(--c-muted); font-weight:600; text-transform:uppercase; letter-spacing:.6px; }
.kv{ display:flex; justify-content:space-between; gap:12px; padding:9px 0; border-bottom:1px solid rgba(255,255,255,.04); font-size:14px; align-items:center; }
.kv:last-child{ border-bottom:0; }
.kv > :first-child{ min-width:0; overflow-wrap:anywhere; }
.kv > :last-child{ flex:0 0 auto; }
.kv .why{ font-size:11.5px; color:var(--c-muted); }
.locked-field{ opacity:.55; }
.toggle{ position:relative; width:44px; height:26px; border-radius:13px; background:var(--c-raise2); flex:0 0 auto; transition:background .2s var(--ease); cursor:pointer; border:0; padding:0; }
.toggle::after{ content:""; position:absolute; top:3px; left:3px; width:20px; height:20px; border-radius:50%; background:#fff; transition:transform .25s var(--spring); }
.toggle.on{ background:var(--c-teal); }
.toggle.on::after{ transform:translateX(18px); }
.toggle:disabled{ opacity:.4; }
.bottom{ display:none; }
.sheet{ position:fixed; inset:0; z-index:9; background:var(--c-scrim); backdrop-filter:var(--c-blur); -webkit-backdrop-filter:var(--c-blur); display:flex; justify-content:center; align-items:flex-end; animation:mh-fade .2s; }
.sheet .panel{ background:var(--c-surface); width:min(720px,100%); max-height:92vh; overflow:auto; border-radius:var(--rad) var(--rad) 0 0; padding:20px 18px 30px; animation:mh-sheet .38s var(--ease); }
@media (min-width:761px){ .sheet{ align-items:center; } .sheet .panel{ border-radius:var(--rad); } }
@keyframes mh-sheet{ from{ transform:translateY(40px); opacity:.4 } to{ transform:none; opacity:1 } }
.pixels{ display:grid; grid-auto-flow:column; grid-template-rows:repeat(7,1fr); gap:3px; overflow-x:auto; padding-bottom:4px; }
.pixels i{ width:11px; height:11px; border-radius:3px; background:var(--c-raise); display:block; }
.bars{ display:flex; align-items:flex-end; gap:6px; height:110px; }
.bars > div{ height:100%; display:flex; flex-direction:column; justify-content:flex-end; }
.bars .b{ border-radius:8px 8px 4px 4px; background:var(--c-teal); min-height:3px; position:relative; transition:height .6s var(--ease); }
.bars .lb{ font-size:10.5px; color:var(--c-muted); text-align:center; margin-top:4px; }
.comp{ display:grid; grid-template-columns:minmax(0,1fr) minmax(48px,42%) auto; align-items:center; gap:10px; font-size:13px; margin:7px 0; }
.comp .clabel{ min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.comp .bar{ min-width:0; height:8px; background:var(--c-raise2); border-radius:4px; overflow:hidden; }
.comp .bar i{ display:block; height:100%; border-radius:4px; background:var(--c-teal); transform-origin:left; animation:mh-grow .9s var(--ease) both; }
@keyframes mh-grow{ from{ transform:scaleX(0) } }
.cal{ display:grid; grid-template-columns:repeat(7,1fr); gap:6px; }
.cal .d{ aspect-ratio:1; border-radius:12px; background:var(--c-raise); display:grid; place-items:center; font-size:13px; cursor:pointer; position:relative; transition:transform .16s var(--spring); border:0; padding:0; color:var(--c-text); }
.cal .d.today{ outline:2px solid var(--c-teal); outline-offset:-2px; }
.cal .d.sel{ transform:scale(1.08); box-shadow:0 0 0 3px var(--c-active); }
.cal .d.out{ opacity:.25; }
.cal .wd{ font-size:11px; color:var(--c-muted); text-align:center; }
.res{ padding:12px; border-radius:var(--rad-in); background:var(--c-raise); margin-bottom:8px; cursor:pointer; transition:background .2s; }
@media (hover:hover){ .res:hover{ background:var(--c-raise2); } }
.res mark{ background:rgba(47,214,176,.25); color:inherit; border-radius:4px; padding:0 2px; }
.search{ display:flex; gap:8px; }
.search input{ flex:1; }
.daynav{ display:flex; align-items:center; gap:8px; }
.entry{ background:var(--c-raise); border-radius:var(--rad-in); padding:14px; margin-top:10px; }
.entry ul{ margin:6px 0 0; padding-left:18px; }
.entry li{ margin:3px 0; font-size:14px; }
.journal{ white-space:pre-wrap; line-height:1.55; font-size:14px; margin-top:8px; }
canvas.model{ width:100%; height:280px; display:block; border-radius:var(--rad-in); background:var(--c-bg); }
.graph{ position:relative; }
.graph svg{ width:100%; height:180px; display:block; touch-action:none; }
.thr{ cursor:ns-resize; }
.person-row{ display:flex; align-items:center; gap:12px; padding:12px; border-radius:var(--rad-in); background:var(--c-raise); margin-bottom:8px; cursor:pointer; transition:background .2s; }
@media (hover:hover){ .person-row:hover{ background:var(--c-raise2); } }
.avatar{ width:40px; height:40px; border-radius:50%; background:var(--c-raise2); display:grid; place-items:center; overflow:hidden; flex:0 0 auto; font-weight:600; }
.avatar img{ width:100%; height:100%; object-fit:cover; }
.steps{ display:flex; gap:6px; margin-bottom:14px; }
.steps i{ flex:1; height:4px; border-radius:2px; background:var(--c-raise2); transition:background .3s; }
.steps i.on{ background:var(--c-teal); }
.slot{ padding:2px 0 4px; }
.slot + .slot{ border-top:1px solid rgba(255,255,255,.06); margin-top:16px; padding-top:18px; }
.slot-title{ font-size:14px; font-weight:600; margin:0 0 10px 2px; display:flex; align-items:center; gap:8px; }
.msegs{ position:relative; display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); background:var(--c-raise); border-radius:999px; padding:4px; isolation:isolate; }
.msegs::before{ content:""; position:absolute; z-index:-1; top:4px; bottom:4px; left:4px; width:calc((100% - 8px) / 4); border-radius:999px; background:var(--c-active);
  transform:translateX(calc(100% * var(--k, 0))); transition:transform .38s var(--spring); }
.mseg{ background:transparent; padding:9px 4px; font-size:13px; color:var(--c-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; min-width:0; transition:color .2s var(--ease); }
.mseg.on{ background:transparent; color:var(--c-teal); font-weight:600; }
@media (hover:hover){ .mseg:not(:disabled):not(.on):hover{ background:transparent; color:var(--c-text); } }
.mseg:disabled{ opacity:.38; }
.mhint{ font-size:12px; color:var(--c-muted); line-height:1.45; margin:9px 4px 0; animation:mh-fade .3s var(--ease); }
.mhint .need{ color:var(--c-amber); }
.slot-body{ margin-top:12px; animation:mh-rise .32s var(--ease) both; }
.slot-body .field{ margin:0 0 6px; }
.wd-times{ display:grid; grid-template-columns:repeat(auto-fill,minmax(112px,1fr)); gap:8px; }
.tcell{ display:flex; align-items:center; gap:6px; height:46px; padding:0 4px 0 13px; min-width:0; cursor:text; background:var(--c-raise); border-radius:14px;
  border:1.5px solid rgba(255,255,255,.09); border-color:color-mix(in srgb, var(--c-line) 75%, transparent);
  transition:border-color .2s var(--ease), background .2s, box-shadow .2s; }
.wd-times .tcell{ animation:mh-pop .28s var(--spring) both; animation-delay:calc(var(--i, 0) * 25ms); }
.tcell > span{ font-size:12px; font-weight:600; color:var(--c-muted); flex:0 0 auto; }
.tcell.we > span{ color:var(--c-amber); }
.tcell .tin{ flex:1 1 auto; min-width:0; width:100%; height:100%; border:0; background:transparent; box-shadow:none; padding:0 9px 0 4px; border-radius:0;
  text-align:right; font-size:16px; font-weight:600; font-variant-numeric:tabular-nums; letter-spacing:.3px; }
.tcell .tin:focus, .tcell .tin:hover{ background:transparent; box-shadow:none; }
.tcell .tin::placeholder{ color:var(--c-muted); opacity:.55; font-weight:500; }
.tcell:focus-within{ border-color:var(--c-teal); background:var(--c-raise2); box-shadow:0 0 0 3px var(--c-active); }
@media (hover:hover){ .tcell:not(:focus-within):hover{ border-color:color-mix(in srgb, var(--c-teal) 45%, var(--c-line)); } }
.tcell.err{ border-color:var(--c-red); }
.tcell.tick{ animation:mh-tick .32s var(--spring); }
.tcell.solo{ width:112px; padding:0 4px; }
.tcell.solo .tin{ text-align:center; padding:0 6px; }
.tcell[aria-disabled="true"]{ opacity:.6; }
.tsame{ display:flex; align-items:center; gap:10px; flex-wrap:wrap; }
.tsame .tcell{ flex:1 1 170px; max-width:240px; }
.slot-foot{ display:flex; justify-content:flex-end; margin-top:10px; }
.linkbtn{ padding:9px 14px; font-size:13px; display:inline-flex; align-items:center; gap:6px; }
.linkbtn .chev{ font-size:15px; line-height:1; color:var(--c-muted); }
.kv.tight{ border-bottom:0; padding:4px 0; }
.stepper{ display:inline-flex; align-items:center; gap:2px; padding:3px; background:var(--c-raise); border-radius:999px; border:1.5px solid rgba(255,255,255,.09);
  border-color:color-mix(in srgb, var(--c-line) 75%, transparent); transition:border-color .2s var(--ease), box-shadow .2s; }
.stepper:focus-within{ border-color:var(--c-teal); box-shadow:0 0 0 3px var(--c-active); }
.stepper .st-btn{ width:34px; height:34px; padding:0; border-radius:50%; font-size:18px; line-height:1; background:var(--c-raise2); color:var(--c-text); flex:0 0 auto; }
.stepper input{ width:50px; border:0; background:transparent; box-shadow:none; padding:0 2px; border-radius:0; text-align:right; font-size:16px; font-weight:600; font-variant-numeric:tabular-nums; }
.stepper input:focus, .stepper input:hover{ background:transparent; box-shadow:none; }
.stepper .unit{ font-size:12px; color:var(--c-muted); padding:0 6px 0 2px; }
.stepper.tick input{ animation:mh-tick .3s var(--spring); }
.stepper[aria-disabled="true"]{ opacity:.55; }
.pause-h{ border-top:1px solid rgba(255,255,255,.06); padding-top:18px; margin-top:20px !important; }
@keyframes mh-tick{ 0%{ transform:scale(1) } 40%{ transform:scale(1.05) } 100%{ transform:none } }
.admin-flag{ display:inline-flex; align-items:center; gap:6px; }
.kbtn{ padding:8px 12px; font-size:15px; }
.dm-row{ display:flex; align-items:center; gap:6px; width:100%; max-width:380px; }
.dmask{ display:flex; align-items:center; gap:4px; flex:1 1 auto; min-width:0; }
.dmask .grp{ display:flex; gap:4px; min-width:0; }
.dmask .grp.dg, .dmask .grp.mg{ flex:2 1 0; }
.dmask .grp.yg{ flex:4 1 0; }
.dmask input{ flex:1 1 0; min-width:0; width:100%; max-width:42px; height:46px; padding:0; text-align:center; font-size:19px; font-weight:600; border-radius:11px;
  caret-color:var(--c-teal); font-variant-numeric:tabular-nums; transition:border-color .2s var(--ease), background .2s, transform .16s var(--spring); }
.dmask input.filled{ background:var(--c-active); color:var(--c-teal); }
.dmask input.pop{ animation:mh-pop .22s var(--spring); }
.dmask input:focus{ transform:translateY(-1px); }
.dmask input::placeholder{ color:var(--c-muted); opacity:.5; font-weight:500; font-size:13px; }
.dmask input:focus::placeholder{ color:transparent; }
.dmask .sep{ color:var(--c-muted); font-size:20px; flex:0 0 8px; text-align:center; }
.dmask.err input{ border-color:var(--c-red); }
.dmask[aria-disabled="true"]{ opacity:.55; pointer-events:none; }
.dm-clear{ padding:6px 10px; font-size:13px; flex:0 0 auto; }
.dprev{ display:flex; align-items:center; gap:10px; padding:8px 2px; border-bottom:1px solid color-mix(in srgb, var(--c-line) 35%, transparent); }
.dprev:last-child{ border-bottom:0; }
.dprev .dot{ width:8px; height:8px; border-radius:50%; background:var(--c-teal); flex:0 0 auto; opacity:.8; }
.dprev .dot.old{ background:var(--c-amber); }
.dprev .t{ flex:1; min-width:0; font-size:14px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.dprev .when{ font-size:11px; color:var(--c-muted); flex:0 0 auto; }
.dgrp{ font-size:11px; letter-spacing:.6px; text-transform:uppercase; color:var(--c-muted); margin:10px 0 2px; }
.dtree{ margin-top:12px; }
.dnode > .drow{ transition:background .2s var(--ease); }
@media (hover:hover){ .dnode > .drow:hover{ background:var(--c-raise); } }
.dnode.sel > .drow{ background:var(--c-raise); }
.dmore{ flex:0 0 auto; padding:6px 10px; font-size:16px; background:transparent; color:var(--c-muted); }
.dacts{ display:grid; grid-template-rows:0fr; transition:grid-template-rows .25s var(--ease); }
.dacts.open{ grid-template-rows:1fr; }
.dacts > div{ overflow:hidden; min-height:0; }
.dacts .bar{ display:flex; flex-wrap:wrap; gap:6px; padding:6px 0 10px 62px; }
.dacts .bar button{ padding:7px 12px; font-size:13px; }
.dedit{ flex:1; min-width:0; padding:7px 10px; font-size:14.5px; }
.dsubadd{ display:flex; gap:8px; padding:4px 0 10px 62px; }
.dsubadd input{ flex:1; min-width:0; padding:8px 12px; font-size:14px; }
.lock{ display:grid; place-items:center; min-height:60vh; text-align:center; gap:14px; }
.dialog > div:first-child{ white-space:pre-line; }
.note{ font-size:11.5px; color:var(--c-muted); text-align:center; margin-top:18px; }
@media (max-width:760px){
  .app{ padding:10px 10px 92px; }
  .layout{ flex-direction:column-reverse; }
  .guide, .guide.collapsed{ width:100%; flex-basis:auto; position:static; padding:14px 16px; }
  .guide.collapsed .gbody{ display:none; }
  .main{ grid-template-columns:1fr; width:100%; }
  .top .tabs{ display:none; }
  .bottom{ display:flex; position:fixed; left:10px; right:10px; bottom:10px; z-index:8; background:var(--c-raise2); border-radius:999px; padding:5px; justify-content:space-around; box-shadow:0 10px 30px rgba(0,0,0,.4); }
  .bottom button{ flex:1; padding:9px 4px; font-size:11.5px; background:transparent; color:var(--c-muted); display:flex; flex-direction:column; align-items:center; gap:2px; }
  .bottom button.on{ color:var(--c-teal); background:var(--c-active); }
  .bottom .ic{ font-size:17px; }
}
`;


/* Datumsmaske im 2FA-Stil: TT.MM.JJJJ als 8 Ziffernfelder (Jahr optional für Geburtstage) */
function dmParts(v) {
  const s = String(v || "");
  let m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  if (m) return m[3] + m[2] + m[1];
  m = /^--(\d{2})-(\d{2})$/.exec(s);
  if (m) return m[2] + m[1];
  return "";
}
function dateMaskHtml(key, value, lang, opts = {}) {
  const d = dmParts(value).padEnd(8, " ");
  const sep = lang === "de" ? "." : "/";
  const ph = lang === "de" ? ["T", "T", "M", "M", "J", "J", "J", "J"] : ["D", "D", "M", "M", "Y", "Y", "Y", "Y"];
  const lab = lang === "de" ? ["Tag", "Monat", "Jahr"] : ["Day", "Month", "Year"];
  const cell = (i, g) => `<input type="text" inputmode="numeric" autocomplete="off" spellcheck="false" data-i="${i}" placeholder="${ph[i]}"
    aria-label="${lab[g]}, ${i < 2 ? i + 1 : i < 4 ? i - 1 : i - 3}" value="${d[i] === " " ? "" : d[i]}" class="${d[i] === " " ? "" : "filled"}" ${opts.disabled ? "disabled" : ""}>`;
  return `<div class="dm-row"><div class="dmask" data-dm="${key}" data-noyear="${opts.noYear ? 1 : 0}" aria-disabled="${opts.disabled ? "true" : "false"}" role="group">
    <span class="grp dg">${cell(0, 0)}${cell(1, 0)}</span><span class="sep">${sep}</span><span class="grp mg">${cell(2, 1)}${cell(3, 1)}</span><span class="sep">${sep}</span>
    <span class="grp yg">${cell(4, 2)}${cell(5, 2)}${cell(6, 2)}${cell(7, 2)}</span></div>
    ${opts.clear && !opts.disabled ? `<button class="ghost dm-clear" data-dmclear="${key}" title="${lang === "de" ? "Leeren" : "Clear"}" aria-label="${lang === "de" ? "Leeren" : "Clear"}">✕</button>` : ""}</div>`;
}
/* Ergebnis: ISO "YYYY-MM-DD", "--MM-DD" (ohne Jahr), null (leer), undefined (unvollständig/ungültig) */
function dmValue(box) {
  const v = [...box.querySelectorAll("input")].map((x) => x.value);
  const all = v.join("");
  if (!all) return null;
  const dd = v[0] + v[1], mm = v[2] + v[3], yy = v.slice(4).join("");
  if (dd.length < 2 || mm.length < 2) return undefined;
  const d = +dd, m = +mm;
  if (m < 1 || m > 12 || d < 1) return undefined;
  if (!yy) {
    if (box.dataset.noyear !== "1") return undefined;
    return d <= [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1] ? `--${mm}-${dd}` : undefined;
  }
  if (yy.length < 4) return undefined;
  const dt = new Date(+yy, m - 1, d);
  if (dt.getFullYear() !== +yy || dt.getMonth() !== m - 1 || dt.getDate() !== d || +yy < 1900 || +yy > 2100) return undefined;
  return `${yy}-${mm}-${dd}`;
}
/* Verhalten wie ein Code-Feld: jede Ziffer überschreibt das aktuelle Kästchen und springt weiter;
   der Cursor bleibt sichtbar (blinkt, wenn nicht getippt wird). Gespeichert wird erst, wenn das
   Datum vollständig ist – oder beim Verlassen (Geburtstag ohne Jahr, Leeren). */
function bindDateMask(box, onChange) {
  const cells = [...box.querySelectorAll("input")];
  let last = dmValue(box);
  const caretEnd = (c) => { try { const n = c.value.length; c.setSelectionRange(n, n); } catch (e) { /* ignorieren */ } };
  const focusCell = (i) => { const c = cells[Math.max(0, Math.min(7, i))]; c.focus(); caretEnd(c); };
  const state = () => {
    cells.forEach((c) => c.classList.toggle("filled", !!c.value));
    const val = dmValue(box);
    const full = cells.every((c) => c.value);
    const shortFull = box.dataset.noyear === "1" && cells.slice(0, 4).every((c) => c.value) && cells.slice(4).every((c) => !c.value);
    return { val, full, shortFull };
  };
  const emit = (final) => {
    const { val, full, shortFull } = state();
    const invalid = val === undefined && (full || (final && (shortFull || cells.some((c) => c.value))));
    box.classList.toggle("err", invalid);
    if (invalid && (full || final)) shake(box);
    if (val === undefined || val === last) return;
    if (full || final) { last = val; onChange(val); }
  };
  const put = (i, digit) => {
    const c = cells[i];
    c.value = digit;
    c.classList.remove("pop"); void c.offsetWidth; c.classList.add("pop");
    if (i < 7) focusCell(i + 1); else caretEnd(c);
    emit(false);
  };
  const fillFrom = (start, digits) => {
    let i = start;
    for (const ch of digits) { if (i > 7) break; cells[i].value = ch; i++; }
    focusCell(Math.min(i, 7));
    emit(false);
  };
  cells.forEach((c, i) => {
    c.addEventListener("focus", () => setTimeout(() => caretEnd(c), 0));
    c.addEventListener("mouseup", (ev) => { ev.preventDefault(); caretEnd(c); });
    c.addEventListener("keydown", (ev) => {
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      if (/^[0-9]$/.test(ev.key)) { ev.preventDefault(); put(i, ev.key); return; }
      if (ev.key === "Backspace") {
        ev.preventDefault();
        if (c.value) c.value = ""; else if (i > 0) { cells[i - 1].value = ""; focusCell(i - 1); }
        emit(false);
      } else if (ev.key === "Delete") { ev.preventDefault(); c.value = ""; emit(false); }
      else if (ev.key === "ArrowLeft" || (ev.key === "Tab" && ev.shiftKey && i > 0)) { if (i > 0) { ev.preventDefault(); focusCell(i - 1); } }
      else if (ev.key === "ArrowRight") { if (i < 7) { ev.preventDefault(); focusCell(i + 1); } }
      else if (ev.key === "Home") { ev.preventDefault(); focusCell(0); }
      else if (ev.key === "End") { ev.preventDefault(); focusCell(7); }
      else if (ev.key === "." || ev.key === "/" || ev.key === "-" || ev.key === ",") {
        ev.preventDefault();
        // Trennzeichen: einstellige Eingabe auffüllen (5. -> 05.) und zum nächsten Block springen
        if (i === 1 && cells[0].value && !cells[1].value) { cells[1].value = cells[0].value; cells[0].value = "0"; }
        if (i === 3 && cells[2].value && !cells[3].value) { cells[3].value = cells[2].value; cells[2].value = "0"; }
        focusCell(i < 2 ? 2 : i < 4 ? 4 : i);
        emit(false);
      } else if (ev.key.length === 1) ev.preventDefault();   // keine Buchstaben
    });
    // Handy-Tastaturen melden oft keine Tasten (key "Unidentified") -> über "input" auswerten
    c.addEventListener("input", () => {
      const digits = c.value.replace(/\D/g, "");
      const prev = c.dataset.prev || "";
      let fresh = digits;
      if (prev && digits.length > 1 && digits.startsWith(prev)) fresh = digits.slice(prev.length);
      else if (prev && digits.length > 1 && digits.endsWith(prev)) fresh = digits.slice(0, digits.length - prev.length);
      c.value = "";
      if (!fresh) { emit(false); return; }
      if (fresh.length === 1) put(i, fresh); else fillFrom(i, fresh);
    });
    c.addEventListener("beforeinput", () => { c.dataset.prev = c.value; });
    c.addEventListener("paste", (ev) => {
      const t = (ev.clipboardData || window.clipboardData).getData("text").trim();
      ev.preventDefault();
      let m = /^(\d{4})-(\d{1,2})-(\d{1,2})$/.exec(t);
      let digits;
      if (m) digits = m[3].padStart(2, "0") + m[2].padStart(2, "0") + m[1];
      else if ((m = /^(\d{1,2})[./-](\d{1,2})(?:[./-](\d{4}))?$/.exec(t))) digits = m[1].padStart(2, "0") + m[2].padStart(2, "0") + (m[3] || "");
      else digits = t.replace(/\D/g, "");
      cells.forEach((x) => { x.value = ""; });
      fillFrom(0, digits.slice(0, 8));
    });
  });
  // Verlassen der ganzen Maske -> Geburtstag ohne Jahr bzw. Leeren übernehmen
  box.addEventListener("focusout", () => {
    setTimeout(() => {
      const active = box.getRootNode().activeElement;
      if (!active || !box.contains(active)) emit(true);
    }, 0);
  });
  const row = box.parentElement;
  const clr = row && row.querySelector("[data-dmclear]");
  if (clr) clr.addEventListener("click", () => { cells.forEach((x) => { x.value = ""; }); box.classList.remove("err"); emit(true); focusCell(0); });
}

/* ---- Uhrzeit-Feld HH:MM ----
   Eigenes Textfeld statt <input type="time">: Der native Uhrzeit-Auswähler hat die macOS-App
   (WKWebView) beim Anklicken abstürzen lassen und sieht in jedem Browser anders aus. */
function timeFieldHtml(attrs, value, disabled) {
  return `<input type="text" class="tin" inputmode="numeric" autocomplete="off" spellcheck="false" maxlength="5" placeholder="--:--" value="${esc(value || "")}" ${attrs} ${disabled ? "disabled" : ""}>`;
}
/* "7" -> 07:00, "21:3" -> 21:30, "730" -> 07:30, "2130"/"21.30" -> 21:30; leer -> null; ungültig -> undefined */
function tmNormalize(raw) {
  const s = String(raw == null ? "" : raw).trim();
  if (!s) return null;
  let h, m;
  const c = /^(\d{1,2})\s*[:.h]\s*(\d{0,2})$/.exec(s);
  if (c) { h = +c[1]; m = c[2] ? +c[2].padEnd(2, "0") : 0; }
  else if (/^\d{1,4}$/.test(s)) {
    if (s.length <= 2) { h = +s; m = 0; } else if (s.length === 3) { h = +s[0]; m = +s.slice(1); } else { h = +s.slice(0, 2); m = +s.slice(2); }
  } else return undefined;
  if (h > 23 || m > 59) return undefined;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}
/* Pfeiltasten: auf das nächste Vielfache von step springen (21:03 +5 -> 21:05) */
function tmStep(v, delta) {
  const t = tmNormalize(v) || "00:00", st = Math.abs(delta), cur = +t.slice(0, 2) * 60 + +t.slice(3);
  let n = delta > 0 ? Math.floor(cur / st) * st + st : Math.ceil(cur / st) * st - st;
  n = ((n % 1440) + 1440) % 1440;
  return `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;
}
function bindTimeField(inp, onChange) {
  const cell = inp.closest(".tcell") || inp;
  let last = tmNormalize(inp.value) || null, timer = null;
  const tick = () => { cell.classList.remove("tick"); void cell.offsetWidth; cell.classList.add("tick"); };
  const commit = (v, later) => {
    cell.classList.remove("err");
    inp.value = v;
    if (v === last) return;
    last = v; tick();
    clearTimeout(timer);
    if (later) timer = setTimeout(() => onChange(v), 500); else onChange(v);
  };
  const caretEnd = () => { try { const n = inp.value.length; inp.setSelectionRange(n, n); } catch (e) { /* ignorieren */ } };
  inp.addEventListener("focus", () => setTimeout(caretEnd, 0));
  inp.addEventListener("beforeinput", () => { inp._prev = inp.value.replace(/\D/g, ""); });
  inp.addEventListener("keydown", (ev) => {
    if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
    if (ev.key === "ArrowUp" || ev.key === "ArrowDown") {
      ev.preventDefault();
      commit(tmStep(inp.value || last, (ev.shiftKey ? 60 : 5) * (ev.key === "ArrowUp" ? 1 : -1)), true);
      caretEnd();
    } else if (ev.key === "Enter") { ev.preventDefault(); inp.blur(); }
    else if (ev.key === "Escape") { inp.value = last || ""; cell.classList.remove("err"); inp.blur(); }
    else if (/^[0-9]$/.test(ev.key) && inp.value.length >= 5 && inp.selectionStart === inp.selectionEnd && inp.selectionStart >= 5) {
      inp.value = "";      // volles Feld, Cursor am Ende: neue Ziffer beginnt eine neue Uhrzeit
    } else if (ev.key.length === 1 && !/[0-9:.]/.test(ev.key)) ev.preventDefault();
  });
  inp.addEventListener("input", (ev) => {
    const raw = inp.value, pos = inp.selectionStart == null ? raw.length : inp.selectionStart;
    const del = !!(ev.inputType && ev.inputType.startsWith("delete"));
    let d = raw.replace(/\D/g, ""), before = raw.slice(0, pos).replace(/\D/g, "").length;
    if (del && d === inp._prev && d.length > 2) { d = d.slice(0, 1) + d.slice(2); before = 1; }   // nur der Doppelpunkt wurde gelöscht
    if (!del && d && (+d[0] > 2 || (d.length >= 2 && +d.slice(0, 2) > 23))) { d = "0" + d; before++; }   // "7" -> 07:
    d = d.slice(0, 4);
    inp.value = d.length <= 2 ? d : `${d.slice(0, 2)}:${d.slice(2)}`;
    const p = Math.min(inp.value.length, before <= 2 ? before : before + 1);
    try { inp.setSelectionRange(p, p); } catch (e) { /* ignorieren */ }
    const v = d.length === 4 ? tmNormalize(inp.value) : null;
    cell.classList.toggle("err", d.length === 4 && v === undefined);
    if (v) commit(v);
  });
  inp.addEventListener("blur", () => {
    const v = tmNormalize(inp.value);
    if (v === undefined) { shake(cell); inp.value = last || ""; setTimeout(() => cell.classList.remove("err"), 450); return; }
    if (v === null) { inp.value = last || ""; return; }
    clearTimeout(timer);
    if (v !== last) commit(v); else inp.value = v;
  });
}
/* ---- Zahlenfeld mit − / + (ohne <input type="number">) ---- */
function stepperHtml(attrs, value, o = {}) {
  const dis = o.disabled ? "disabled" : "";
  return `<div class="stepper" ${attrs} data-min="${o.min}" data-max="${o.max}" data-step="${o.step || 1}" aria-disabled="${o.disabled ? "true" : "false"}">
    <button type="button" class="st-btn" data-d="-1" aria-label="−" ${dis}>−</button><input type="text" inputmode="numeric" autocomplete="off" value="${esc(String(value == null ? "" : value))}" ${dis}>${o.unit ? `<span class="unit">${esc(o.unit)}</span>` : ""}<button type="button" class="st-btn" data-d="1" aria-label="+" ${dis}>+</button></div>`;
}
function bindStepper(box, onChange) {
  const inp = box.querySelector("input"), min = +box.dataset.min, max = +box.dataset.max, step = +box.dataset.step || 1;
  let last = parseInt(inp.value, 10), timer = null;
  const set = (n, now) => {
    n = Math.max(min, Math.min(max, n));
    inp.value = String(n);
    if (n === last) return;
    last = n;
    box.classList.remove("tick"); void box.offsetWidth; box.classList.add("tick");
    clearTimeout(timer);
    if (now) onChange(n); else timer = setTimeout(() => onChange(n), 450);
  };
  const cur = () => { const n = parseInt(inp.value, 10); return isNaN(n) ? last : n; };
  const move = (d) => { const c = cur(); set(d > 0 ? Math.floor(c / step) * step + step : Math.ceil(c / step) * step - step); };
  box.querySelectorAll(".st-btn").forEach((b) => b.addEventListener("click", () => move(+b.dataset.d)));
  inp.addEventListener("input", () => { const neg = min < 0 && inp.value.trim().startsWith("-"); inp.value = (neg ? "-" : "") + inp.value.replace(/\D/g, "").slice(0, 4); });
  inp.addEventListener("keydown", (ev) => {
    if (ev.key === "ArrowUp" || ev.key === "ArrowDown") { ev.preventDefault(); move(ev.key === "ArrowUp" ? 1 : -1); }
    else if (ev.key === "Enter") { ev.preventDefault(); inp.blur(); }
  });
  inp.addEventListener("change", () => {
    const n = parseInt(inp.value, 10);
    if (isNaN(n)) { inp.value = String(last); shake(box); return; }
    if (n < min || n > max) shake(box);
    set(n, true);
  });
}

const TAB_ICONS = { today: "☀️", insights: "✨", history: "🗓️", family: "🏡", profile: "👤", admin: "🛠️" };
const KINDS = ["binary", "numeric", "enum", "probability", "aux"];
const AUX_ROLES = ["screen", "charging", "light", "away_motion", "room", "home"];
const MODULE_KEYS = ["mood", "energy", "health", "sleep_quality", "sleep_tracking", "good_bad", "goals", "journal", "brain_dump", "weight", "training", "cycle", "birthday", "suggestions", "llm"];

class MHPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.tab = lsGet("mh_tab", "today");
    this.guideOpen = lsGet("mh_guide", true);
    this.hist = { view: lsGet("mh_hview", "calendar"), month: null, sel: null, chips: null, query: "" };
    this.insRange = lsGet("mh_irange", 30);
  }
  set hass(h) {
    const first = !this._hass;
    this._hass = h;
    if (!this.api) this.api = new Api(h); else this.api.hass = h;
    if (first) this.boot();
  }
  set narrow(v) { this._narrow = v; }
  set panel(p) { this._panel = p; }
  set route(r) { this._route = r; }
  get lang() { return M.langOf(this._hass); }
  t(k, v) { return M.tr(this.lang, k, v); }
  disconnectedCallback() { if (this._unsub) { this._unsub.then((u) => u && u()).catch(() => {}); this._unsub = null; } }
  connectedCallback() { if (this._hass && !this._unsub && this._me) this._subscribe(); }

  async boot() {
    this.shadowRoot.innerHTML = `<style>${CSS}${PCSS}</style><div class="center" style="min-height:60vh"><div class="spinner"></div></div>`;
    try { this._me = await this.api.call("me"); } catch (e) {
      this.shadowRoot.innerHTML = `<style>${CSS}${PCSS}</style><div class="center" style="min-height:60vh">${esc(this.t("not_loaded"))}</div>`;
      return;
    }
    const q = new URLSearchParams(location.search);
    if (q.get("admin") && this._me.is_admin) { this.tab = "admin"; this._adminFocus = { section: q.get("admin"), user: q.get("user") }; }
    if (!this._me.setup && this.tab !== "admin") this.tab = "today";
    this._subscribe();
    await this.render();
    if (q.get("view") === "dump" && this._me.setup) { this.sub = "dump"; this.render(true); }
    const ci = q.get("checkin");
    if (ci && this._me.setup && (ci === "morning" || ci === "evening")) this.openCheckin(ci);
  }
  _subscribe() {
    if (this._unsub) return;
    this._unsub = this.api.subscribe((ev) => {
      if (this._sheetOpen) return;
      clearTimeout(this._rt);
      this._rt = setTimeout(() => { if (["today", "family"].includes(this.tab)) this.render(true); }, 700);
    }).catch(() => null);
  }
  /* Ein Feld für alles: persönliche PIN (Admins kommen damit auch in den Admin-Bereich)
     oder stattdessen die Admin-PIN (Admin-Rechte nur für diese Sitzung). */
  async unlock(admin) {
    const me = this._me || {};
    const sub = me.admin_pin ? this.t(me.has_pin ? "pin_sub_both" : "pin_sub_admin") : this.t("pin_sub");
    const r = await pinDialog(this.shadowRoot, this.lang, { title: this.t(admin && !me.has_pin ? "admin_pin_title" : "pin_title"), sub, check: async (pin) => {
      const res = await this.api.call("unlock", { pin }, { session: false });
      if (res.ok && res.token) this.api.session = res.token;
      if (res.ok && res.admin_token) this.api.adminSession = res.admin_token;
      return res;
    } });
    const before = !!me.admin_elevated;
    try { this._me = await this.api.call("me"); } catch (e) { /* bleibt */ }
    if (this._me.admin_elevated && !before) toast(this.shadowRoot, this.t("admin_in"));
    return r;
  }
  adminUnlock() { return this.unlock(true); }
  async lockNow() {
    try { await this.api.call("lock", {}); } catch (e) { /* egal */ }
    this.api.session = null;
    this.api.adminSession = null;
    toast(this.shadowRoot, this.t("locked_now"));
    this.boot();
  }
  call(type, data, admin) {
    return this.api.call(type, data, { admin, onLocked: () => this.unlock(), onAdminLocked: () => this.adminUnlock() });
  }

  /* ---------------------------------------------------------- Gerüst */
  tabs() {
    const t = [];
    if (this._me.setup) t.push("today", "insights", "history", "family", "profile");
    else t.push("today", "family");
    if (this._me.is_admin) t.push("admin");
    return t;
  }
  async render(quiet) {
    const tabs = this.tabs();
    if (!tabs.includes(this.tab)) this.tab = tabs[0];
    const L = (k, v) => this.t(k, v);
    const me = this._me;
    const flag = me.admin_elevated ? `<span class="chip amber admin-flag" title="${esc(L("admin_in_hint"))}">🛡️ ${esc(L("admin_in_short"))}</span><button class="ghost kbtn lockb" title="${esc(L("admin_end"))}">${esc(L("admin_end"))}</button>` : "";
    const showKey = !me.admin_elevated && ((me.has_pin && !this.api.session) || (me.admin_pin && !me.admin_access));
    const showLock = !me.admin_elevated && me.has_pin && !!this.api.session;
    const keys = `${showKey ? `<button class="ghost kbtn keyb" title="${esc(L("enter_code"))}" aria-label="${esc(L("enter_code"))}">🔑</button>` : ""}${showLock ? `<button class="ghost kbtn lockb" title="${esc(L("lock_now"))}" aria-label="${esc(L("lock_now"))}">🔒</button>` : ""}`;
    const head = `<div class="top"><button class="ghost menu" title="Menu">☰</button><div class="h1">${esc(L("app"))}</div>${flag}<span class="spacer"></span>${keys}
      <div class="tabs">${tabs.map((k) => `<button class="tab ${this.tab === k ? "on" : ""}" data-tab="${k}">${esc(L("tab_" + k))}</button>`).join("")}</div></div>`;
    const guide = `<aside class="guide ${this.guideOpen ? "" : "collapsed"}"><div class="row"><b style="color:var(--c-teal)">${this.guideOpen ? esc(L("guide_title")) : "?"}</b><span class="spacer"></span>
      <button class="ghost gt" style="padding:4px 10px">${this.guideOpen ? "‹" : "›"}</button></div>
      <div class="gbody">${["g_1", "g_2", "g_3", "g_4", "g_5", "g_6", "g_7"].map((k) => `<p>${L(k)}</p>`).join("")}<p style="font-size:11.5px">${esc(L("not_medical"))}</p></div></aside>`;
    const bottom = `<nav class="bottom">${tabs.map((k) => `<button class="${this.tab === k ? "on" : ""}" data-tab="${k}"><span class="ic">${TAB_ICONS[k]}</span>${esc(L("tab_" + k))}</button>`).join("")}</nav>`;
    if (!quiet || !this.shadowRoot.querySelector(".main")) {
      this.shadowRoot.innerHTML = `<style>${CSS}${PCSS}</style><div class="app">${head}<div class="layout">${guide}<main class="main"><div class="sec wide center"><div class="spinner"></div></div></main></div></div>${bottom}`;
      this.bindShell();
    }
    const main = this.shadowRoot.querySelector(".main");
    try {
      const html = this.sub === "dump" ? await this.page_dump() : await this["tab_" + this.tab](quiet);
      if (html != null) { main.innerHTML = html; this.afterRender(main); }
    } catch (e) {
      if (e && e.code === "locked") {
        main.innerHTML = `<div class="sec wide lock"><div style="font-size:46px">🔒</div><div class="title">${esc(L("pin_title"))}</div><div class="sub">${esc(L("pin_sub"))}</div><button class="primary unl">${esc(L("pin_title"))}</button></div>`;
        main.querySelector(".unl").addEventListener("click", () => this.unlock().then(() => this.render()).catch(() => {}));
        return;
      }
      if (e && e.code === "admin_locked") {
        main.innerHTML = `<div class="sec wide lock"><div style="font-size:46px">🛠️</div><div class="title">${esc(L("admin_pin_title"))}</div><button class="primary unl">${esc(L("admin_pin_title"))}</button></div>`;
        main.querySelector(".unl").addEventListener("click", () => this.adminUnlock().then(() => this.render()).catch(() => {}));
        return;
      }
      console.error("Mental Health", e);
      main.innerHTML = `<div class="sec wide center">${esc(L("error"))}<button class="retry">${esc(L("retry"))}</button></div>`;
      main.querySelector(".retry").addEventListener("click", () => this.render());
    }
  }
  bindShell() {
    const R = this.shadowRoot;
    R.querySelectorAll("[data-tab]").forEach((b) => b.addEventListener("click", () => {
      this.tab = b.dataset.tab; lsSet("mh_tab", this.tab); this.sub = null;
      R.querySelectorAll("[data-tab]").forEach((x) => x.classList.toggle("on", x.dataset.tab === this.tab));
      this.render(true);
    }));
    R.querySelector(".gt").addEventListener("click", () => { this.guideOpen = !this.guideOpen; lsSet("mh_guide", this.guideOpen); this.render(true); this.shadowRoot.querySelector(".guide").classList.toggle("collapsed", !this.guideOpen); this.bindShellGuide(); });
    R.querySelector(".menu").addEventListener("click", () => this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true })));
    const kb = R.querySelector(".keyb");
    if (kb) kb.addEventListener("click", () => this.unlock().then(() => this.render()).catch(() => {}));
    R.querySelectorAll(".lockb").forEach((b) => b.addEventListener("click", () => this.lockNow()));
  }
  bindShellGuide() {
    const g = this.shadowRoot.querySelector(".guide");
    const L = (k) => this.t(k);
    g.querySelector("b").textContent = this.guideOpen ? L("guide_title") : "?";
    g.querySelector(".gt").textContent = this.guideOpen ? "‹" : "›";
  }
  afterRender(root) {
    attachTips(root);
    countUp(root);
    root.querySelectorAll("[data-act]").forEach((el) => el.addEventListener("click", (ev) => this.onAct(el.dataset.act, el, ev)));
    if (this._bind) { const b = this._bind; this._bind = null; b(root); }
  }
  onAct(act, el) {
    if (act === "checkin") return this.openCheckin(el.dataset.slot, el.dataset.day);
    if (act === "tab") { this.tab = el.dataset.v; lsSet("mh_tab", this.tab); this.sub = null; return this.render(); }
    if (act === "dump") { this.sub = "dump"; this.render(true); this.shadowRoot.querySelector(".main").scrollIntoView({ block: "start" }); return; }
  }

  /* ---------------------------------------------------------- Check-in als Sheet */
  openCheckin(slot, day) {
    const L = (k, v) => this.t(k, v);
    const sh = document.createElement("div");
    sh.className = "sheet";
    sh.innerHTML = `<div class="panel"><div class="row" style="margin-bottom:14px"><div class="title">${esc(L("checkin_" + slot))}${day ? " · " + esc(fmtDate(day, this.lang)) : ""}</div><span class="spacer"></span><button class="ghost x">✕</button></div><mh-checkin></mh-checkin></div>`;
    this.shadowRoot.appendChild(sh);
    this._sheetOpen = true;
    const close = () => { sh.remove(); this._sheetOpen = false; const u = new URL(location.href); if (u.searchParams.has("checkin")) { u.searchParams.delete("checkin"); history.replaceState(null, "", u.pathname + u.search); } };
    sh.querySelector(".x").addEventListener("click", close);
    sh.addEventListener("click", (ev) => { if (ev.target === sh) close(); });
    const el = sh.querySelector("mh-checkin");
    el.hass = this._hass;
    el.load(slot, day || undefined);
    el.addEventListener("mh-saved", (ev) => {
      close();
      toast(this.shadowRoot, (ev.detail.info && ev.detail.info.early_training) ? L("early_training") : L("saved"));
      this.render(true);
    });
  }

  /* ---------------------------------------------------------- Heute */
  async tab_today() {
    const L = (k, v) => this.t(k, v), lang = this.lang;
    if (!this._me.setup) {
      this._bind = (root) => bindPreview({ shadowRoot: root, api: this.api, t: (k) => this.t(k), refresh: () => this.boot() });
      return `<div class="sec wide">${previewHtml(lang, this._me, false)}</div>`;
    }
    const d = await this.call("dashboard");
    this._d = d;
    const v = d.values || {};
    const out = [];
    let i = 0;
    const sec = (html, cls = "") => out.push(`<section class="sec rise ${cls}" style="animation-delay:${Math.min(i++ * 50, 400)}ms">${html}</section>`);
    // Check-in
    const open = ["morning", "evening"].find((s) => d.status[s] && d.status[s].state === "open");
    const eveDone = d.status.evening && d.status.evening.state === "done";
    const mornDone = d.status.morning && d.status.morning.state === "done";
    let ci = "";
    if (d.paused) ci = `<div class="row"><span class="emoji">⏸️</span><div><b>${esc(L("paused"))}</b>${d.pause && d.pause.until ? `<div class="sub">${esc(L("paused_until", { d: fmtDate(d.pause.until, lang) }))}</div>` : ""}</div></div>`;
    else if (open) ci = `<div class="row" style="flex-wrap:wrap"><span class="emoji">${open === "morning" ? "🌅" : "🌙"}</span><div><b>${esc(L("checkin_open", { slot: L(open) }))}</b>
      <div class="sub">${esc(L("until", { t: fmtTime(d.status[open].until, lang) }))}</div></div><span class="spacer"></span>
      <button class="primary pulse" data-act="checkin" data-slot="${open}">${esc(L("open_checkin"))}</button></div>`;
    else {
      const btns = [];
      if (!mornDone && new Date().getHours() < 14) btns.push(`<button data-act="checkin" data-slot="morning">${esc(L("enter_morning"))}</button>`);
      if (d.evening_manual && !eveDone) btns.push(`<button class="primary" data-act="checkin" data-slot="evening">${esc(L("enter_evening"))}</button>`);
      if (eveDone) btns.push(`<span class="chip teal">${esc(L("done_today"))}</span>`);
      if (!d.evening_manual && !eveDone) btns.push(`<span class="hint">${esc(L("evening_from", { t: d.evening_open_from }))}</span>`);
      const h = new Date().getHours();
      ci = `<div class="row" style="flex-wrap:wrap;gap:12px"><div><div class="title">${esc(h < 11 ? L("hello_m") : h < 17 ? L("hello_d") : L("hello_e"))}, ${esc(this._me.name.split(" ")[0])}</div>
        <div class="sub">${v.streak ? esc(L("streak", { n: v.streak })) : esc(L("first_days"))}</div></div><span class="spacer"></span>${btns.join("")}</div>`;
    }
    sec(ci, "wide");
    if (d.protect) out.push(`<div class="wide">${protectHtml(lang, d.child)}</div>`);
    // Stimmung + Prognose
    const fc = d.forecast;
    sec(`<h3>${moodEmoji(v.mood_today, d.child)} ${esc(L("mood"))}</h3>
      <div class="row" style="gap:16px">${ring(v.mood_today == null ? null : v.mood_today * 10, 100, 104, moodColor(v.mood_today), v.mood_today == null ? "–" : fmtNum(v.mood_today, 1, lang), L("today"))}
      <div class="col" style="gap:4px"><div class="sub">${esc(L("morning"))}: <b style="color:var(--c-text)">${v.mood_morning ?? "–"}</b> · ${esc(L("evening"))}: <b style="color:var(--c-text)">${v.mood_evening ?? "–"}</b></div>
      <div class="sub">Ø 7: <b style="color:var(--c-text)">${v.mood_avg7 == null ? "–" : fmtNum(v.mood_avg7, 1, lang)}</b> · Ø 30: <b style="color:var(--c-text)">${v.mood_avg30 == null ? "–" : fmtNum(v.mood_avg30, 1, lang)}</b></div>
      ${v.mood_trend != null ? `<span class="chip small ${v.mood_trend > 0.2 ? "good" : v.mood_trend < -0.2 ? "bad" : ""}">${esc(L("trend"))} ${sign(v.mood_trend, 1, lang)}</span>` : ""}</div></div>
      ${fc ? (fc.ready ? `<div class="tile" style="margin-top:12px"><div class="k">${esc(L("forecast"))}</div><div class="row"><span class="emoji">${moodEmoji(fc.value, d.child)}</span><b>${fmtNum(fc.low, 1, lang)} – ${fmtNum(fc.high, 1, lang)}</b><span class="hint">${esc(L("forecast_conf", { p: Math.round(fc.confidence * 100) }))}</span></div>
        ${(fc.reasons || []).length ? `<div class="hint">${esc(L("because"))} ${esc(fc.reasons.map((r) => L(r.key) + (r.effect > 0 ? " ↑" : " ↓")).join(", "))}</div>` : ""}</div>`
        : fc.paused ? "" : `<div class="hint" style="margin-top:10px">${esc(L("forecast_learning", { n: fc.days || 0, m: fc.needed || 10 }))}</div>`) : ""}`);
    // Health Score
    sec(`<h3>💚 ${esc(L("health_score"))}</h3><div class="row" style="gap:16px">${ring(d.health.score, 100, 104, "var(--c-teal)", d.health.score ?? "–", "/100")}
      <div style="flex:1">${Object.entries(d.health.comps || {}).slice(0, 5).map(([k, val]) => `<div class="comp"><span class="sub clabel">${esc(L("c_" + k))}</span><div class="bar"><i style="width:${val}%"></i></div></div>`).join("")}</div></div>`);
    // Schlaf
    if (d.sleep && d.sleep.enabled) {
      const n = d.sleep.today, mx = d.sleep.maxing;
      sec(`<h3>🌙 ${esc(L("sleep"))} ${d.sleep.state ? `<span class="chip small ${d.sleep.state === "asleep" ? "teal" : ""}">${esc(L("st_" + d.sleep.state))}</span>` : ""}</h3>
        ${n ? `<div class="row" style="gap:14px">${ring(n.score, 100, 92, "var(--c-violet)", n.score ?? "–", "Score")}<div><div class="big" style="font-size:26px">${fmtDur(n.asleep)}</div>
          <div class="sub">${fmtTime(n.start, lang)} – ${fmtTime(n.end, lang)}${n.src === "auto" && n.conf < 0.6 ? " · ?" : ""}</div></div></div>
          <div style="margin-top:12px">${nightRow(n, lang)}<div class="timeaxis"><span>18</span><span>22</span><span>02</span><span>06</span><span>10</span><span>14</span></div></div>
          <div class="row" style="flex-wrap:wrap;gap:6px;margin-top:10px">${mx ? `<span class="chip ${mx.week_color}">${sign(mx.week_pct)} % ${esc(L("vs_week"))}</span><span class="chip ${mx.opt_color}">${sign(mx.opt_pct)} % ${esc(L("vs_opt"))}</span>` : ""}
          <span class="chip">${esc(L("optimum", { t: fmtDur(d.sleep.optimum_h * 60) }))}</span></div>`
          : `<div class="hint">${esc(d.sleep.learning ? L("sleep_learning", { n: d.sleep.night_of }) : L("no_sleep"))}</div>`}`);
    }
    if (d.weight && !d.weight.child) sec(`<h3>⚖️ ${esc(L("weight"))}</h3>${weightTile(d.weight, lang) || `<div class="hint">${esc(L("no_data"))}</div>`}`);
    if (d.training) {
      const tr_ = d.training;
      const txt = tr_.status === "recommended" ? (tr_.child ? L("training_good_child") : L("training_good")) : tr_.status === "overdue" ? L("training_overdue", { n: tr_.overdue }) : tr_.status === "pause" ? L("training_pause") : L("training_ready_soon");
      sec(`<h3>💪 ${esc(tr_.child ? L("m_training_child") : L("training"))} <span class="chip small ${tr_.status === "overdue" ? "amber" : tr_.status === "recommended" ? "teal" : ""}">${esc(L("ts_" + tr_.status))}</span></h3>
        <div class="tile ${tr_.highlight ? "pulse" : ""}" style="${tr_.highlight ? "background:rgba(245,177,76,.14)" : tr_.status === "recommended" ? "background:var(--c-active)" : ""}">${esc(txt)}</div>
        ${tr_.days_since != null ? `<div class="hint" style="margin-top:8px">${esc(this.lang === "de" ? `Letztes Training vor ${tr_.days_since} Tagen` : `Last training ${tr_.days_since} days ago`)}${tr_.soreness != null ? " · " + esc(L("f_soreness")) + " " + tr_.soreness : ""}</div>` : ""}`);
    }
    if (d.cycle) {
      const c = d.cycle;
      sec(`<h3>🩸 ${esc(L("cycle"))}</h3><div class="row" style="gap:14px">${ring(c.day ? Math.min(c.day, c.cycle_len) : 0, c.cycle_len, 92, "#fb7185", c.day ? (this.lang === "de" ? "Tag " : "Day ") + c.day : "–", c.active ? "🩸" : "")}
        <div><div class="sub">${esc(this.lang === "de" ? "Nächste Periode" : "Next period")}</div><b>${c.next_start ? fmtDate(c.next_start, lang) : "–"}</b>
        <div class="hint">± ${fmtNum(c.window, 0, lang)} ${this.lang === "de" ? "Tage" : "days"} · ${Math.round(c.confidence * 100)} %</div></div></div>
        <div class="hint" style="margin-top:10px">${esc(L("not_medical"))}</div>`);
    }
    if ((d.birthdays || []).length) {
      const own = d.birthdays.find((b) => b.self && b.days === 0);
      sec(`<h3>🎂 ${esc(L("birthdays"))}</h3>${d.birthdays.slice(0, 4).map((b) => `<div class="row" style="margin:6px 0"><span>${b.days === 0 ? "🎉" : "🎈"}</span><span>${esc(b.self && b.days === 0 ? L("bd_own") : b.days === 0 ? L("bd_today", { name: b.name }) : b.days === 1 ? L("bd_tomorrow", { name: b.name }) : L("bd_in", { name: b.name, n: b.days }))}</span></div>`).join("")}`, own ? "bday" : "");
      if (own) this._bind = (root) => { const el = root.querySelector(".bday"); if (el) confetti(el); };
    }
    if ((d.on_this_day || []).length || d.jar) {
      sec(`<h3>🫙 ${esc(L("on_this_day"))}</h3>${(d.on_this_day || []).map((o) => `<div class="tile" style="margin-bottom:8px"><div class="k">${esc(L(o.when === "month" ? "month_ago" : "year_ago"))} · ${esc(fmtDate(o.day, lang))} ${o.mood != null ? moodEmoji(o.mood, d.child) : ""}</div>${(o.good || []).map((g) => `<div>🌱 ${esc(g)}</div>`).join("")}</div>`).join("")}
        ${d.jar ? `<div class="tile" style="background:var(--c-active)"><div class="k">${esc(L("jar"))} · ${esc(fmtDate(d.jar.day, lang))}</div><div>✨ ${esc(d.jar.text)}</div></div>` : ""}`);
    }
    if (d.missing && d.missing.length) {
      const can = this._me.rights && this._me.rights.profile_edit && this._me.rights.profile_edit.ok;
      out.push(`<div class="wide hint" style="padding:0 6px">${esc(L("p_missing", { what: d.missing.map((m) => L("mf_" + m)).join(", ") }))} ${can ? `<a href="#" data-act="tab" data-v="profile" style="color:var(--c-teal)">→ ${esc(L("tab_profile"))}</a>` : esc(L("p_missing_admin"))}</div>`);
    }
    if (d.dump) {
      const dp = d.dump;
      const row = (it, old) => `<div class="dprev"><span class="dot ${old ? "old" : ""}"></span><span class="t">${esc(it.text)}</span>
        ${it.sub ? `<span class="dsub">${esc(L("dump_sub", { d: it.sub_done, n: it.sub }))}</span>` : ""}<span class="when">${esc(fmtDate(it.created, lang, { day: "numeric", month: "short" }))}</span></div>`;
      sec(`<h3>🧠 ${esc(L("dump"))} ${dp.locked ? "" : `<span class="chip small ${dp.open ? "teal" : ""}">${esc(L("dump_open_n", { n: dp.open }))}</span>`}</h3>
        ${dp.locked ? `<div class="hint">🔒 ${esc(L("insights_locked"))}</div>`
          : !dp.total ? `<div class="hint">${esc(L("dump_empty"))}</div>`
          : `${dp.oldest.length ? `<div class="dgrp">${esc(L("dump_oldest"))}</div>${dp.oldest.map((it) => row(it, true)).join("")}` : ""}
             ${dp.newest.length ? `<div class="dgrp">${esc(L("dump_newest"))}</div>${dp.newest.map((it) => row(it, false)).join("")}` : ""}
             ${!dp.open ? `<div class="hint">${esc(L("dump_none_open"))}</div>` : ""}`}
        <div class="row" style="margin-top:12px;justify-content:flex-end"><button data-act="dump">${esc(L("dump_all"))} ›</button></div>`);
    }
    out.push(`<div class="wide note">${esc(L("not_medical"))}</div>`);
    return out.join("");
  }

  /* ---------------------------------------------------------- Brain Dump (Unterseite) */
  async page_dump() {
    this._dumpData = await this.call("dump", {});
    this._dumpShowDone = lsGet("mh_dump_done", false);
    this._dumpOpen = new Set(lsGet("mh_dump_open", []));
    this._bind = (root) => this.bindDumpPage(root);
    return `<section class="sec wide rise dumppage">${this.dumpPageHtml()}</section>`;
  }
  dumpPageHtml() {
    const L = (k, v) => this.t(k, v);
    const dd = this._dumpData, pv = dd.preview;
    const filt = (xs) => xs.filter((x) => this._dumpShowDone || !x.done);
    const node = (it, depth) => {
      const kidsAll = it.children || [];
      const kids = filt(kidsAll);
      const all = [];
      const walk = (xs) => xs.forEach((x) => { all.push(x); walk(x.children || []); });
      walk(kidsAll);
      const nd = all.filter((x) => x.done).length;
      const open = this._dumpOpen.has(it.id);
      const sel = this._dumpMenu === it.id;
      const editing = this._dumpEdit === it.id;
      return `<div class="dnode ${sel ? "sel" : ""}" data-node="${esc(it.id)}"><div class="drow ${it.done ? "done" : ""}">
          <button class="dchev ${kids.length ? "" : "none"} ${open ? "open" : ""}" data-pexp="${esc(it.id)}" aria-label="${open ? "−" : "+"}"><svg viewBox="0 0 12 12" width="12" height="12" aria-hidden="true"><path d="M4.5 2.5 8 6l-3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
          <button class="chk ${it.done ? "on" : nd ? "part" : ""}" data-pchk="${esc(it.id)}" role="checkbox" aria-checked="${!!it.done}" aria-label="${esc(it.text)}"></button>
          ${editing ? `<input class="dedit" data-pedit="${esc(it.id)}" value="${esc(it.text)}" maxlength="300">` : `<span class="dtext">${esc(it.text)}</span>`}
          ${all.length ? `<span class="dsub">${esc(L("dump_sub", { d: nd, n: all.length }))}</span>` : ""}
          <button class="dmore" data-pmenu="${esc(it.id)}" aria-label="${esc(L("dump_actions"))}" aria-expanded="${sel}">⋯</button></div>
        <div class="dacts ${sel ? "open" : ""}"><div><div class="bar">
          ${depth < 3 ? `<button data-pop="addsub" data-id="${esc(it.id)}">＋ ${esc(L("dump_subitem"))}</button>` : ""}
          <button data-pop="edit" data-id="${esc(it.id)}">✎ ${esc(L("edit"))}</button>
          <button data-pop="up" data-id="${esc(it.id)}" aria-label="${esc(L("dump_up"))}">↑</button>
          <button data-pop="down" data-id="${esc(it.id)}" aria-label="${esc(L("dump_down"))}">↓</button>
          <button data-pop="indent" data-id="${esc(it.id)}" title="${esc(L("dump_indent"))}">⇥</button>
          ${depth > 1 ? `<button data-pop="outdent" data-id="${esc(it.id)}" title="${esc(L("dump_outdent"))}">⇤</button>` : ""}
          <button class="danger" data-pop="delete" data-id="${esc(it.id)}">🗑 ${esc(L("delete"))}</button></div>
          ${this._dumpAddTo === it.id ? `<div class="dsubadd"><input class="psubin" placeholder="${esc(L("dump_ph"))}" maxlength="300"><button class="primary psubok" data-id="${esc(it.id)}">＋</button></div>` : ""}</div></div>
        ${kids.length ? `<div class="dkids ${open ? "open" : ""}"><div>${kids.map((k) => node(k, depth + 1)).join("")}</div></div>` : ""}</div>`;
    };
    const top = filt(dd.items);
    return `<div class="row" style="flex-wrap:wrap;gap:10px"><button class="ghost dback">‹ ${esc(L("tab_today"))}</button><h3 style="margin:0">🧠 ${esc(L("dump"))}</h3>
        <span class="spacer"></span><span class="chip small teal">${esc(L("dump_open_n", { n: pv.open }))}</span><span class="chip small">${esc(L("dump_done_n", { n: pv.done }))}</span>
        <button class="ghost dshowdone ${this._dumpShowDone ? "on" : ""}">${esc(L(this._dumpShowDone ? "dump_hide_done" : "dump_show_done"))}</button></div>
      <div class="dadd" style="margin-top:14px"><input class="pdin" placeholder="${esc(L("dump_ph"))}" maxlength="300" enterkeyhint="done"><button class="primary pdplus" aria-label="${esc(L("add"))}">＋</button></div>
      <div class="hint" style="margin-top:6px">${esc(L("dump_page_hint"))}</div>
      <div class="dtree">${top.length ? top.map((it) => node(it, 1)).join("") : `<div class="hint" style="padding:16px 4px">${esc(L(dd.items.length ? "dump_none_open" : "dump_empty"))}</div>`}</div>`;
  }
  async dumpOp(op, data) {
    try {
      this._dumpData = await this.call("dump_op", Object.assign({ op }, data));
    } catch (e) {
      toast(this.shadowRoot, e && e.code === "too_deep" ? this.t("dump_too_deep") : this.t("error"));
      return;
    }
    this.redrawDump();
  }
  redrawDump(focusSel) {
    const box = this.shadowRoot.querySelector(".dumppage");
    if (!box) return;
    box.classList.remove("rise");
    box.innerHTML = this.dumpPageHtml();
    this.bindDumpPage(box.parentElement);
    if (focusSel) { const el = box.querySelector(focusSel); if (el) { el.focus(); if (el.select && focusSel === ".dedit") el.select(); } }
  }
  bindDumpPage(root) {
    const L = (k) => this.t(k);
    const box = root.querySelector(".dumppage");
    if (!box) return;
    const q = (x) => box.querySelector(x);
    q(".dback").addEventListener("click", () => { this.sub = null; this.render(true); });
    q(".dshowdone").addEventListener("click", () => { this._dumpShowDone = !this._dumpShowDone; lsSet("mh_dump_done", this._dumpShowDone); this.redrawDump(); });
    const addTop = async () => {
      const inp = q(".pdin");
      const texts = inp.value.split(/\n/).map((x) => x.trim()).filter(Boolean);
      if (!texts.length) { shake(inp); return; }
      await this.dumpOp("add", { texts });
      this.redrawDump(".pdin");
    };
    q(".pdplus").addEventListener("click", addTop);
    q(".pdin").addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); addTop(); } });
    q(".pdin").addEventListener("paste", (ev) => {
      const t = (ev.clipboardData || window.clipboardData).getData("text");
      if (t && t.includes("\n")) { ev.preventDefault(); q(".pdin").value = t; addTop(); }
    });
    box.querySelectorAll("[data-pexp]").forEach((b) => b.addEventListener("click", () => {
      const id = b.dataset.pexp;
      this._dumpOpen.has(id) ? this._dumpOpen.delete(id) : this._dumpOpen.add(id);
      lsSet("mh_dump_open", [...this._dumpOpen]);
      b.classList.toggle("open", this._dumpOpen.has(id));
      const kids = b.closest(".dnode").querySelector(":scope > .dkids");
      if (kids) kids.classList.toggle("open", this._dumpOpen.has(id));
    }));
    box.querySelectorAll("[data-pchk]").forEach((b) => b.addEventListener("click", () => {
      const done = !b.classList.contains("on");
      b.classList.toggle("on", done);
      this.dumpOp("toggle", { item_id: b.dataset.pchk, done });
    }));
    box.querySelectorAll("[data-pmenu]").forEach((b) => b.addEventListener("click", () => {
      const id = b.dataset.pmenu;
      this._dumpMenu = this._dumpMenu === id ? null : id;
      this._dumpAddTo = null;
      box.querySelectorAll(".dnode").forEach((n) => {
        const on = n.dataset.node === this._dumpMenu;
        n.classList.toggle("sel", on);
        const a = n.querySelector(":scope > .dacts"); if (a) a.classList.toggle("open", on);
      });
    }));
    box.querySelectorAll("[data-pop]").forEach((b) => b.addEventListener("click", async () => {
      const op = b.dataset.pop, id = b.dataset.id;
      if (op === "addsub") { this._dumpAddTo = id; this._dumpOpen.add(id); lsSet("mh_dump_open", [...this._dumpOpen]); this.redrawDump(".psubin"); return; }
      if (op === "edit") { this._dumpEdit = id; this.redrawDump(".dedit"); return; }
      if (op === "delete") {
        const n = box.querySelector(`.dnode[data-node="${window.CSS.escape(id)}"]`);
        const hasKids = n && n.querySelector(".dkids");
        if (hasKids && !(await this.confirm(L("dump_delete_confirm"), L("delete")))) return;
        if (n && !reduced()) { n.style.transition = "opacity .2s, transform .2s"; n.style.opacity = "0"; n.style.transform = "translateX(10px)"; await new Promise((r) => setTimeout(r, 180)); }
        this._dumpMenu = null;
        return this.dumpOp("delete", { item_id: id });
      }
      this.dumpOp("step", { item_id: id, direction: op });
    }));
    const sub = q(".psubin");
    if (sub) {
      const go = async () => {
        const texts = sub.value.split(/\n/).map((x) => x.trim()).filter(Boolean);
        if (!texts.length) { shake(sub); return; }
        await this.dumpOp("add", { texts, parent_id: this._dumpAddTo });
        this.redrawDump(".psubin");
      };
      sub.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); go(); } if (ev.key === "Escape") { this._dumpAddTo = null; this.redrawDump(); } });
      q(".psubok").addEventListener("click", go);
    }
    const ed = q(".dedit");
    if (ed) {
      const save = async () => { const id = ed.dataset.pedit, text = ed.value.trim(); this._dumpEdit = null; if (text) await this.dumpOp("edit", { item_id: id, text }); else this.redrawDump(); };
      ed.addEventListener("keydown", (ev) => { if (ev.key === "Enter") { ev.preventDefault(); save(); } if (ev.key === "Escape") { this._dumpEdit = null; this.redrawDump(); } });
      ed.addEventListener("blur", () => { if (this._dumpEdit) save(); });
    }
  }

  /* ---------------------------------------------------------- Insights */
  async tab_insights() {
    const L = (k, v) => this.t(k, v), lang = this.lang;
    const d = this._d && this._d.days ? this._d : await this.call("dashboard");
    this._d = d;
    let ins = null;
    try { ins = await this.call("insights"); } catch (e) { if (e && e.code !== "locked") throw e; }
    const range = this.insRange;
    const now = Date.now(), from = range ? now - range * 86400e3 : 0;
    const days = (d.days || []).slice().reverse();
    const inR = days.filter((x) => new Date(x.day + "T12:00") >= from);
    const X = (x) => new Date(x.day + "T12:00").getTime();
    const out = [];
    let i = 0;
    const sec = (html, cls = "") => out.push(`<section class="sec rise ${cls}" style="animation-delay:${Math.min(i++ * 45, 360)}ms">${html}</section>`);
    sec(`<div class="row" style="flex-wrap:wrap"><h3 style="margin:0">✨ ${esc(L("tab_insights"))}</h3><span class="spacer"></span>
      <div class="segs">${[[7, "days7"], [30, "days30"], [90, "days90"], [365, "days365"], [0, "all"]].map(([r, k]) => `<button class="seg ${range === r ? "on" : ""}" data-range="${r}">${esc(L(k))}</button>`).join("")}</div></div>`, "wide");
    // Health ring + Komponenten
    sec(`<h3>💚 ${esc(L("health_score"))}</h3><div class="row" style="gap:18px;flex-wrap:wrap">${ring(d.health.score, 100, 132, "var(--c-teal)", d.health.score ?? "–", "/100", { sw: 11 })}
      <div style="flex:1;min-width:180px"><h4 style="margin-top:0">${esc(L("components"))}</h4>${Object.entries(d.health.comps || {}).map(([k, val]) => `<div class="comp"><span class="sub clabel">${esc(L("c_" + k))}</span><div class="bar"><i style="width:${val}%"></i></div><span class="hint" style="width:28px;text-align:right">${val}</span></div>`).join("")}</div></div>`);
    // Stimmungsverlauf
    const pm = inR.map((x) => ({ x: X(x), y: x.mood_m, tip: `${fmtDate(x.day, lang)} · ${L("morning")} ${x.mood_m ?? "–"}` }));
    const pe = inR.map((x) => ({ x: X(x), y: x.mood_e, tip: `${fmtDate(x.day, lang)} · ${L("evening")} ${x.mood_e ?? "–"}` }));
    const fh = (d.forecast_history || []).filter((h) => new Date(h.day + "T12:00") >= from);
    sec(`<h3>📈 ${esc(L("mood"))}</h3>${inR.length ? lineChart([
      { points: smooth(pm, 3), color: "#f5b14c" }, { points: pm, color: "#f5b14c", dots: true, r: 3, opacity: 0 },
      { points: smooth(pe, 3), color: "#2fd6b0", area: true }, { points: pe, color: "#2fd6b0", dots: true, r: 3, opacity: 0 },
      { points: fh.filter((h) => h.p != null).map((h) => ({ x: new Date(h.day + "T12:00").getTime(), y: h.p })), color: "#a78bfa", dash: "4 5" }],
      { h: 200, ph: 200, y0: 1, y1: 10, yticks: [1, 4, 7, 10], x0: range ? from : undefined, x1: now }) : `<div class="hint">${esc(L("first_days"))}</div>`}
      <div class="row hint" style="gap:14px;margin-top:6px;flex-wrap:wrap"><span><b style="color:#f5b14c">━</b> ${esc(L("morning"))}</span><span><b style="color:#2fd6b0">━</b> ${esc(L("evening"))}</span><span><b style="color:#a78bfa">┅</b> ${esc(L("forecast_vs"))}</span></div>`, "wide");
    // Year in Pixels
    const map = {};
    for (const x of days) map[x.day] = x;
    let px = "";
    const start = new Date(); start.setDate(start.getDate() - 364); start.setDate(start.getDate() - ((start.getDay() + 6) % 7));
    for (let k = 0; k < 371; k++) {
      const dt = new Date(start); dt.setDate(start.getDate() + k);
      if (dt > new Date()) break;
      const key = dt.toISOString().slice(0, 10), r = map[key];
      px += `<i style="${r && r.mood != null ? `background:${moodColor(r.mood)}` : ""}" data-tip="${esc(fmtDate(key, lang))}${r && r.mood != null ? " · " + fmtNum(r.mood, 1, lang) : ""}"></i>`;
    }
    sec(`<h3>🟩 ${esc(L("year_pixels"))}</h3><div class="pixels">${px}</div>`, "wide");
    // Wochentage + Verteilung + Morgen/Abend
    const wd = [[], [], [], [], [], [], []];
    for (const x of inR) if (x.mood != null) wd[(new Date(x.day + "T12:00").getDay() + 6) % 7].push(x.mood);
    const wdn = L("weekdays").split(",");
    const avg = (a) => (a.length ? a.reduce((s, v) => s + v, 0) / a.length : null);
    sec(`<h3>📅 ${esc(L("weekday_pattern"))}</h3><div class="bars">${wd.map((a, k) => { const m = avg(a); return `<div style="flex:1"><div class="b" style="height:${m == null ? 3 : (m / 10) * 100}%;background:${moodColor(m)}" data-tip="${esc(wdn[k])} · ${m == null ? "–" : fmtNum(m, 1, lang)}"></div><div class="lb">${esc(wdn[k])}</div></div>`; }).join("")}</div>`);
    const dist = Array(10).fill(0);
    for (const x of inR) if (x.mood != null) dist[clamp(Math.round(x.mood), 1, 10) - 1]++;
    const dmax = Math.max(1, ...dist);
    const deltas = inR.filter((x) => x.mood_m != null && x.mood_e != null).map((x) => x.mood_e - x.mood_m);
    sec(`<h3>📊 ${esc(L("distribution"))}</h3><div class="bars" style="height:80px">${dist.map((n, k) => `<div style="flex:1"><div class="b" style="height:${(n / dmax) * 100}%;background:${moodColor(k + 1)}" data-tip="${k + 1}: ${n}"></div><div class="lb">${k + 1}</div></div>`).join("")}</div>
      <h4>${esc(L("me_delta"))}</h4><div class="big" style="font-size:26px">${deltas.length ? sign(avg(deltas), 1, lang) : "–"}</div>`);
    // Energie/Gesundheit
    const pen = inR.map((x) => ({ x: X(x), y: x.energy })), phe = inR.map((x) => ({ x: X(x), y: x.health }));
    sec(`<h3>⚡ ${esc(L("energy"))} · ${esc(L("c_health"))}</h3>${lineChart([{ points: smooth(pen, 3), color: "#f5b14c" }, { points: smooth(phe, 3), color: "#60a5fa" }], { w: 320, h: 130, ph: 130, y0: 1, y1: 10, yticks: [1, 5.5, 10], x0: range ? from : undefined, x1: now, empty: L("no_data") })}`);
    // Schlaf
    if (d.sleep && d.sleep.enabled) {
      const nights = (d.sleep.nights || []).slice(0, 14);
      const opt = d.sleep.optimum_h, rng = d.sleep.range || [7, 9];
      const sd = inR.filter((x) => x.sleep_h != null).map((x) => ({ x: X(x), y: x.sleep_h, tip: `${fmtDate(x.day, lang)} · ${fmtNum(x.sleep_h, 1, lang)} h` }));
      const ss = inR.filter((x) => x.sleep_score != null).map((x) => ({ x: X(x), y: x.sleep_score }));
      sec(`<h3>🌙 ${esc(L("sleep_nights"))}</h3>${nights.length ? nights.map((n) => `<div class="row" style="gap:8px;margin:5px 0"><span class="hint" style="width:62px">${esc(fmtDate(n.day, lang, { weekday: "short", day: "numeric" }))}</span><div style="flex:1">${nightRow(n, lang)}</div><span class="hint" style="width:44px;text-align:right">${n.score ?? ""}</span></div>`).join("")
        + `<div class="row" style="gap:8px"><span style="width:62px"></span><div class="timeaxis" style="flex:1"><span>18</span><span>22</span><span>02</span><span>06</span><span>10</span><span>14</span></div><span style="width:44px"></span></div>` : `<div class="hint">${esc(L("no_sleep"))}</div>`}`, "wide");
      sec(`<h3>⏱️ ${esc(L("duration_vs_opt"))}</h3>${lineChart([{ points: sd, color: "#a78bfa", dots: true, hband: rng }, { points: sd.length ? [{ x: sd[0].x, y: opt }, { x: sd[sd.length - 1].x, y: opt }] : [], color: "#2fd6b0", dash: "3 4" }], { w: 320, h: 140, ph: 140, y0: 4, y1: 11, yticks: [4, 6, 8, 10], empty: L("no_data") })}
        <h4>${esc(L("score_trend"))}</h4>${lineChart([{ points: smooth(ss, 3), color: "#a78bfa", area: true }], { w: 320, h: 90, ph: 90, y0: 0, y1: 100, yticks: [0, 50, 100], empty: L("no_data") })}`);
      // Zusammenhang Schlaf ↔ Stimmung (Streudiagramm)
      const pairs = days.filter((x) => x.sleep_h != null && x.mood != null).map((x) => ({ x: x.sleep_h, y: x.mood, tip: `${fmtNum(x.sleep_h, 1, lang)} h → ${fmtNum(x.mood, 1, lang)}` }));
      sec(`<h3>🔗 ${esc(L("sleep_mood"))}</h3>${pairs.length > 3 ? lineChart([{ points: pairs.sort((a, b) => a.x - b.x), color: "#2fd6b0", dots: true, r: 3.5, opacity: 0 }], { w: 320, h: 150, ph: 150, y0: 1, y1: 10, x0: 4, x1: 11, yticks: [1, 5.5, 10], xlabels: [[5, "5 h"], [7, "7 h"], [9, "9 h"], [11, "11 h"]] }) : `<div class="hint">${esc(L("no_data"))}</div>`}`);
    }
    // Training ↔ Energie
    if (d.training) {
      const after = [], other = [];
      for (let k = 1; k < days.length; k++) { const prev = days[k - 1], cur = days[k]; if (cur.energy == null || prev.trained == null) continue; (prev.trained ? after : other).push(cur.energy); }
      const a = avg(after), o = avg(other);
      sec(`<h3>🔗 ${esc(L("training_energy"))}</h3><div class="bars" style="height:90px"><div style="flex:1"><div class="b" style="height:${a == null ? 3 : a * 10}%;background:var(--c-teal)"></div><div class="lb">💪 ${a == null ? "–" : fmtNum(a, 1, lang)}</div></div>
        <div style="flex:1"><div class="b" style="height:${o == null ? 3 : o * 10}%;background:var(--c-raise2)"></div><div class="lb">😌 ${o == null ? "–" : fmtNum(o, 1, lang)}</div></div></div>`);
    }
    // Gewicht
    if (d.weight && !d.weight.child && (d.weights || []).length > 1) {
      const pts = d.weights.filter((w) => new Date(w.day + "T12:00") >= from).map((w) => ({ x: new Date(w.day + "T12:00").getTime(), y: w.kg, tip: fmtNum(w.kg, 1, lang) + " kg" }));
      let t = null; const trend = pts.map((p) => { t = t == null ? p.y : t + 0.18 * (p.y - t); return { x: p.x, y: t }; });
      const ys = pts.map((p) => p.y).concat(d.weight.range || []);
      if (pts.length > 1) sec(`<h3>⚖️ ${esc(L("weight"))}</h3>${lineChart([{ points: pts, color: "#22d3ee", dots: true, r: 2.5, opacity: 0.4, hband: d.weight.range }, { points: trend, color: "#22d3ee" }], { w: 320, h: 150, ph: 150, y0: Math.floor(Math.min(...ys) - 1), y1: Math.ceil(Math.max(...ys) + 1) })}`);
    }
    // Text-Insights
    if (ins) {
      const der = ins.derived || {};
      const insights = (der.insights || []).map((x) => {
        const p = Object.assign({}, x.params || {});
        if (x.key === "i_best_days") p.items = (p.items || []).map((it) => it.topic ? `„${L("tp_" + it.topic)}“` : `„${it.word}“`).join(this.lang === "de" ? " und " : " and ");
        if (x.key === "i_weekday") { p.best = wdn[p.best]; p.worst = wdn[p.worst]; p.diff = fmtNum(p.diff, 1, lang); }
        if (p.diff != null && typeof p.diff === "number") p.diff = fmtNum(p.diff, 1, lang);
        if (p.hours != null) p.hours = fmtNum(p.hours, 1, lang);
        return `<div class="tile" style="margin-bottom:8px">${x.tone === "good" ? "🌱" : "💡"} ${esc(L(x.key, p))}</div>`;
      });
      if (insights.length) sec(`<h3>💡 ${esc(L("tab_insights"))}</h3>${insights.join("")}`, "wide");
      const tp = der.topics || {};
      sec(`<h3>🌱 ${esc(L("good_for_you"))}</h3>${(tp.good || []).length ? tp.good.map((t2) => `<span class="chip good" style="margin:3px">${esc(L("tp_" + t2.topic))} ${sign(t2.effect, 1, lang)}</span>`).join("") : `<div class="hint">${esc(L("no_data"))}</div>`}
        <h4>🌧️ ${esc(L("drags_down"))}</h4>${(tp.bad || []).length ? tp.bad.map((t2) => `<span class="chip bad" style="margin:3px">${esc(L("tp_" + t2.topic))} ${sign(t2.effect, 1, lang)}</span>`).join("") : `<div class="hint">${esc(L("no_data"))}</div>`}`);
      if ((der.goals || []).length) sec(`<h3>🎯 ${esc(L("goals_tracker"))}</h3>${der.goals.slice(0, 8).map((g) => `<div class="comp"><span style="flex:1" class="sub">${esc(g.text)}${g.recurring ? " 🔁" : ""}</span><div class="bar" style="flex:0 0 90px"><i style="width:${Math.round(g.rate * 100)}%"></i></div><span class="hint">${g.done}/${g.n}</span></div>`).join("")}`);
      for (const [key, rep] of [["week_report", ins.week], ["month_report", ins.month]]) {
        if (!rep) continue;
        const c = rep.cur || {};
        sec(`<h3>🗒️ ${esc(L(key))}</h3><div class="grid2">
          <div class="tile"><div class="k">${esc(L("mood"))}</div><div class="v">${c.mood == null ? "–" : fmtNum(c.mood, 1, lang)}</div>${rep.delta && rep.delta.mood != null ? `<span class="chip small ${rep.delta.mood >= 0 ? "good" : "bad"}">${sign(rep.delta.mood, 1, lang)} ${esc(L("vs_prev"))}</span>` : ""}</div>
          <div class="tile"><div class="k">${esc(L("sleep"))}</div><div class="v">${c.sleep_h == null ? "–" : fmtNum(c.sleep_h, 1, lang) + " h"}</div></div>
          <div class="tile"><div class="k">💪</div><div class="v">${c.trainings || 0}</div><div class="hint">${esc(L("trainings"))}</div></div>
          <div class="tile"><div class="k">🌱</div><div class="v">${c.good_count || 0}</div><div class="hint">${esc(L("good_things"))}</div></div></div>
          ${(c.highlights || []).length ? `<div style="margin-top:10px">${c.highlights.slice(0, 3).map((h) => `<div class="sub">✨ ${esc(h)}</div>`).join("")}</div>` : ""}`);
      }
    } else {
      sec(`<div class="hint">🔒 ${esc(L("insights_locked"))}</div>`, "wide");
    }
    // LLM
    if (this._me.llm && this._me.llm.enabled) {
      sec(`<h3>🤖 ${esc(L("llm_summary"))}</h3>${this._me.modules.llm ? `<button class="llmrun">${esc(L("llm_run"))}</button><div class="llmout journal"></div>` : `<div class="hint">${esc(L("llm_off"))}</div>`}`, "wide");
    }
    this._bind = (root) => {
      root.querySelectorAll("[data-range]").forEach((b) => b.addEventListener("click", () => { this.insRange = parseInt(b.dataset.range, 10); lsSet("mh_irange", this.insRange); this.render(true); }));
      root.querySelectorAll(".pixels i, .bars .b").forEach((el) => el.addEventListener("click", () => { if (el.dataset.tip) toast(this.shadowRoot, el.dataset.tip); }));
      const lr = root.querySelector(".llmrun");
      if (lr) lr.addEventListener("click", async () => {
        lr.disabled = true; const o = root.querySelector(".llmout"); o.innerHTML = `<div class="spinner"></div>`;
        try { const r = await this.call("llm", { action: "summary", days: Math.min(31, range || 31) }); o.textContent = r.ok ? r.text : L("error") + " (" + r.error + ")"; } catch (e) { o.textContent = L("error"); }
        lr.disabled = false;
      });
    };
    return out.join("");
  }

  /* ---------------------------------------------------------- Verlauf */
  async tab_history() {
    const L = (k, v) => this.t(k, v), lang = this.lang;
    const d = this._d && this._d.days ? this._d : await this.call("dashboard");
    this._d = d;
    const h = this.hist;
    if (!h.month) { const n = new Date(); h.month = new Date(n.getFullYear(), n.getMonth(), 1); }
    if (!h.sel) h.sel = d.today;
    const map = {};
    for (const x of d.days || []) map[x.day] = x;
    const out = [];
    const quick = [["polarity", "positive", "flt_positive"], ["polarity", "neutral", "flt_neutral"], ["polarity", "negative", "flt_negative"], ["journal", true, "flt_journal"],
      ["goals", true, "flt_goals"], ["trained", true, "flt_training"], ["period", true, "flt_period"], ["slot", "morning", "flt_morning"], ["slot", "evening", "flt_evening"]];
    const chips = h.chips || [];
    const has = (k, v) => chips.some((c) => c.k === k && c.v === v);
    out.push(`<section class="sec wide rise"><div class="search"><input class="q" placeholder="${esc(L("search_ph"))}" value="${esc(h.query)}">
      ${this._me.llm && this._me.llm.enabled && this._me.modules.llm ? `<button class="llm ${h.llm ? "on" : ""}" title="LLM">${esc(L("search_llm"))}</button>` : ""}<button class="primary go">🔍</button></div>
      <div class="choices" style="margin-top:10px">${quick.map(([k, v, lab]) => `<button class="chip ${has(k, v) ? "on" : ""}" data-qk="${k}" data-qv="${v}">${esc(L(lab))}</button>`).join("")}</div>
      ${chips.length ? `<div class="choices" style="margin-top:8px">${chips.map((c, k) => `<button class="chip teal small" data-rm="${k}">${esc(this.chipLabel(c))} ✕</button>`).join("")}</div>` : ""}</section>`);
    if (h.results) {
      const groups = {};
      for (const r of h.results) { const key = r.day.slice(0, 7); (groups[key] = groups[key] || []).push(r); }
      const hl = (txt, hits) => {
        let s = esc(txt || "");
        for (const st of hits || []) if (st.length >= 3) s = s.replace(new RegExp(`(${st.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}[\\wäöüß]*)`, "gi"), "<mark>$1</mark>");
        return s;
      };
      out.push(`<section class="sec wide rise"><h3>🔎 ${esc(L("results", { n: h.results.length }))}${h.llmUsed ? ` <span class="chip small teal">${esc(L("search_llm"))}</span>` : ""}</h3>
        ${h.results.length ? Object.entries(groups).map(([m, rs]) => `<h4>${esc(new Date(m + "-15").toLocaleDateString(lang === "de" ? "de-DE" : "en-GB", { month: "long", year: "numeric" }))}</h4>
        ${rs.map((r) => `<div class="res" data-day="${r.day}"><div class="row"><span class="emoji" style="font-size:22px">${moodEmoji(r.mood)}</span><b>${esc(fmtDate(r.day, lang))}</b><span class="spacer"></span>
          ${r.trained ? "<span>💪</span>" : ""}${r.period ? "<span>🩸</span>" : ""}${r.sleep_h ? `<span class="hint">${fmtNum(r.sleep_h, 1, lang)} h</span>` : ""}</div>
          ${(r.good || []).length ? `<div class="sub" style="margin-top:4px">🌱 ${r.good.map((g) => hl(g, r.hits)).join(" · ")}</div>` : ""}
          ${(r.bad || []).length ? `<div class="sub">🌧️ ${r.bad.map((g) => hl(g, r.hits)).join(" · ")}</div>` : ""}
          ${r.journal ? `<div class="sub" style="margin-top:4px">📝 ${hl(r.journal, r.hits)}${r.journal.length >= 280 ? "…" : ""}</div>` : ""}</div>`).join("")}`).join("") : `<div class="hint">${esc(L("no_results"))}</div>`}</section>`);
    }
    // Kalender
    const m0 = h.month, y = m0.getFullYear(), mo = m0.getMonth();
    const first = (new Date(y, mo, 1).getDay() + 6) % 7, dim = new Date(y, mo + 1, 0).getDate();
    let cal = L("weekdays").split(",").map((w) => `<div class="wd">${esc(w)}</div>`).join("");
    for (let k = 0; k < first; k++) cal += `<div></div>`;
    for (let k = 1; k <= dim; k++) {
      const key = `${y}-${String(mo + 1).padStart(2, "0")}-${String(k).padStart(2, "0")}`, r = map[key];
      cal += `<button class="d ${key === d.today ? "today" : ""} ${key === h.sel ? "sel" : ""}" data-day="${key}" style="${r && r.mood != null ? `background:${moodColor(r.mood)};color:#0b0c0e;font-weight:600` : ""}">${k}${r && r.journal ? "<span style='position:absolute;top:4px;right:6px;font-size:8px'>●</span>" : ""}</button>`;
    }
    out.push(`<section class="sec rise"><div class="row"><button class="ghost pm">‹</button><b style="flex:1;text-align:center">${esc(m0.toLocaleDateString(lang === "de" ? "de-DE" : "en-GB", { month: "long", year: "numeric" }))}</b><button class="ghost nm">›</button></div>
      <div class="cal" style="margin-top:10px">${cal}</div></section>`);
    // Tagesdetail
    out.push(`<section class="sec rise dayd" style="animation-delay:60ms"><div class="center"><div class="spinner"></div></div></section>`);
    this._bind = (root) => this.bindHistory(root, map);
    return out.join("");
  }
  chipLabel(c) {
    const L = (k, v) => this.t(k, v), lang = this.lang;
    if (c.k === "range") return L("chip_range", { a: c.start ? fmtDate(c.start, lang) : "…", b: c.end ? fmtDate(c.end, lang) : "…" });
    if (c.k === "months") return c.v.map((m) => new Date(2026, m - 1, 15).toLocaleDateString(lang === "de" ? "de-DE" : "en-GB", { month: "short" })).join(", ");
    if (c.k === "polarity") return L("flt_" + c.v);
    if (c.k === "sleep") return L(c.v === "short" ? "ch_sleep_short" : "ch_sleep_long");
    if (c.k === "slot") return L("ch_" + c.v);
    if (c.k === "weekend") return L(c.v ? "ch_weekend" : "ch_weekdays");
    if (c.k === "term") return `„${c.v}“`;
    if (c.k === "trained") return (c.v ? "" : "¬ ") + L("ch_trained");
    return L("ch_" + c.k);
  }
  bindHistory(root, map) {
    const h = this.hist;
    const runSearch = async () => {
      h.query = root.querySelector(".q").value.trim();
      const payload = h.chips && !h.query ? { chips: h.chips } : { query: h.query, llm: !!h.llm };
      if (h.chips && h.query) { payload.query = h.query; delete payload.chips; }
      if (!h.query && !(h.chips || []).length) { h.results = null; return this.render(true); }
      const r = await this.call("search", payload);
      h.results = r.results; h.chips = r.chips; h.llmUsed = r.llm;
      this.render(true);
    };
    root.querySelector(".go").addEventListener("click", runSearch);
    root.querySelector(".q").addEventListener("keydown", (ev) => { if (ev.key === "Enter") runSearch(); });
    const lb = root.querySelector(".llm");
    if (lb) lb.addEventListener("click", () => { h.llm = !h.llm; lb.classList.toggle("on", h.llm); });
    root.querySelectorAll("[data-qk]").forEach((b) => b.addEventListener("click", async () => {
      const k = b.dataset.qk; let v = b.dataset.qv; v = v === "true" ? true : v;
      const chips = (h.chips || []).filter((c) => !(c.k === k));
      if (!(h.chips || []).some((c) => c.k === k && c.v === v)) chips.push({ k, v });
      h.chips = chips; h.query = "";
      if (!chips.length) { h.results = null; return this.render(true); }
      const r = await this.call("search", { chips });
      h.results = r.results; h.chips = r.chips;
      this.render(true);
    }));
    root.querySelectorAll("[data-rm]").forEach((b) => b.addEventListener("click", async () => {
      const chips = (h.chips || []).slice(); chips.splice(parseInt(b.dataset.rm, 10), 1);
      h.chips = chips; h.query = "";
      if (!chips.length) { h.results = null; return this.render(true); }
      const r = await this.call("search", { chips }); h.results = r.results; h.chips = r.chips; this.render(true);
    }));
    root.querySelector(".pm").addEventListener("click", () => { h.month = new Date(h.month.getFullYear(), h.month.getMonth() - 1, 1); this.render(true); });
    root.querySelector(".nm").addEventListener("click", () => { h.month = new Date(h.month.getFullYear(), h.month.getMonth() + 1, 1); this.render(true); });
    root.querySelectorAll(".cal .d, .res").forEach((b) => b.addEventListener("click", () => {
      h.sel = b.dataset.day; const dd = new Date(h.sel + "T12:00"); h.month = new Date(dd.getFullYear(), dd.getMonth(), 1); this.render(true);
    }));
    this.loadDay(root.querySelector(".dayd"));
  }
  async loadDay(box) {
    const L = (k, v) => this.t(k, v), lang = this.lang, h = this.hist;
    let r;
    try { r = await this.call("day", { day: h.sel }); } catch (e) { box.innerHTML = `<div class="hint">${esc(L("error"))}</div>`; return; }
    const shift = (n) => { const dd = new Date(h.sel + "T12:00"); dd.setDate(dd.getDate() + n); h.sel = dd.toISOString().slice(0, 10); h.month = new Date(dd.getFullYear(), dd.getMonth(), 1); this.render(true); };
    const e = r.entries || {};
    const ent = (slot) => {
      const x = e[slot] || {};
      if (!Object.keys(x).length) return "";
      const edited = (r.edits || {})[slot];
      return `<div class="entry"><div class="row"><b>${esc(L(slot))}</b>${x.mood != null ? `<span class="emoji" style="font-size:20px">${moodEmoji(x.mood)}</span><span>${x.mood}/10</span>` : ""}<span class="spacer"></span>
        ${edited && edited.length ? `<span class="hint">${esc(L("edited"))}</span>` : ""}<button class="ghost" data-edit="${slot}">✎</button><button class="ghost danger" data-del="${slot}">🗑</button></div>
        <div class="sub">${["energy", "health", "sleep_quality"].filter((k) => x[k] != null).map((k) => `${esc(L(k === "health" ? "c_health" : k))}: ${x[k]}`).join(" · ")}${x.soreness != null ? ` · ${esc(L("f_soreness"))}: ${x.soreness}` : ""}${x.trained ? ` · 💪 ${x.trained.done ? "✓" : "✗"}` : ""}</div></div>`;
    };
    const texts = `${(r.good || []).length ? `<div class="entry"><b>🌱 ${esc(L("f_good"))}</b><ul>${r.good.map((g) => `<li>${esc(g)}</li>`).join("")}</ul></div>` : ""}
      ${(r.bad || []).length ? `<div class="entry"><b>🌧️ ${esc(L("f_bad"))}</b><ul>${r.bad.map((g) => `<li>${esc(g)}</li>`).join("")}</ul></div>` : ""}
      ${(r.goals || []).length ? `<div class="entry"><b>🎯 ${esc(L("f_goals"))}</b><ul>${r.goals.map((g) => `<li>${esc(g)}</li>`).join("")}</ul></div>` : ""}
      ${r.journal ? `<div class="entry"><b>📝 ${esc(L("f_journal"))}</b><div class="journal">${esc(r.journal)}</div></div>` : ""}`;
    box.innerHTML = `<div class="daynav"><button class="ghost prev">‹</button><b style="flex:1;text-align:center">${esc(fmtDate(h.sel, lang, { weekday: "long", day: "numeric", month: "long" }))}</b><button class="ghost next">›</button></div>
      ${r.sleep ? `<div class="entry"><b>🌙 ${fmtDur(r.sleep.asleep)}</b> <span class="hint">${fmtTime(r.sleep.start, lang)} – ${fmtTime(r.sleep.end, lang)} · ${r.sleep.score ?? ""}</span><div style="margin-top:8px">${nightRow(r.sleep, lang)}</div></div>` : ""}
      ${ent("morning")}${ent("evening")}${texts}
      ${!e.morning || !Object.keys(e.morning).length || !e.evening || !Object.keys(e.evening).length ? `<div class="row" style="margin-top:12px;gap:8px;flex-wrap:wrap">${!r.mood_m ? `<button data-add="morning">＋ ${esc(L("morning"))}</button>` : ""}${!r.mood_e ? `<button data-add="evening">＋ ${esc(L("evening"))}</button>` : ""}</div>` : ""}
      ${!r.slots || !r.slots.length ? `<div class="hint" style="margin-top:10px">${esc(L("day_empty"))}</div>` : ""}`;
    box.querySelector(".prev").addEventListener("click", () => shift(-1));
    box.querySelector(".next").addEventListener("click", () => shift(1));
    // Wischen
    let sx = null;
    box.addEventListener("touchstart", (ev) => { sx = ev.touches[0].clientX; }, { passive: true });
    box.addEventListener("touchend", (ev) => { if (sx == null) return; const dx = ev.changedTouches[0].clientX - sx; if (Math.abs(dx) > 60) shift(dx < 0 ? 1 : -1); sx = null; });
    box.querySelectorAll("[data-edit],[data-add]").forEach((b) => b.addEventListener("click", () => this.openCheckin(b.dataset.edit || b.dataset.add, h.sel)));
    box.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", async () => {
      if (!(await this.confirm(L("delete_confirm")))) return;
      await this.call("delete_entry", { day: h.sel, slot: b.dataset.del });
      this._d = null; toast(this.shadowRoot, L("saved")); this.render(true);
    }));
  }
  confirm(text, okLabel) {
    const L = (k) => this.t(k);
    return new Promise((resolve) => {
      const s = document.createElement("div");
      s.className = "scrim";
      s.innerHTML = `<div class="dialog"><div style="line-height:1.55">${esc(text)}</div><div class="row" style="margin-top:18px;justify-content:flex-end"><button class="ghost no">${esc(L("cancel"))}</button><button class="primary yes">${esc(okLabel || L("ok"))}</button></div></div>`;
      this.shadowRoot.appendChild(s);
      s.querySelector(".no").addEventListener("click", () => { s.remove(); resolve(false); });
      s.querySelector(".yes").addEventListener("click", () => { s.remove(); resolve(true); });
    });
  }

  /* ---------------------------------------------------------- Familie */
  async tab_family() {
    const L = (k, v) => this.t(k, v), lang = this.lang;
    const f = await this.call("family");
    const pts = (f.history || []).map((h) => ({ x: new Date(h.day + "T12:00").getTime(), y: h.mood, tip: `${fmtDate(h.day, lang)} · ${fmtNum(h.mood, 1, lang)}` }));
    return `<section class="sec wide rise"><div class="row" style="flex-wrap:wrap;gap:18px">
      ${f.enough ? `<span style="font-size:72px;display:inline-block;animation:mh-breathe 4s ease-in-out infinite">${M.WEATHER[f.weather] || "⛅"}</span>
        <div><div class="title" style="font-size:24px">${esc(L("weather_" + f.weather))}</div><div class="sub">${esc(L("mood"))} ${fmtNum(f.mood, 1, lang)} · ${esc(L("members", { n: f.members }))}</div></div>`
        : `<div class="hint">${esc(L("family_not_enough", { k: f.k }))}</div>`}
      <span class="spacer"></span>${f.health != null ? ring(f.health, 100, 112, "var(--c-teal)", f.health, L("health_score")) : ""}
      ${f.participation != null ? ring(f.participation, 100, 112, "var(--c-amber)", f.participation + " %", L("participation")) : ""}</div></section>
      <section class="sec wide rise" style="animation-delay:60ms"><h3>📈 ${esc(L("family_hist"))}</h3>${pts.length ? lineChart([{ points: pts, color: "#2fd6b0", area: true, dots: true, r: 2.5 }], { h: 170, ph: 170, y0: 1, y1: 10, yticks: [1, 5.5, 10] }) : `<div class="hint">${esc(L("family_not_enough", { k: f.k }))}</div>`}</section>
      <section class="sec rise" style="animation-delay:120ms"><h3>🎂 ${esc(L("birthdays"))}</h3>${(f.birthdays || []).length ? f.birthdays.map((b) => `<div class="row" style="margin:8px 0"><span>${b.days === 0 ? "🎉" : "🎈"}</span><span>${esc(b.days === 0 ? L("bd_today", { name: b.name }) : b.days === 1 ? L("bd_tomorrow", { name: b.name }) : L("bd_in", { name: b.name, n: b.days }))}</span>${b.turning ? `<span class="hint">· ${esc(L("turning", { n: b.turning }))}</span>` : ""}</div>`).join("") : `<div class="hint">${esc(L("no_data"))}</div>`}</section>`;
  }

  /* ---------------------------------------------------------- Profil (eigenes oder als Admin) */
  async tab_profile() {
    const pv = await this.call("profile", {});
    return this.profileHtml(pv, false);
  }
  why(r) { return r && !r.ok ? this.t("why_" + r.why) : ""; }
  profileHtml(pv, admin) {
    const L = (k, v) => this.t(k, v), lang = this.lang, p = pv.profile, R = pv.rights;
    const can = (a) => R[a] && R[a].ok;
    const lockedNote = (a) => (can(a) ? "" : `<div class="why hint">🔒 ${esc(this.why(R[a]))}</div>`);
    const dis = (a) => (can(a) ? "" : "disabled");
    const out = [];
    let i = 0;
    const sec = (html, cls = "") => out.push(`<section class="sec rise ${cls}" style="animation-delay:${Math.min(i++ * 40, 320)}ms">${html}</section>`);
    // Grunddaten
    sec(`<h3>👤 ${esc(L("p_basics"))}</h3>${lockedNote("profile_edit")}
      <div class="${can("profile_edit") ? "" : "locked-field"}">
      <div class="field"><label class="lbl">${esc(L("p_name"))}</label><input data-p="name" value="${esc(p.name)}" ${dis("profile_edit")}></div>
      <div class="grid2"><div class="field" style="grid-column:1 / -1"><label class="lbl">${esc(L("p_birthdate"))}</label>${dateMaskHtml("birthdate", p.birthdate, lang, { noYear: true, clear: true, disabled: !can("profile_edit") })}<div class="hint" style="margin-top:6px">${esc(L("p_birth_noyear"))}</div></div>
      <div class="field"><label class="lbl">${esc(L("p_sex"))}</label><select data-p="sex" ${dis("profile_edit")}>${["female", "male", "other", "unspecified"].map((s) => `<option value="${s}" ${p.sex === s ? "selected" : ""}>${esc(L("sex_" + s))}</option>`).join("")}</select></div>
      <div class="field"><label class="lbl">${esc(L("p_height"))}</label><input type="number" data-p="height_cm" value="${p.height_cm ?? ""}" ${dis("profile_edit")}></div>
      <div class="field"><label class="lbl">${esc(L("p_weight"))}</label>${pv.weight_hidden ? `<div class="hint">🔒 ${esc(L("p_weight_hidden", { name: p.name }))}</div>` : `<input type="number" step="0.1" data-p="weight_kg" value="${p.weight_kg ?? ""}" ${can("weight_edit") ? "" : "disabled"}>`}</div></div>
      ${p.modules.weight ? `<div class="kv"><div>${esc(L("p_weight_live"))}<div class="why">${esc(L("p_weight_live_hint"))}</div></div><button class="toggle ${p.weight_live ? "on" : ""}" data-pt="weight_live" ${dis("profile_edit")}></button></div>
        ${p.weight_live ? `<div class="field" style="margin-top:10px"><label class="lbl">${esc(L("p_weight_entity"))}</label><input data-p="weight_entity" list="mh-sensors" value="${esc(p.weight_entity || "")}" ${dis("profile_edit")}><div class="hint">${esc(L("p_weight_entity_hint"))}</div></div>` : ""}
        <div class="field" style="margin-top:10px"><label class="lbl">${esc(L("p_target"))}</label><input type="number" step="0.1" data-p="target_weight" value="${p.target_weight ?? ""}" ${dis("target_weight_edit")}><div class="hint">${esc(L("p_target_hint"))}</div></div>` : ""}
      </div>${admin ? `<h4>${esc(L("a_status"))}</h4>
        <div class="kv"><div>${esc(L("a_child"))}<div class="why">${esc(L("a_child_hint"))}</div></div><button class="toggle ${p.child ? "on" : ""}" data-pt="child"></button></div>
        ${!p.child ? `<div class="kv"><div>${esc(L("a_can_edit"))}</div><button class="toggle ${p.can_edit_own ? "on" : ""}" data-pt="can_edit_own"></button></div>` : `
        <div class="kv"><div>${esc(L("a_cycle_child"))}</div><button class="toggle ${p.cycle_child_allowed ? "on" : ""}" data-pt="cycle_child_allowed"></button></div>
        <div class="kv"><div>${esc(L("a_llm_child"))}</div><button class="toggle ${p.llm_child_allowed ? "on" : ""}" data-pt="llm_child_allowed"></button></div>`}` : ""}`);
    // Module
    sec(`<h3>🧩 ${esc(L("p_modules"))}</h3>${lockedNote("modules_edit")}${MODULE_KEYS.map((m) => {
      const locked = m === "mood", cycleNo = m === "cycle" && !["female", "other"].includes(p.sex);
      const llmNo = m === "llm" && p.child && !p.llm_child_allowed;
      return `<div class="kv ${can("modules_edit") ? "" : "locked-field"}"><div>${esc(L(m === "training" && p.child ? "m_training_child" : "m_" + m))}${locked ? `<div class="why">${esc(L("m_core"))}</div>` : cycleNo ? `<div class="why">${esc(L("m_cycle_hint"))}</div>` : llmNo ? `<div class="why">${esc(L("llm_blocked"))}</div>` : ""}</div>
        <button class="toggle ${p.modules[m] ? "on" : ""}" data-mod="${m}" ${locked || cycleNo || llmNo || !can("modules_edit") ? "disabled" : ""}></button></div>`;
    }).join("")}`);
    // Zeiten + Pause
    sec(`<h3>⏰ ${esc(L("p_times"))}</h3>${lockedNote("schedule_edit")}${["morning", "evening"].map((x) => this.slotHtml(pv, x)).join("")}
      <h4 class="pause-h">⏸️ ${esc(L("p_pause"))}</h4>${p.pause ? `<div class="row"><span class="chip amber">${esc(p.pause.until ? L("paused_until", { d: fmtDate(p.pause.until, lang) }) : L("paused"))}</span><span class="spacer"></span><button class="pauseoff" ${dis("pause")}>${esc(L("pause_off"))}</button></div>`
        : `<label class="lbl">${esc(L("pause_until"))}</label>${dateMaskHtml("pause_until", null, lang, { clear: true, disabled: !can("pause") })}
          <div class="row" style="margin-top:12px;justify-content:flex-end"><button class="pauseon" ${dis("pause")}>${esc(L("pause_on"))}</button></div>`}`);
    // Benachrichtigungen
    const nt = p.notify;
    sec(`<h3>🔔 ${esc(L("p_notify"))}</h3>${lockedNote("schedule_edit")}
      <h4>${esc(L("n_targets"))}</h4>${(p.targets || []).map((t, k) => `<div class="kv"><div>${esc(t.name || t.service || t.entity)}<div class="why">${esc(t.kind === "service" ? (pv.platforms[t.id] || "") : t.kind)}</div></div><button class="ghost danger" data-trm="${k}" ${dis("schedule_edit")}>✕</button></div>`).join("") || `<div class="hint">–</div>`}
      <div class="row" style="margin-top:10px;flex-wrap:wrap;gap:8px"><select class="tsel" style="flex:1;min-width:180px" ${dis("schedule_edit")}><option value="">${esc(L("n_add"))} …</option>${(pv.notify_services || []).filter((s) => !(p.targets || []).some((t) => t.service === s)).map((s) => `<option value="svc:${s}">${esc(s)}</option>`).join("")}
        ${Object.keys(this._hass.states).filter((e) => e.startsWith("notify.")).map((e) => `<option value="ent:${e}">${esc(e)}</option>`).join("")}${Object.keys(this._hass.states).filter((e) => e.startsWith("script.")).map((e) => `<option value="scr:${e}">${esc(L("n_kind_script"))}: ${esc(e)}</option>`).join("")}</select>
        <button class="tadd" ${dis("schedule_edit")}>${esc(L("add"))}</button><button class="primary ttest">${esc(L("n_test"))}</button></div>
      <div class="scriptmap"></div>
      ${[["details", "n_details", "n_details_hint"], ["remind", "n_remind"], ["later", "n_later"], ["persist", "n_persist"], ["weekly", "n_weekly"]].map(([k, l, h]) => `<div class="kv"><div>${esc(L(l))}${h ? `<div class="why">${esc(L(h))}</div>` : ""}</div><button class="toggle ${nt[k] ? "on" : ""}" data-nt="${k}" ${dis("schedule_edit")}></button></div>`).join("")}
      <div class="grid2" style="margin-top:8px"><div><label class="lbl">${esc(L("n_importance"))}</label><select data-ns="importance" ${dis("schedule_edit")}>${["high", "default", "low"].map((v) => `<option ${nt.importance === v ? "selected" : ""}>${v}</option>`).join("")}</select></div>
      <div><label class="lbl">${esc(L("n_ios"))}</label><select data-ns="ios_level" ${dis("schedule_edit")}>${["time-sensitive", "active", "passive", "critical"].map((v) => `<option ${nt.ios_level === v ? "selected" : ""}>${v}</option>`).join("")}</select></div></div>
      <details style="margin-top:12px"><summary class="sub" style="cursor:pointer">📱 Android · iOS</summary><p class="hint">${esc(L("n_guide_android"))}</p><p class="hint">${esc(L("n_guide_ios"))}</p><p class="hint">${esc(L("n_guide_other"))}</p></details>`, "wide");
    // Schlafquellen + Modell
    if (p.modules.sleep_tracking) {
      sec(`<h3>🛏️ ${esc(L("p_sleep"))}</h3>${lockedNote("profile_edit")}${(p.sleep_sources || []).map((s, k) => `<div class="kv"><div>${esc(s.entity)}<div class="why">${esc(L("k_" + s.kind))}${s.kind === "aux" ? " · " + esc(L("r_" + s.role)) : ""}${s.threshold != null ? " · " + s.threshold : ""}</div></div>
        <div class="row"><button class="ghost" data-sedit="${k}" ${dis("profile_edit")}>✎</button><button class="ghost danger" data-srm="${k}" ${dis("profile_edit")}>✕</button></div></div>`).join("") || `<div class="hint">${esc(L("s_no_sources"))}</div>`}
        <div class="row" style="margin-top:10px"><button class="sadd" ${dis("profile_edit")}>＋ ${esc(L("s_add"))}</button></div>
        <div class="field" style="margin-top:12px"><label class="lbl">${esc(L("s_alarm"))}</label><input list="mh-sensors" data-p="alarm_entity" value="${esc(p.alarm_entity || "")}" ${dis("profile_edit")}></div>
        <div class="swiz"></div>`, "wide");
      if ((p.sleep_sources || []).length) sec(`<h3>🧠 ${esc(L("model_title"))}</h3><div class="modelbox"><div class="center"><div class="spinner"></div></div></div>`, "wide");
    }
    // PIN, Daten, LLM (nur die Person selbst)
    if (pv.self) {
      sec(`<h3>🔐 ${esc(L("p_pin"))}</h3><div class="hint" style="margin-bottom:12px">${esc(L("pin_hint"))}</div>
        <div class="row" style="flex-wrap:wrap;gap:8px">${pv.has_pin ? `<button class="pinchg">${esc(L("pin_change"))}</button><button class="ghost danger pinrm">${esc(L("pin_off"))}</button>` : `<button class="primary pinset">${esc(L("pin_on"))}</button>`}</div>
        ${pv.has_pin ? `<div class="field" style="margin-top:12px"><label class="lbl">${esc(L("pin_session"))}</label><input type="number" min="1" max="1440" data-p="pin_session_min" value="${p.pin_session_min}"></div>` : ""}`);
      sec(`<h3>📦 ${esc(L("p_data"))}</h3><div class="row" style="flex-wrap:wrap;gap:8px"><button data-exp="json">${esc(L("export_json"))}</button><button data-exp="md">${esc(L("export_md"))}</button>
        <label class="chip" style="cursor:pointer;padding:10px 16px">${esc(L("import"))}<input type="file" accept=".json" class="imp" hidden></label></div>`);
      if (this._me.llm && this._me.llm.enabled) {
        const okL = can("llm_consent");
        sec(`<h3>🤖 ${esc(L("p_llm"))}</h3>${okL ? `<div class="kv"><div>${esc(L("llm_consent"))}<div class="why">${esc(L("llm_hint", { b: "AI" }))}</div></div><button class="toggle ${p.llm_consent ? "on" : ""}" data-pt="llm_consent"></button></div>` : `<div class="hint">🔒 ${esc(L("llm_blocked"))}</div>`}`);
      }
    }
    out.push(`<datalist id="mh-sensors">${Object.keys(this._hass.states).filter((e) => /^(sensor|binary_sensor|input_boolean|input_datetime|light|switch|device_tracker|person|sun|weather|calendar)\./.test(e)).slice(0, 3000).map((e) => `<option value="${esc(e)}">`).join("")}</datalist>`);
    this._bind = (root) => this.bindProfile(root, pv, admin);
    return out.join("");
  }
  async saveProfile(pv, changes, admin) {
    const data = { changes };
    if (admin) data.pid = pv.profile.id;
    const res = await this.call("profile_update", data, admin);
    if (res.refused && Object.keys(res.refused).length) toast(this.shadowRoot, this.t("why_" + Object.values(res.refused)[0]));
    else toast(this.shadowRoot, this.t("saved_short") + " ✓");
    Object.assign(pv, res);
    return res;
  }
  /* Check-in-Zeiten: ein Block je Zeitfenster (Modus-Schalter, kurzer Hinweis, nur die Felder des Modus) */
  slotHtml(pv, slot) {
    const L = (k, v) => this.t(k, v), p = pv.profile, R = pv.rights, sch = p.schedule, s = sch[slot];
    const ok = !!(R.schedule_edit && R.schedule_edit.ok), hasSleep = (p.sleep_sources || []).length > 0;
    const modes = ["fixed", "entity", "sleep", "manual"], k = Math.max(0, modes.indexOf(s.mode));
    const wdn = L("weekdays").split(",");
    let body = "";
    if (s.mode === "fixed") {
      const same = s.times.every((t) => t === s.times[0]);
      const open = !same || !!(this._wdOpen && this._wdOpen[slot]);
      body = open
        ? `<div class="wd-times">${s.times.map((t, i) => `<label class="tcell ${i > 4 ? "we" : ""}" style="--i:${i}" aria-disabled="${!ok}"><span>${esc(wdn[i])}</span>${timeFieldHtml(`data-time="${slot}" data-i="${i}" aria-label="${esc(L(slot) + " " + wdn[i])}"`, t, !ok)}</label>`).join("")}</div>
          ${ok ? `<div class="slot-foot"><button class="ghost linkbtn" data-wdsame="${slot}">${esc(L("t_same"))}</button></div>` : ""}`
        : `<div class="tsame"><label class="tcell" aria-disabled="${!ok}"><span>${esc(L("t_every_day"))}</span>${timeFieldHtml(`data-timeall="${slot}" aria-label="${esc(L(slot) + " " + L("t_every_day"))}"`, s.times[0], !ok)}</label>
          ${ok ? `<button class="ghost linkbtn" data-wdopen="${slot}">${esc(L("t_per_day"))}<span class="chev">›</span></button>` : ""}</div>`;
    } else if (s.mode === "entity") {
      body = `<div class="field"><label class="lbl">${esc(L("t_entity"))}</label><input list="mh-sensors" data-sent="${slot}" value="${esc(s.entity || "")}" placeholder="input_datetime.…" ${ok ? "" : "disabled"}></div>
        <div class="kv tight"><div>${esc(L("t_offset"))}<div class="why">${esc(L("t_offset_hint"))}</div></div>${stepperHtml(`data-soff="${slot}"`, s.offset_min || 0, { min: -720, max: 720, step: 5, unit: "min", disabled: !ok })}</div>`;
    } else if (s.mode === "sleep" && ["morning", "evening"].find((x) => sch[x].mode === "sleep") === slot) {
      // Abstand gilt für beide Zeitfenster -> nur einmal zeigen
      body = `<div class="kv tight"><div>${esc(L("t_gap"))}<div class="why">${esc(L("t_gap_hint"))}</div></div>${stepperHtml("data-gap", sch.sleep_gap_min, { min: 5, max: 90, step: 5, unit: "min", disabled: !ok })}</div>`;
    }
    return `<div class="slot" data-slot="${slot}"><div class="slot-title">${slot === "morning" ? "🌅" : "🌙"} ${esc(L(slot))}</div>
      <div class="msegs" data-mode="${slot}" style="--k:${k}" role="radiogroup" aria-label="${esc(L("t_mode"))}">${modes.map((m) => `<button class="mseg ${s.mode === m ? "on" : ""}" data-v="${m}" role="radio" aria-checked="${s.mode === m}" ${(m === "sleep" && !hasSleep) || !ok ? "disabled" : ""}${m === "sleep" && !hasSleep ? ` title="${esc(L("mh_sleep_need"))}"` : ""}>${esc(L("mode_" + m))}</button>`).join("")}</div>
      <div class="mhint">${esc(L("mh_" + s.mode))}${s.mode === "sleep" && !hasSleep ? ` <span class="need">${esc(L("mh_sleep_need"))}</span>` : ""}</div>
      ${body ? `<div class="slot-body">${body}</div>` : ""}</div>`;
  }
  bindSlot(el, pv, admin) {
    const slot = el.dataset.slot, sched = () => pv.profile.schedule;
    el._src = this.slotHtml(pv, slot);
    const save = (ch, redraw) => this.saveProfile(pv, ch, admin).then(() => { if (redraw) this.redrawSlots(el.closest(".sec"), pv, admin); });
    // sofort lokal übernehmen, damit schnelle Folgeänderungen nicht auf altem Stand aufbauen
    const upd = (obj, redraw) => { pv.profile.schedule = Object.assign({}, sched(), { [slot]: Object.assign({}, sched()[slot], obj) }); return save({ schedule: { [slot]: pv.profile.schedule[slot] } }, redraw); };
    const segs = el.querySelector(".msegs");
    if (segs && !segs._bound) {
      segs._bound = true;
      segs.querySelectorAll(".mseg").forEach((b, k) => b.addEventListener("click", () => {
        if (b.classList.contains("on")) return;
        segs.style.setProperty("--k", k);
        segs.querySelectorAll(".mseg").forEach((x) => { x.classList.toggle("on", x === b); x.setAttribute("aria-checked", String(x === b)); });
        // el kann nach dem Neuzeichnen schon ersetzt sein -> Abschnitt über den (bleibenden) Schalter finden
        upd({ mode: b.dataset.v }).then(() => this.redrawSlots(segs.closest(".sec"), pv, admin));
      }));
    }
    el.querySelectorAll("[data-time]").forEach((inp) => bindTimeField(inp, (v) => { const times = sched()[slot].times.slice(); times[+inp.dataset.i] = v; upd({ times }); }));
    const all = el.querySelector("[data-timeall]");
    if (all) bindTimeField(all, (v) => upd({ times: Array(7).fill(v) }));
    const op = el.querySelector("[data-wdopen]");
    if (op) op.addEventListener("click", () => { this._wdOpen = Object.assign({}, this._wdOpen, { [slot]: true }); this.redrawSlots(el.closest(".sec"), pv, admin); });
    const sm = el.querySelector("[data-wdsame]");
    if (sm) sm.addEventListener("click", () => {
      this._wdOpen = Object.assign({}, this._wdOpen, { [slot]: false });
      const t = sched()[slot].times;
      if (t.every((x) => x === t[0])) this.redrawSlots(el.closest(".sec"), pv, admin);
      else upd({ times: Array(7).fill(t[0]) }, true);
    });
    const ent = el.querySelector("[data-sent]");
    if (ent) ent.addEventListener("change", () => upd({ entity: ent.value.trim() || null }));
    const off = el.querySelector("[data-soff]");
    if (off) bindStepper(off, (n) => upd({ offset_min: n }));
    const gap = el.querySelector("[data-gap]");
    if (gap) bindStepper(gap, (n) => { pv.profile.schedule = Object.assign({}, sched(), { sleep_gap_min: n }); save({ schedule: { sleep_gap_min: n } }); });
  }
  /* nur geänderte Zeitfenster neu zeichnen; der Modus-Schalter bleibt stehen, damit seine Animation durchläuft */
  redrawSlots(sec, pv, admin) {
    if (!sec) return;
    sec.querySelectorAll(".slot").forEach((old) => {
      const html = this.slotHtml(pv, old.dataset.slot);
      if (old._src === html) return;
      const tpl = document.createElement("template");
      tpl.innerHTML = html.trim();
      const nu = tpl.content.firstElementChild, segs = old.querySelector(".msegs"), nsegs = nu.querySelector(".msegs");
      segs.style.setProperty("--k", nsegs.style.getPropertyValue("--k"));
      segs.querySelectorAll(".mseg").forEach((b, i) => { const n = nsegs.children[i]; b.className = n.className; b.disabled = n.disabled; b.setAttribute("aria-checked", n.getAttribute("aria-checked")); });
      nu.replaceChild(segs, nsegs);
      if (old.querySelector(".slot-body") && nu.querySelector(".slot-body") && old.dataset.mode === pv.profile.schedule[old.dataset.slot].mode) nu.querySelector(".slot-body").style.animation = "none";
      nu.dataset.mode = pv.profile.schedule[old.dataset.slot].mode;
      old.replaceWith(nu);
      this.bindSlot(nu, pv, admin);
    });
  }
  bindProfile(root, pv, admin) {
    const p = pv.profile;
    const save = (ch, rerender) => this.saveProfile(pv, ch, admin).then(() => { if (rerender) this.rerenderProfile(pv, admin); });
    root.querySelectorAll("[data-p]").forEach((inp) => inp.addEventListener("change", () => {
      let v = inp.value;
      if (inp.type === "number") v = v === "" ? null : parseFloat(v);
      if (v === "") v = null;
      save({ [inp.dataset.p]: v }, inp.dataset.p === "sex");
    }));
    const bd = root.querySelector('[data-dm="birthdate"]');
    if (bd) bindDateMask(bd, (v) => save({ birthdate: v }));
    const pu = root.querySelector('[data-dm="pause_until"]');
    if (pu) bindDateMask(pu, () => {});
    root.querySelectorAll("[data-pt]").forEach((b) => b.addEventListener("click", () => { const k = b.dataset.pt; save({ [k]: !p[k] }, true); }));
    root.querySelectorAll("[data-mod]").forEach((b) => b.addEventListener("click", () => { const m = b.dataset.mod; b.classList.toggle("on"); save({ modules: { [m]: !p.modules[m] } }, true); }));
    root.querySelectorAll(".slot").forEach((el) => { el.dataset.mode = p.schedule[el.dataset.slot].mode; this.bindSlot(el, pv, admin); });
    const pon = root.querySelector(".pauseon"), poff = root.querySelector(".pauseoff");
    if (pon) pon.addEventListener("click", async () => { const box = root.querySelector('[data-dm="pause_until"]'); const u = box ? dmValue(box) : null;
      if (u === undefined) { shake(box); return; } await this.call("pause", Object.assign({ on: true, until: u }, admin ? { pid: p.id } : {}), admin); this.rerenderProfile(pv, admin, true); });
    if (poff) poff.addEventListener("click", async () => { await this.call("pause", Object.assign({ on: false }, admin ? { pid: p.id } : {}), admin); this.rerenderProfile(pv, admin, true); });
    root.querySelectorAll("[data-nt]").forEach((b) => b.addEventListener("click", () => save({ notify: { [b.dataset.nt]: !p.notify[b.dataset.nt] } }, true)));
    root.querySelectorAll("[data-ns]").forEach((s) => s.addEventListener("change", () => save({ notify: { [s.dataset.ns]: s.value } })));
    root.querySelectorAll("[data-trm]").forEach((b) => b.addEventListener("click", () => { const t = p.targets.slice(); t.splice(parseInt(b.dataset.trm, 10), 1); save({ targets: t }, true); }));
    const tadd = root.querySelector(".tadd");
    if (tadd) tadd.addEventListener("click", () => {
      const v = root.querySelector(".tsel").value;
      if (!v) return;
      const [kind, id] = [v.slice(0, 3), v.slice(4)];
      if (kind === "svc") save({ targets: p.targets.concat([{ kind: "service", service: id, name: id.replace("notify.mobile_app_", "") }]) }, true);
      else if (kind === "ent") save({ targets: p.targets.concat([{ kind: "entity", entity: id, name: id }]) }, true);
      else this.scriptMapper(root.querySelector(".scriptmap"), id, (t) => save({ targets: p.targets.concat([t]) }, true));
    });
    const tt = root.querySelector(".ttest");
    if (tt) tt.addEventListener("click", async () => { const r = await this.call("test_notification", admin ? { pid: p.id } : {}, admin); toast(this.shadowRoot, this.t("n_sent", { n: r.sent, m: r.targets })); });
    // Schlafquellen
    root.querySelectorAll("[data-srm]").forEach((b) => b.addEventListener("click", () => { const s = p.sleep_sources.slice(); s.splice(parseInt(b.dataset.srm, 10), 1); save({ sleep_sources: s }, true); }));
    root.querySelectorAll("[data-sedit]").forEach((b) => b.addEventListener("click", () => this.sourceWizard(root.querySelector(".swiz"), pv, admin, parseInt(b.dataset.sedit, 10))));
    const sadd = root.querySelector(".sadd");
    if (sadd) sadd.addEventListener("click", () => this.sourceWizard(root.querySelector(".swiz"), pv, admin, -1));
    const mb = root.querySelector(".modelbox");
    if (mb) this.modelView(mb, pv, admin);
    // PIN
    const pinFlow = async (mode) => {
      const L = (k) => this.t(k);
      let old = null;
      try {
        if (pv.has_pin) old = await this.pinEntry(L("pin_old"));
        let nw = null;
        if (mode !== "off") nw = await this.pinEntry(L("pin_new"));
        const r = await this.call("set_pin", { old, new: nw });
        if (!r.ok) { toast(this.shadowRoot, L("pin_wrong").replace("{n}", r.left ?? "?")); return; }
        if (r.token) this.api.session = r.token;
        toast(this.shadowRoot, nw ? L("pin_set_ok") : L("pin_removed"));
        this.render(true);
      } catch (e) { /* abgebrochen */ }
    };
    const ps = root.querySelector(".pinset"), pc = root.querySelector(".pinchg"), pr = root.querySelector(".pinrm");
    if (ps) ps.addEventListener("click", () => pinFlow("set"));
    if (pc) pc.addEventListener("click", () => pinFlow("change"));
    if (pr) pr.addEventListener("click", () => pinFlow("off"));
    root.querySelectorAll("[data-exp]").forEach((b) => b.addEventListener("click", async () => {
      const r = await this.call("export", { format: b.dataset.exp });
      const blob = new Blob([r.content], { type: b.dataset.exp === "json" ? "application/json" : "text/markdown" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = `mental-health-${new Date().toISOString().slice(0, 10)}.${b.dataset.exp}`; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    }));
    const imp = root.querySelector(".imp");
    if (imp) imp.addEventListener("change", async () => {
      const f = imp.files[0]; if (!f) return;
      const r = await this.call("import", { content: await f.text() });
      toast(this.shadowRoot, this.t("imported", { n: r.added }));
    });
  }
  pinEntry(title) {
    return pinDialog(this.shadowRoot, this.lang, { title, sub: "", check: async (pin) => ({ ok: true, pin }) }).then((r) => r.pin);
  }
  async rerenderProfile(pv, admin, reload) {
    if (reload || !pv.rights) {
      const fresh = await this.call("profile", admin ? { pid: pv.profile.id } : {}, admin);
      Object.assign(pv, fresh);
    }
    const main = this.shadowRoot.querySelector(".main");
    main.innerHTML = (admin ? this.adminBackHtml() : "") + this.profileHtml(pv, admin);
    this.afterRender(main);
    if (admin) this.bindAdminBack(main, pv);
  }
  scriptMapper(box, entity, done) {
    const L = (k) => this.t(k);
    box.innerHTML = `<div class="tile" style="margin-top:10px"><b>${esc(L("n_fields"))}: ${esc(entity)}</b>
      <div class="grid2" style="margin-top:10px">${["title", "message", "data", "target"].map((f) => `<div><label class="lbl">${esc(L("n_f_" + f))}</label><input data-f="${f}" placeholder="${f === "message" ? "message" : f === "title" ? "title" : ""}"></div>`).join("")}
      <div><label class="lbl">${esc(L("n_target_value"))}</label><input data-tv></div><div><label class="lbl">${esc(L("n_platform"))}</label><select data-pl><option value="android">Android</option><option value="ios">iOS</option><option value="other">other</option></select></div></div>
      <div class="row" style="margin-top:10px;justify-content:flex-end"><button class="primary ok">${esc(L("save"))}</button></div></div>`;
    box.querySelector(".ok").addEventListener("click", () => {
      const fields = {};
      box.querySelectorAll("[data-f]").forEach((i) => { if (i.value.trim()) fields[i.dataset.f] = i.value.trim(); });
      done({ kind: "script", entity, fields, target_value: box.querySelector("[data-tv]").value.trim(), platform: box.querySelector("[data-pl]").value, name: entity });
      box.innerHTML = "";
    });
  }

  /* Quellen-Assistent mit Live-Vorschau (48 h aus dem Recorder, Erkennung darübergelegt) */
  sourceWizard(box, pv, admin, idx) {
    const L = (k, v) => this.t(k, v);
    const p = pv.profile;
    const src = Object.assign({ entity: "", kind: "numeric", role: "in_bed", on_means: true, threshold: null, direction: null, mapping: {}, shared_with: [] }, idx >= 0 ? p.sleep_sources[idx] : {});
    const others = (this._adminPersons || []).filter((x) => x.profile.id !== p.id);
    const draw = () => {
      const st = src.entity && this._hass.states[src.entity];
      const isNum = src.kind === "numeric";
      box.innerHTML = `<div class="tile rise" style="margin-top:14px"><div class="steps"><i class="on"></i><i class="${src.entity ? "on" : ""}"></i><i class="${this._prev ? "on" : ""}"></i></div>
        <div class="grid2"><div><label class="lbl">${esc(L("s_entity"))}</label><input list="mh-sensors" class="se" value="${esc(src.entity)}"></div>
        <div><label class="lbl">${esc(L("s_kind"))}</label><select class="sk">${KINDS.map((k) => `<option value="${k}" ${src.kind === k ? "selected" : ""}>${esc(L("k_" + k))}</option>`).join("")}</select></div></div>
        ${src.kind === "binary" ? `<div class="grid2" style="margin-top:10px"><div><label class="lbl">${esc(L("s_role"))}</label><select class="sr"><option value="in_bed" ${src.role === "in_bed" ? "selected" : ""}>${esc(L("r_in_bed"))}</option><option value="asleep" ${src.role === "asleep" ? "selected" : ""}>${esc(L("r_asleep"))}</option></select></div>
          <div><label class="lbl">&nbsp;</label><div class="segs"><button class="seg ${src.on_means ? "on" : ""}" data-om="1">${esc(L("s_on_means"))}</button><button class="seg ${!src.on_means ? "on" : ""}" data-om="0">${esc(L("s_off_means"))}</button></div></div></div>` : ""}
        ${src.kind === "aux" ? `<div style="margin-top:10px"><label class="lbl">${esc(L("s_role"))}</label><select class="sr">${AUX_ROLES.map((r) => `<option value="${r}" ${src.role === r ? "selected" : ""}>${esc(L("r_" + r))}</option>`).join("")}</select></div>` : ""}
        ${isNum ? `<div class="grid2" style="margin-top:10px"><div><label class="lbl">${esc(L("s_threshold"))}</label><input type="number" step="0.01" class="sth" value="${src.threshold ?? ""}"></div>
          <div><label class="lbl">${esc(L("s_direction"))}</label><select class="sdir"><option value="">${esc(L("dir_auto"))}</option><option value="-1" ${src.direction === -1 ? "selected" : ""}>${esc(L("dir_down"))}</option><option value="1" ${src.direction === 1 ? "selected" : ""}>${esc(L("dir_up"))}</option></select></div></div>
          <div class="hint">${esc(L("s_threshold_hint"))}</div>` : ""}
        ${isNum && others.length ? `<div style="margin-top:10px"><label class="lbl">${esc(L("s_shared"))}</label><div class="choices">${others.map((o) => `<button class="chip ${src.shared_with.includes(o.profile.id) ? "on" : ""}" data-sh="${o.profile.id}">${esc(o.profile.name)}</button>`).join("")}</div></div>` : ""}
        <div class="smap"></div>
        <h4>${esc(L("s_preview"))}</h4><div class="graph">${src.entity ? `<div class="center"><div class="spinner"></div></div>` : `<div class="hint" style="padding:18px 4px">${esc(L("s_pick_entity"))}</div>`}</div>
        <div class="row" style="margin-top:12px;justify-content:flex-end;gap:8px"><button class="ghost cancel">${esc(L("cancel"))}</button><button class="primary ssave">${esc(L("s_save"))}</button></div></div>`;
      const q = (s) => box.querySelector(s);
      q(".se").addEventListener("change", () => { src.entity = q(".se").value.trim(); const dom = src.entity.split(".")[0];
        if (["binary_sensor", "input_boolean"].includes(dom) && src.kind === "numeric") src.kind = "binary";
        draw(); });
      q(".sk").addEventListener("change", () => { src.kind = q(".sk").value; src.role = src.kind === "aux" ? "screen" : "in_bed"; draw(); });
      if (q(".sr")) q(".sr").addEventListener("change", () => { src.role = q(".sr").value; preview(); });
      box.querySelectorAll("[data-om]").forEach((b) => b.addEventListener("click", () => { src.on_means = b.dataset.om === "1"; draw(); }));
      if (q(".sth")) q(".sth").addEventListener("change", () => { src.threshold = q(".sth").value === "" ? null : parseFloat(q(".sth").value); preview(); });
      if (q(".sdir")) q(".sdir").addEventListener("change", () => { src.direction = q(".sdir").value ? parseInt(q(".sdir").value, 10) : null; preview(); });
      box.querySelectorAll("[data-sh]").forEach((b) => b.addEventListener("click", () => { const id = b.dataset.sh; src.shared_with = src.shared_with.includes(id) ? src.shared_with.filter((x) => x !== id) : src.shared_with.concat([id]); draw(); }));
      q(".cancel").addEventListener("click", () => { box.innerHTML = ""; this._prev = null; });
      q(".ssave").addEventListener("click", async () => {
        if (!src.entity) { shake(q(".se")); return; }
        const list = p.sleep_sources.slice();
        if (idx >= 0) list[idx] = src; else list.push(src);
        await this.saveProfile(pv, { sleep_sources: list }, admin);
        this._prev = null;
        this.rerenderProfile(pv, admin, true);
      });
      if (st) preview();
    };
    const preview = async () => {
      const g = box.querySelector(".graph");
      if (!src.entity) return;
      g.innerHTML = `<div class="center"><div class="spinner"></div></div>`;
      let r;
      try { r = await this.call("source_preview", Object.assign({ source: src }, admin ? { pid: p.id } : {}), admin); } catch (e) { g.innerHTML = `<div class="hint">${esc(this.t("error"))}</div>`; return; }
      this._prev = r;
      this.drawPreview(g, r, src);
      if (src.kind === "enum") {
        const sm = box.querySelector(".smap");
        sm.innerHTML = `<h4>${esc(L("s_mapping"))}</h4>${(r.states || []).map((s) => `<div class="kv"><span>${esc(s)}</span><select data-map="${esc(s)}">${["asleep", "awake", "in_bed", "ignore"].map((t) => `<option value="${t}" ${(src.mapping[s] || "") === t ? "selected" : ""}>${t}</option>`).join("")}</select></div>`).join("")}`;
        sm.querySelectorAll("[data-map]").forEach((s) => s.addEventListener("change", () => { src.mapping[s.dataset.map] = s.value; }));
      }
    };
    draw();
  }
  drawPreview(g, r, src) {
    const L = (k, v) => this.t(k, v), lang = this.lang;
    const vals = r.values || [];
    const known = vals.filter((v) => v != null);
    if (!known.length) { g.innerHTML = `<div class="hint">${esc(L("no_data"))}</div>`; return; }
    const W = 600, H = 180, n = vals.length;
    let lo = Math.min(...known), hi = Math.max(...known);
    if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
    const pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
    const sx = (i) => (i / Math.max(1, n - 1)) * W, sy = (v) => H - ((v - lo) / (hi - lo)) * H;
    const sleepBand = r.sleep ? `<rect x="${sx((r.sleep.start - r.start) / r.step)}" width="${Math.max(2, sx((r.sleep.end - r.sleep.start) / r.step))}" y="0" height="${H}" fill="rgba(167,139,250,.18)"/>` : "";
    const naps = (r.naps || []).map((x) => `<rect x="${sx((x.start - r.start) / r.step)}" width="${Math.max(2, sx((x.end - x.start) / r.step))}" y="0" height="${H}" fill="rgba(245,177,76,.16)"/>`).join("");
    const d = vals.map((v, i) => (v == null ? null : `${sx(i).toFixed(1)},${sy(v).toFixed(1)}`)).filter(Boolean).join(" ");
    const lvl = r.level;
    const thr = src.threshold != null ? src.threshold : lvl && lvl.threshold;
    const hours = [];
    for (let i = 0; i < n; i += 72) hours.push(`<text x="${sx(i)}" y="${H - 4}" fill="var(--c-muted)" font-size="10">${esc(fmtTime(new Date((r.start + i * r.step) * 60000).toISOString(), lang))}</text>`);
    g.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">${sleepBand}${naps}<polyline points="${d}" fill="none" stroke="#60a5fa" stroke-width="1.6"/>
      ${thr != null && src.kind === "numeric" ? `<line class="thr" x1="0" x2="${W}" y1="${sy(thr)}" y2="${sy(thr)}" stroke="var(--c-teal)" stroke-width="2.5" stroke-dasharray="6 5"/><rect class="thr thrh" x="0" width="${W}" y="${sy(thr) - 10}" height="20" fill="transparent"/>` : ""}${hours.join("")}</svg>
      <div class="row hint" style="gap:12px;flex-wrap:wrap;margin-top:6px"><span><b style="color:#a78bfa">■</b> ${esc(L("asleep"))}</span><span><b style="color:#f5b14c">■</b> ${esc(L("nap"))}</span>
      ${lvl && lvl.learned != null ? `<span>${esc(L("s_learned", { v: fmtNum(lvl.learned, 2, lang) }))}</span>` : ""}${thr != null && src.kind === "numeric" ? `<span class="thrv">${esc(L("model_threshold"))}: ${fmtNum(thr, 2, lang)}</span>` : ""}</div>`;
    const h = g.querySelector(".thrh");
    if (h) {
      const svg = g.querySelector("svg");
      h.addEventListener("pointerdown", (ev) => {
        ev.preventDefault(); h.setPointerCapture(ev.pointerId);
        const rect = svg.getBoundingClientRect();
        const move = (e) => {
          const y = clamp((e.clientY - rect.top) / rect.height, 0, 1) * H;
          const v = lo + (1 - y / H) * (hi - lo);
          src.threshold = Math.round(v * 100) / 100;
          g.querySelectorAll("line.thr").forEach((l) => { l.setAttribute("y1", y); l.setAttribute("y2", y); });
          h.setAttribute("y", y - 10);
          const tv = g.querySelector(".thrv"); if (tv) tv.textContent = `${L("model_threshold")}: ${fmtNum(src.threshold, 2, lang)}`;
          const inp = g.closest(".tile").querySelector(".sth"); if (inp) inp.value = src.threshold;
        };
        const up = () => { h.removeEventListener("pointermove", move); h.removeEventListener("pointerup", up); };
        h.addEventListener("pointermove", move); h.addEventListener("pointerup", up);
      });
    }
  }

  /* Modell-Ansicht – „lebt“: Prior-Ring atmet, Partikel fließen; ohne Inhalte */
  async modelView(box, pv, admin) {
    const L = (k, v) => this.t(k, v), lang = this.lang;
    let m;
    try { m = await this.call("sleep_model", admin ? { pid: pv.profile.id } : {}, admin); } catch (e) { box.innerHTML = `<div class="hint">${esc(L("error"))}</div>`; return; }
    const lv = Object.values(m.levels || {})[0];
    box.innerHTML = `<div class="row" style="flex-wrap:wrap;gap:8px;margin-bottom:10px"><span class="chip teal">${esc(L("model_maturity"))} ${Math.round(m.maturity * 100)} %</span>
      ${m.learning ? `<span class="chip amber">${esc(L("sleep_learning", { n: m.night_of }))}</span>` : ""}<span class="chip">${esc(L("nights_learned", { n: m.nights, l: m.labels }))}</span>
      ${lv && lv.baseline != null ? `<span class="chip">${esc(L("model_baseline"))} ${fmtNum(lv.baseline, 2, lang)}</span><span class="chip">${esc(L("model_threshold"))} ${fmtNum(lv.threshold, 2, lang)}</span>` : ""}
      <span class="spacer"></span><button class="ghost danger mreset">${esc(L("model_reset"))}</button></div>
      <canvas class="model"></canvas>
      ${(m.history || []).length ? `<h4>${esc(L("sleep_nights"))}</h4>${m.history.slice(-7).reverse().map((h) => `<div class="row hint" style="gap:8px"><span style="width:90px">${esc(h.day)}</span><span>${h.asleep ? fmtDur(h.asleep) : "–"}</span><span>· ${Math.round((h.conf || 0) * 100)} %</span>${h.src ? `<span class="chip small">${esc(h.src)}</span>` : ""}</div>`).join("")}` : ""}`;
    box.querySelector(".mreset").addEventListener("click", async () => {
      if (!(await this.confirm(L("model_reset_confirm")))) return;
      await this.call("sleep_reset", admin ? { pid: pv.profile.id } : {}, admin);
      this.modelView(box, pv, admin);
    });
    this.animateModel(box.querySelector("canvas"), m);
  }
  animateModel(cv, m) {
    const ctx = cv.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const prior = m.prior || [];
    const parts = Array.from({ length: 60 }, () => ({ a: Math.random() * Math.PI * 2, r: 0.55 + Math.random() * 0.35, s: 0.0015 + Math.random() * 0.003 }));
    const draw = (time) => {
      if (!cv.isConnected) return;
      const w = cv.clientWidth, h = cv.clientHeight;
      if (cv.width !== w * dpr) { cv.width = w * dpr; cv.height = h * dpr; }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const cx = w / 2, cy = h / 2, R = Math.max(40, Math.min(w, h) / 2 - 46);   // Platz für Ausschlag (bis +36 px) und Strichbreite
      const breathe = reduced() ? 0 : Math.sin(time / 1800) * 0.03;
      // Prior-Ring: 48 Halbstunden
      for (let i = 0; i < prior.length; i++) {
        const a0 = (i / prior.length) * Math.PI * 2 - Math.PI / 2, a1 = ((i + 1) / prior.length) * Math.PI * 2 - Math.PI / 2;
        const v = prior[i];
        const wob = reduced() ? 0 : Math.sin(time / 900 + i * 0.4) * 2;
        ctx.beginPath();
        ctx.arc(cx, cy, R * (1 + breathe) + 10 + v * 26 + wob, a0, a1 - 0.012);
        ctx.strokeStyle = `rgba(${Math.round(47 + 120 * (1 - v))},${Math.round(214 - 75 * (1 - v))},${Math.round(176 + 74 * (1 - v))},${0.25 + v * 0.75})`;
        ctx.lineWidth = 6 + v * 8;
        ctx.lineCap = "round";
        ctx.stroke();
      }
      // Stundenmarken
      ctx.fillStyle = "rgba(134,136,148,.8)"; ctx.font = "11px system-ui"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      for (const hh of [0, 6, 12, 18]) { const a = (hh / 24) * Math.PI * 2 - Math.PI / 2; ctx.fillText(String(hh).padStart(2, "0"), cx + Math.cos(a) * (R - 18), cy + Math.sin(a) * (R - 18)); }
      // fließende Partikel
      for (const p of parts) {
        if (!reduced()) p.a += p.s;
        const idx = Math.floor((((p.a + Math.PI / 2) % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2) / (Math.PI * 2) * prior.length) % Math.max(1, prior.length);
        const v = prior[idx] || 0;
        ctx.beginPath();
        ctx.arc(cx + Math.cos(p.a) * R * p.r, cy + Math.sin(p.a) * R * p.r, 1.2 + v * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(167,139,250,${0.2 + v * 0.6})`;
        ctx.fill();
      }
      // Kern
      const g = ctx.createRadialGradient(cx, cy, 2, cx, cy, R * 0.45);
      g.addColorStop(0, "rgba(47,214,176,.35)"); g.addColorStop(1, "rgba(47,214,176,0)");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R * 0.45 * (1 + breathe * 2), 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = "#f1f2f4"; ctx.font = "600 20px system-ui";
      ctx.fillText(`${Math.round((m.maturity || 0) * 100)} %`, cx, cy - 6);
      ctx.fillStyle = "rgba(134,136,148,1)"; ctx.font = "11px system-ui";
      ctx.fillText(m.state ? this.t("st_" + m.state) : this.t("model_prior"), cx, cy + 14);
      requestAnimationFrame(draw);
    };
    requestAnimationFrame(draw);
  }

  /* ---------------------------------------------------------- Admin */
  async tab_admin() {
    const a = await this.call("admin", {}, true);
    this._admin = a;
    this._adminPersons = a.persons;
    if (this._adminEdit) {
      const pv = await this.call("profile", { pid: this._adminEdit }, true);
      return this.adminBackHtml() + this.profileHtml(pv, true) + (this._bindAdminPerson(pv) || "");
    }
    return this.adminHtml(a);
  }
  adminBackHtml() {
    const L = (k) => this.t(k);
    return `<section class="sec wide"><div class="row"><button class="ghost back">‹ ${esc(L("a_persons"))}</button><span class="spacer"></span>
      <button class="ghost rpin">${esc(L("a_reset_pin"))}</button><button class="ghost danger delp">${esc(L("a_delete_person"))}</button></div></section>`;
  }
  _bindAdminPerson(pv) {
    const prev = this._bind;
    this._bind = (root) => { if (prev) prev(root); this.bindAdminBack(root, pv); };
    return "";
  }
  bindAdminBack(root, pv) {
    const L = (k, v) => this.t(k, v);
    const p = pv ? pv.profile : (this._adminPersons || []).find((x) => x.profile.id === this._adminEdit).profile;
    root.querySelector(".back").addEventListener("click", () => { this._adminEdit = null; this.render(true); });
    root.querySelector(".delp").addEventListener("click", async () => {
      if (!(await this.confirm(L("a_delete_confirm", { name: p.name }), L("delete")))) return;
      await this.call("admin_delete_person", { pid: p.id }, true);
      this._adminEdit = null; this.render(true);
    });
    root.querySelector(".rpin").addEventListener("click", async () => {
      if (!(await this.confirm(L("a_reset_confirm", { name: p.name })))) return;
      const r = await this.call("admin_reset_pin", { pid: p.id }, true);
      toast(this.shadowRoot, L("a_pin_lost", { n: r.lost || 0 }));
    });
  }
  adminHtml(a) {
    const L = (k, v) => this.t(k, v), lang = this.lang, s = a.settings;
    const out = [];
    let i = 0;
    const sec = (html, cls = "") => out.push(`<section class="sec rise ${cls}" style="animation-delay:${Math.min(i++ * 40, 320)}ms">${html}</section>`);
    const focusUser = this._adminFocus && this._adminFocus.user;
    // Personen
    sec(`<h3>👥 ${esc(L("a_persons"))}</h3>${a.persons.length ? a.persons.map((x) => `<div class="person-row" data-pp="${x.profile.id}">
        <div class="avatar">${x.picture ? `<img src="${esc(x.picture)}" alt="">` : esc((x.profile.name || "?")[0])}</div>
        <div style="flex:1;min-width:0"><b>${esc(x.profile.name)}</b> ${x.profile.child ? "<span class='chip small'>🧒</span>" : ""} ${x.has_pin ? "🔒" : ""}
        <div class="hint">${esc(L("participation_14"))}: ${x.participation == null ? "–" : Math.round(x.participation * 100) + " %"} · ${esc(L("model_state"))}: ${Math.round((x.model.sleep.maturity || 0) * 100)} %${x.model.sleep.learning ? " · " + esc(L("learning_hint")) : ""}</div></div>
        ${x.status.morning || x.status.evening ? `<span class="chip small teal pulse">●</span>` : ""}<span>›</span></div>`).join("") : `<div class="hint">${esc(L("no_persons"))}</div>`}
      <h4>${esc(L("a_add"))}</h4><div class="col">${a.ha_persons.map((hp) => `<div class="kv"><div>${esc(hp.name)}<div class="why">${esc(hp.entity_id)}${!hp.eligible ? " · " + esc(L("a_no_user")) : hp.taken ? " · " + esc(L("a_taken")) : ""}</div></div>
        ${hp.eligible && !hp.taken ? `<button class="${focusUser && hp.user_id === focusUser ? "primary pulse" : ""}" data-create="${esc(hp.entity_id)}">${esc(L("setup_for"))}</button>` : ""}</div>`).join("")}</div>
      <div class="cwiz"></div>`, "wide");
    if (a.requests.length) sec(`<h3>📨 ${esc(L("a_requests"))}</h3>${a.requests.map((r) => `<div class="kv"><div>${esc(r.name)}<div class="why">${esc(fmtDate(new Date(r.ts * 1000).toISOString(), lang, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }))}</div></div><button class="ghost" data-dismiss="${esc(r.user_id)}">${esc(L("dismiss"))}</button></div>`).join("")}`);
    // Einstellungen
    const timeIn = (k) => `<div class="kv"><span>${esc(L("st_" + k))}</span><label class="tcell solo">${timeFieldHtml(`data-sttime="${k}" aria-label="${esc(L("st_" + k))}"`, s[k])}</label></div>`;
    const numIn = (k, key, min, max) => `<div class="kv"><span>${esc(L(key))}</span><input type="number" data-st="${k}" min="${min}" max="${max}" value="${s[k]}" style="max-width:110px"></div>`;
    sec(`<h3>⚙️ ${esc(L("a_settings"))}</h3>${timeIn("day_boundary")}${timeIn("evening_from")}${timeIn("morning_until")}${timeIn("nightly")}
      ${numIn("window_min", "st_window", 5, 1440)}${numIn("remind_min", "st_remind", 0, 240)}
      <div class="kv"><span>${esc(L("st_late"))}</span><select data-st="late_entry" style="max-width:200px">${["none", "day_end", "3_days"].map((v) => `<option value="${v}" ${s.late_entry === v ? "selected" : ""}>${esc(L("late_" + v))}</option>`).join("")}</select></div>
      <div class="kv"><span>${esc(L("st_load"))}</span><div class="segs">${[1, 2, 3].map((v) => `<button class="seg ${s.load_level === v ? "on" : ""}" data-load="${v}">${v}</button>`).join("")}</div></div>
      ${numIn("family_k", "st_family_k", 2, 10)}${numIn("low_mood_days", "st_low_days", 1, 14)}${numIn("low_mood_max", "st_low_max", 1, 6)}${numIn("request_cooldown_h", "st_cooldown", 1, 336)}
      <div class="kv"><span>${esc(L("st_weekly"))}</span><button class="toggle ${s.weekly_report ? "on" : ""}" data-stt="weekly_report"></button></div>
      ${["workday_entity", "weather_entity", "daylight_entity"].map((k) => `<div class="field" style="margin-top:8px"><label class="lbl">${esc(L("st_" + k.replace("_entity", "")))}</label><input list="mh-all" data-st="${k}" value="${esc(s[k] || "")}"></div>`).join("")}`);
    // Admin-Benachrichtigungen + PIN
    sec(`<h3>🔔 ${esc(L("a_notify"))}</h3>${(s.admin_targets || []).map((t, k) => `<div class="kv"><span>${esc(t.name)}</span><button class="ghost danger" data-atrm="${k}">✕</button></div>`).join("") || `<div class="hint">–</div>`}
      <div class="row" style="margin-top:8px"><select class="atsel" style="flex:1"><option value="">${esc(L("n_add"))} …</option>${a.notify_services.map((x) => `<option value="${esc(x)}">${esc(x)}</option>`).join("")}</select><button class="atadd">${esc(L("add"))}</button></div>
      <h3 style="margin-top:22px">🔐 ${esc(L("a_pin"))}</h3><div class="hint">${esc(L("a_pin_hint"))}</div>
      <div class="row" style="margin-top:10px;gap:8px">${s.admin_pin ? `<button class="apchg">${esc(L("pin_change"))}</button><button class="ghost danger aprm">${esc(L("pin_off"))}</button>` : `<button class="apset">${esc(L("pin_on"))}</button>`}</div>`);
    // LLM
    const caps = a.llm_caps || {};
    sec(`<h3>🤖 ${esc(L("a_llm"))} <span class="chip small amber">Beta</span></h3>
      <div class="kv"><span>${esc(L("m_llm"))}</span><button class="toggle ${s.llm.enabled ? "on" : ""}" data-llm-en></button></div>
      <div class="kv"><span>${esc(L("llm_mode"))}</span><div class="segs">${["ai_task", "conversation"].map((v) => `<button class="seg ${s.llm.mode === v ? "on" : ""}" data-llm-mode="${v}" ${(v === "ai_task" && !caps.ai_task) || (v === "conversation" && !caps.conversation) ? "disabled" : ""}>${v}</button>`).join("")}</div></div>
      ${s.llm.mode === "ai_task" ? `<div class="field"><label class="lbl">${esc(L("llm_entity"))}</label><select data-llm-k="entity"><option value="">(default)</option>${(caps.ai_task_entities || []).map((e) => `<option ${s.llm.entity === e ? "selected" : ""}>${esc(e)}</option>`).join("")}</select></div>`
        : `<div class="field"><label class="lbl">${esc(L("llm_agent"))}</label><select data-llm-k="agent"><option value="">(default)</option>${(caps.agents || []).map((e) => `<option ${s.llm.agent === e ? "selected" : ""}>${esc(e)}</option>`).join("")}</select></div>`}
      <div class="hint">${esc(L("llm_caps", { a: [caps.ai_task ? "ai_task" : null, caps.conversation ? "conversation" : null].filter(Boolean).join(", ") || "–" }))}</div>
      ${a.llm_state && a.llm_state.last_error ? `<div class="hint" style="color:var(--c-red)">${esc(a.llm_state.last_error)}</div>` : ""}`);
    // Backup
    const b = s.backup;
    sec(`<h3>💾 ${esc(L("a_backup"))}</h3><div class="hint">${esc(L("ha_backup_hint"))}</div>
      <h4>${esc(L("b_password"))}</h4><div class="hint">${esc(L("b_password_hint"))}</div>
      <div class="row" style="margin-top:8px;gap:8px"><input type="password" class="bpw" placeholder="${b.password ? esc(L("b_password_set")) : "••••••••"}" autocomplete="new-password"><button class="bpwset">${esc(L("save"))}</button></div>
      <div class="kv" style="margin-top:10px"><span>${esc(L("b_auto"))}</span><div class="segs">${["off", "daily", "weekly"].map((v) => `<button class="seg ${b.auto === v ? "on" : ""}" data-bauto="${v}">${esc(L("b_" + v))}</button>`).join("")}</div></div>
      <div class="kv"><span>${esc(L("b_keep"))}</span><input type="number" min="1" max="60" class="bkeep" value="${b.keep}" style="max-width:100px"></div>
      <div class="row" style="margin-top:10px;gap:8px;flex-wrap:wrap"><button class="primary bnow" ${b.password ? "" : "disabled"}>${esc(L("b_create"))}</button>
        <label class="chip" style="cursor:pointer;padding:10px 16px">${esc(L("b_upload"))}<input type="file" accept=".mhbackup" class="bup" hidden></label></div>
      <h4>${esc(L("b_list"))}</h4>${a.backups.length ? a.backups.map((x) => `<div class="kv"><div>${esc(x.name)}<div class="why">${(x.size / 1024).toFixed(0)} kB · ${esc(fmtDate(new Date(x.mtime * 1000).toISOString(), lang, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }))}</div></div>
        <div class="row"><button class="ghost" data-bdl="${esc(x.name)}" title="${esc(L("b_download"))}">⬇</button><button class="ghost" data-brs="${esc(x.name)}">${esc(L("b_restore"))}</button>
        <button class="ghost danger" data-bdel="${esc(x.name)}" title="${esc(L("b_delete"))}">🗑</button></div></div>`).join("") : `<div class="hint">${esc(L("b_none"))}</div>`}
      <div class="restore"></div>`, "wide");
    out.push(`<datalist id="mh-all">${Object.keys(this._hass.states).slice(0, 4000).map((e) => `<option value="${esc(e)}">`).join("")}</datalist>`);
    this._bind = (root) => this.bindAdmin(root, a);
    return out.join("");
  }
  bindAdmin(root, a) {
    const L = (k, v) => this.t(k, v), s = a.settings;
    const setS = async (changes) => { const r = await this.call("admin_settings", { changes }, true); this._admin = Object.assign(this._admin || {}, r); toast(this.shadowRoot, L("saved_short") + " ✓"); return r; };
    root.querySelectorAll("[data-pp]").forEach((r) => r.addEventListener("click", () => { this._adminEdit = r.dataset.pp; this.render(true); }));
    root.querySelectorAll("[data-create]").forEach((b) => b.addEventListener("click", () => this.createWizard(root.querySelector(".cwiz"), b.dataset.create, a)));
    if (this._adminFocus && this._adminFocus.user) {
      const hp = a.ha_persons.find((x) => x.user_id === this._adminFocus.user && !x.taken);
      if (hp) this.createWizard(root.querySelector(".cwiz"), hp.entity_id, a);
      this._adminFocus = null;
    }
    root.querySelectorAll("[data-dismiss]").forEach((b) => b.addEventListener("click", async () => { await this.call("admin_dismiss_request", { user_id: b.dataset.dismiss }, true); this.render(true); }));
    root.querySelectorAll("[data-st]").forEach((inp) => inp.addEventListener("change", () => {
      let v = inp.value; if (inp.type === "number") v = parseInt(v, 10); if (v === "") v = null;
      setS({ [inp.dataset.st]: v });
    }));
    root.querySelectorAll("[data-sttime]").forEach((inp) => bindTimeField(inp, (v) => setS({ [inp.dataset.sttime]: v })));
    root.querySelectorAll("[data-load]").forEach((b) => b.addEventListener("click", async () => { await setS({ load_level: parseInt(b.dataset.load, 10) }); this.render(true); }));
    root.querySelectorAll("[data-stt]").forEach((b) => b.addEventListener("click", async () => { await setS({ [b.dataset.stt]: !s[b.dataset.stt] }); this.render(true); }));
    root.querySelectorAll("[data-atrm]").forEach((b) => b.addEventListener("click", async () => { const t = s.admin_targets.slice(); t.splice(parseInt(b.dataset.atrm, 10), 1); await setS({ admin_targets: t }); this.render(true); }));
    root.querySelector(".atadd").addEventListener("click", async () => { const v = root.querySelector(".atsel").value; if (!v) return; await setS({ admin_targets: s.admin_targets.concat([{ kind: "service", service: v, name: v }]) }); this.render(true); });
    const apFlow = async (off) => {
      try {
        const pin = off ? null : await this.pinEntry(L("pin_new"));
        await this.call("admin_set_pin", { pin }, true);
        this.api.adminSession = null;
        toast(this.shadowRoot, off ? L("pin_removed") : L("pin_set_ok"));
        this.render(true);
      } catch (e) { /* abgebrochen */ }
    };
    const aps = root.querySelector(".apset"), apc = root.querySelector(".apchg"), apr = root.querySelector(".aprm");
    if (aps) aps.addEventListener("click", () => apFlow(false));
    if (apc) apc.addEventListener("click", () => apFlow(false));
    if (apr) apr.addEventListener("click", () => apFlow(true));
    // LLM
    root.querySelector("[data-llm-en]").addEventListener("click", async () => {
      if (!s.llm.enabled && !s.llm.accepted) {
        if (!(await this.confirm(`${L("llm_warn_title")}\n\n${L("llm_warn")}`, L("llm_accept")))) return;
        await this.call("admin_llm", { changes: { accepted: true, enabled: true } }, true);
      } else await this.call("admin_llm", { changes: { enabled: !s.llm.enabled } }, true);
      this._me = await this.api.call("me");
      this.render(true);
    });
    root.querySelectorAll("[data-llm-mode]").forEach((b) => b.addEventListener("click", async () => { await this.call("admin_llm", { changes: { mode: b.dataset.llmMode } }, true); this.render(true); }));
    root.querySelectorAll("[data-llm-k]").forEach((sel) => sel.addEventListener("change", () => this.call("admin_llm", { changes: { [sel.dataset.llmK]: sel.value || null } }, true)));
    // Backup
    root.querySelector(".bpwset").addEventListener("click", async () => {
      const pw = root.querySelector(".bpw").value;
      try { await this.call("backup_password", { password: pw || null }, true); toast(this.shadowRoot, L("saved_short") + " ✓"); this.render(true); }
      catch (e) { shake(root.querySelector(".bpw")); toast(this.shadowRoot, e.code === "password_short" ? (this.lang === "de" ? "Mindestens 8 Zeichen" : "At least 8 characters") : L("error")); }
    });
    root.querySelectorAll("[data-bauto]").forEach((b) => b.addEventListener("click", async () => { await setS({ backup: { auto: b.dataset.bauto } }); this.render(true); }));
    root.querySelector(".bkeep").addEventListener("change", (ev) => setS({ backup: { keep: parseInt(ev.target.value, 10) } }));
    root.querySelector(".bnow").addEventListener("click", async (ev) => {
      ev.target.disabled = true;
      try { await this.call("backup_create", {}, true); toast(this.shadowRoot, L("b_created")); this.render(true); } catch (e) { toast(this.shadowRoot, L("error")); ev.target.disabled = false; }
    });
    root.querySelectorAll("[data-bdl]").forEach((b) => b.addEventListener("click", async () => {
      const q = this.api.adminSession ? `?admin_session=${encodeURIComponent(this.api.adminSession)}` : "";
      const r = await this._hass.fetchWithAuth(`/api/mental_health/backup/${encodeURIComponent(b.dataset.bdl)}${q}`);
      if (!r.ok) { toast(this.shadowRoot, L("error")); return; }
      const blob = await r.blob();
      const el = document.createElement("a"); el.href = URL.createObjectURL(blob); el.download = b.dataset.bdl; el.click(); setTimeout(() => URL.revokeObjectURL(el.href), 3000);
    }));
    root.querySelectorAll("[data-brs]").forEach((b) => b.addEventListener("click", () => this.restoreFlow(root.querySelector(".restore"), b.dataset.brs, a)));
    root.querySelectorAll("[data-bdel]").forEach((b) => b.addEventListener("click", async () => {
      const name = b.dataset.bdel;
      if (!(await this.confirm(L("b_delete_confirm", { name }), L("delete")))) return;
      const row = b.closest(".kv");
      try {
        await this.call("backup_delete", { name }, true);
        if (row && !reduced()) { row.style.transition = "opacity .25s, transform .25s"; row.style.opacity = "0"; row.style.transform = "translateX(12px)"; }
        toast(this.shadowRoot, L("b_deleted"));
        setTimeout(() => this.render(true), reduced() ? 0 : 260);
      } catch (e) { toast(this.shadowRoot, L("error")); }
    }));
    root.querySelector(".bup").addEventListener("change", async (ev) => {
      const f = ev.target.files[0]; if (!f) return;
      const q = this.api.adminSession ? `?admin_session=${encodeURIComponent(this.api.adminSession)}` : "";
      const r = await this._hass.fetchWithAuth(`/api/mental_health/backup${q}`, { method: "POST", body: f });
      const j = await r.json().catch(() => ({}));
      if (!r.ok) { toast(this.shadowRoot, L("error") + (j.error ? ` (${j.error})` : "")); return; }
      await this.render(true);
      this.restoreFlow(this.shadowRoot.querySelector(".restore"), j.name, a);
    });
  }
  restoreFlow(box, name, a) {
    const L = (k, v) => this.t(k, v), lang = this.lang;
    box.innerHTML = `<div class="tile rise" style="margin-top:14px"><b>${esc(L("b_restore"))}: ${esc(name)}</b>
      <div class="row" style="margin-top:10px;gap:8px"><input type="password" class="rpw" placeholder="${esc(L("b_enter_pw"))}"><button class="rprev">${esc(L("b_preview"))}</button></div><div class="rbody"></div></div>`;
    box.querySelector(".rprev").addEventListener("click", async () => {
      const pw = box.querySelector(".rpw").value;
      let pv;
      try { pv = await this.call("backup_preview", { name, password: pw }, true); } catch (e) { shake(box.querySelector(".rpw")); toast(this.shadowRoot, e.code === "wrong_password" ? L("pin_wrong").replace("{n}", "…") : L("error")); return; }
      const body = box.querySelector(".rbody");
      body.innerHTML = `<div class="sub" style="margin-top:10px">${esc(fmtDate(pv.created, lang, { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit" }))} · v${esc(pv.version)} · ${(pv.size / 1024).toFixed(0)} kB</div>
        ${pv.persons.map((x) => `<div class="kv"><span>${esc(x.name)}</span><span class="hint">${x.days} ${this.lang === "de" ? "Tage" : "days"}</span></div>`).join("")}
        <div class="kv"><span>${esc(L("b_scope"))}</span><select class="rscope"><option value="all">${esc(L("b_all"))}</option><option value="config">${esc(L("b_config"))}</option>${pv.persons.map((x) => `<option value="p:${esc(x.id)}">${esc(L("b_person"))}: ${esc(x.name)}</option>`).join("")}</select></div>
        <div class="hint" style="margin:8px 0">${esc(L("b_restore_hint"))}</div><button class="primary rgo">${esc(L("b_restore_go"))}</button>`;
      body.querySelector(".rgo").addEventListener("click", async () => {
        const sc = body.querySelector(".rscope").value;
        const data = { name, password: pw, scope: sc.startsWith("p:") ? "person" : sc };
        if (sc.startsWith("p:")) data.pid = sc.slice(2);
        try { await this.call("backup_restore", data, true); toast(this.shadowRoot, L("b_restored")); setTimeout(() => this.boot(), 4000); } catch (e) { toast(this.shadowRoot, L("error")); }
      });
    });
  }
  createWizard(box, entity, a) {
    const L = (k, v) => this.t(k, v);
    const hp = a.ha_persons.find((x) => x.entity_id === entity);
    const data = { name: hp ? hp.name : "", child: false, can_edit_own: false, birthdate: "", sex: "unspecified", modules: {} };
    let step = 0;
    const age = () => { const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(data.birthdate || ""); if (!m) return null; const b = new Date(+m[1], +m[2] - 1, +m[3]); const n = new Date(); let a2 = n.getFullYear() - b.getFullYear(); if (n < new Date(n.getFullYear(), b.getMonth(), b.getDate())) a2--; return a2; };
    const draw = () => {
      const ag = age();
      box.innerHTML = `<div class="tile rise" style="margin-top:14px"><div class="steps">${[0, 1, 2].map((k) => `<i class="${k <= step ? "on" : ""}"></i>`).join("")}</div>
        ${step === 0 ? `<div class="field"><label class="lbl">${esc(L("p_name"))}</label><input class="wn" value="${esc(data.name)}"></div>
          <div class="grid2"><div class="field" style="grid-column:1 / -1"><label class="lbl">${esc(L("p_birthdate"))}</label>${dateMaskHtml("wbirth", data.birthdate, this.lang, { noYear: true, clear: true })}<div class="hint" style="margin-top:6px">${esc(L("p_birth_noyear"))}</div></div>
          <div class="field"><label class="lbl">${esc(L("p_sex"))}</label><select class="ws">${["female", "male", "other", "unspecified"].map((s) => `<option value="${s}" ${data.sex === s ? "selected" : ""}>${esc(L("sex_" + s))}</option>`).join("")}</select></div></div>`
        : step === 1 ? `<div class="kv"><div>${esc(L("a_child"))}<div class="why">${esc(L("a_child_hint"))}</div>${ag != null && ag <= 12 && !data.child ? `<div class="why" style="color:var(--c-amber)">${esc(L("a_child_suggest", { n: ag }))}</div>` : ""}</div><button class="toggle ${data.child ? "on" : ""}" data-w="child"></button></div>
          ${!data.child ? `<div class="kv"><div>${esc(L("a_can_edit"))}</div><button class="toggle ${data.can_edit_own ? "on" : ""}" data-w="can_edit_own"></button></div>` : ""}`
        : `<div class="hint" style="margin-bottom:8px">${esc(L("p_modules"))}</div>${MODULE_KEYS.filter((m) => m !== "mood" && m !== "llm").map((m) => {
          const def = { weight: false, cycle: false }[m] ?? true;
          const on = data.modules[m] ?? (data.child && m === "weight" ? false : def);
          const no = m === "cycle" && !["female", "other"].includes(data.sex);
          return `<div class="kv"><span>${esc(L(m === "training" && data.child ? "m_training_child" : "m_" + m))}</span><button class="toggle ${on && !no ? "on" : ""}" data-wm="${m}" ${no ? "disabled" : ""}></button></div>`;
        }).join("")}`}
        <div class="row" style="margin-top:12px;justify-content:flex-end;gap:8px">${step ? `<button class="ghost wprev">${esc(L("back"))}</button>` : `<button class="ghost wcancel">${esc(L("cancel"))}</button>`}
          <button class="primary wnext">${esc(step < 2 ? L("next") : L("a_create"))}</button></div></div>`;
      const q = (x) => box.querySelector(x);
      if (q(".wn")) q(".wn").addEventListener("input", () => { data.name = q(".wn").value; });
      const wb = box.querySelector('[data-dm="wbirth"]');
      if (wb) bindDateMask(wb, (v) => { data.birthdate = v || ""; });
      if (q(".ws")) q(".ws").addEventListener("change", () => { data.sex = q(".ws").value; });
      box.querySelectorAll("[data-w]").forEach((b) => b.addEventListener("click", () => { data[b.dataset.w] = !data[b.dataset.w]; draw(); }));
      box.querySelectorAll("[data-wm]").forEach((b) => b.addEventListener("click", () => { data.modules[b.dataset.wm] = !b.classList.contains("on"); draw(); }));
      if (q(".wcancel")) q(".wcancel").addEventListener("click", () => { box.innerHTML = ""; });
      if (q(".wprev")) q(".wprev").addEventListener("click", () => { step--; draw(); });
      q(".wnext").addEventListener("click", async () => {
        if (step < 2) {
          const wbx = box.querySelector('[data-dm="wbirth"]');
          if (step === 0 && wbx && dmValue(wbx) === undefined) { shake(wbx); return; }
          step++; draw(); return;
        }
        const payload = Object.assign({}, data);
        if (!payload.birthdate) delete payload.birthdate;
        try {
          await this.call("admin_create_person", { person_entity: entity, data: payload }, true);
          toast(this.shadowRoot, L("a_created", { name: data.name }));
          this._me = await this.api.call("me");
          this.render(true);
        } catch (e) { toast(this.shadowRoot, L("error")); }
      });
    };
    draw();
    box.scrollIntoView({ behavior: reduced() ? "auto" : "smooth", block: "center" });
  }
}

if (!customElements.get("mental-health-panel")) customElements.define("mental-health-panel", MHPanel);
