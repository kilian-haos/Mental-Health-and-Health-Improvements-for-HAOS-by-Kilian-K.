// Browser test of cards + panel with a simulated backend (tests/browser/harness.html).
// German + English, desktop + phone width, adult / child / admin / not set up. Screenshots in <out>.
//   npm install --no-save playwright@1.47.2 && npx playwright install chromium
//   node tests/browser/run.js tests/browser/out
// Optional: MH_BROWSER=/path/to/chromium-based-browser
const { chromium } = require("playwright");
const http = require("http");
const fs = require("fs");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..");
const OUT = path.resolve(process.argv[2] || path.join(__dirname, "out"));
fs.mkdirSync(OUT, { recursive: true });

const TYPES = { ".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".png": "image/png" };
const server = http.createServer((req, res) => {
  if (req.url.startsWith("/favicon")) { res.writeHead(204); res.end(); return; }
  const p = path.join(ROOT, decodeURIComponent(req.url.split("?")[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); res.end(); return; }
  res.writeHead(200, { "Content-Type": TYPES[path.extname(p)] || "application/octet-stream" });
  fs.createReadStream(p).pipe(res);
});

let passed = 0, failed = 0;
const fails = [];
function check(name, cond, info) {
  if (cond) passed++;
  else { failed++; fails.push(name + (info ? ` – ${info}` : "")); }
}

// Shadow-DOM-tiefe Suche
const deep = `(sel) => { const out = []; const walk = (root) => { root.querySelectorAll(sel).forEach((e) => out.push(e)); root.querySelectorAll("*").forEach((e) => { if (e.shadowRoot) walk(e.shadowRoot); }); }; walk(document); return out; }`;

async function open(browser, q, viewport) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, reducedMotion: "reduce" });
  const page = await ctx.newPage();
  const errs = [];
  page.on("pageerror", (e) => errs.push(String(e.message)));
  page.on("console", (m) => { if (m.type() === "error") errs.push(m.text()); });
  page.on("response", (r) => { if (r.status() >= 400) errs.push(`${r.status()} ${r.url()}`); });
  await page.goto(`http://127.0.0.1:${server.address().port}/tests/browser/harness.html?${q}`);
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 15000 });
  await page.waitForTimeout(900);
  return { page, ctx, errs };
}
const count = (page, sel) => page.evaluate(`(${deep})(${JSON.stringify(sel)}).length`);
const text = (page, sel) => page.evaluate(`(${deep})(${JSON.stringify(sel)}).map((e) => e.textContent).join(" | ")`);
const click = (page, sel, i = 0) => page.evaluate(`(() => { const l = (${deep})(${JSON.stringify(sel)}); if (!l[${i}]) return false; l[${i}].click(); return true; })()`);

