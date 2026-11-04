// Renders cover.png, slides.pdf, architecture diagram frames and end cards from the HTML templates.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const OUT = path.resolve("out");
const WORK = `${OUT}/work/html`;
fs.mkdirSync(WORK, { recursive: true });
fs.mkdirSync(`${OUT}/work/frames`, { recursive: true });
fs.copyFileSync("theme.css", `${WORK}/theme.css`);

const index = fs.readFileSync("../web/index.html", "utf8");
const svg = index.match(/<svg id="ahmes"[\s\S]*?<\/svg>/)[0]
  .replace('id="ahmes" class="ahmes"', 'class="ahmes is-happy" style="width:100%;height:auto"');

for (const f of ["slides", "cover", "diagram", "endcard"]) {
  const html = fs.readFileSync(`${f}.html`, "utf8").replaceAll("<!--AHMES-HAPPY-->", svg);
  fs.writeFileSync(`${WORK}/${f}.html`, html);
}

const b = await chromium.launch();
const page = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, colorScheme: "light" });
const open = async (f, q = "") => {
  await page.goto(`file://${WORK}/${f}.html${q}`, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(300);
};

await open("cover");
await page.screenshot({ path: `${OUT}/cover.png` });
for (let i = 1; i <= 6; i++) { await open("diagram", `?step=${i}`); await page.screenshot({ path: `${OUT}/work/frames/diagram${i}.png` }); }
await open("endcard", "?mode=quote"); await page.screenshot({ path: `${OUT}/work/frames/end_quote.png` });
await open("endcard", "?mode=url"); await page.screenshot({ path: `${OUT}/work/frames/end_url.png` });
await open("slides");
await page.pdf({ path: `${OUT}/slides.pdf`, width: "1920px", height: "1080px", printBackground: true, preferCSSPageSize: true });
await b.close();
console.log("assets done");
