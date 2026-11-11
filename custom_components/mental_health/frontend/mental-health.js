/* Mental Health and Health Improvements for HAOS by Kilian K. – core + dashboard cards
 * Loaded on every dashboard (add_extra_js_url). The large panel lives in mental-health-panel.js
 * and is only loaded when the sidebar panel opens (keeps every page light on phones).
 * Vanilla JS + SVG, no external libraries. Design: Obsidian Teal tokens, no glass look.
 */
const SELF_URL = import.meta.url;
(() => {
if (window.__MH) return;
const VERSION = "1.0.0";
const DOMAIN = "mental_health";
const PANEL = "/mental-health";

/* ============================================================ Sprache */
const I18N = {
  en: {
    app: "Mental Health", loading: "Loading…", retry: "Try again", save: "Save", cancel: "Cancel", close: "Close",
    back: "Back", next: "Next", done: "Done", edit: "Edit", delete: "Delete", yes: "Yes", no: "No", ok: "OK",
    error: "Something went wrong.", not_loaded: "Mental Health is not set up yet.",
    hello_m: "Good morning", hello_d: "Hello", hello_e: "Good evening", hello_n: "Good night",
    mood: "Mood", energy: "Energy", health: "How healthy do you feel?", sleep_quality: "Sleep quality",
    health_score: "Health score", sleep: "Sleep", weight: "Weight", training: "Training", cycle: "Cycle",
    birthdays: "Birthdays", family: "Family", today: "Today", streak: "{n} day streak",
    morning: "Morning", evening: "Evening", checkin: "Check-in", checkin_morning: "Morning check-in",
    checkin_evening: "Evening check-in", open_now: "Open now", start: "Start", enter_evening: "Fill in evening",
    enter_morning: "Fill in morning", done_today: "Done for today ✓", checkin_open: "Your {slot} check-in is open",
    until: "until {t}", saved: "Saved ✓", required_missing: "Please fill in the marked fields.",
    not_allowed: "Not possible right now.", late: "Filled in later", from_time: "from {t}",
    // Felder
    f_mood: "How are you feeling?", f_mood_child: "How are you today?", f_energy: "Energy",
    f_health: "How healthy do you feel today?", f_sleep_quality: "How well did you sleep?",
    f_soreness: "Muscle soreness", f_soreness_child: "Do your muscles hurt?",
    s0: "none", s1: "light", s2: "noticeable", s3: "strong",
    f_good: "Good things today", f_bad: "Not so good today", f_goals: "Intentions & goals for tomorrow",
    f_journal: "Journal", f_journal_ph: "Anything else on your mind? (optional)", f_good_ph: "Something good …",
    f_bad_ph: "Something not so good …", f_goal_ph: "e.g. go to bed earlier", add: "Add",
    f_trained: "Did you train today?", f_trained_child: "Did you do sport today?", f_type: "Type", f_minutes: "Minutes",
    tt_strength: "Strength", tt_cardio: "Cardio", tt_endurance: "Endurance", tt_mobility: "Mobility", tt_team: "Team sport",
    tt_other: "Other",
    f_weight: "Weight", f_weight_warn: "Your last weight is {n} days old.", f_weight_req: "Please enter your weight today (once).",
    f_period: "Do you have your period right now?", pa_no: "No", pa_yes: "Yes", pa_started: "Just started",
    pa_ended: "Over", f_flow: "Flow", fl_light: "light", fl_medium: "medium", fl_heavy: "heavy", fl_very_heavy: "very heavy",
    f_pain: "Pain", f_symptoms: "Symptoms (optional)",
    sy_cramps: "Cramps", sy_headache: "Headache", sy_fatigue: "Tiredness", sy_mood: "Mood", sy_bloating: "Bloating",
    sy_back_pain: "Back pain", sy_nausea: "Nausea", sy_tender_breasts: "Tender breasts", sy_acne: "Skin", sy_cravings: "Cravings",
    f_goals_review: "Yesterday you planned:", gr_done: "done", gr_partly: "partly", gr_not: "not",
    f_sleep: "Your night", sleep_confirm: "Confirm", sleep_correct: "Correct", sleep_skip: "Skip",
    sleep_ask: "I'm not quite sure here – does this fit?", sleep_learning: "The model is still learning (night {n} of ~14)",
    sleep_drag: "Drag the ends to correct the times.",
    forecast: "Mood forecast", forecast_learning: "I'm still getting to know you ({n} of {m} days).",
    forecast_conf: "{p} % sure", because: "because", optimum: "Optimum {t}", vs_week: "vs. week", vs_opt: "vs. optimum",
    training_good: "Today is a good day for a workout 💪", training_good_child: "Today is a great day for some exercise 🏃",
    training_overdue: "Due for {n} days – today?", training_pause: "Rest – recovery is part of training",
    training_ready_soon: "Almost ready again", early_training: "Recovery is part of training 🌱",
    ts_pause: "Rest", ts_ready_soon: "Ready soon", ts_recommended: "Recommended", ts_overdue: "Overdue",
    w_trend: "Trend", w_week: "vs. week", w_opt: "vs. optimum", w_add_height: "Add your height for an optimum.",
    w_below: "Your weight is below the healthy range. Best talk to a doctor about it.",
    w_fast: "Your weight is dropping very quickly. Best talk to a doctor about it.",
    bd_today: "Today is {name}'s birthday 🎂", bd_own: "Happy birthday! 🎉", bd_in: "{name} in {n} days",
    bd_tomorrow: "{name} tomorrow", turning: "turns {n}",
    protect_title: "You've had a few heavy days.",
    protect_text: "It can really help to talk to someone you trust. And if things feel too much, there are people who listen – any time, free and anonymous:",
    protect_de: "TelefonSeelsorge 0800 111 0 111 or 0800 111 0 222", protect_kids: "Nummer gegen Kummer 116 111 (children & teens)",
    protect_en: "Your local helplines and emergency numbers are there for you.",
    // Vorschau / Einrichtung
    preview_title: "Your personal companion", preview_badge: "Preview",
    preview_text: "Mood, sleep, journal and more – private, local and only visible to you. An admin needs to set it up for you first.",
    request: "Request setup", request_sent: "Request sent ✓", request_again: "You can ask again {t}.",
    pv_1: "Daily check-ins in under a minute", pv_2: "Sleep detection that learns", pv_3: "Insights about what does you good",
    pv_4: "Only you see your entries",
    // PIN
    pin_title: "Enter your PIN", pin_sub: "Your entries are protected.", pin_wrong: "Wrong PIN – {n} tries left.",
    pin_locked: "Locked until {t}.", admin_pin_title: "Admin PIN",
    // Karten
    card_person: "Your personal overview", card_family: "Family weather & health", card_checkin: "Check-in directly on the dashboard",
    card_sleep: "Last night & sleepmaxing", card_weight: "Weight trend", card_training: "Training rhythm",
    card_mood: "Mood chart", card_birthday: "Upcoming birthdays", checkin_note: "Entries belong to the logged-in Home Assistant user.",
    wall_note: "Wall display: the entry is saved for {name}.",
    no_data: "No data yet.", first_days: "Your first days – fill in a check-in and this fills up.",
    open_panel: "Open", days7: "7 D", days30: "30 D", days90: "3 M", days365: "1 Y", all: "All",
    family_not_enough: "Family values appear once at least {k} people have filled in.",
    weather_sunny: "Sunny", weather_mostly_sunny: "Mostly sunny", weather_cloudy: "Cloudy", weather_rain: "Rainy", weather_storm: "Stormy",
    participation: "Participation", trend: "Trend", ed_period: "Period", ed_title: "Title (optional)", ed_compact: "Compact",
    ed_show: "Show", paused: "Paused", paused_until: "Paused until {d}", no_sleep: "No night detected yet.",
    asleep: "asleep", in_bed: "in bed", away: "up", nap: "nap", st_asleep: "Asleep", st_in_bed: "In bed", st_away: "Up",
    st_nap: "Nap", interruptions: "{n} interruptions", latency: "fell asleep after {n} min", conf: "confidence {p} %",
    learning_hint: "Learning", min: "min", h: "h", kg: "kg",
  },
  de: {
    app: "Mental Health", loading: "Lädt …", retry: "Erneut versuchen", save: "Speichern", cancel: "Abbrechen", close: "Schließen",
    back: "Zurück", next: "Weiter", done: "Fertig", edit: "Bearbeiten", delete: "Löschen", yes: "Ja", no: "Nein", ok: "OK",
    error: "Da ist etwas schiefgegangen.", not_loaded: "Mental Health ist noch nicht eingerichtet.",
    hello_m: "Guten Morgen", hello_d: "Hallo", hello_e: "Guten Abend", hello_n: "Gute Nacht",
    mood: "Stimmung", energy: "Energie", health: "Wie gesund fühlst du dich?", sleep_quality: "Schlafqualität",
    health_score: "Health Score", sleep: "Schlaf", weight: "Gewicht", training: "Training", cycle: "Zyklus",
    birthdays: "Geburtstage", family: "Familie", today: "Heute", streak: "{n} Tage in Folge",
    morning: "Morgen", evening: "Abend", checkin: "Check-in", checkin_morning: "Morgen-Check-in",
    checkin_evening: "Abend-Check-in", open_now: "Jetzt öffnen", start: "Starten", enter_evening: "Abend eintragen",
    enter_morning: "Morgen eintragen", done_today: "Für heute erledigt ✓", checkin_open: "Dein {slot}-Check-in ist offen",
    until: "bis {t}", saved: "Gespeichert ✓", required_missing: "Bitte die markierten Felder ausfüllen.",
    not_allowed: "Gerade nicht möglich.", late: "Nachgetragen", from_time: "ab {t}",
    f_mood: "Wie geht es dir?", f_mood_child: "Wie geht's dir heute?", f_energy: "Energie",
    f_health: "Wie gesund fühlst du dich heute?", f_sleep_quality: "Wie gut hast du geschlafen?",
    f_soreness: "Muskelkater", f_soreness_child: "Tun dir die Muskeln weh?",
    s0: "keiner", s1: "leicht", s2: "spürbar", s3: "stark",
    f_good: "Gute Dinge heute", f_bad: "Nicht so gut heute", f_goals: "Vorsätze & Ziele für morgen",
    f_journal: "Journal", f_journal_ph: "Noch etwas auf dem Herzen? (optional)", f_good_ph: "Etwas Gutes …",
    f_bad_ph: "Etwas nicht so Gutes …", f_goal_ph: "z. B. früher ins Bett", add: "Hinzufügen",
    f_trained: "Heute trainiert?", f_trained_child: "Heute Sport gemacht?", f_type: "Art", f_minutes: "Minuten",
    tt_strength: "Kraft", tt_cardio: "Cardio", tt_endurance: "Ausdauer", tt_mobility: "Beweglichkeit", tt_team: "Teamsport",
    tt_other: "Anderes",
    f_weight: "Gewicht", f_weight_warn: "Dein letztes Gewicht ist {n} Tage alt.", f_weight_req: "Bitte trag heute (einmalig) dein Gewicht ein.",
    f_period: "Hast du gerade deine Periode?", pa_no: "Nein", pa_yes: "Ja", pa_started: "Gerade begonnen",
    pa_ended: "Vorbei", f_flow: "Stärke", fl_light: "leicht", fl_medium: "mittel", fl_heavy: "stark", fl_very_heavy: "sehr stark",
    f_pain: "Schmerz", f_symptoms: "Symptome (optional)",
    sy_cramps: "Krämpfe", sy_headache: "Kopfschmerz", sy_fatigue: "Müdigkeit", sy_mood: "Stimmung", sy_bloating: "Blähbauch",
    sy_back_pain: "Rückenschmerz", sy_nausea: "Übelkeit", sy_tender_breasts: "Spannen in der Brust", sy_acne: "Haut", sy_cravings: "Heißhunger",
    f_goals_review: "Gestern hast du dir vorgenommen:", gr_done: "geschafft", gr_partly: "teilweise", gr_not: "nicht",
    f_sleep: "Deine Nacht", sleep_confirm: "Bestätigen", sleep_correct: "Korrigieren", sleep_skip: "Überspringen",
    sleep_ask: "Hier bin ich mir nicht ganz sicher – passt das?", sleep_learning: "Das Modell lernt noch (Nacht {n} von ~14)",
    sleep_drag: "Zieh an den Enden, um die Zeiten zu korrigieren.",
    forecast: "Stimmungsprognose", forecast_learning: "Ich lerne dich noch kennen ({n} von {m} Tagen).",
    forecast_conf: "{p} % sicher", because: "weil", optimum: "Optimum {t}", vs_week: "ggü. Woche", vs_opt: "ggü. Optimum",
    training_good: "Heute ist ein guter Tag für ein Training 💪", training_good_child: "Heute ist ein super Tag für Bewegung 🏃",
    training_overdue: "Seit {n} Tagen fällig – heute?", training_pause: "Pause – Erholung gehört dazu",
    training_ready_soon: "Bald wieder bereit", early_training: "Erholung ist Teil des Trainings 🌱",
    ts_pause: "Pause", ts_ready_soon: "Bald bereit", ts_recommended: "Empfohlen", ts_overdue: "Überfällig",
    w_trend: "Trend", w_week: "ggü. Woche", w_opt: "ggü. Optimum", w_add_height: "Gib deine Größe an, dann gibt es ein Optimum.",
    w_below: "Dein Gewicht liegt unter dem gesunden Bereich. Sprich am besten mit einer Ärztin oder einem Arzt darüber.",
    w_fast: "Dein Gewicht sinkt sehr schnell. Sprich am besten mit einer Ärztin oder einem Arzt darüber.",
    bd_today: "Heute hat {name} Geburtstag 🎂", bd_own: "Alles Gute zum Geburtstag! 🎉", bd_in: "{name} in {n} Tagen",
    bd_tomorrow: "{name} morgen", turning: "wird {n}",
    protect_title: "Du hattest ein paar schwere Tage.",
    protect_text: "Es kann richtig gut tun, mit jemandem zu sprechen, dem du vertraust. Und wenn es zu viel wird: Es gibt Menschen, die zuhören – rund um die Uhr, kostenlos und anonym:",
    protect_de: "TelefonSeelsorge 0800 111 0 111 oder 0800 111 0 222", protect_kids: "Nummer gegen Kummer 116 111 (für Kinder und Jugendliche)",
    protect_en: "Örtliche Hilfsangebote und Notrufnummern sind für dich da.",
    preview_title: "Dein persönlicher Begleiter", preview_badge: "Vorschau",
    preview_text: "Stimmung, Schlaf, Journal und mehr – privat, lokal und nur für dich sichtbar. Ein Admin muss es zuerst für dich einrichten.",
    request: "Einrichtung anfragen", request_sent: "Anfrage gesendet ✓", request_again: "Erneut anfragen geht {t}.",
    pv_1: "Tägliche Check-ins in unter einer Minute", pv_2: "Schlaferkennung, die dazulernt", pv_3: "Einblicke, was dir guttut",
    pv_4: "Nur du siehst deine Einträge",
    pin_title: "PIN eingeben", pin_sub: "Deine Einträge sind geschützt.", pin_wrong: "Falsche PIN – noch {n} Versuche.",
    pin_locked: "Gesperrt bis {t}.", admin_pin_title: "Admin-PIN",
    card_person: "Deine persönliche Übersicht", card_family: "Familien-Wetter & Health Score", card_checkin: "Check-in direkt im Dashboard",
    card_sleep: "Letzte Nacht & Sleepmaxing", card_weight: "Gewichtstrend", card_training: "Trainingsrhythmus",
    card_mood: "Stimmungsverlauf", card_birthday: "Nächste Geburtstage", checkin_note: "Einträge gehören zum angemeldeten Home-Assistant-Benutzer.",
    wall_note: "Wanddisplay: Der Eintrag wird für {name} gespeichert.",
    no_data: "Noch keine Daten.", first_days: "Deine ersten Tage – trag einen Check-in ein, dann füllt sich das hier.",
    open_panel: "Öffnen", days7: "7 T", days30: "30 T", days90: "3 M", days365: "1 J", all: "Alles",
    family_not_enough: "Familienwerte erscheinen, sobald mindestens {k} Personen eingetragen haben.",
    weather_sunny: "Sonnig", weather_mostly_sunny: "Heiter", weather_cloudy: "Wolkig", weather_rain: "Regnerisch", weather_storm: "Stürmisch",
    participation: "Teilnahme", trend: "Trend", ed_period: "Zeitraum", ed_title: "Titel (optional)", ed_compact: "Kompakt",
    ed_show: "Anzeigen", paused: "Pausiert", paused_until: "Pausiert bis {d}", no_sleep: "Noch keine Nacht erkannt.",
    asleep: "schläft", in_bed: "im Bett", away: "wach", nap: "Nickerchen", st_asleep: "Schläft", st_in_bed: "Im Bett", st_away: "Wach",
    st_nap: "Nickerchen", interruptions: "{n} Unterbrechungen", latency: "nach {n} min eingeschlafen", conf: "Konfidenz {p} %",
    learning_hint: "Lernt", min: "min", h: "h", kg: "kg",
  },
};
const normLang = (v) => (String(v || "").toLowerCase().split(/[-_]/)[0] === "de" ? "de" : "en");
const langOf = (hass) => normLang(hass && ((hass.locale && hass.locale.language) || hass.language));
function tr(lang, key, vars) {
  let s = (I18N[lang] && I18N[lang][key]) || I18N.en[key] || key;
  if (vars) for (const k of Object.keys(vars)) s = s.split("{" + k + "}").join(vars[k]);
  return s;
}
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const reduced = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ============================================================ Formatierung */
function fmtNum(v, d = 1, lang = "en") {
  if (v == null || isNaN(v)) return "–";
  return Number(v).toLocaleString(lang === "de" ? "de-DE" : "en-GB", { minimumFractionDigits: d, maximumFractionDigits: d });
}
function fmtTime(iso, lang) {
  if (!iso) return "–";
  const d = new Date(iso);
  return d.toLocaleTimeString(lang === "de" ? "de-DE" : "en-GB", { hour: "2-digit", minute: "2-digit" });
}
function fmtDate(iso, lang, opts) {
  if (!iso) return "–";
  const d = typeof iso === "string" && iso.length === 10 ? new Date(iso + "T12:00:00") : new Date(iso);
  return d.toLocaleDateString(lang === "de" ? "de-DE" : "en-GB", opts || { weekday: "short", day: "numeric", month: "short" });
}
function fmtDur(min, lang) {
  if (min == null) return "–";
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return `${h} h ${String(m).padStart(2, "0")} min`;
}
const sign = (v, d = 0, lang = "en") => (v == null ? "–" : (v > 0 ? "+" : v < 0 ? "−" : "±") + fmtNum(Math.abs(v), d, lang));

/* ============================================================ Stimmungsfarben/Emojis */
const MOOD_EMOJI = ["😫", "😣", "😞", "😕", "😐", "🙂", "😊", "😄", "😁", "🤩"];
const KID_EMOJI = ["😢", "😢", "😟", "😟", "😐", "🙂", "😊", "😃", "😄", "🥳"];
const moodEmoji = (v, kid) => (v == null ? "·" : (kid ? KID_EMOJI : MOOD_EMOJI)[clamp(Math.round(v), 1, 10) - 1]);
function moodColor(v) {
  if (v == null) return "var(--c-line)";
  const t = clamp((v - 1) / 9, 0, 1);
  // rot -> bernstein -> teal
  const stops = [[239, 123, 99], [245, 177, 76], [47, 214, 176]];
  const seg = t < 0.5 ? 0 : 1, f = t < 0.5 ? t * 2 : (t - 0.5) * 2;
  const a = stops[seg], b = stops[seg + 1];
  return `rgb(${a.map((x, i) => Math.round(x + (b[i] - x) * f)).join(",")})`;
}
const toneColor = (c) => (c === "good" ? "var(--c-good)" : c === "bad" ? "var(--c-red)" : "var(--c-teal)");
const WEATHER = { sunny: "☀️", mostly_sunny: "🌤️", cloudy: "⛅", rain: "🌧️", storm: "⛈️" };

/* ============================================================ CSS */
const CSS = `
:host{
  --c-bg: var(--primary-background-color, #0b0c0e);
  --c-surface: var(--ha-card-background, var(--card-background-color, #17181c));
  --c-raise: var(--gray200, var(--secondary-background-color, #202227));
  --c-raise2: var(--gray300, #2b2d34);
  --c-line: var(--gray400, var(--divider-color, #3f414b));
  --c-teal: var(--teal, var(--primary-color, #2fd6b0));
  --c-amber: var(--amber, #f5b14c);
  --c-ink: var(--text-primary-color, #04130f);
  --c-text: var(--primary-text-color, #f1f2f4);
  --c-muted: var(--secondary-text-color, #868894);
  --c-red: var(--red, var(--error-color, #ef7b63));
  --c-good: #4ade80;
  --c-violet: #a78bfa;
  --c-active: var(--ob-active-teal, rgba(47,214,176,.14));
  --c-press: var(--ob-press, rgba(255,255,255,0.07));
  --c-scrim: var(--ob-scrim, rgba(5,6,8,0.45));
  --c-blur: var(--ob-blur, blur(14px) brightness(0.7));
  --rad: var(--ha-card-border-radius, 28px);
  --rad-in: var(--ob-radius-inner, 20px);
  --ease: var(--ob-ease, cubic-bezier(0.22,1,0.36,1));
  --spring: var(--ob-spring, cubic-bezier(0.34,1.56,0.64,1));
  --font: var(--primary-font-family, 'Outfit','Manrope','Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif);
  display:block; font-family:var(--font); color:var(--c-text); -webkit-tap-highlight-color:transparent;
}
*{ box-sizing:border-box; }
[hidden]{ display:none !important; }
.card{ position:relative; background:var(--c-surface); border-radius:var(--rad); padding:18px; overflow:hidden; height:100%; }
.title{ font-size:19px; font-weight:600; letter-spacing:.2px; }
.sub{ font-size:13px; color:var(--c-muted); }
.hint{ font-size:12px; color:var(--c-muted); line-height:1.45; }
.row{ display:flex; align-items:center; gap:10px; }
.col{ display:flex; flex-direction:column; gap:10px; }
.spacer{ flex:1; }
.grid2{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
button{ font-family:inherit; cursor:pointer; color:var(--c-text); background:var(--c-raise); border:0; border-radius:999px; padding:10px 18px; font-size:14px; font-weight:500;
  transition:background .2s var(--ease), transform .16s var(--spring), color .2s var(--ease), opacity .2s, box-shadow .2s; }
@media (hover:hover){ button:hover{ background:var(--c-raise2); } }
button:active{ transform:scale(.97); background:var(--c-press); }
button:disabled{ opacity:.4; cursor:default; transform:none; }
button.primary{ background:var(--c-teal); color:var(--c-ink); font-weight:600; }
@media (hover:hover){ button.primary:hover{ background:var(--c-teal); filter:brightness(1.08); } }
button.ghost{ background:transparent; color:var(--c-muted); }
button.on, .chip.on{ background:var(--c-active); color:var(--c-teal); font-weight:600; }
button.danger{ color:var(--c-red); }
.chip{ display:inline-flex; align-items:center; gap:6px; font-size:12.5px; padding:6px 12px; border-radius:999px; background:var(--c-raise); color:var(--c-text); border:0; }
.chip.small{ font-size:11.5px; padding:4px 10px; }
.chip.teal{ background:var(--c-active); color:var(--c-teal); }
.chip.good{ background:rgba(74,222,128,.13); color:var(--c-good); }
.chip.bad{ background:rgba(239,123,99,.14); color:var(--c-red); }
.chip.amber{ background:rgba(245,177,76,.14); color:var(--c-amber); }
.segs{ display:inline-flex; background:var(--c-raise); border-radius:999px; padding:3px; gap:2px; flex-wrap:wrap; }
.seg{ padding:7px 13px; font-size:13px; background:transparent; color:var(--c-muted); }
.seg.on{ background:var(--c-active); color:var(--c-teal); font-weight:600; }
.tile{ background:var(--c-raise); border-radius:var(--rad-in); padding:14px; position:relative; overflow:hidden; }
.tile .k{ font-size:12px; color:var(--c-muted); }
.tile .v{ font-size:24px; font-weight:600; margin-top:2px; }
.big{ font-size:34px; font-weight:600; line-height:1.1; }
.emoji{ font-size:30px; line-height:1; }
.rise{ animation:mh-rise .42s var(--ease) both; }
.fade{ animation:mh-fade .3s var(--ease) both; }
.pop{ animation:mh-pop .38s var(--spring) both; }
.pulse{ animation:mh-pulse 2.4s ease-in-out infinite; }
.shake{ animation:mh-shake .42s var(--ease); }
@keyframes mh-rise{ from{ opacity:0; transform:translateY(10px) } to{ opacity:1; transform:none } }
@keyframes mh-fade{ from{ opacity:0 } to{ opacity:1 } }
@keyframes mh-pop{ 0%{ opacity:0; transform:scale(.86) } 100%{ opacity:1; transform:none } }
@keyframes mh-pulse{ 0%,100%{ box-shadow:0 0 0 0 rgba(47,214,176,.35) } 50%{ box-shadow:0 0 0 9px rgba(47,214,176,0) } }
@keyframes mh-shake{ 0%,100%{ transform:none } 20%{ transform:translateX(-7px) } 40%{ transform:translateX(6px) } 60%{ transform:translateX(-4px) } 80%{ transform:translateX(3px) } }
@keyframes mh-breathe{ 0%,100%{ transform:scale(1); opacity:.9 } 50%{ transform:scale(1.04); opacity:1 } }
@keyframes mh-spin{ to{ transform:rotate(360deg) } }
@keyframes mh-dash{ from{ stroke-dashoffset:var(--len) } }
@keyframes mh-conf{ 0%{ transform:translate(0,0) rotate(0); opacity:1 } 100%{ transform:translate(var(--dx),var(--dy)) rotate(var(--rot)); opacity:0 } }
.spinner{ width:22px; height:22px; border-radius:50%; border:2.5px solid var(--c-line); border-top-color:var(--c-teal); animation:mh-spin .9s linear infinite; }
.center{ display:grid; place-items:center; padding:30px 10px; text-align:center; gap:10px; color:var(--c-muted); }
.ring-val{ font-weight:600; }
.badge{ display:inline-grid; place-items:center; min-width:20px; height:20px; padding:0 6px; border-radius:10px; background:var(--c-teal); color:var(--c-ink); font-size:11px; font-weight:700; }
.toast{ position:fixed; left:50%; bottom:22px; transform:translate(-50%,20px); opacity:0; background:var(--c-raise2); color:var(--c-text); padding:11px 18px; border-radius:999px; font-size:14px; box-shadow:0 10px 30px rgba(0,0,0,.35); transition:transform .3s var(--spring), opacity .25s var(--ease); z-index:20; pointer-events:none; }
.toast.show{ transform:translate(-50%,0); opacity:1; }
.scrim{ position:fixed; inset:0; background:var(--c-scrim); backdrop-filter:var(--c-blur); -webkit-backdrop-filter:var(--c-blur); display:grid; place-items:center; z-index:10; animation:mh-fade .2s var(--ease); padding:16px; }
.dialog{ background:var(--c-surface); border-radius:var(--rad); padding:22px; width:min(420px,100%); max-height:88vh; overflow:auto; animation:mh-pop .32s var(--spring); }
.pinbox{ text-align:center; }
.pin-dots{ display:flex; justify-content:center; gap:14px; margin:18px 0; }
.pin-dots i{ width:14px; height:14px; border-radius:50%; background:var(--c-raise2); transition:background .2s, transform .2s var(--spring); }
.pin-dots i.on{ background:var(--c-teal); transform:scale(1.15); }
.pin-pad{ display:grid; grid-template-columns:repeat(3,64px); gap:12px; justify-content:center; }
.pin-pad button{ height:64px; font-size:22px; padding:0; border-radius:50%; }
input, textarea, select{ font-family:inherit; font-size:15px; color:var(--c-text); background:var(--c-raise); border:1.5px solid transparent; border-radius:14px; padding:11px 14px; width:100%; outline:none; transition:border-color .2s var(--ease), background .2s; }
input:focus, textarea:focus, select:focus{ border-color:var(--c-teal); background:var(--c-raise2); }
textarea{ min-height:96px; resize:vertical; line-height:1.5; }
label.lbl{ font-size:13px; color:var(--c-muted); display:block; margin:0 0 6px 2px; }
.field{ margin:0 0 18px; }
.field.err .lbl, .field.err .q{ color:var(--c-red); }
.field.err input, .field.err textarea{ border-color:var(--c-red); }
.q{ font-size:16px; font-weight:600; margin:0 0 10px; display:flex; align-items:center; gap:8px; }
.req{ color:var(--c-teal); font-size:13px; }
/* Regler mit Farbverlauf + Emoji */
.slider{ position:relative; padding:6px 0 4px; }
.slider .face{ position:absolute; top:-6px; transform:translateX(-50%); font-size:30px; transition:left .12s var(--ease); pointer-events:none; filter:drop-shadow(0 4px 10px rgba(0,0,0,.3)); }
.slider .face.bump{ animation:mh-pop .3s var(--spring); }
.slider input[type=range]{ -webkit-appearance:none; appearance:none; height:12px; border-radius:6px; padding:0; margin-top:34px; border:0;
  background:linear-gradient(90deg, #ef7b63 0%, #f5b14c 50%, #2fd6b0 100%); opacity:.55; transition:opacity .2s; }
.slider.set input[type=range]{ opacity:1; }
.slider input[type=range]::-webkit-slider-thumb{ -webkit-appearance:none; width:28px; height:28px; border-radius:50%; background:#fff; border:4px solid var(--c-surface); box-shadow:0 2px 10px rgba(0,0,0,.35); cursor:grab; transition:transform .16s var(--spring); }
.slider input[type=range]:active::-webkit-slider-thumb{ transform:scale(1.15); }
.slider input[type=range]::-moz-range-thumb{ width:24px; height:24px; border-radius:50%; background:#fff; border:4px solid var(--c-surface); cursor:grab; }
.slider .scale{ display:flex; justify-content:space-between; font-size:11px; color:var(--c-muted); margin-top:6px; padding:0 4px; }
.slider .val{ position:absolute; right:0; top:4px; font-size:13px; color:var(--c-muted); }
.kid .slider .face{ font-size:44px; top:-18px; }
.kid .slider input[type=range]{ height:18px; margin-top:44px; }
.kid .q{ font-size:19px; }
.kid button{ padding:13px 20px; font-size:16px; }
.list-in{ display:flex; gap:8px; margin-bottom:8px; }
.list-in input{ flex:1; }
.list-in button{ padding:9px 13px; }
.choices{ display:flex; flex-wrap:wrap; gap:8px; }
/* Schlaf-Zeitleiste */
.night{ position:relative; height:38px; border-radius:12px; background:var(--c-raise); overflow:hidden; touch-action:none; }
.night .bar{ position:absolute; top:6px; bottom:6px; border-radius:9px; background:linear-gradient(90deg, rgba(167,139,250,.55), rgba(47,214,176,.7)); transition:left .25s var(--ease), width .25s var(--ease); }
.night .gap{ position:absolute; top:6px; bottom:6px; background:var(--c-raise); opacity:.8; border-radius:3px; }
.night .handle{ position:absolute; top:2px; bottom:2px; width:16px; margin-left:-8px; border-radius:8px; background:#fff; box-shadow:0 2px 8px rgba(0,0,0,.4); cursor:ew-resize; }
.night .tick{ position:absolute; bottom:0; font-size:10px; color:var(--c-muted); transform:translateX(-50%); }
.timeaxis{ display:flex; justify-content:space-between; font-size:10.5px; color:var(--c-muted); margin-top:4px; }
.chart{ width:100%; display:block; overflow:visible; }
.chart .grid{ stroke:var(--c-line); stroke-width:1; opacity:.5; }
.chart .axis{ fill:var(--c-muted); font-size:10px; }
.chart path.line{ fill:none; stroke-width:2.4; stroke-linecap:round; stroke-linejoin:round; }
.chart path.draw{ stroke-dasharray:var(--len); animation:mh-dash 1.1s var(--ease) both; }
.chart .dot{ transition:r .2s var(--spring); }
.tip{ position:absolute; pointer-events:none; background:var(--c-raise2); border-radius:12px; padding:7px 10px; font-size:12px; box-shadow:0 6px 18px rgba(0,0,0,.3); white-space:nowrap; transform:translate(-50%,-110%); animation:mh-fade .15s; z-index:3; }
.confetti{ position:absolute; inset:0; pointer-events:none; overflow:hidden; }
.confetti i{ position:absolute; top:30%; width:8px; height:12px; border-radius:2px; animation:mh-conf 1.6s var(--ease) forwards; }
.preview-tag{ position:absolute; top:14px; right:14px; }
.blur-demo{ filter:saturate(.8); opacity:.85; pointer-events:none; }
.protect{ background:linear-gradient(135deg, rgba(167,139,250,.14), rgba(47,214,176,.10)); border-radius:var(--rad-in); padding:16px; line-height:1.55; font-size:14px; }
.protect b{ display:block; margin-bottom:6px; font-size:15px; }
.protect .tel{ display:block; margin-top:6px; color:var(--c-teal); font-weight:600; }
@media (prefers-reduced-motion: reduce){ *, *::before, *::after{ animation-duration:.001s !important; animation-iteration-count:1 !important; transition-duration:.001s !important; } }
`;

/* ============================================================ API */
const SESS_KEY = (uid, admin) => `mh_${admin ? "a" : "p"}_${uid}`;
function ssGet(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }
function ssSet(k, v) { try { if (v) sessionStorage.setItem(k, v); else sessionStorage.removeItem(k); } catch (e) { /* privat */ } }
function lsGet(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }
function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) { /* privat */ } }

