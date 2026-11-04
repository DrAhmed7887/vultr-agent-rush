// v2 stills: architecture frame, score badges (transparent), end card.
import { chromium } from "playwright";
import fs from "node:fs";
const W = "out/work2/html", F = "out/work2/frames";
fs.mkdirSync(W, { recursive: true }); fs.mkdirSync(F, { recursive: true });
fs.copyFileSync("theme.css", `${W}/theme.css`);
const svg = fs.readFileSync("../web/index.html", "utf8").match(/<svg id="ahmes"[\s\S]*?<\/svg>/)[0]
  .replace('id="ahmes" class="ahmes"', 'class="ahmes is-happy" style="width:100%;height:auto"');
for (const f of ["diagram2", "endcard", "badge"]) fs.writeFileSync(`${W}/${f}.html`, fs.readFileSync(`${f}.html`, "utf8").replaceAll("<!--AHMES-HAPPY-->", svg));
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
const shot = async (f, q, out, transparent = false) => {
  await p.goto(`file://${process.cwd()}/${W}/${f}.html${q}`, { waitUntil: "networkidle" });
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(250);
  await p.screenshot({ path: `${F}/${out}.png`, omitBackground: transparent });
};
await shot("diagram2", "", "diagram");
await shot("badge", "?n=24%20%2F%2040&l=on%20his%2040-problem%20test&c=%23C6432A", "badge24", true);
await shot("badge", "?n=40%20%2F%2040&l=brand-new%20problems&c=%2312857D", "badge40", true);
await shot("endcard", "?mode=url", "end_url");
await b.close(); console.log("v2 stills done");