(async () => {
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  const browser = await chromium.launch(process.env.MH_BROWSER ? { executablePath: process.env.MH_BROWSER } : {});
  const DESK = { width: 1300, height: 950 }, PHONE = { width: 390, height: 844 };
  for (const lang of ["de", "en"]) {
    const T = (de, en) => (lang === "de" ? de : en);
    // ---------------- Panel: Heute (Erwachsener)
    let { page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&tab=today&open=evening`, DESK);
    check(`${lang} today: Tabs`, (await count(page, ".tab")) >= 5);
    check(`${lang} today: offene Abfrage pulsiert`, (await count(page, "button.primary.pulse")) >= 1);
    check(`${lang} today: Sektionen`, (await count(page, "section.sec")) >= 6);
    check(`${lang} today: Sprache`, (await text(page, ".tab")).includes(T("Heute", "Today")));
    check(`${lang} today: Guide`, (await count(page, ".guide p")) >= 7);
    check(`${lang} today: Sleepmaxing`, (await text(page, ".chip")).includes(T("ggü. Woche", "vs. week")));
    check(`${lang} today: Optimum sichtbar`, (await text(page, ".chip")).includes("Optimum"));
    check(`${lang} today: Konfetti-Geburtstag/Glücksglas`, (await text(page, "section")).includes(T("Glücksglas", "happiness jar")));
    await page.screenshot({ path: path.join(OUT, `${lang}_today_desktop.png`), fullPage: true });
    // Check-in abends: Pflichtfelder
    await click(page, "button.primary.pulse");
    await page.waitForTimeout(700);
    check(`${lang} checkin: Formular`, (await count(page, "mh-checkin")) === 1);
    check(`${lang} checkin: Regler`, (await count(page, ".slider")) >= 3);
    await click(page, "button.save");
    await page.waitForTimeout(500);
    const errFields = await count(page, ".field.err");
    check(`${lang} checkin: Pflichtfelder markiert`, errFields >= 4, `got ${errFields}`);
    await page.screenshot({ path: path.join(OUT, `${lang}_checkin_evening_errors.png`), fullPage: false });
    // ausfüllen
    await page.evaluate(`(() => { const r = (${deep})(".slider input")[0]; r.value = 8; r.dispatchEvent(new Event("input", { bubbles: true })); })()`);
    await page.evaluate(`(() => { const ins = (${deep})('[data-list="good"] input'); ins[0].value = "Spaziergang"; ins[0].dispatchEvent(new Event("input", { bubbles: true })); const b = (${deep})('[data-list="bad"] input'); b[0].value = "Regen"; b[0].dispatchEvent(new Event("input", { bubbles: true })); })()`);
    await click(page, '[data-yesno] button[data-v="1"]');
    await page.waitForTimeout(250);
    check(`${lang} checkin: Trainingsart erscheint`, (await count(page, "[data-ttype] button")) === 6);
    await click(page, '[data-period] button[data-v="yes"]');
    await page.waitForTimeout(250);
    check(`${lang} checkin: Periode Details`, (await count(page, "[data-flow] button")) === 4);
    await click(page, '[data-flow] button[data-v="medium"]');
    await page.evaluate(`(() => { const p = (${deep})("[data-pain]")[0]; p.value = 4; p.dispatchEvent(new Event("change", { bubbles: true })); })()`);
    await page.waitForTimeout(250);
    await page.screenshot({ path: path.join(OUT, `${lang}_checkin_evening.png`), fullPage: false });
    // Brain Dump im Abend-Check-in: mehrere neue Punkte, nur die neuen sichtbar, aufklappbares Abhaken
    await page.evaluate(`(() => { const i = (${deep})(".dinput")[0]; i.focus(); })()`);
    await page.keyboard.type(T("Zahnarzt anrufen", "Call dentist"));
    await page.keyboard.press("Enter");
    await page.waitForTimeout(150);
    await page.keyboard.type(T("Milch kaufen", "Buy milk"));
    await page.keyboard.press("Enter");
    await page.waitForTimeout(200);
    check(`${lang} dump: zwei neue Punkte sichtbar`, (await count(page, ".dnew .drow")) === 2);
    check(`${lang} dump: Fokus bleibt im Eingabefeld`, await page.evaluate(`(() => { const i = (${deep})(".dinput")[0]; return i.getRootNode().activeElement === i; })()`));
    await click(page, ".dnew [data-dnew]");
    check(`${lang} dump: neuer Punkt abhakbar`, (await count(page, ".dnew .chk.on")) === 1);
    check(`${lang} dump: Abhak-Bereich eingeklappt`, (await count(page, ".foldbody.open")) === 0);
    await click(page, "[data-dfold]");
    await page.waitForTimeout(400);
    check(`${lang} dump: Abhak-Bereich aufgeklappt`, (await count(page, ".foldbody.open")) === 1);
    await click(page, '[data-dexp="a"]');
    await page.waitForTimeout(350);
    check(`${lang} dump: Unterpunkte aufgeklappt`, (await count(page, ".dkids.open")) >= 1);
    await click(page, '[data-dchk="a"]');
    await page.waitForTimeout(200);
    check(`${lang} dump: Haken gilt für alle Unterpunkte`, (await count(page, '[data-dchk="a31"].on')) === 1 && (await count(page, '[data-dchk="a2"].on')) === 1);
    await page.screenshot({ path: path.join(OUT, `${lang}_checkin_dump.png`), fullPage: false });
    await click(page, "button.save");
    await page.waitForTimeout(900);
    const sub = await page.evaluate(() => { const c = window.__calls.filter((x) => x.type === "mental_health/submit").pop(); return c && c.data.dump; });
    check(`${lang} dump: wird mit gespeichert`, sub && sub.add.length === 2 && sub.done.includes("a") && sub.done.includes("a31"), JSON.stringify(sub));
    const submits = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/submit").length);
    check(`${lang} checkin: gespeichert`, (await count(page, "mh-checkin")) === 0, `submits=${submits}`);
    const drafts = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/draft").length);
    check(`${lang} checkin: Entwurf serverseitig`, drafts >= 0);
    // Brain-Dump-Vorschau + Unterseite
    check(`${lang} dump: Vorschau 2 älteste + 2 neueste`, (await count(page, ".dprev")) === 4);
    await click(page, '[data-act="dump"]');
    await page.waitForTimeout(700);
    check(`${lang} dump: Unterseite`, (await count(page, ".dumppage .dnode")) >= 4);
    await click(page, '[data-pmenu="b"]');
    await page.waitForTimeout(300);
    check(`${lang} dump: Aktionsleiste`, (await count(page, ".dacts.open")) === 1);
    await click(page, '[data-pop="addsub"][data-id="b"]');
    await page.waitForTimeout(400);
    await page.keyboard.type("Belege sammeln");
    await page.keyboard.press("Enter");
    await page.waitForTimeout(400);
    const dumpState = await page.evaluate(() => (window.__dump || []).find((x) => x.id === "b"));
    check(`${lang} dump: Unterpunkt angelegt`, dumpState && dumpState.children.length === 1, JSON.stringify(dumpState));
    await click(page, '[data-pchk="a"]');
    await page.waitForTimeout(400);
    const a = await page.evaluate(() => (window.__dump || []).find((x) => x.id === "a"));
    check(`${lang} dump: Kaskade auf Unterseite`, a && a.done && a.children.every((c) => c.done));
    await click(page, ".dshowdone");
    await page.waitForTimeout(300);
    check(`${lang} dump: Erledigte einblenden`, (await count(page, ".dumppage .drow.done")) >= 2);
    await page.screenshot({ path: path.join(OUT, `${lang}_dump_page.png`), fullPage: true });
    await click(page, ".dback");
    await page.waitForTimeout(500);
    check(`${lang} dump: zurück zu Heute`, (await count(page, ".dprev")) >= 1);
    check(`${lang} today: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Morgen-Check-in mit Schlafkorrektur
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&tab=today&open=morning`, PHONE));
    await click(page, "button.primary.pulse");
    await page.waitForTimeout(700);
    check(`${lang} morning: Schlafkarte`, (await count(page, "[data-night]")) === 1);
    await click(page, '[data-sleep] button[data-v="correct"]');
    await page.waitForTimeout(300);
    check(`${lang} morning: Zieh-Griffe`, (await count(page, ".night .handle")) === 2);
    check(`${lang} morning: Prognose`, (await text(page, ".tile")).includes(T("Stimmungsprognose", "Mood forecast")));
    await page.screenshot({ path: path.join(OUT, `${lang}_checkin_morning_phone.png`), fullPage: false });
    check(`${lang} morning: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Insights
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&tab=insights`, DESK));
    check(`${lang} insights: Year in Pixels`, (await count(page, ".pixels i")) > 300);
    check(`${lang} insights: Diagramme`, (await count(page, "svg.chart")) >= 5);
    check(`${lang} insights: Text-Insights`, (await text(page, ".tile")).includes(T("Natur", "nature")));
    check(`${lang} insights: Wochenrückblick`, (await text(page, "h3")).includes(T("Wochenrückblick", "Weekly review")));
    await page.screenshot({ path: path.join(OUT, `${lang}_insights.png`), fullPage: true });
    check(`${lang} insights: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Verlauf + Suche
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&tab=history`, DESK));
    check(`${lang} history: Kalender`, (await count(page, ".cal .d")) >= 28);
    await page.waitForTimeout(400);
    check(`${lang} history: Tagesdetail`, (await count(page, ".entry")) >= 2);
    await page.evaluate(`(() => { const q = (${deep})("input.q")[0]; q.value = ${JSON.stringify(T("schlechte Tage letzten Monat Wald", "bad days last month forest"))}; })()`);
    await click(page, "button.go");
    await page.waitForTimeout(700);
    check(`${lang} history: Suchergebnisse`, (await count(page, ".res")) >= 3);
    check(`${lang} history: Filter-Chips`, (await count(page, "[data-rm]")) >= 2);
    check(`${lang} history: Hervorhebung`, (await count(page, ".res mark")) >= 1);
    await page.screenshot({ path: path.join(OUT, `${lang}_history.png`), fullPage: true });
    check(`${lang} history: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Familie
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&tab=family`, PHONE));
    check(`${lang} family: Wetter`, (await text(page, ".title")).includes(T("Heiter", "Mostly sunny")));
    check(`${lang} family: Handy-Leiste`, await page.evaluate(`getComputedStyle((${deep})("nav.bottom")[0]).display !== "none"`));
    await page.screenshot({ path: path.join(OUT, `${lang}_family_phone.png`), fullPage: true });
    check(`${lang} family: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Profil + Quellen-Assistent + Modell
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&tab=profile`, DESK));
    check(`${lang} profile: Module`, (await count(page, "[data-mod]")) === 15);
    // Check-in-Zeiten: eigene Zeitfelder (kein nativer Picker), schlafbasiert ohne Uhrzeiten
    check(`${lang} profile: kein nativer Zeit-/Datumspicker`, (await count(page, 'input[type="time"], input[type="date"], input[type="datetime-local"]')) === 0);
    check(`${lang} profile: zwei Zeitfenster`, (await count(page, ".slot")) === 2);
    check(`${lang} profile: morgens ein Feld für jeden Tag`, (await count(page, '[data-timeall="morning"]')) === 1 && (await count(page, '[data-time="morning"]')) === 0);
    check(`${lang} profile: schlafbasiert ohne Uhrzeiten`, (await count(page, '.slot[data-slot="evening"] .tin')) === 0 && (await count(page, '.slot[data-slot="evening"] [data-gap]')) === 1);
    const lastSched = () => page.evaluate(() => { const c = window.__calls.filter((x) => x.type === "mental_health/profile_update" && x.changes.schedule); return c.length ? c[c.length - 1].changes.schedule : null; });
    await page.evaluate(`(() => { const i = (${deep})('[data-timeall="morning"]')[0]; i.focus(); i.select(); })()`);
    await page.keyboard.type("645");
    await page.waitForTimeout(150);
    check(`${lang} profile: Zeitmaske formatiert`, (await page.evaluate(`(${deep})('[data-timeall="morning"]')[0].value`)) === "06:45");
    let sc = await lastSched();
    check(`${lang} profile: jeden Tag gespeichert`, !!sc && sc.morning && sc.morning.times.every((t) => t === "06:45"), JSON.stringify(sc));
    await page.evaluate(`(${deep})('[data-wdopen="morning"]')[0].click()`);
    await page.waitForTimeout(400);
    check(`${lang} profile: pro Wochentag 7 Felder`, (await count(page, '[data-time="morning"]')) === 7);
    await page.evaluate(`(() => { const i = (${deep})('[data-time="morning"][data-i="5"]')[0]; i.focus(); i.select(); })()`);
    await page.keyboard.type("915");
    await page.waitForTimeout(150);
    sc = await lastSched();
    check(`${lang} profile: Samstag einzeln gespeichert`, !!sc && sc.morning.times[5] === "09:15" && sc.morning.times[0] === "06:45", JSON.stringify(sc && sc.morning));
    // ungültige Zeit -> zurück auf alten Wert, nichts gespeichert
    const nCalls = await page.evaluate(() => window.__calls.length);
    await page.evaluate(`(() => { const i = (${deep})('[data-time="morning"][data-i="0"]')[0]; i.focus(); i.select(); })()`);
    await page.keyboard.type("2");
    await page.keyboard.press("Tab");
    await page.waitForTimeout(150);
    check(`${lang} profile: kurze Eingabe wird ergänzt`, (await page.evaluate(`(${deep})('[data-time="morning"][data-i="0"]')[0].value`)) === "02:00");
    await page.evaluate(`(() => { const i = (${deep})('[data-time="morning"][data-i="1"]')[0]; i.focus(); i.value = "25:99"; i.dispatchEvent(new Event("blur")); })()`);
    check(`${lang} profile: ungültige Zeit verworfen`, (await page.evaluate(`(${deep})('[data-time="morning"][data-i="1"]')[0].value`)) === "06:45");
    // Pfeiltaste: +5 min
    await page.evaluate(`(${deep})('[data-time="morning"][data-i="2"]')[0].focus()`);
    await page.keyboard.press("ArrowUp");
    await page.waitForTimeout(650);
    sc = await lastSched();
    check(`${lang} profile: Pfeiltaste +5 min`, !!sc && sc.morning.times[2] === "06:50", JSON.stringify(sc && sc.morning));
    check(`${lang} profile: gültige Eingaben gespeichert`, (await page.evaluate(() => window.__calls.length)) > nCalls);
    // Abstand zum Schlaf mit − / +
    await page.evaluate(`(${deep})('[data-gap] .st-btn[data-d="1"]')[0].click()`);
    await page.waitForTimeout(600);
    let gapCalls = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/profile_update" && c.changes.schedule && c.changes.schedule.sleep_gap_min != null).map((c) => c.changes.schedule.sleep_gap_min));
    check(`${lang} profile: Abstand + 5`, gapCalls.includes(25), JSON.stringify(gapCalls));
    // Modus wechseln: abends feste Uhrzeit -> Uhrzeiten erscheinen, Abstand verschwindet
    await page.evaluate(`(${deep})('[data-mode="evening"] .mseg[data-v="fixed"]')[0].click()`);
    await page.waitForTimeout(500);
    sc = await lastSched();
    check(`${lang} profile: Moduswechsel gespeichert`, !!sc && sc.evening && sc.evening.mode === "fixed" && sc.evening.times.length === 7, JSON.stringify(sc));
    check(`${lang} profile: abends Uhrzeit sichtbar`, (await count(page, '[data-timeall="evening"]')) === 1 && (await count(page, "[data-gap]")) === 0);
    check(`${lang} profile: Moduswahl markiert`, (await page.evaluate(`(${deep})('[data-mode="evening"]')[0].style.getPropertyValue("--k")`)).trim() === "0");
    await page.evaluate(`(${deep})('[data-mode="evening"] .mseg[data-v="entity"]')[0].click()`);
    await page.waitForTimeout(500);
    await (await page.evaluateHandle(`(${deep})('.slot')[0].closest('.sec')`)).asElement().screenshot({ path: path.join(OUT, `${lang}_profile_times_entity.png`) }).catch((e) => errs.push(String(e)));
    check(`${lang} profile: Entität mit Versatz`, (await count(page, '[data-sent="evening"]')) === 1 && (await count(page, '[data-soff="evening"]')) === 1);
    await page.evaluate(`(${deep})('[data-mode="evening"] .mseg[data-v="sleep"]')[0].click()`);
    await page.waitForTimeout(500);
    check(`${lang} profile: zurück auf Schlaf`, (await count(page, '.slot[data-slot="evening"] .tin')) === 0 && (await count(page, "[data-gap]")) === 1);
    await (await page.evaluateHandle(`(${deep})('.slot')[0].closest('.sec')`)).asElement().screenshot({ path: path.join(OUT, `${lang}_profile_times.png`) }).catch((e) => errs.push(String(e)));
    await page.waitForTimeout(600);
    check(`${lang} profile: Modell-Canvas`, (await count(page, "canvas.model")) === 1);
    // Datumsmaske (2FA-Stil): Tippen springt weiter, gültiges Datum wird gespeichert
    check(`${lang} profile: Datumsmaske 8 Felder`, (await count(page, '[data-dm="birthdate"] input')) === 8);
    await page.evaluate(`(() => { const c = (${deep})('[data-dm="birthdate"] input'); c.forEach((x) => { x.value = ""; }); c[0].focus(); })()`);
    await page.keyboard.type("05111991");
    await page.waitForTimeout(300);
    let upd = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/profile_update").map((c) => c.changes.birthdate));
    check(`${lang} profile: Datum TT.MM.JJJJ gespeichert`, upd.includes("1991-11-05"), JSON.stringify(upd));
    // ungültiges Datum: rot markiert, nicht gespeichert
    await page.evaluate(`(() => { const c = (${deep})('[data-dm="birthdate"] input'); c.forEach((x) => { x.value = ""; }); c[0].focus(); })()`);
    await page.keyboard.type("31022000");
    await page.waitForTimeout(250);
    check(`${lang} profile: ungültiges Datum markiert`, (await count(page, '[data-dm="birthdate"].err')) === 1);
    upd = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/profile_update").map((c) => c.changes.birthdate));
    check(`${lang} profile: ungültiges Datum nicht gespeichert`, !upd.includes("2000-02-31"));
    // ohne Jahr + Rücktaste
    await page.keyboard.press("Backspace"); await page.keyboard.press("Backspace"); await page.keyboard.press("Backspace"); await page.keyboard.press("Backspace");
    await page.waitForTimeout(250);
    upd = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/profile_update").map((c) => c.changes.birthdate));
    check(`${lang} profile: ungültiger Tag ohne Jahr nie gespeichert`, upd.includes("--02-31") === false);
    await page.evaluate(`(() => { const c = (${deep})('[data-dm="birthdate"] input'); c.forEach((x) => { x.value = ""; }); c[0].focus(); })()`);
    await page.keyboard.type("2412");
    await page.waitForTimeout(250);
    const focusedIdx = await page.evaluate(`(() => { const box = (${deep})('[data-dm="birthdate"]')[0]; const a = box.getRootNode().activeElement; return a && a.dataset ? a.dataset.i : null; })()`);
    check(`${lang} profile: springt von Monat ins Jahr`, focusedIdx === "4", String(focusedIdx));
    upd = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/profile_update").map((c) => c.changes.birthdate));
    check(`${lang} profile: ohne Jahr nicht vorschnell gespeichert`, !upd.includes("--12-24"));
    await page.evaluate(`(() => { const b = (${deep})('[data-dm="birthdate"] input')[4]; b.blur(); (${deep})('h3')[0].click(); })()`);
    await page.waitForTimeout(300);
    upd = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/profile_update").map((c) => c.changes.birthdate));
    check(`${lang} profile: ohne Jahr beim Verlassen gespeichert`, upd.includes("--12-24"), JSON.stringify(upd));
    // befüllte Felder überschreiben (Jahr ändern)
    await page.evaluate(`(() => { const c = (${deep})('[data-dm="birthdate"] input'); "20042016".split("").forEach((d, i) => { c[i].value = d; }); c[4].focus(); })()`);
    await page.keyboard.type("2017");
    await page.waitForTimeout(300);
    upd = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/profile_update").map((c) => c.changes.birthdate));
    check(`${lang} profile: befülltes Jahr überschrieben`, upd.includes("2017-04-20"), JSON.stringify(upd));
    // Einfügen eines ganzen Datums
    await page.evaluate(`(() => { const c = (${deep})('[data-dm="birthdate"] input')[0]; const dt = new DataTransfer(); dt.setData("text", "17.05.1990"); c.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true })); })()`);
    await page.waitForTimeout(250);
    upd = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/profile_update").map((c) => c.changes.birthdate));
    check(`${lang} profile: Einfügen`, upd.includes("1990-05-17"), JSON.stringify(upd));
    check(`${lang} profile: Pause-Datum als Maske`, (await count(page, '[data-dm="pause_until"] input')) === 8);
    await page.evaluate(`(() => { const el = (${deep})('[data-dm="birthdate"]')[0]; el.scrollIntoView(); })()`);
    await page.screenshot({ path: path.join(OUT, `${lang}_datemask.png`), fullPage: false });
    await click(page, "[data-sedit]");
    await page.waitForTimeout(800);
    check(`${lang} profile: Quellen-Vorschau`, (await count(page, ".graph polyline")) === 1);
    check(`${lang} profile: ziehbare Schwelle`, (await count(page, ".graph .thrh")) === 1);
    await page.screenshot({ path: path.join(OUT, `${lang}_profile.png`), fullPage: true });
    check(`${lang} profile: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Profil am Handy: Check-in-Zeiten ohne Überlauf, auch pro Wochentag
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&tab=profile`, PHONE));
    await page.evaluate(`(${deep})('[data-wdopen="morning"]')[0].click()`);
    await page.waitForTimeout(600);
    const over = await page.evaluate(`(() => { const sec = (${deep})('.slot')[0].closest('.sec'); const r = sec.getBoundingClientRect(); const bad = [];
      sec.querySelectorAll('*').forEach((e) => { const b = e.getBoundingClientRect(); if (b.width && (b.right > r.right + 0.5 || b.left < r.left - 0.5)) bad.push(e.tagName + '.' + e.className); }); return bad; })()`);
    check(`${lang} profile phone: Zeiten ohne Überlauf`, over.length === 0, over.slice(0, 5).join(", "));
    const segFit = await page.evaluate(`(${deep})('.mseg').every((b) => b.scrollWidth <= b.clientWidth + 1)`);
    check(`${lang} profile phone: Modus-Beschriftungen passen`, segFit);
    await (await page.evaluateHandle(`(${deep})('.slot')[0].closest('.sec')`)).asElement().screenshot({ path: path.join(OUT, `${lang}_profile_times_phone.png`) }).catch((e) => errs.push(String(e)));
    check(`${lang} profile phone: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Kind
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=child&tab=today&open=evening`, PHONE));
    await click(page, "button.primary.pulse");
    await page.waitForTimeout(700);
    check(`${lang} child: kindgerechte Frage`, (await text(page, ".q")).includes(T("Wie geht's dir heute?", "How are you today?")));
    check(`${lang} child: kein Gewicht`, (await count(page, "[data-num]")) === 0);
    check(`${lang} child: Sport statt Training`, (await text(page, ".q")).includes(T("Sport", "sport")));
    await page.screenshot({ path: path.join(OUT, `${lang}_child_checkin.png`), fullPage: false });
    await page.evaluate(`(() => { const s = (${deep})(".sheet .x")[0]; if (s) s.click(); })()`);
    await page.waitForTimeout(300);
    await click(page, '[data-tab="profile"]');
    await page.waitForTimeout(900);
    check(`${lang} child: Einstellungen ausgegraut`, (await count(page, ".locked-field")) >= 1);
    check(`${lang} child: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Admin
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=admin&tab=admin`, DESK));
    check(`${lang} admin: Personenliste`, (await count(page, ".person-row")) === 3);
    check(`${lang} admin: Anfrage`, (await text(page, "h3")).includes(T("Einrichtungs-Anfragen", "Setup requests")));
    check(`${lang} admin: Backup`, (await count(page, "[data-brs]")) === 1);
    check(`${lang} admin: Uhrzeiten ohne nativen Picker`, (await count(page, "[data-sttime]")) === 4 && (await count(page, 'input[type="time"]')) === 0);
    await page.evaluate(`(() => { const i = (${deep})('[data-sttime="nightly"]')[0]; i.focus(); i.select(); })()`);
    await page.keyboard.type("0415");
    await page.waitForTimeout(200);
    const stc = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/admin_settings" || (c.changes && c.changes.nightly)).map((c) => JSON.stringify(c)));
    check(`${lang} admin: Uhrzeit gespeichert`, stc.some((x) => x.includes('"04:15"')), stc.join(" | ").slice(0, 300) + " value=" + (await page.evaluate(`(${deep})('[data-sttime="nightly"]')[0].value`)));
    // Backup löschen mit Bestätigung
    await click(page, "[data-bdel]");
    await page.waitForTimeout(300);
    check(`${lang} admin: Lösch-Bestätigung`, (await count(page, ".scrim .dialog")) === 1);
    await click(page, ".scrim .yes");
    await page.waitForTimeout(500);
    const del = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/backup_delete").map((c) => c.name));
    check(`${lang} admin: Backup gelöscht`, del.length === 1 && del[0].endsWith(".mhbackup"), JSON.stringify(del));
    await page.waitForTimeout(400);
    await click(page, "[data-create]");
    await page.waitForTimeout(300);
    check(`${lang} admin: Datumsmaske im Assistenten`, (await count(page, '[data-dm="wbirth"] input')) === 8);
    await page.waitForTimeout(300);
    check(`${lang} admin: Anlege-Assistent`, (await count(page, ".steps i")) >= 3);
    await page.screenshot({ path: path.join(OUT, `${lang}_admin.png`), fullPage: true });
    await click(page, "[data-pp]");
    await page.waitForTimeout(900);
    check(`${lang} admin: Person bearbeiten`, (await count(page, ".delp")) === 1);
    check(`${lang} admin: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Admin-PIN statt persönlicher PIN: Admin für diese Sitzung, mit Hinweis
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&tab=today&apin=1`, DESK));
    check(`${lang} adminpin: Schlüssel-Knopf`, (await count(page, ".keyb")) === 1);
    check(`${lang} adminpin: kein Admin-Tab vorher`, (await count(page, '.tab[data-tab="admin"]')) === 0);
    await click(page, ".keyb");
    await page.waitForTimeout(300);
    for (const d of "9999") { await click(page, `.pin-pad button[data-k="${d}"]`); await page.waitForTimeout(40); }
    await page.waitForTimeout(900);
    check(`${lang} adminpin: Admin-Tab danach`, (await count(page, '.tab[data-tab="admin"]')) === 1);
    check(`${lang} adminpin: Hinweis „als Admin“`, (await count(page, ".admin-flag")) === 1);
    await page.screenshot({ path: path.join(OUT, `${lang}_admin_elevated.png`), fullPage: false });
    check(`${lang} adminpin: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Nicht angelegt: Vorschau + Anfrage
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=new`, PHONE));
    check(`${lang} preview: Vorschau-Badge`, (await text(page, ".preview-tag")).includes(T("Vorschau", "Preview")));
    await page.screenshot({ path: path.join(OUT, `${lang}_preview_phone.png`), fullPage: true });
    await click(page, "button.req");
    await page.waitForTimeout(900);
    const req = await page.evaluate(() => window.__calls.some((c) => c.type === "mental_health/request_setup"));
    check(`${lang} preview: Anfrage gesendet`, req);
    check(`${lang} preview: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();

    // Dashboard-Karten
    ({ page, ctx, errs } = await open(browser, `lang=${lang}&user=adult&view=cards&open=evening`, DESK));
    await page.waitForTimeout(800);
    check(`${lang} cards: 8 Karten`, (await count(page, ".card")) >= 8);
    check(`${lang} cards: Ringe`, (await count(page, "svg.ringsvg")) >= 3);
    check(`${lang} cards: customCards`, await page.evaluate(() => window.customCards.filter((c) => c.type.startsWith("mental-health")).length === 8));
    check(`${lang} cards: Strategie`, await page.evaluate(() => !!customElements.get("ll-strategy-dashboard-mental-health")));
    await page.screenshot({ path: path.join(OUT, `${lang}_cards.png`), fullPage: true });
    check(`${lang} cards: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
    await ctx.close();
  }
  await browser.close();
  server.close();
  console.log(`Browser checks: ${passed} passed, ${failed} failed`);
  for (const f of fails) console.log("  ✗ " + f);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
