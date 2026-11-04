// Renders transparent caption PNGs (1920x1080, text in the bottom third) from a manifest.
import { chromium } from "playwright";
import fs from "node:fs";
const items = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const LABEL = { Ahmes: "Ahmes", Child: "Child types" };
const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;");
const CSS = `body{margin:0;width:1920px;height:1080px;background:transparent;font-family:'Lexend',sans-serif}
.w{position:absolute;left:0;right:0;bottom:44px;display:flex;justify-content:center}
.c{max-width:1560px;background:rgba(14,22,56,.93);color:#fff;border-radius:22px;padding:16px 38px 20px;text-align:center;font-size:46px;font-weight:600;line-height:1.28;border:3px solid rgba(255,255,255,.2)}
.s{display:block;font-size:25px;letter-spacing:.12em;text-transform:uppercase;font-weight:700;margin-bottom:2px}
.Ahmes .s{color:#F2C14E}.Child .s{color:#7FF3E6}`;
const b = await chromium.launch();
const pg = await b.newPage({ viewport: { width: 1920, height: 1080 } });
for (const c of items) {
  const label = LABEL[c.who] ? `<span class="s">${LABEL[c.who]}</span>` : "";
  await pg.setContent(`<link href="https://fonts.googleapis.com/css2?family=Lexend:wght@400;600;700&display=swap" rel="stylesheet"><style>${CSS}</style><div class="w"><div class="c ${c.who}">${label}${esc(c.text)}</div></div>`, { waitUntil: "networkidle" });
  await pg.evaluate(() => document.fonts.ready);
  await pg.screenshot({ path: c.file, omitBackground: true });
}
await b.close();