class Api {
  constructor(hass) { this.hass = hass; this._waiters = []; }
  get uid() { return this.hass && this.hass.user ? this.hass.user.id : "anon"; }
  get session() { return ssGet(SESS_KEY(this.uid)); }
  set session(v) { ssSet(SESS_KEY(this.uid), v); }
  get adminSession() { return ssGet(SESS_KEY(this.uid, true)); }
  set adminSession(v) { ssSet(SESS_KEY(this.uid, true), v); }
  async call(type, data, opts = {}) {
    const msg = Object.assign({ type: `${DOMAIN}/${type}` }, data || {});
    if (opts.session !== false && this.session) msg.session = this.session;
    if (opts.admin && this.adminSession) msg.admin_session = this.adminSession;
    try {
      return await this.hass.callWS(msg);
    } catch (e) {
      const code = e && e.code;
      if (code === "locked" && opts.onLocked) { await opts.onLocked(); return this.call(type, data, Object.assign({}, opts, { onLocked: null })); }
      if (code === "admin_locked" && opts.onAdminLocked) { await opts.onAdminLocked(); return this.call(type, data, Object.assign({}, opts, { onAdminLocked: null })); }
      throw e;
    }
  }
  subscribe(cb) {
    return this.hass.connection.subscribeMessage(cb, { type: `${DOMAIN}/subscribe` });
  }
}

