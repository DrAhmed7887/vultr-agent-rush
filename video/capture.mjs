// Drives the LIVE Teach Ahmes site and records raw scenes + event marks. One Chromium at a time.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE = "https://64-177-33-215.sslip.io";
const OUT = path.resolve("out/work");
fs.mkdirSync(`${OUT}/raw`, { recursive: true });
const ZOOM = 1.25;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const marks = {};
const says = {};

async function scene(name, fn) {
  const b = await chromium.launch();
  const ctx = await b.newContext({
    viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, colorScheme: "light",
    recordVideo: { dir: `${OUT}/raw/${name}`, size: { width: 1920, height: 1080 } },
  });
  const page = await ctx.newPage();
  const t0 = Date.now();
  const m = (marks[name] = {});
  const mark = (k) => { m[k] = +((Date.now() - t0) / 1000).toFixed(2); console.log(name, k, m[k]); };
  page.on("response", async (r) => {
    if (!/\/api\/(teach|chip|session)$/.test(r.url())) return;
    try { const d = await r.json(); (says[name] ??= []).push({ t: +((Date.now() - t0) / 1000).toFixed(2), url: r.url(), d }); } catch { /* ignore */ }
  });
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate((z) => { document.documentElement.style.zoom = z; }, ZOOM);
  await sleep(600);
  const scrollY = async (y) => { await page.evaluate((y) => window.scrollTo({ top: y, behavior: "smooth" }), y); await sleep(1200); };
  // page-y (in zoomed px) of an element's top
  const topOf = (sel) => page.evaluate(([s, z]) => (document.querySelector(s).getBoundingClientRect().top + window.scrollY) , [sel, ZOOM]);
  const type = async (text, delay) => { await page.click("#sentence"); await page.fill("#sentence", ""); await page.type("#sentence", text, { delay }); };
  const teach = async () => {
    const resp = page.waitForResponse((r) => r.url().endsWith("/api/teach"), { timeout: 30000 });
    await page.click("#teach"); await resp; await sleep(400);
  };
  try { await fn({ page, mark, scrollY, topOf, type, teach }); }
  finally { await page.close(); await ctx.close(); await b.close(); }
}

const only = process.argv[2];

if (!only || only === "A") await scene("A", async ({ page, mark, scrollY, topOf, type, teach }) => {
  mark("welcome"); await sleep(3500);
  mark("type1_start"); await type("Look at the tenths first.", 70); mark("type1_end"); await sleep(500);
  mark("click1"); await teach(); mark("resp1"); await sleep(1800);
  await scrollY(520); mark("grid1"); await sleep(2800);
  await scrollY(0);
  mark("type2_start"); await type("If the tenths are the same, check the next place, and if every place is the same, they're equal.", 38); mark("type2_end"); await sleep(500);
  mark("click2"); await teach(); mark("resp2"); await sleep(3000);
  await scrollY(520); mark("grid2"); await sleep(2800);
  const y = await topOf(".brain");
  await scrollY(y - 110); mark("brain"); await sleep(1500);
  const lis = await page.$$(".steps li");
  for (const li of lis.slice(0, 3)) { await li.hover(); mark("hover"); await sleep(2600); }
  mark("end"); await sleep(800);
});

if (!only || only === "B") await scene("B", async ({ page, mark, scrollY, type }) => {
  mark("start"); await sleep(1500);
  await page.click("#tab-add_fractions"); mark("tab"); await sleep(2500);
  mark("type_start"); await type("Keep doubling both bottoms until they're the same.", 60); mark("type_end"); await sleep(500);
  mark("click");
  const resp = page.waitForResponse((r) => r.url().endsWith("/api/teach"), { timeout: 30000 });
  await page.click("#teach"); await resp; mark("resp");
  await page.waitForSelector("#stamp:not([hidden])", { timeout: 8000 }).catch(() => {}); mark("stamp"); await sleep(4500);
  await scrollY(520); mark("grid"); await sleep(2500); mark("end");
});

if (!only || only === "C") await scene("C", async ({ page, mark, scrollY, topOf }) => {
  mark("start"); await sleep(1200);
  const y = await topOf(".hood");
  await scrollY(y - 20); await sleep(600); mark("hood");
  await page.click('.chip[data-k="copying"]'); mark("click_oom");
  await page.waitForSelector("#result .facts", { timeout: 20000 }); mark("oom_done"); await sleep(1500);
  const fy = await topOf("#result .facts");
  await scrollY(fy - 230); mark("oom_facts"); await sleep(4200);
  await page.click('#beyond .chip[data-k="network"]'); mark("click_net");
  await page.waitForFunction(() => /unreachable/i.test(document.querySelector("#result")?.textContent || ""), { timeout: 20000 }); mark("net_done");
  await sleep(800);
  const ry = await topOf("#result");
  await scrollY(ry - 220); mark("net_shown"); await sleep(3500);
  const ly = await topOf("#live");
  await scrollY(ly - 220); mark("log"); await sleep(3500); mark("end");
});

const f = `${OUT}/capture.json`;
const prev = fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, "utf8")) : { marks: {}, says: {} };
fs.writeFileSync(f, JSON.stringify({ marks: { ...prev.marks, ...marks }, says: { ...prev.says, ...says } }, null, 1));
