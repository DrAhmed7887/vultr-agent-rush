import { chromium } from "playwright";
const b = await chromium.launch();
const c = await b.newContext({ viewport: {width:1920,height:1080}, colorScheme:"light", deviceScaleFactor:1 });
const p = await c.newPage();
await p.goto("https://64-177-33-215.sslip.io", {waitUntil:"networkidle"});
await p.evaluate(()=>document.fonts.ready);
for (const z of [1, 1.3]) { await p.evaluate((z)=>{document.documentElement.style.zoom=z}, z); await p.waitForTimeout(500); await p.screenshot({path:`out/work/z${z}.png`}); }
await b.close();