/* ============================================================ UI-Bausteine */
function ring(value, max, size, color, label, sub, opts = {}) {
  const r = size / 2 - 8, c = 2 * Math.PI * r;
  const f = value == null ? 0 : clamp(value / max, 0, 1);
  const anim = reduced() ? "" : `style="--len:${c.toFixed(1)};animation:mh-dash 1.2s var(--ease) both"`;
  return `<svg viewBox="0 0 ${size} ${size}" width="${opts.w || size}" height="${opts.w || size}" class="ringsvg">
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="var(--c-raise2)" stroke-width="${opts.sw || 9}"/>
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${color}" stroke-width="${opts.sw || 9}" stroke-linecap="round"
      stroke-dasharray="${(c * f).toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 ${size / 2} ${size / 2})" ${anim}/>
    <text x="50%" y="${label && sub ? "47%" : "53%"}" text-anchor="middle" dominant-baseline="middle" fill="var(--c-text)" font-size="${size / 4.2}" font-weight="600">${esc(label == null ? "–" : label)}</text>
    ${sub ? `<text x="50%" y="66%" text-anchor="middle" fill="var(--c-muted)" font-size="${size / 10}">${esc(sub)}</text>` : ""}
  </svg>`;
}

function lineChart(series, opts = {}) {
  // series: [{points:[{x:Date|num,y}], color, dash, area, band:[{x,lo,hi}]}]
  const W = opts.w || 600, H = opts.h || 170, P = { l: 26, r: 8, t: 10, b: 20 };
  const all = series.flatMap((s) => s.points || []).filter((p) => p.y != null);
  if (!all.length) return `<div class="center hint">${esc(opts.empty || "")}</div>`;
  const xs = all.map((p) => +p.x);
  const x0 = opts.x0 != null ? opts.x0 : Math.min(...xs), x1 = opts.x1 != null ? opts.x1 : Math.max(...xs);
  const y0 = opts.y0 != null ? opts.y0 : Math.min(...all.map((p) => p.y)), y1 = opts.y1 != null ? opts.y1 : Math.max(...all.map((p) => p.y));
  const sx = (x) => P.l + ((+x - x0) / ((x1 - x0) || 1)) * (W - P.l - P.r);
  const sy = (y) => P.t + (1 - (y - y0) / ((y1 - y0) || 1)) * (H - P.t - P.b);
  let g = "";
  const ticks = opts.yticks || [y0, (y0 + y1) / 2, y1];
  for (const t of ticks) g += `<line class="grid" x1="${P.l}" x2="${W - P.r}" y1="${sy(t)}" y2="${sy(t)}"/><text class="axis" x="${P.l - 6}" y="${sy(t) + 3}" text-anchor="end">${esc(opts.yfmt ? opts.yfmt(t) : Math.round(t))}</text>`;
  if (opts.xlabels) for (const [x, l] of opts.xlabels) g += `<text class="axis" x="${sx(x)}" y="${H - 4}" text-anchor="middle">${esc(l)}</text>`;
  for (const s of series) {
    if (s.band && s.band.length) {
      const top = s.band.map((p) => `${sx(p.x).toFixed(1)},${sy(p.hi).toFixed(1)}`);
      const bot = s.band.slice().reverse().map((p) => `${sx(p.x).toFixed(1)},${sy(p.lo).toFixed(1)}`);
      g += `<polygon points="${top.concat(bot).join(" ")}" fill="${s.color}" opacity=".12"/>`;
    }
    if (s.hband) g += `<rect x="${P.l}" width="${W - P.l - P.r}" y="${sy(s.hband[1])}" height="${Math.max(1, sy(s.hband[0]) - sy(s.hband[1]))}" fill="${s.color}" opacity=".09" rx="6"/>`;
    const pts = (s.points || []).filter((p) => p.y != null);
    if (!pts.length) continue;
    const d = pts.map((p, i) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join("");
    const len = Math.max(50, pts.length * 30);
    if (s.opacity === 0) { if (s.dots) for (const p of pts) g += `<circle class="dot" cx="${sx(p.x).toFixed(1)}" cy="${sy(p.y).toFixed(1)}" r="${s.r || 3}" fill="${p.color || s.color}" data-tip="${esc(p.tip || "")}"/>`; continue; }
    if (s.area) g += `<path d="${d}L${sx(pts[pts.length - 1].x).toFixed(1)},${H - P.b}L${sx(pts[0].x).toFixed(1)},${H - P.b}Z" fill="${s.color}" opacity=".08"/>`;
    g += `<path class="line ${reduced() || s.dash ? "" : "draw"}" d="${d}" stroke="${s.color}" ${s.dash ? `stroke-dasharray="${s.dash}"` : ""} style="--len:${len}" opacity="${s.opacity ?? 1}"/>`;
    if (s.dots) for (const p of pts) g += `<circle class="dot" cx="${sx(p.x).toFixed(1)}" cy="${sy(p.y).toFixed(1)}" r="${s.r || 3}" fill="${p.color || s.color}" data-tip="${esc(p.tip || "")}"/>`;
  }
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="height:${opts.ph || H}px">${g}</svg>`;
}

function smooth(points, k = 3) {
  return points.map((p, i) => {
    const win = points.slice(Math.max(0, i - k + 1), i + 1).filter((q) => q.y != null);
    return { x: p.x, y: win.length ? win.reduce((a, q) => a + q.y, 0) / win.length : null };
  });
}

function attachTips(root) {
  root.querySelectorAll("svg.chart").forEach((svg) => {
    const host = svg.parentElement;
    host.style.position = host.style.position || "relative";
    svg.addEventListener("click", (ev) => {
      const t = ev.target.closest("[data-tip]");
      host.querySelectorAll(".tip").forEach((x) => x.remove());
      if (!t || !t.dataset.tip) return;
      const r = host.getBoundingClientRect(), b = t.getBoundingClientRect();
      const tip = document.createElement("div");
      tip.className = "tip";
      tip.textContent = t.dataset.tip;
      tip.style.left = (b.left - r.left + b.width / 2) + "px";
      tip.style.top = (b.top - r.top) + "px";
      host.appendChild(tip);
      setTimeout(() => tip.remove(), 2600);
    });
  });
}

function countUp(root) {
  if (reduced()) return;
  root.querySelectorAll("[data-count]").forEach((el) => {
    const target = parseFloat(el.dataset.count), dec = parseInt(el.dataset.dec || "0", 10);
    if (isNaN(target)) return;
    const t0 = performance.now(), dur = 700;
    const step = (now) => {
      const f = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - f, 3);
      el.textContent = (target * e).toFixed(dec).replace(".", el.dataset.dc || ".");
      if (f < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  });
}

function confetti(host) {
  if (reduced()) return;
  const box = document.createElement("div");
  box.className = "confetti";
  const colors = ["#2fd6b0", "#f5b14c", "#a78bfa", "#f472b6", "#60a5fa"];
  for (let i = 0; i < 36; i++) {
    const p = document.createElement("i");
    p.style.left = 40 + Math.random() * 20 + "%";
    p.style.background = colors[i % colors.length];
    p.style.setProperty("--dx", (Math.random() * 360 - 180) + "px");
    p.style.setProperty("--dy", (Math.random() * 220 + 40) + "px");
    p.style.setProperty("--rot", (Math.random() * 720 - 360) + "deg");
    p.style.animationDelay = Math.random() * 0.25 + "s";
    box.appendChild(p);
  }
  host.appendChild(box);
  setTimeout(() => box.remove(), 2200);
}

function toast(root, text) {
  let el = root.querySelector(".toast");
  if (!el) { el = document.createElement("div"); el.className = "toast"; root.appendChild(el); }
  el.textContent = text;
  requestAnimationFrame(() => el.classList.add("show"));
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), 2400);
}

function shake(el) {
  if (!el) return;
  el.classList.remove("shake");
  void el.offsetWidth;
  el.classList.add("shake");
}

/* PIN-Dialog (Personen-PIN oder Admin-PIN) – Prüfung immer auf dem Server */
function pinDialog(root, lang, opts) {
  return new Promise((resolve, reject) => {
    const scrim = document.createElement("div");
    scrim.className = "scrim";
    scrim.innerHTML = `<div class="dialog pinbox">
      <div class="title">${esc(opts.title || tr(lang, "pin_title"))}</div>
      <div class="sub" style="margin-top:6px">${esc(opts.sub || tr(lang, "pin_sub"))}</div>
      <div class="pin-dots"><i></i><i></i><i></i><i></i></div>
      <div class="hint msg" style="min-height:18px;margin-bottom:10px"></div>
      <div class="pin-pad">${[1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => `<button data-k="${n}">${n}</button>`).join("")}
        <button data-k="x" class="ghost">✕</button><button data-k="0">0</button><button data-k="del" class="ghost">⌫</button></div></div>`;
    root.appendChild(scrim);
    let buf = "";
    const dots = scrim.querySelectorAll(".pin-dots i"), msg = scrim.querySelector(".msg"), box = scrim.querySelector(".dialog");
    const paint = () => dots.forEach((d, i) => d.classList.toggle("on", i < buf.length));
    const press = async (k) => {
      if (k === "x") { scrim.remove(); document.removeEventListener("keydown", onKey); reject(new Error("cancel")); return; }
      if (k === "del") { buf = buf.slice(0, -1); paint(); return; }
      if (buf.length >= 4) return;
      buf += k; paint();
      if (buf.length === 4) {
        try {
          const res = await opts.check(buf);
          if (res && res.ok) { scrim.remove(); document.removeEventListener("keydown", onKey); resolve(res); return; }
          buf = ""; paint(); shake(box);
          msg.textContent = res && res.locked_until ? tr(lang, "pin_locked", { t: fmtTime(new Date(res.locked_until * 1000).toISOString(), lang) })
            : tr(lang, "pin_wrong", { n: res && res.left != null ? res.left : "?" });
        } catch (e) { buf = ""; paint(); shake(box); msg.textContent = tr(lang, "error"); }
      }
    };
    const onKey = (ev) => { if (/^[0-9]$/.test(ev.key)) press(ev.key); else if (ev.key === "Backspace") press("del"); else if (ev.key === "Escape") press("x"); };
    document.addEventListener("keydown", onKey);
    scrim.querySelectorAll("[data-k]").forEach((b) => b.addEventListener("click", () => press(b.dataset.k)));
  });
}

/* ============================================================ Check-in-Formular */
class MHCheckin extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this.values = {}; this._err = {}; }
  set hass(h) { this._hass = h; if (!this.api) this.api = new Api(h); else this.api.hass = h; }
  get lang() { return langOf(this._hass); }
  t(k, v) { return tr(this.lang, k, v); }
  async load(slot, day) {
    this.slot = slot; this.day = day;
    this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="center"><div class="spinner"></div></div>`;
    try {
      this.form = await this.api.call("form", { slot, day }, { onLocked: () => this.unlock() });
    } catch (e) {
      this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="center">${esc(this.t("error"))}</div>`;
      return;
    }
    this.values = Object.assign({}, this.form.existing || {}, this.form.draft || {});
    this._err = {};
    this.render();
  }
  unlock() {
    return pinDialog(this.shadowRoot, this.lang, { check: async (pin) => {
      const r = await this.api.call("unlock", { pin }, { session: false });
      if (r.ok && r.token) this.api.session = r.token;
      return r;
    } });
  }
  _draft() {
    clearTimeout(this._dt);
    this._dt = setTimeout(() => {
      const data = Object.assign({}, this.values);
      this.api.call("draft", { slot: this.slot, data }).catch(() => {});
    }, 1500);
  }
  set(key, val) { this.values[key] = val; delete this._err[key]; this._draft(); }
  render() {
    const f = this.form, kid = f.child;
    const L = (k, v) => this.t(k, v);
    let html = `<div class="${kid ? "kid" : ""}" style="padding:2px 2px 6px">`;
    if (!f.allowed) html += `<div class="chip amber" style="margin-bottom:14px">${esc(L("not_allowed"))}</div>`;
    if (f.late) html += `<div class="chip" style="margin-bottom:14px">${esc(L("late"))}</div>`;
    let i = 0;
    for (const fd of f.fields) html += `<div class="field rise ${this._err[fd.key] ? "err" : ""}" data-key="${fd.key}" style="animation-delay:${Math.min(i++ * 45, 400)}ms">${this.fieldHtml(fd, kid)}</div>`;
    html += `<div class="row" style="margin-top:6px"><span class="hint msg"></span><span class="spacer"></span>
      <button class="primary save" ${f.allowed ? "" : "disabled"}>${esc(L("save"))}</button></div></div>`;
    this.shadowRoot.innerHTML = `<style>${CSS}</style>${html}`;
    this.bind();
  }
  fieldHtml(fd, kid) {
    const L = (k, v) => this.t(k, v);
    const v = this.values[fd.key];
    const req = fd.required ? `<span class="req">•</span>` : "";
    switch (fd.type) {
      case "info": return this.infoHtml(fd);
      case "scale10": {
        const q = fd.key === "mood" ? (kid ? L("f_mood_child") : L("f_mood")) : fd.key === "health" ? L("f_health") : fd.key === "sleep_quality" ? L("f_sleep_quality") : L("f_energy");
        const val = v == null ? 5.5 : v;
        return `<div class="q">${esc(q)} ${req}</div><div class="slider ${v == null ? "" : "set"}" data-slider="${fd.key}">
          <span class="face" style="left:${((val - 1) / 9) * 100}%">${v == null ? "🫥" : moodEmoji(v, kid)}</span>
          <span class="val">${v == null ? "" : v + "/10"}</span>
          <input type="range" min="1" max="10" step="1" value="${Math.round(val)}" aria-label="${esc(q)}">
          <div class="scale"><span>1</span><span>5</span><span>10</span></div></div>`;
      }
      case "scale3": {
        const q = kid ? L("f_soreness_child") : L("f_soreness");
        return `<div class="q">${esc(q)} ${req}</div><div class="segs" data-choice="${fd.key}">${[0, 1, 2, 3].map((n) =>
          `<button class="seg ${v === n ? "on" : ""}" data-v="${n}">${n} · ${esc(L("s" + n))}</button>`).join("")}</div>`;
      }
      case "texts": {
        const items = Array.isArray(v) ? v.slice() : [];
        const min = fd.opts.min || 0, max = fd.opts.max || 3;
        while (items.length < Math.max(1, min)) items.push("");
        const ph = fd.key === "good" ? L("f_good_ph") : fd.key === "bad" ? L("f_bad_ph") : L("f_goal_ph");
        const title = fd.key === "good" ? L("f_good") : fd.key === "bad" ? L("f_bad") : L("f_goals");
        return `<div class="q">${fd.key === "good" ? "🌱" : fd.key === "bad" ? "🌧️" : "🎯"} ${esc(title)} ${req}</div>
          <div data-list="${fd.key}" data-max="${max}">${items.map((t, k) => `<div class="list-in"><input maxlength="${fd.opts.maxlen || 200}" value="${esc(t)}" placeholder="${esc(ph)}" data-i="${k}"></div>`).join("")}</div>
          ${items.length < max ? `<button class="ghost add" data-add="${fd.key}">＋ ${esc(L("add"))}</button>` : ""}`;
      }
      case "text":
        return `<div class="q">📝 ${esc(L("f_journal"))}</div><textarea data-text="${fd.key}" maxlength="${fd.opts.maxlen || 4000}" placeholder="${esc(L("f_journal_ph"))}">${esc(v || "")}</textarea>`;
      case "yesno": {
        const done = v && typeof v === "object" ? v.done : v;
        const q = kid ? L("f_trained_child") : L("f_trained");
        let h = `<div class="q">💪 ${esc(q)} ${req}</div><div class="segs" data-yesno="${fd.key}">
          <button class="seg ${done === true ? "on" : ""}" data-v="1">${esc(L("yes"))}</button><button class="seg ${done === false ? "on" : ""}" data-v="0">${esc(L("no"))}</button></div>`;
        if (done === true && !kid) {
          const ty = (v && v.type) || "";
          h += `<div class="choices" style="margin-top:10px" data-ttype>${(fd.opts.types || []).map((x) => `<button class="chip ${ty === x ? "on" : ""}" data-v="${x}">${esc(L("tt_" + x))}</button>`).join("")}</div>
            <div class="row" style="margin-top:10px;max-width:220px"><input type="number" min="1" max="600" inputmode="numeric" data-tmin placeholder="${esc(L("f_minutes"))}" value="${esc((v && v.minutes) || "")}"></div>`;
        }
        return h;
      }
      case "number": {
        const due = fd.opts.due;
        return `<div class="q">⚖️ ${esc(L("f_weight"))} ${req}</div>
          ${due === "required" ? `<div class="hint" style="margin:-4px 0 8px">${esc(L("f_weight_req"))}</div>` : due === "warn" ? `<div class="hint" style="margin:-4px 0 8px;color:var(--c-amber)">${esc(L("f_weight_warn", { n: "7+" }))}</div>` : ""}
          <div class="row" style="max-width:220px"><input type="number" step="0.1" min="${fd.opts.min}" max="${fd.opts.max}" inputmode="decimal" data-num="${fd.key}" value="${v == null ? "" : esc(v)}"><span class="sub">kg</span></div>`;
      }
      case "choice": {
        const p = v && typeof v === "object" ? v : {};
        let h = `<div class="q">🩸 ${esc(L("f_period"))} ${req}</div><div class="segs" data-period>${fd.opts.options.map((o) =>
          `<button class="seg ${p.answer === o ? "on" : ""}" data-v="${o}">${esc(L("pa_" + o))}</button>`).join("")}</div>`;
        if (p.answer === "yes" || p.answer === "started") {
          h += `<div style="margin-top:12px"><label class="lbl">${esc(L("f_flow"))}</label><div class="segs" data-flow>${fd.opts.flow.map((o) =>
            `<button class="seg ${p.flow === o ? "on" : ""}" data-v="${o}">${esc(L("fl_" + o))}</button>`).join("")}</div></div>
            <div style="margin-top:12px"><label class="lbl">${esc(L("f_pain"))} ${p.pain == null ? "" : "· " + p.pain + "/10"}</label>
            <input type="range" min="0" max="10" step="1" value="${p.pain == null ? 0 : p.pain}" data-pain style="padding:0;height:10px;accent-color:var(--c-violet)"></div>
            <div style="margin-top:12px"><label class="lbl">${esc(L("f_symptoms"))}</label><div class="choices" data-sym>${fd.opts.symptoms.map((o) =>
            `<button class="chip ${(p.symptoms || []).includes(o) ? "on" : ""}" data-v="${o}">${esc(L("sy_" + o))}</button>`).join("")}</div></div>`;
        }
        return h;
      }
      case "goals_review": {
        const r = v || {};
        return `<div class="q">🎯 ${esc(L("f_goals_review"))}</div>${fd.opts.goals.map((g) => `<div class="row" style="margin-bottom:8px;flex-wrap:wrap">
          <span style="flex:1;min-width:140px">${esc(g.text)}</span><div class="segs" data-goal="${esc(g.id)}">${["done", "partly", "not"].map((o) =>
          `<button class="seg ${r[g.id] === o ? "on" : ""}" data-v="${o}">${esc(L("gr_" + o))}</button>`).join("")}</div></div>`).join("")}`;
      }
      case "sleep": return this.sleepHtml(fd, v);
      default: return "";
    }
  }
  infoHtml(fd) {
    const L = (k, v) => this.t(k, v), o = fd.opts || {};
    if (fd.key === "greeting") {
      const hello = this.slot === "morning" ? L("hello_m") : L("hello_e");
      const fc = o.forecast;
      let fh = "";
      if (fc && fc.ready) {
        const why = (fc.reasons || []).map((r) => this.t(r.key) !== r.key ? this.t(r.key) : "").filter(Boolean).join(", ");
        fh = `<div class="tile" style="margin-top:10px"><div class="row"><span class="emoji">${moodEmoji(fc.value, this.form.child)}</span>
          <div><div class="k">${esc(L("forecast"))}</div><div style="font-weight:600">${fmtNum(fc.low, 1, this.lang)} – ${fmtNum(fc.high, 1, this.lang)}</div>
          <div class="hint">${esc(L("forecast_conf", { p: Math.round(fc.confidence * 100) }))}${why ? " · " + esc(why) : ""}</div></div></div></div>`;
      } else if (fc && fc.ready === false && !fc.paused) {
        fh = `<div class="hint" style="margin-top:8px">${esc(L("forecast_learning", { n: fc.days || 0, m: fc.needed || 10 }))}</div>`;
      }
      return `<div class="title">${esc(hello)} ${this.form.child ? "☀️" : ""}</div>${fh}`;
    }
    if (fd.key === "weight_info") return weightTile(o, this.lang);
    if (fd.key === "training_info") {
      const txt = o.status === "overdue" ? L("training_overdue", { n: o.overdue }) : (o.child ? L("training_good_child") : L("training_good"));
      return `<div class="tile pop" style="${o.status === "overdue" ? "background:rgba(245,177,76,.14)" : "background:var(--c-active)"}"><b>${esc(txt)}</b></div>`;
    }
    if (fd.key === "birthday_info") return `<div class="tile">${(o.people || []).map((p) => `<div>${esc(p.self && p.days === 0 ? L("bd_own") : p.days === 0 ? L("bd_today", { name: p.name }) : p.days === 1 ? L("bd_tomorrow", { name: p.name }) : L("bd_in", { name: p.name, n: p.days }))}</div>`).join("")}</div>`;
    return "";
  }
  sleepHtml(fd, v) {
    const L = (k, x) => this.t(k, x), o = fd.opts || {};
    if (!o.start) return "";
    const s = new Date(o.start), e = new Date(o.end);
    const cur = v && v.action === "correct" ? { s: new Date(v.start), e: new Date(v.end) } : { s, e };
    const base = new Date(s); base.setHours(18, 0, 0, 0); if (s.getHours() < 18) base.setDate(base.getDate() - 1);
    const span = 20 * 3600e3;
    const pos = (d) => clamp((d - base) / span * 100, 0, 100);
    const mx = o.maxing;
    const chips = mx ? `<span class="chip ${mx.week_color}">${sign(mx.week_pct)} % ${esc(L("vs_week"))}</span>
      <span class="chip ${mx.opt_color}">${sign(mx.opt_pct)} % ${esc(L("vs_opt"))}</span>
      <span class="chip">${esc(L("optimum", { t: fmtDur(mx.optimum_min) }))}</span>` : `<span class="chip">${esc(L("optimum", { t: fmtDur((o.optimum_h || 8) * 60) }))}</span>`;
    const act = v && v.action;
    return `<div class="q">🌙 ${esc(L("f_sleep"))}</div>
      <div class="row" style="flex-wrap:wrap;gap:8px;margin-bottom:10px"><b style="font-size:17px">${fmtTime(cur.s.toISOString(), this.lang)} – ${fmtTime(cur.e.toISOString(), this.lang)}</b>
      <span class="sub">· ${fmtDur((cur.e - cur.s) / 60000 - (act === "correct" ? 0 : (o.int_min || 0)))}</span>
      ${o.score != null ? `<span class="chip teal">${o.score}</span>` : ""}</div>
      <div class="night" data-night>
        <div class="bar" style="left:${pos(cur.s)}%;width:${pos(cur.e) - pos(cur.s)}%"></div>
        ${(o.segments || []).map((g) => `<div class="gap" style="left:${pos(new Date(g.s * 60000))}%;width:${Math.max(0.4, pos(new Date(g.e * 60000)) - pos(new Date(g.s * 60000)))}%"></div>`).join("")}
        ${act === "correct" ? `<div class="handle" data-h="s" style="left:${pos(cur.s)}%"></div><div class="handle" data-h="e" style="left:${pos(cur.e)}%"></div>` : ""}
      </div><div class="timeaxis"><span>18:00</span><span>22:00</span><span>02:00</span><span>06:00</span><span>10:00</span><span>14:00</span></div>
      <div class="row" style="flex-wrap:wrap;gap:6px;margin-top:10px">${chips}</div>
      ${o.ask ? `<div class="hint" style="margin-top:8px;color:var(--c-amber)">${esc(L("sleep_ask"))}</div>` : ""}
      ${o.learning ? `<div class="hint" style="margin-top:4px">${esc(L("sleep_learning", { n: o.learning }))}</div>` : ""}
      ${act === "correct" ? `<div class="hint" style="margin-top:4px">${esc(L("sleep_drag"))}</div>` : ""}
      <div class="segs" data-sleep style="margin-top:10px">${["confirm", "correct", "skip"].map((a) => `<button class="seg ${act === a ? "on" : ""}" data-v="${a}">${esc(L("sleep_" + a))}</button>`).join("")}</div>`;
  }
  bind() {
    const R = this.shadowRoot;
    R.querySelectorAll("[data-slider]").forEach((box) => {
      const key = box.dataset.slider, inp = box.querySelector("input"), face = box.querySelector(".face"), val = box.querySelector(".val");
      const upd = () => {
        const v = parseInt(inp.value, 10);
        box.classList.add("set");
        const em = moodEmoji(v, this.form.child);
        if (face.textContent !== em) { face.textContent = em; face.classList.remove("bump"); void face.offsetWidth; face.classList.add("bump"); }
        face.style.left = ((v - 1) / 9 * 100) + "%";
        val.textContent = v + "/10";
        this.set(key, v);
        box.closest(".field").classList.remove("err");
      };
      inp.addEventListener("input", upd);
      inp.addEventListener("change", upd);
      inp.addEventListener("pointerdown", () => { if (this.values[key] == null) setTimeout(upd, 0); });
    });
    R.querySelectorAll("[data-choice]").forEach((g) => g.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      this.set(g.dataset.choice, parseInt(b.dataset.v, 10)); this.render();
    })));
    R.querySelectorAll("[data-list]").forEach((box) => {
      const key = box.dataset.list;
      box.querySelectorAll("input").forEach((inp) => inp.addEventListener("input", () => {
        const items = [...box.querySelectorAll("input")].map((x) => x.value);
        this.set(key, items);
        box.closest(".field").classList.remove("err");
      }));
    });
    R.querySelectorAll("[data-add]").forEach((b) => b.addEventListener("click", () => {
      const key = b.dataset.add, items = (Array.isArray(this.values[key]) ? this.values[key] : [""]).concat([""]);
      this.values[key] = items; this.render();
      const ins = R.querySelectorAll(`[data-list="${key}"] input`); if (ins.length) ins[ins.length - 1].focus();
    }));
    R.querySelectorAll("[data-text]").forEach((ta) => ta.addEventListener("input", () => this.set(ta.dataset.text, ta.value)));
    R.querySelectorAll("[data-yesno]").forEach((g) => g.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const cur = this.values[g.dataset.yesno];
      this.set(g.dataset.yesno, Object.assign({}, typeof cur === "object" && cur ? cur : {}, { done: b.dataset.v === "1" })); this.render();
    })));
    const ty = R.querySelector("[data-ttype]");
    if (ty) ty.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const cur = Object.assign({}, this.values.trained); cur.type = cur.type === b.dataset.v ? undefined : b.dataset.v; this.set("trained", cur); this.render();
    }));
    const tm = R.querySelector("[data-tmin]");
    if (tm) tm.addEventListener("input", () => { const cur = Object.assign({}, this.values.trained); cur.minutes = parseInt(tm.value, 10) || undefined; this.set("trained", cur); });
    R.querySelectorAll("[data-num]").forEach((inp) => inp.addEventListener("input", () => this.set(inp.dataset.num, inp.value === "" ? null : parseFloat(String(inp.value).replace(",", ".")))));
    const per = R.querySelector("[data-period]");
    if (per) {
      const cur = () => Object.assign({}, this.values.period || {});
      per.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { const c = cur(); c.answer = b.dataset.v; this.set("period", c); this.render(); }));
      const fl = R.querySelector("[data-flow]");
      if (fl) fl.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { const c = cur(); c.flow = b.dataset.v; this.set("period", c); this.render(); }));
      const pn = R.querySelector("[data-pain]");
      if (pn) pn.addEventListener("change", () => { const c = cur(); c.pain = parseInt(pn.value, 10); this.set("period", c); this.render(); });
      const sy = R.querySelector("[data-sym]");
      if (sy) sy.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
        const c = cur(); const s = new Set(c.symptoms || []); s.has(b.dataset.v) ? s.delete(b.dataset.v) : s.add(b.dataset.v); c.symptoms = [...s]; this.set("period", c); this.render();
      }));
    }
    R.querySelectorAll("[data-goal]").forEach((g) => g.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const c = Object.assign({}, this.values.goals_review || {}); c[g.dataset.goal] = b.dataset.v; this.set("goals_review", c); this.render();
    })));
    const sl = R.querySelector("[data-sleep]");
    if (sl) sl.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => {
      const fd = this.form.fields.find((f) => f.key === "sleep");
      const v = { action: b.dataset.v };
      if (v.action === "correct") { v.start = fd.opts.start; v.end = fd.opts.end; }
      this.set("sleep", v); this.render();
    }));
    const night = R.querySelector("[data-night]");
    if (night) this.bindNight(night);
    R.querySelector(".save").addEventListener("click", () => this.submit());
  }
  bindNight(night) {
    const v = this.values.sleep;
    if (!v || v.action !== "correct") return;
    const fd = this.form.fields.find((f) => f.key === "sleep");
    const s0 = new Date(fd.opts.start);
    const base = new Date(s0); base.setHours(18, 0, 0, 0); if (s0.getHours() < 18) base.setDate(base.getDate() - 1);
    const span = 20 * 3600e3;
    night.querySelectorAll(".handle").forEach((h) => {
      h.addEventListener("pointerdown", (ev) => {
        ev.preventDefault(); h.setPointerCapture(ev.pointerId);
        const r = night.getBoundingClientRect();
        const move = (e) => {
          const f = clamp((e.clientX - r.left) / r.width, 0, 1);
          let d = new Date(+base + f * span);
          d = new Date(Math.round(d / 300000) * 300000);      // 5-Minuten-Raster
          const cur = Object.assign({}, this.values.sleep);
          if (h.dataset.h === "s" && d < new Date(cur.end)) cur.start = d.toISOString();
          if (h.dataset.h === "e" && d > new Date(cur.start)) cur.end = d.toISOString();
          this.values.sleep = cur;
          const pos = (x) => clamp((new Date(x) - base) / span * 100, 0, 100);
          night.querySelector(".bar").style.left = pos(cur.start) + "%";
          night.querySelector(".bar").style.width = (pos(cur.end) - pos(cur.start)) + "%";
          h.style.left = pos(h.dataset.h === "s" ? cur.start : cur.end) + "%";
          const lbl = this.shadowRoot.querySelector(".field[data-key=sleep] b");
          if (lbl) lbl.textContent = `${fmtTime(cur.start, this.lang)} – ${fmtTime(cur.end, this.lang)}`;
        };
        const up = () => { h.removeEventListener("pointermove", move); h.removeEventListener("pointerup", up); this._draft(); };
        h.addEventListener("pointermove", move); h.addEventListener("pointerup", up);
      });
    });
  }
  async submit() {
    const btn = this.shadowRoot.querySelector(".save");
    btn.disabled = true;
    const data = Object.assign({}, this.values);
    for (const k of ["good", "bad", "goals"]) if (Array.isArray(data[k])) data[k] = data[k].map((x) => String(x).trim()).filter(Boolean);
    try {
      const res = await this.api.call("submit", { slot: this.slot, day: this.form.day, data }, { onLocked: () => this.unlock() });
      if (!res.ok) {
        this._err = res.errors || {};
        btn.disabled = false;
        if (this._err._) { toast(this.shadowRoot, this.t("not_allowed")); return; }
        this.render();
        const first = this.shadowRoot.querySelector(".field.err");
        this.shadowRoot.querySelectorAll(".field.err").forEach((f) => shake(f));
        if (first) first.scrollIntoView({ behavior: reduced() ? "auto" : "smooth", block: "center" });
        this.shadowRoot.querySelector(".msg").textContent = this.t("required_missing");
        return;
      }
      clearTimeout(this._dt);
      this.dispatchEvent(new CustomEvent("mh-saved", { detail: res, bubbles: true, composed: true }));
    } catch (e) {
      btn.disabled = false;
      toast(this.shadowRoot, this.t("error"));
    }
  }
}
customElements.define("mh-checkin", MHCheckin);

function weightTile(o, lang) {
  const L = (k, v) => tr(lang, k, v);
  if (!o || o.trend == null) return "";
  const hint = o.hint === "below_range" ? L("w_below") : o.hint === "fast_loss" ? L("w_fast") : o.hint === "add_height" ? L("w_add_height") : "";
  return `<div class="tile"><div class="row" style="gap:8px"><span class="emoji" style="font-size:24px">⚖️</span>
    <b style="font-size:20px">${fmtNum(o.trend, 1, lang)} kg</b><span class="hint">${esc(L("w_trend"))}</span></div>
    <div class="row" style="flex-wrap:wrap;gap:6px;margin-top:10px">
    ${o.delta_week != null ? `<span class="chip ${o.color_week}">${sign(o.delta_week, 1, lang)} kg ${esc(L("w_week"))}</span>` : ""}
    ${o.delta_opt != null ? `<span class="chip ${o.color_opt}">${sign(o.delta_opt, 1, lang)} kg ${esc(L("w_opt"))}</span>` : ""}
    ${o.optimum != null ? `<span class="chip">${esc(L("optimum", { t: fmtNum(o.optimum, 1, lang) + " kg" }))}</span>` : ""}</div>
    ${hint ? `<div class="hint" style="margin-top:8px">${esc(hint)}</div>` : ""}</div>`;
}

function protectHtml(lang, child) {
  const L = (k) => tr(lang, k);
  return `<div class="protect rise"><b>💜 ${esc(L("protect_title"))}</b>${esc(L("protect_text"))}
    ${lang === "de" ? `<span class="tel">${esc(L(child ? "protect_kids" : "protect_de"))}</span>${child ? "" : `<span class="tel" style="font-weight:500">${esc(L("protect_kids"))}</span>`}` : `<span class="tel">${esc(L("protect_en"))}</span>`}</div>`;
}

/* ============================================================ Basiskarte */
class MHBase extends HTMLElement {
  constructor() { super(); this.attachShadow({ mode: "open" }); this._config = {}; }
  setConfig(c) { this._config = Object.assign({}, c || {}); if (this._hass) this.refresh(); }
  set hass(h) {
    const first = !this._hass;
    this._hass = h;
    if (!this.api) this.api = new Api(h); else this.api.hass = h;
    if (first) this.refresh();
  }
  get lang() { return langOf(this._hass); }
  t(k, v) { return tr(this.lang, k, v); }
  connectedCallback() { if (this._hass && !this._unsub) this.refresh(); }
  disconnectedCallback() { if (this._unsub) { this._unsub.then((u) => u && u()).catch(() => {}); this._unsub = null; } }
  _subscribe() {
    if (this._unsub || !this._hass || !this._hass.connection) return;
    this._unsub = this.api.subscribe(() => { clearTimeout(this._rt); this._rt = setTimeout(() => this.refresh(true), 400); }).catch(() => null);
  }
  frame(inner) {
    const title = this._config.title;
    this.shadowRoot.innerHTML = `<style>${CSS}</style><div class="card">${title ? `<div class="title" style="margin-bottom:10px">${esc(title)}</div>` : ""}${inner}</div>`;
    attachTips(this.shadowRoot);
    countUp(this.shadowRoot);
  }
  loadingHtml() { return `<div class="center"><div class="spinner"></div></div>`; }
  unlock() {
    return pinDialog(this.shadowRoot, this.lang, { check: async (pin) => {
      const r = await this.api.call("unlock", { pin }, { session: false });
      if (r.ok && r.token) this.api.session = r.token;
      return r;
    } });
  }
  async refresh(quiet) {
    if (!this._hass) return;
    if (!quiet && !this._me) this.frame(this.loadingHtml());
    try {
      this._me = await this.api.call("me");
    } catch (e) {
      this.frame(`<div class="center">${esc(this.t("not_loaded"))}</div>`);
      return;
    }
    this._subscribe();
    if (!this._me.setup && this.needsPerson) { this.frame(previewHtml(this.lang, this._me, this.compact)); bindPreview(this); return; }
    try { await this.load(quiet); } catch (e) {
      if (e && e.code === "locked") {
        this.frame(`<div class="center"><div class="emoji">🔒</div><div>${esc(this.t("pin_sub"))}</div><button class="primary unlock">${esc(this.t("pin_title"))}</button></div>`);
        this.shadowRoot.querySelector(".unlock").addEventListener("click", () => this.unlock().then(() => this.refresh()).catch(() => {}));
        return;
      }
      this.frame(`<div class="center">${esc(this.t("error"))}<button class="retry">${esc(this.t("retry"))}</button></div>`);
      const b = this.shadowRoot.querySelector(".retry"); if (b) b.addEventListener("click", () => this.refresh());
    }
  }
  get needsPerson() { return true; }
  get compact() { return !!this._config.compact; }
  openPanel(q) { history.pushState(null, "", PANEL + (q || "")); window.dispatchEvent(new CustomEvent("location-changed")); }
  getCardSize() { return 4; }
  getGridOptions() { return { columns: 6, rows: "auto", min_columns: 3, min_rows: 2 }; }
}

/* Vorschau für Personen, die noch nicht angelegt sind */
function previewHtml(lang, me, compact) {
  const L = (k, v) => tr(lang, k, v);
  const req = me.request;
  const now = Date.now() / 1000;
  const sent = req && req.next > now;
  const demo = [6, 7, 5, 8, 7, 9, 8].map((v, i) => ({ x: i, y: v }));
  return `<div class="preview-tag chip teal small">${esc(L("preview_badge"))}</div>
    <div class="title rise">${esc(L("preview_title"))} 🌿</div>
    <div class="sub rise" style="margin:6px 0 14px;animation-delay:60ms">${esc(L("preview_text"))}</div>
    ${compact ? "" : `<div class="grid2 blur-demo rise" style="animation-delay:120ms">
      <div class="tile" style="display:grid;place-items:center">${ring(82, 100, 110, "var(--c-teal)", "82", L("health_score"))}</div>
      <div class="tile"><div class="k">${esc(L("mood"))}</div><div class="emoji" style="animation:mh-breathe 3s ease-in-out infinite">😊</div>${lineChart([{ points: demo, color: "#2fd6b0", area: true }], { w: 260, h: 70, ph: 70, y0: 1, y1: 10, yticks: [] })}</div></div>
    <div class="col rise" style="margin:14px 0;gap:6px;animation-delay:180ms">${["pv_1", "pv_2", "pv_3", "pv_4"].map((k) => `<div class="row"><span style="color:var(--c-teal)">✓</span><span class="sub" style="color:var(--c-text)">${esc(L(k))}</span></div>`).join("")}</div>`}
    <div class="row" style="flex-wrap:wrap"><button class="primary req ${sent ? "" : "pulse"}" ${sent ? "disabled" : ""}>${esc(sent ? L("request_sent") : L("request"))}</button>
    ${sent ? `<span class="hint">${esc(L("request_again", { t: fmtDate(new Date(req.next * 1000).toISOString(), lang, { weekday: "short", hour: "2-digit", minute: "2-digit" }) }))}</span>` : ""}</div>`;
}
function bindPreview(card) {
  const b = card.shadowRoot.querySelector(".req");
  if (!b) return;
  b.addEventListener("click", async () => {
    b.disabled = true;
    try { await card.api.call("request_setup"); toast(card.shadowRoot, card.t("request_sent")); } catch (e) { b.disabled = false; }
    setTimeout(() => card.refresh(true), 600);
  });
}

/* ============================================================ Karten */
class PersonCard extends MHBase {
  async load() {
    const d = await this.api.call("dashboard", {}, {});
    this._d = d;
    const L = (k, v) => this.t(k, v), v = d.values || {}, lang = this.lang;
    const open = ["morning", "evening"].find((s) => d.status[s] && d.status[s].state === "open");
    const h = new Date().getHours();
    const hello = h < 11 ? L("hello_m") : h < 17 ? L("hello_d") : h < 22 ? L("hello_e") : L("hello_n");
    const sl = d.sleep || {};
    const mx = sl.maxing;
    const tr_ = d.training;
    let btn = "";
    if (open) btn = `<button class="primary pulse go" data-slot="${open}">${esc(L("checkin_" + open))} · ${esc(L("open_now"))}</button>`;
    else if (d.evening_manual && !(d.status.evening && d.status.evening.state === "done")) btn = `<button class="go" data-slot="evening">${esc(L("enter_evening"))}</button>`;
    else if (d.status.evening && d.status.evening.state === "done") btn = `<span class="chip teal">${esc(L("done_today"))}</span>`;
    const bd = (d.birthdays || []).find((b) => b.days === 0);
    this.frame(`<div class="row rise"><div><div class="title">${esc(hello)}, ${esc(this._me.name.split(" ")[0])}</div>
        <div class="sub">${d.paused ? esc(L("paused")) : v.streak ? esc(L("streak", { n: v.streak })) : esc(L("first_days"))}</div></div>
        <span class="spacer"></span><button class="ghost openp" title="${esc(L("open_panel"))}">↗</button></div>
      <div class="grid2" style="margin-top:14px">
        <div class="tile rise" style="display:grid;place-items:center;animation-delay:60ms">${ring(d.health.score, 100, 112, "var(--c-teal)", d.health.score == null ? "–" : d.health.score, L("health_score"))}</div>
        <div class="tile rise" style="animation-delay:100ms"><div class="k">${esc(L("mood"))} · ${esc(L("today"))}</div>
          <div class="row" style="margin-top:6px"><span class="emoji" style="font-size:38px">${moodEmoji(v.mood_today, d.child)}</span>
          <span class="big" ${v.mood_today != null ? `data-count="${v.mood_today}" data-dec="1"` : ""}>${v.mood_today == null ? "–" : fmtNum(v.mood_today, 1, lang)}</span></div>
          ${d.forecast && d.forecast.ready ? `<div class="hint">${esc(L("forecast"))}: ${fmtNum(d.forecast.value, 1, lang)}</div>` : ""}</div>
      </div>
      ${sl.enabled && sl.today ? `<div class="tile rise" style="margin-top:10px;animation-delay:140ms"><div class="row" style="flex-wrap:wrap;gap:8px"><span>🌙</span>
        <b>${fmtDur(sl.today.asleep)}</b><span class="chip teal small">${sl.today.score ?? "–"}</span><span class="spacer"></span>
        ${mx ? `<span class="chip small ${mx.week_color}">${sign(mx.week_pct)} % ${esc(L("vs_week"))}</span><span class="chip small ${mx.opt_color}">${sign(mx.opt_pct)} %</span>` : ""}</div></div>` : ""}
      ${tr_ && (tr_.status === "recommended" || tr_.status === "overdue") ? `<div class="tile rise" style="margin-top:10px;background:${tr_.highlight ? "rgba(245,177,76,.14)" : "var(--c-active)"}">
        ${esc(tr_.status === "overdue" ? L("training_overdue", { n: tr_.overdue }) : (tr_.child ? L("training_good_child") : L("training_good")))}</div>` : ""}
      ${bd ? `<div class="tile rise bday" style="margin-top:10px">${esc(bd.self ? L("bd_own") : L("bd_today", { name: bd.name }))}</div>` : ""}
      ${d.protect ? `<div style="margin-top:10px">${protectHtml(lang, d.child)}</div>` : ""}
      <div class="row" style="margin-top:14px">${btn}</div>`);
    const R = this.shadowRoot;
    R.querySelectorAll(".go").forEach((b) => b.addEventListener("click", () => this.openPanel(`?checkin=${b.dataset.slot}`)));
    R.querySelector(".openp").addEventListener("click", () => this.openPanel(""));
    if (bd && bd.self) confetti(R.querySelector(".card"));
  }
  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement("mental-health-card-editor"); }
  getGridOptions() { return { columns: 6, rows: "auto", min_columns: 4, min_rows: 4 }; }
}

class FamilyCard extends MHBase {
  get needsPerson() { return false; }
  async load() {
    const f = await this.api.call("family");
    const L = (k, v) => this.t(k, v), lang = this.lang;
    const pts = (f.history || []).map((h) => ({ x: new Date(h.day + "T12:00").getTime(), y: h.mood }));
    this.frame(`<div class="row rise"><div class="title">${esc(L("family"))}</div><span class="spacer"></span>
      ${f.participation != null ? `<span class="chip small">${esc(L("participation"))} ${f.participation} %</span>` : ""}</div>
      ${f.enough ? `<div class="row rise" style="margin:14px 0 6px;gap:16px"><span style="font-size:58px;animation:mh-breathe 4s ease-in-out infinite;display:inline-block">${WEATHER[f.weather] || "⛅"}</span>
        <div><div class="big">${esc(L("weather_" + f.weather))}</div><div class="sub">${esc(L("mood"))} ${fmtNum(f.mood, 1, lang)}</div></div>
        <span class="spacer"></span>${f.health != null ? ring(f.health, 100, 92, "var(--c-teal)", f.health, L("health_score")) : ""}</div>`
        : `<div class="center hint">${esc(L("family_not_enough", { k: f.k }))}</div>`}
      ${pts.length > 1 ? `<div class="rise" style="animation-delay:120ms">${lineChart([{ points: pts, color: "#2fd6b0", area: true }], { w: 340, h: 90, ph: 90, y0: 1, y1: 10, yticks: [1, 5.5, 10] })}</div>` : ""}
      ${(f.birthdays || []).slice(0, 3).map((b) => `<div class="row rise" style="margin-top:8px"><span>🎂</span><span>${esc(b.days === 0 ? L("bd_today", { name: b.name }) : b.days === 1 ? L("bd_tomorrow", { name: b.name }) : L("bd_in", { name: b.name, n: b.days }))}</span></div>`).join("")}`);
  }
  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement("mental-health-card-editor"); }
}

class CheckinCard extends MHBase {
  async load() {
    const d = await this.api.call("dashboard");
    const open = ["morning", "evening"].find((s) => d.status[s] && d.status[s].state === "open");
    const h = new Date().getHours();
    const slot = this._config.slot && this._config.slot !== "auto" ? this._config.slot : open || (h < 14 ? "morning" : "evening");
    this.frame(`<div class="row"><div class="title">${esc(this.t("checkin_" + slot))}</div><span class="spacer"></span>
      <div class="segs"><button class="seg ${slot === "morning" ? "on" : ""}" data-s="morning">${esc(this.t("morning"))}</button><button class="seg ${slot === "evening" ? "on" : ""}" data-s="evening">${esc(this.t("evening"))}</button></div></div>
      <div class="hint" style="margin:6px 0 14px">${esc(this.t("wall_note", { name: this._me.name }))}</div><mh-checkin></mh-checkin>`);
    const el = this.shadowRoot.querySelector("mh-checkin");
    el.hass = this._hass;
    el.load(slot, d.today);
    el.addEventListener("mh-saved", () => { toast(this.shadowRoot, this.t("saved")); setTimeout(() => this.refresh(true), 900); });
    this.shadowRoot.querySelectorAll("[data-s]").forEach((b) => b.addEventListener("click", () => { this._config = Object.assign({}, this._config, { slot: b.dataset.s }); this.refresh(true); }));
  }
  static getStubConfig() { return { slot: "auto" }; }
  static getConfigElement() { return document.createElement("mental-health-card-editor"); }
  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6, min_rows: 6 }; }
}

function nightRow(n, lang) {
  if (!n || !n.start) return "";
  const s = new Date(n.start), e = new Date(n.end);
  const base = new Date(s); base.setHours(18, 0, 0, 0); if (s.getHours() < 18) base.setDate(base.getDate() - 1);
  const span = 20 * 3600e3, pos = (d) => clamp((d - base) / span * 100, 0, 100);
  return `<div class="night" style="height:22px;border-radius:8px"><div class="bar" style="top:4px;bottom:4px;left:${pos(s)}%;width:${pos(e) - pos(s)}%"></div>
    ${(n.segments || []).map((g) => `<div class="gap" style="top:4px;bottom:4px;left:${pos(new Date(g.s * 60000))}%;width:${Math.max(.4, pos(new Date(g.e * 60000)) - pos(new Date(g.s * 60000)))}%"></div>`).join("")}</div>`;
}

class SleepCard extends MHBase {
  async load() {
    const d = await this.api.call("dashboard");
    const sl = d.sleep || {}, L = (k, v) => this.t(k, v), lang = this.lang;
    if (!sl.enabled) { this.frame(`<div class="center hint">${esc(L("no_sleep"))}</div>`); return; }
    const n = sl.today, mx = sl.maxing;
    const stateTxt = sl.state ? L("st_" + sl.state) : "";
    this.frame(`<div class="row"><div class="title">🌙 ${esc(L("sleep"))}</div><span class="spacer"></span>${stateTxt ? `<span class="chip small ${sl.state === "asleep" ? "teal pulse" : ""}">${esc(stateTxt)}</span>` : ""}</div>
      ${n ? `<div class="row rise" style="margin:12px 0;gap:14px">${ring(n.score, 100, 96, "var(--c-violet)", n.score ?? "–", "Score")}
        <div><div class="big">${fmtDur(n.asleep)}</div><div class="sub">${fmtTime(n.start, lang)} – ${fmtTime(n.end, lang)}</div>
        ${n.int ? `<div class="hint">${esc(L("interruptions", { n: n.int }))}</div>` : ""}</div></div>
        ${nightRow(n, lang)}<div class="timeaxis"><span>18</span><span>22</span><span>02</span><span>06</span><span>10</span><span>14</span></div>
        <div class="row" style="flex-wrap:wrap;gap:6px;margin-top:12px">${mx ? `<span class="chip ${mx.week_color}">${sign(mx.week_pct)} % ${esc(L("vs_week"))}</span><span class="chip ${mx.opt_color}">${sign(mx.opt_pct)} % ${esc(L("vs_opt"))}</span>` : ""}
        <span class="chip">${esc(L("optimum", { t: fmtDur((sl.optimum_h || 8) * 60) }))}</span></div>`
        : `<div class="center hint">${esc(sl.learning ? L("sleep_learning", { n: sl.night_of }) : L("no_sleep"))}</div>`}`);
  }
  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement("mental-health-card-editor"); }
}

class WeightCard extends MHBase {
  async load() {
    const d = await this.api.call("dashboard");
    const L = (k, v) => this.t(k, v), lang = this.lang;
    if (!d.weight || d.weight.child) { this.frame(`<div class="center hint">${esc(L("no_data"))}</div>`); return; }
    const pts = (d.weights || []).slice(-90).map((w) => ({ x: new Date(w.day + "T12:00").getTime(), y: w.kg }));
    let trend = [], t = null;
    for (const p of pts) { t = t == null ? p.y : t + 0.18 * (p.y - t); trend.push({ x: p.x, y: t }); }
    const w = d.weight;
    const ys = pts.map((p) => p.y).concat(w.range ? w.range : []);
    this.frame(`<div class="title">⚖️ ${esc(L("weight"))}</div><div style="margin-top:10px">${weightTile(w, lang)}</div>
      ${pts.length > 1 ? `<div style="margin-top:10px">${lineChart([
        { points: pts.map((p) => Object.assign({}, p, { tip: fmtNum(p.y, 1, lang) + " kg" })), color: "#22d3ee", dots: true, r: 2.2, opacity: .5, hband: w.range },
        { points: trend, color: "#22d3ee" }], { w: 340, h: 120, ph: 120, y0: Math.floor(Math.min(...ys) - 1), y1: Math.ceil(Math.max(...ys) + 1), yfmt: (x) => Math.round(x) })}</div>` : ""}`);
  }
  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement("mental-health-card-editor"); }
}

class TrainingCard extends MHBase {
  async load() {
    const d = await this.api.call("dashboard");
    const L = (k, v) => this.t(k, v);
    const tr_ = d.training;
    if (!tr_) { this.frame(`<div class="center hint">${esc(L("no_data"))}</div>`); return; }
    const days = d.days || [], map = {};
    for (const x of days) map[x.day] = x;
    let cal = "";
    for (let i = 27; i >= 0; i--) {
      const dt = new Date(); dt.setDate(dt.getDate() - i);
      const k = dt.toISOString().slice(0, 10), r = map[k];
      const col = r && r.trained ? "var(--c-teal)" : r && r.soreness >= 2 ? "rgba(245,177,76,.6)" : "var(--c-raise2)";
      cal += `<i title="${k}" style="display:block;aspect-ratio:1;border-radius:6px;background:${col}"></i>`;
    }
    const txt = tr_.status === "recommended" ? (tr_.child ? L("training_good_child") : L("training_good")) : tr_.status === "overdue" ? L("training_overdue", { n: tr_.overdue }) : tr_.status === "pause" ? L("training_pause") : L("training_ready_soon");
    this.frame(`<div class="row"><div class="title">💪 ${esc(tr_.child ? L("training") : L("training"))}</div><span class="spacer"></span><span class="chip ${tr_.status === "overdue" ? "amber" : tr_.status === "recommended" ? "teal" : ""}">${esc(L("ts_" + tr_.status))}</span></div>
      <div class="tile rise" style="margin:12px 0;${tr_.highlight ? "background:rgba(245,177,76,.14)" : ""}">${esc(txt)}</div>
      <div style="display:grid;grid-template-columns:repeat(14,1fr);gap:4px">${cal}</div>`);
  }
  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement("mental-health-card-editor"); }
}

class MoodChartCard extends MHBase {
  async load() {
    const d = await this.api.call("dashboard");
    const L = (k, v) => this.t(k, v), lang = this.lang;
    const range = this._range || this._config.days || 30;
    const now = Date.now(), from = now - range * 86400e3;
    const days = (d.days || []).filter((x) => new Date(x.day + "T12:00") >= from).reverse();
    const pm = days.map((x) => ({ x: new Date(x.day + "T12:00").getTime(), y: x.mood_m, tip: `${fmtDate(x.day, lang)} · ${x.mood_m ?? "–"}` }));
    const pe = days.map((x) => ({ x: new Date(x.day + "T12:00").getTime(), y: x.mood_e, tip: `${fmtDate(x.day, lang)} · ${x.mood_e ?? "–"}` }));
    const fc = (d.forecast_history || []).filter((h) => h.p != null).map((h) => ({ x: new Date(h.day + "T12:00").getTime(), y: h.p }));
    this.frame(`<div class="row" style="flex-wrap:wrap"><div class="title">${esc(L("mood"))}</div><span class="spacer"></span>
      <div class="segs">${[7, 30, 90, 365].map((r) => `<button class="seg ${range === r ? "on" : ""}" data-r="${r}">${esc(L(r === 7 ? "days7" : r === 30 ? "days30" : r === 90 ? "days90" : "days365"))}</button>`).join("")}</div></div>
      <div style="margin-top:12px">${days.length ? lineChart([
        { points: smooth(pm, 3), color: "#f5b14c" }, { points: pm, color: "#f5b14c", dots: true, r: 2.5, opacity: .0 },
        { points: smooth(pe, 3), color: "#2fd6b0" }, { points: pe, color: "#2fd6b0", dots: true, r: 2.5, opacity: .0 },
        { points: fc.filter((p) => p.x >= from), color: "#a78bfa", dash: "4 5" }],
        { w: 360, h: 160, ph: 160, y0: 1, y1: 10, yticks: [1, 5.5, 10], x0: from, x1: now }) : `<div class="center hint">${esc(L("first_days"))}</div>`}</div>
      <div class="row hint" style="gap:14px;margin-top:6px"><span><b style="color:#f5b14c">━</b> ${esc(L("morning"))}</span><span><b style="color:#2fd6b0">━</b> ${esc(L("evening"))}</span><span><b style="color:#a78bfa">┅</b> ${esc(L("forecast"))}</span></div>`);
    this.shadowRoot.querySelectorAll("[data-r]").forEach((b) => b.addEventListener("click", () => { this._range = parseInt(b.dataset.r, 10); this.load(); }));
  }
  static getStubConfig() { return { days: 30 }; }
  static getConfigElement() { return document.createElement("mental-health-card-editor"); }
}

class BirthdayCard extends MHBase {
  get needsPerson() { return false; }
  async load() {
    const f = await this.api.call("family");
    const L = (k, v) => this.t(k, v);
    const list = f.birthdays || [];
    this.frame(`<div class="title">🎂 ${esc(L("birthdays"))}</div>
      ${list.length ? list.map((b, i) => `<div class="row rise" style="margin-top:10px;animation-delay:${i * 50}ms">
        <span class="emoji" style="font-size:24px">${b.days === 0 ? "🎉" : "🎈"}</span><div><div>${esc(b.name)}</div>
        <div class="hint">${esc(b.days === 0 ? L("today") : b.days === 1 ? L("bd_tomorrow", { name: "" }).trim() : L("bd_in", { name: "", n: b.days }).trim())}${b.turning ? " · " + esc(L("turning", { n: b.turning })) : ""}</div></div></div>`).join("")
        : `<div class="center hint">${esc(L("no_data"))}</div>`}`);
    if (list.some((b) => b.days === 0)) confetti(this.shadowRoot.querySelector(".card"));
  }
  static getStubConfig() { return {}; }
  static getConfigElement() { return document.createElement("mental-health-card-editor"); }
}

/* Visueller Editor (gemeinsam): Titel, ggf. Zeitraum/Check-in-Art */
class CardEditor extends HTMLElement {
  setConfig(c) { this._config = Object.assign({}, c || {}); this.render(); }
  set hass(h) { this._hass = h; this.render(); }
  get lang() { return langOf(this._hass); }
  render() {
    if (!this._hass || !this._config) return;
    const type = String(this._config.type || "");
    const schema = [{ name: "title", selector: { text: {} } }];
    if (type.endsWith("mood-chart-card")) schema.push({ name: "days", selector: { select: { mode: "dropdown", options: [7, 30, 90, 365].map((d) => ({ value: d, label: String(d) })) } } });
    if (type.endsWith("checkin-card")) schema.push({ name: "slot", selector: { select: { mode: "dropdown", options: ["auto", "morning", "evening"].map((v) => ({ value: v, label: v === "auto" ? "Auto" : tr(this.lang, v) })) } } });
    if (type.endsWith("person-card")) schema.push({ name: "compact", selector: { boolean: {} } });
    if (!customElements.get("ha-form")) { this.innerHTML = `<p style="color:var(--secondary-text-color)">${esc(tr(this.lang, "card_person"))}</p>`; return; }
    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.addEventListener("value-changed", (ev) => {
        const c = Object.assign({}, this._config, ev.detail.value);
        if (!c.title) delete c.title;
        this._config = c;
        this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: c }, bubbles: true, composed: true }));
      });
      this.appendChild(this._form);
    }
    this._form.hass = this._hass;
    this._form.data = this._config;
    this._form.schema = schema;
    this._form.computeLabel = (s) => tr(this.lang, s.name === "title" ? "ed_title" : s.name === "days" ? "ed_period" : s.name === "compact" ? "ed_compact" : "checkin");
  }
}
customElements.define("mental-health-card-editor", CardEditor);

const CARDS = [
  ["mental-health-person-card", PersonCard, "card_person", "Mental Health – Person"],
  ["mental-health-family-card", FamilyCard, "card_family", "Mental Health – Family"],
  ["mental-health-checkin-card", CheckinCard, "card_checkin", "Mental Health – Check-in"],
  ["mental-health-sleep-card", SleepCard, "card_sleep", "Mental Health – Sleep"],
  ["mental-health-weight-card", WeightCard, "card_weight", "Mental Health – Weight"],
  ["mental-health-training-card", TrainingCard, "card_training", "Mental Health – Training"],
  ["mental-health-mood-chart-card", MoodChartCard, "card_mood", "Mental Health – Mood chart"],
  ["mental-health-birthday-card", BirthdayCard, "card_birthday", "Mental Health – Birthdays"],
];
window.customCards = window.customCards || [];
const nl = normLang(navigator.language);
for (const [tag, cls, desc, name] of CARDS) {
  if (!customElements.get(tag)) customElements.define(tag, cls);
  if (!window.customCards.find((c) => c.type === tag)) window.customCards.push({ type: tag, name, description: tr(nl, desc), preview: true, documentationURL: "https://github.com/kilian-haos/Mental-Health-and-Health-Improvements-for-HAOS-by-Kilian-K." });
}

/* Dashboard-Strategie: "strategy: type: custom:mental-health" – jede Person sieht nur sich selbst */
class MHStrategy extends HTMLElement {
  static async generate(config, hass) {
    return { title: "Mental Health", views: [{ title: "Mental Health", path: "mental-health", icon: "mdi:heart-pulse", panel: true,
      cards: [{ type: "custom:mental-health-app-card" }] }] };
  }
}
if (!customElements.get("ll-strategy-dashboard-mental-health")) customElements.define("ll-strategy-dashboard-mental-health", MHStrategy);

/* App als Karte (für die Strategie): lädt das Panel-Modul bei Bedarf */
class AppCard extends HTMLElement {
  setConfig(c) { this._config = c; }
  set hass(h) {
    this._hass = h;
    if (!this._el) {
      this._el = document.createElement("mental-health-panel");
      this._el.setAttribute("embedded", "");
      this.appendChild(this._el);
      loadPanel().then(() => { this._el.hass = this._hass; this._el.narrow = window.innerWidth < 760; });
    }
    if (customElements.get("mental-health-panel")) this._el.hass = h;
  }
  getCardSize() { return 12; }
}
if (!customElements.get("mental-health-app-card")) customElements.define("mental-health-app-card", AppCard);

let _panelPromise = null;
function loadPanel() {
  if (customElements.get("mental-health-panel")) return Promise.resolve();
  if (!_panelPromise) {
    // Panel-URL aus der eigenen Modul-URL ableiten (…/mental-health.js?v=<karte>&p=<panel>)
    const u = new URL(SELF_URL, location.href);
    const url = new URL("mental-health-panel.js", u);
    url.searchParams.set("v", u.searchParams.get("p") || u.searchParams.get("v") || VERSION);
    _panelPromise = import(url.href);
  }
  return _panelPromise;
}

window.__MH = { VERSION, DOMAIN, PANEL, I18N, tr, langOf, normLang, esc, clamp, reduced, fmtNum, fmtTime, fmtDate, fmtDur, sign,
  moodEmoji, moodColor, toneColor, WEATHER, CSS, Api, ring, lineChart, smooth, attachTips, countUp, confetti, toast, shake,
  pinDialog, weightTile, protectHtml, nightRow, previewHtml, bindPreview, lsGet, lsSet, MHBase, MHCheckin, loadPanel, ssGet, ssSet };
console.info(`%c Mental Health %c ${VERSION} `, "background:#2fd6b0;color:#04130f;border-radius:4px 0 0 4px;padding:2px 6px", "background:#17181c;color:#2fd6b0;border-radius:0 4px 4px 0;padding:2px 6px");
})();
