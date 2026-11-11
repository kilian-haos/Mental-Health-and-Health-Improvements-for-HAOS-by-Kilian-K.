// Renders SVG icons to PNG (256 px + 512 px @2x) via canvas in Chromium.
// Usage: node tools/render_icon.js <in.svg> <out.png> [<out@2x.png>]
// Optional: MH_BROWSER=/path/to/chromium-based-browser
const { chromium } = require("playwright");
const fs = require("fs");

(async () => {
  const [svgPath, out1, out2] = process.argv.slice(2);
  const svg = fs.readFileSync(svgPath, "utf8");
  const browser = await chromium.launch(process.env.MH_BROWSER ? { executablePath: process.env.MH_BROWSER } : {});
  const page = await browser.newPage();
  for (const [size, out] of [[256, out1], [512, out2]]) {
    if (!out) continue;
    const data = await page.evaluate(async ({ svg, size }) => {
      const img = new Image();
      img.src = "data:image/svg+xml;base64," + btoa(unescape(encodeURIComponent(svg)));
      await img.decode();
      const c = document.createElement("canvas");
      c.width = c.height = size;
      c.getContext("2d").drawImage(img, 0, 0, size, size);
      return c.toDataURL("image/png");
    }, { svg, size });
    fs.writeFileSync(out, Buffer.from(data.split(",")[1], "base64"));
  }
  await browser.close();
})();
