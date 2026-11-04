// v2 capture: drives the LIVE kid flow and records scenes, event marks, API replies and Ahmes's
// real voice clips (with the moment each one was fetched). One Chromium at a time.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE = "https://64-177-33-215.sslip.io";
const OUT = path.resolve("out/work2");
fs.mkdirSync(`${OUT}/raw`, { recursive: true });
fs.mkdirSync(`${OUT}/ahmes`, { recursive: true });
fs.mkdirSync(`${OUT}/frames`, { recursive: true });
const ZOOM = 1.25;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const store = fs.existsSync(`${OUT}/capture.json`) ? JSON.parse(fs.readFileSync(`${OUT}/capture.json`, "utf8")) : { marks: {}, api: {}, voice: {} };

async function scene(name, fn) {
  const b = await chromium.launch();
  const ctx = await b.newContext({
    viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1, colorScheme: "light", acceptDownloads: true,
    recordVideo: { dir: `${OUT}/raw/${name}`, size: { width: 1920, height: 1080 } },
  });
  await ctx.addInitScript(() => { try { localStorage.clear(); } catch { /* fine */ } });
  const page = await ctx.newPage();
  const t0 = Date.now();
  const now = () => +((Date.now() - t0) / 1000).toFixed(2);
  const m = (store.marks[name] = {}); store.api[name] = []; store.voice[name] = [];
  const mark = (k) => { m[k] = now(); console.log(name, k, m[k]); };
  page.on("response", async (r) => {
    const u = r.url();
    try {
      if (/\/api\/(teach|quiz|session|chip|beyond\/\w+)$/.test(u)) store.api[name].push({ t: now(), url: u, d: await r.json() });
      const a = u.match(/\/audio\/(\w+)\.mp3$/);
      if (a && r.ok()) {
        const f = `${OUT}/ahmes/${name}_${String(store.voice[name].length).padStart(2, "0")}_${a[1]}.mp3`;
        fs.writeFileSync(f, await r.body());
        store.voice[name].push({ t: now(), id: a[1], file: f });
      }
    } catch { /* ignore */ }
  });
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate((z) => { document.documentElement.style.zoom = z; }, ZOOM);
  await page.waitForSelector(".lesson", { timeout: 20000 });
  await sleep(500);
  const H = helpers(page, mark);
  try { await fn({ page, mark, ...H }); }
  catch (e) { console.log("SCENE FAILED", name, e.message.split("\n")[0]); store.failed = [...(store.failed || []), name]; }
  finally {
    await page.close(); await ctx.close(); await b.close();
    fs.writeFileSync(`${OUT}/capture.json`, JSON.stringify(store, null, 1));
  }
}

function helpers(page, mark) {
  const visible = (id) => page.waitForSelector(`#${id}:not([hidden])`, { timeout: 40000 });
  const top = () => page.evaluate(() => window.scrollTo({ top: 0, behavior: "smooth" }));
  const lesson = async (k) => { await page.click("#lessons-btn").catch(() => {}); await sleep(400); await page.click(`.lesson[data-k="${k}"]`); await visible("s-check"); };
  const type = async (text, delay = 45) => { await page.click("#sentence"); await page.fill("#sentence", ""); await page.type("#sentence", text, { delay }); };
  const teach = async (text, tag, delay) => {
    await type(text, delay); mark(`${tag}_typed`);
    const resp = page.waitForResponse((r) => r.url().endsWith("/api/teach"), { timeout: 60000 });
    await page.click("#teach"); mark(`${tag}_click`);
    await resp; mark(`${tag}_resp`);
    await page.waitForFunction(() => !document.getElementById("s-retry").hidden || !document.getElementById("s-oops").hidden, null, { timeout: 30000 });
    await sleep(300); mark(`${tag}_shown`);
    console.log("   ", tag, await page.evaluate(() => [...document.querySelectorAll(".screen")].find((x) => !x.hidden)?.querySelector("h1")?.textContent));
  };
  const quiz = async (tag) => {
    await page.click("#retry-next"); mark(`${tag}_click`);
    await page.waitForFunction(() => !document.getElementById("quiz-next").hidden || !document.getElementById("s-win").hidden, null, { timeout: 40000 });
    mark(`${tag}_done`);
    console.log("   ", tag, await page.evaluate(() => document.getElementById("s-win").hidden ? document.getElementById("quiz-text").textContent : "WIN"));
  };
  return { visible, top, lesson, type, teach, quiz };
}

const only = process.argv[2];

