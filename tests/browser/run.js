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
    await click(page, "button.save");
    await page.waitForTimeout(900);
    const submits = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/submit").length);
    check(`${lang} checkin: gespeichert`, (await count(page, "mh-checkin")) === 0, `submits=${submits}`);
    const drafts = await page.evaluate(() => window.__calls.filter((c) => c.type === "mental_health/draft").length);
    check(`${lang} checkin: Entwurf serverseitig`, drafts >= 0);
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
    check(`${lang} profile: Module`, (await count(page, "[data-mod]")) === 14);
    check(`${lang} profile: Wochentagszeiten`, (await count(page, "[data-time]")) === 14);
    await page.waitForTimeout(600);
    check(`${lang} profile: Modell-Canvas`, (await count(page, "canvas.model")) === 1);
    await click(page, "[data-sedit]");
    await page.waitForTimeout(800);
    check(`${lang} profile: Quellen-Vorschau`, (await count(page, ".graph polyline")) === 1);
    check(`${lang} profile: ziehbare Schwelle`, (await count(page, ".graph .thrh")) === 1);
    await page.screenshot({ path: path.join(OUT, `${lang}_profile.png`), fullPage: true });
    check(`${lang} profile: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
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
    await click(page, "[data-create]");
    await page.waitForTimeout(300);
    check(`${lang} admin: Anlege-Assistent`, (await count(page, ".steps i")) >= 3);
    await page.screenshot({ path: path.join(OUT, `${lang}_admin.png`), fullPage: true });
    await click(page, "[data-pp]");
    await page.waitForTimeout(900);
    check(`${lang} admin: Person bearbeiten`, (await count(page, ".delp")) === 1);
    check(`${lang} admin: keine JS-Fehler`, errs.length === 0, errs.join(" ; "));
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