// 1-4: decimals, from the first mistake to the seal, then the report
if (!only || only === "D") await scene("D", async ({ page, mark, visible, lesson, teach, quiz }) => {
  mark("map"); await sleep(1200);
  await lesson("compare_decimals"); mark("check"); await sleep(4200);
  await page.click("#mark-no"); mark("marked"); await sleep(4200);
  await page.click("#go-teach"); await visible("s-teach"); mark("teach_screen"); await sleep(1200);
  await teach("Look at the tenths first.", "t1", 70); await sleep(4500);
  await quiz("q1"); await sleep(4500);
  await page.click("#quiz-next"); await visible("s-check"); mark("hw2"); await sleep(3500);
  await page.click("#mark-no"); mark("hw2_marked"); await sleep(3000);
  await page.click("#go-teach"); await visible("s-teach"); await sleep(500);
  await teach("Bigger tenths win.", "t2", 60); await sleep(2500);
  await page.click("#retry-next"); await visible("s-teach"); await sleep(500);
  await teach("The bigger tenth is the bigger number.", "t3", 55); mark("thoth"); await sleep(6500);
  await page.click("#retry-next"); await visible("s-teach"); await sleep(500);
  await teach("The answer is 0.61.", "t_ans", 60); mark("no_rule"); await sleep(4000);
  await page.click("#oops-again"); await visible("s-teach"); await sleep(500);
  await teach("If the tenths are the same, check the next place, and if every place is the same, they're equal.", "t4", 32); await sleep(4000);
  await quiz("q2"); await sleep(5000);
  mark("win"); await sleep(2500);
  const dl = page.waitForEvent("download", { timeout: 10000 }).catch(() => null);
  await page.click("#win-cert"); const d = await dl; if (d) await d.saveAs(path.resolve("out/work2/frames/certificate.png"));
  mark("cert"); await sleep(800);
  await page.click("#report-btn"); await visible("report"); await sleep(1500); mark("report"); await sleep(5500);
  await page.evaluate(() => window.scrollBy({ top: 420, behavior: "smooth" })); await sleep(4000); mark("end");
});

// 5: fractions, the rule that never ends
if (!only || only === "F") await scene("F", async ({ page, mark, visible, lesson, teach }) => {
  await lesson("add_fractions"); mark("check"); await sleep(3500);
  await page.click("#mark-no"); mark("marked"); await sleep(4500);
  await page.click("#go-teach"); await visible("s-teach"); await sleep(800);
  await teach("Keep doubling both bottoms until they're the same.", "t1", 55); mark("dizzy"); await sleep(6500); mark("end");
});

// 6: the Year 6 lessons, one picture each
if (!only || only === "Y") await scene("Y", async ({ page, mark, lesson }) => {
  mark("map"); await sleep(3000);
  for (const k of ["times_tens", "compare_fractions", "order_of_operations", "intervals"]) {
    await lesson(k); mark(`${k}_check`); await sleep(1800);
    await page.click("#mark-no"); mark(`${k}_proof`); await sleep(3200);
  }
  mark("end");
});

// 7: how it works, for the judges
if (!only || only === "H") await scene("H", async ({ page, mark, visible, lesson, teach }) => {
  await lesson("compare_decimals"); await page.click("#mark-no"); await sleep(300); await page.click("#go-teach"); await visible("s-teach");
  await teach("Look at the tenths first.", "t1", 10); mark("taught"); await sleep(600);
  await page.click("#how-btn"); await sleep(1500);
  await page.evaluate(() => document.querySelector(".pipe").scrollIntoView({ behavior: "smooth", block: "start" })); await sleep(1500); mark("pipeline"); await sleep(6000);
  await page.evaluate(() => document.querySelector(".hood").scrollIntoView({ behavior: "smooth", block: "start" })); await sleep(1500); mark("hood"); await sleep(1500);
  await page.click('.chip[data-k="copying"]'); mark("oom_click");
  await page.waitForSelector("#result .facts", { timeout: 30000 }); mark("oom_done"); await sleep(1200);
  await page.evaluate(() => { const r = document.querySelector("#result .facts").getBoundingClientRect(); window.scrollBy({ top: r.top - 260, behavior: "smooth" }); }); await sleep(1500); mark("facts"); await sleep(5000);
  await page.evaluate(() => document.querySelector(".hood").scrollIntoView({ behavior: "smooth", block: "start" })); await sleep(1200);
  await page.click('#beyond .chip[data-k="network"]'); mark("net_click");
  await page.waitForFunction(() => /unreachable/i.test(document.querySelector("#result")?.textContent || ""), null, { timeout: 30000 }); mark("net_done");
  await page.evaluate(() => { const r = document.querySelector("#result").getBoundingClientRect(); window.scrollBy({ top: r.top - 200, behavior: "smooth" }); }); await sleep(4500);
  await page.evaluate(() => document.querySelector("#live").scrollIntoView({ behavior: "smooth", block: "center" })); await sleep(1500); mark("log"); await sleep(4000); mark("end");
});

fs.writeFileSync(`${OUT}/capture.json`, JSON.stringify(store, null, 1));
console.log("saved", Object.keys(store.marks));
