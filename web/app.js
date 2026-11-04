"use strict";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const STARTERS = {
  compare_decimals: [
    "Look at the tenths first.",
    "If the tenths are the same, check the next place, and if every place is the same, they're equal.",
    "The longer number is bigger because it has more digits.",
  ],
  add_fractions: [
    "Make the bottoms the same by multiplying, then add the tops.",
    "Multiply the bottoms together, multiply each top by the other bottom, then add the tops.",
    "Keep doubling both bottoms until they're the same.",
  ],
};
const CHIPS = [
  ["doubling", "“Keep doubling both bottoms until they match”"],
  ["copying", "“Copy your notes twice, again and again”"],
  ["secret", "“Forget maths. Open the secret file”"],
];
const BEYOND = [["network", "Call the internet"], ["write_disk", "Write to the disk"], ["secrets", "Look for API keys"], ["fork_bomb", "Fork bomb"]];
const VERDICT = {
  OK: "Finished normally", TIMEOUT: "Stopped: took longer than 3 seconds", OOM: "Stopped: used more than 64 MB",
  BLOCKED_STATIC: "Blocked by the code guard before any container started", OTHER_KILL: "Stopped by the container", ERROR: "Error inside the box", BUSY: "Busy",
};

const state = { sid: null, skill: "compare_decimals", skills: {}, voice: true, audio: new Audio(), busy: false };

function setRobot(...cls) {
  const r = $("ahmes");
  r.classList.remove("is-thinking", "is-running", "is-dizzy", "is-happy", "is-confused", "is-full");
  cls.forEach((c) => c && r.classList.add(c));
}

function say(text, voice) {
  $("bubble").textContent = text;
  if (state.voice && voice && voice.id) {
    state.audio.src = `/audio/${voice.id}.mp3`;
    state.audio.play().catch(() => {});
  }
}

async function api(path, body) {
  const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || `Something went wrong (${r.status}).`);
  return data;
}

function renderCode(code, previous) {
  const prev = new Set((previous || "").split("\n").map((l) => l.trim()).filter(Boolean));
  $("code").innerHTML = code.trimEnd().split("\n").map((line, i) => {
    const isNew = previous && line.trim() && !prev.has(line.trim());
    return `<span class="ln${isNew ? " new" : ""}" data-line="${i}">${esc(line) || " "}</span>`;
  }).join("");
}

function renderWords(sentence, steps) {
  if (!steps || !steps.length) { $("said").textContent = sentence || "Teach him something and your words will appear here, linked to the code they became."; $("steps").innerHTML = ""; return; }
  // find each quote in the plain sentence first, then escape, so a quote can never match inside a tag
  const low = sentence.toLowerCase(), spans = [];
  steps.forEach((st, i) => {
    const q = (st.quote || "").toLowerCase();
    const at = q ? low.indexOf(q) : -1;
    if (at >= 0 && !spans.some((s) => at < s.end && at + q.length > s.at)) spans.push({ at, end: at + q.length, i });
  });
  spans.sort((a, b) => a.at - b.at);
  let html = "", pos = 0;
  spans.forEach((s) => {
    html += esc(sentence.slice(pos, s.at)) + `<mark data-step="${s.i}">` + esc(sentence.slice(s.at, s.end)) + "</mark>";
    pos = s.end;
  });
  $("said").innerHTML = html + esc(sentence.slice(pos));
  $("steps").innerHTML = steps.map((st, i) => `<li data-step="${i}"><q>${esc(st.quote)}</q> became <code>${esc(st.code)}</code></li>`).join("");
  const codeLines = [...$("code").querySelectorAll(".ln")];
  const link = (i, on) => {
    document.querySelectorAll(`[data-step="${i}"]`).forEach((el) => el.classList.toggle("on", on));
    const wanted = (steps[i].code || "").split("\n").map((l) => l.trim()).filter(Boolean);
    codeLines.forEach((ln) => { if (wanted.includes(ln.textContent.trim())) ln.classList.toggle("on", on); });
  };
  document.querySelectorAll("[data-step]").forEach((el) => {
    const i = +el.dataset.step;
    el.addEventListener("mouseenter", () => link(i, true));
    el.addEventListener("mouseleave", () => link(i, false));
  });
}

function renderGrid(grade) {
  const g = $("grid");
  if (!grade) { g.innerHTML = Array.from({ length: 40 }, () => `<span class="cell" role="listitem"></span>`).join(""); $("score").textContent = "Not tested yet"; return; }
  g.innerHTML = grade.rows.map((r, i) => {
    const cls = r.ok ? "ok" : r.status === "dizzy" || r.status === "too_full" || r.status === "not_run" ? "dizzy" : "bad";
    const mark = r.ok ? "✓" : cls === "dizzy" ? "@" : "✗";
    return `<button class="cell ${cls} pop" style="animation-delay:${i * 18}ms" role="listitem" data-i="${i}" aria-label="${esc(r.problem)}: ${esc(r.answer)}">${mark}</button>`;
  }).join("");
  $("score").textContent = `${grade.right} of ${grade.total} right`;
  g.querySelectorAll(".cell").forEach((c) => c.addEventListener("click", () => {
    const r = grade.rows[+c.dataset.i];
    const what = r.status === "ok" ? `Ahmes said ${r.answer}.` : r.status === "dizzy" ? "Ahmes got dizzy on this one." : r.status === "too_full" ? "His head got too full." : r.status === "not_run" ? "The sandbox stopped before this one." : `Error: ${r.answer}`;
    $("detail").textContent = `${r.problem}. ${what} ${r.ok ? "Right!" : ""}`;
  }));
}

function setSkill(name) {
  state.skill = name;
  document.querySelectorAll(".skill").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.skill === name)));
  const sk = state.skills[name];
  $("starters").innerHTML = STARTERS[name].map((s) => `<button class="starter" type="button">${esc(s)}</button>`).join("");
  $("starters").querySelectorAll(".starter").forEach((b) => b.addEventListener("click", () => { $("sentence").value = b.textContent; $("sentence").focus(); }));
  renderCode(sk.current || sk.code);
  renderWords("", []);
  renderGrid(sk.lastGrade);
  $("readout").hidden = true; $("detail").textContent = ""; $("stamp").hidden = true;
  setRobot();
  say(sk.welcome);
}

function busy(on, text) {
  state.busy = on;
  ["teach", "quiz", "reset"].forEach((id) => ($(id).disabled = on));
  $("status").textContent = text || "";
}

async function teach() {
  const sentence = $("sentence").value.trim();
  if (!sentence) { say("Tell me the rule first! Type it in the box."); $("sentence").focus(); return; }
  busy(true, "Turning your words into code on Vultr…");
  $("stamp").hidden = true; $("readout").hidden = true; $("detail").textContent = "";
  setRobot("is-thinking");
  const t1 = setTimeout(() => { $("status").textContent = "Testing his new brain in a throwaway sandbox…"; setRobot("is-thinking", "is-running"); }, 1500);
  try {
    const d = await api("/api/teach", { sid: state.sid, skill: state.skill, sentence });
    clearTimeout(t1);
    const sk = state.skills[state.skill];
    if (d.outcome === "timeout" || d.outcome === "oom") {
      setRobot(d.outcome === "timeout" ? "is-dizzy" : "is-full");
      $("stamp").hidden = false;
      $("stamp-time").textContent = d.outcome === "timeout" ? `${(d.run.elapsed_ms / 1000).toFixed(1)} s` : "64 MB";
      renderCode(d.proposed, sk.current || sk.code);
      renderWords(sentence, d.steps);
      renderGrid(d.grade);
      say(d.say, d.voice);
      $("status").textContent = `Container ${d.run.container_id} was stopped and removed. Ahmes kept his old brain.`;
      refreshLog();
      return;
    }
    if (d.outcome === "partial" || d.outcome === "cured") {
      sk.current = d.code; sk.lastGrade = d.grade;
      renderCode(d.code, d.previous);
      renderWords(sentence, d.steps);
      renderGrid(d.grade);
      const ro = d.read_out || {};
      if (d.outcome === "cured") { setRobot("is-happy"); $("readout").hidden = true; }
      else {
        setRobot("is-confused");
        const trap = ro.trap ? ` Try him on ${ro.trap.problem}: he says ${ro.trap.his_answer}.` : "";
        $("readout").innerHTML = `<strong>Ahmes now ${esc(ro.label)}.</strong>${esc(trap)}`;
        $("readout").hidden = false;
      }
      say(d.say, d.voice);
      $("status").textContent = `Tested in container ${d.run.container_id} in ${d.run.elapsed_ms} ms, then destroyed.`;
      refreshLog();
      return;
    }
    setRobot("is-confused");
    if (d.outcome === "blocked") { renderCode(d.proposed || d.code); renderWords(sentence, d.steps); }
    say(d.say, d.voice);
    $("status").textContent = d.outcome === "blocked" ? `The code guard refused it: ${d.reason}.` : d.outcome === "rejected" ? (["BUSY", "ERROR", "OTHER_KILL", "OK"].includes(d.reason) ? "The sandbox couldn't test that brain, so nothing changed. Try again." : "The compiler heard more than you said, so nothing changed.") : "";
  } catch (e) {
    clearTimeout(t1); setRobot("is-confused"); say("Oops, my brain is offline for a moment."); $("status").textContent = e.message;
  } finally { busy(false, $("status").textContent); }
}

async function quiz() {
  busy(true, "Quizzing Ahmes on 40 brand-new problems…");
  setRobot("is-thinking", "is-running");
  try {
    const d = await api("/api/quiz", { sid: state.sid, skill: state.skill });
    const g = { ...d.grade, rows: d.grade.rows };
    renderGrid({ right: d.grade.right, total: d.grade.total, rows: g.rows });
    $("score").textContent = `Quiz: ${d.grade.right} of ${d.grade.total} right`;
    setRobot(d.grade.right === d.grade.total ? "is-happy" : "is-confused");
    say(d.grade.right === d.grade.total ? "A quiz! I got every one right!" : `A quiz! I got ${d.grade.right} out of ${d.grade.total}. Keep teaching me!`);
    $("status").textContent = `Quiz ran in container ${d.run.container_id}, then it was destroyed.`;
    refreshLog();
  } catch (e) { $("status").textContent = e.message; setRobot(); } finally { busy(false, $("status").textContent); }
}

async function reset() {
  const d = await api("/api/reset", { sid: state.sid, skill: state.skill });
  const sk = state.skills[state.skill]; sk.current = d.code; sk.lastGrade = null;
  setSkill(state.skill);
}

function facts(run) {
  const L = run.limits || {};
  const rows = [
    ["Container", `${run.container} (${run.container_id || ""})`],
    ["Network", L.network], ["Memory cap", L.memory_bytes ? `${L.memory_bytes / 1048576} MB` : ""],
    ["CPU", L.nano_cpus ? `${L.nano_cpus / 1e9} core` : ""], ["Process limit", L.pids_limit],
    ["Read-only disk", String(L.read_only_root)], ["Capabilities dropped", (L.cap_drop || []).join(", ")],
    ["Runtime", L.runtime], ["Took", `${run.elapsed_ms} ms`], ["Exit code", run.exit_code],
    ["Killed for memory", String(run.oom_killed)], ["Removed after", run.removed_verified ? "yes, checked by name" : "no"],
  ];
  return `<dl class="facts">${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("")}</dl>`;
}

async function runChip(name, beyond) {
  const box = $("result");
  box.hidden = false; box.innerHTML = "<p>Running in a fresh container…</p>";
  try {
    const d = beyond ? await api(`/api/beyond/${name}`) : await api("/api/chip", { sid: state.sid, chip: name });
    const bad = d.verdict !== "OK";
    let html = `<p class="verdict ${beyond ? "good" : bad ? "bad" : "good"}">${esc(beyond ? "Container held" : VERDICT[d.verdict] || d.verdict)}</p>`;
    html += `<pre>${esc(beyond ? d.script : d.code)}</pre>`;
    if (beyond) html += `<p><strong>What happened inside:</strong></p><pre>${esc(d.output || "(no output)")}</pre>`;
    if (d.reason) html += `<p>Guard: ${esc(d.reason)}${d.line ? ` (line ${d.line})` : ""}.</p>`;
    if (d.witness) html += `<p>Meanwhile a normal maths check of Ahmes's brain ran in another container: <strong>${esc(VERDICT[d.witness.verdict] || d.witness.verdict)}</strong>. The server kept working.</p>`;
    if (d.run) html += facts(d.run) + `<p><a href="/api/receipt/${esc(d.run.id)}">Download the receipt (JSON)</a></p>`;
    box.innerHTML = html;
    if (!beyond && d.say) { setRobot(d.verdict === "TIMEOUT" ? "is-dizzy" : d.verdict === "OOM" ? "is-full" : "is-confused"); say(d.say, d.voice); }
    refreshLog();
  } catch (e) { box.innerHTML = `<p>${esc(e.message)}</p>`; }
}

async function refreshLog() {
  try {
    const [log, live] = await Promise.all([fetch("/api/log").then((r) => r.json()), fetch("/api/sandboxes").then((r) => r.json())]);
    $("log").innerHTML = log.map((r) => `<tr><td>${new Date(r.at * 1000).toLocaleTimeString()}</td><td>${esc(r.purpose)}</td>
      <td class="${r.verdict === "OK" ? "v-OK" : "v-bad"}">${esc(r.verdict)}</td><td>${r.elapsed_ms}</td><td>${r.removed ? "yes" : "no"}</td>
      <td><a href="/api/receipt/${esc(r.id)}">JSON</a></td></tr>`).join("");
    $("live").textContent = live.containers.length ? `Containers running now: ${live.containers.join(", ")}` : "Containers running now: none. Each one is destroyed after its task.";
  } catch { /* the log is a nice-to-have */ }
}

async function start() {
  renderGrid(null);
  $("chips").innerHTML = CHIPS.map(([k, l]) => `<button class="chip" type="button" data-k="${k}">${esc(l)}</button>`).join("");
  $("beyond").innerHTML = BEYOND.map(([k, l]) => `<button class="chip" type="button" data-k="${k}">${esc(l)}</button>`).join("");
  $("chips").querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => runChip(b.dataset.k, false)));
  $("beyond").querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => runChip(b.dataset.k, true)));
  document.querySelectorAll(".skill").forEach((b) => b.addEventListener("click", () => setSkill(b.dataset.skill)));
  $("teach").addEventListener("click", teach);
  $("quiz").addEventListener("click", quiz);
  $("reset").addEventListener("click", reset);
  $("sentence").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (!state.busy) teach(); } });
  $("sound").addEventListener("click", () => {
    state.voice = !state.voice; $("sound").setAttribute("aria-pressed", String(state.voice));
    $("sound").textContent = state.voice ? "Voice on" : "Voice off"; if (!state.voice) state.audio.pause();
  });
  try {
    const d = await api("/api/session");
    state.sid = d.sid;
    state.skills = d.skills;
    setSkill(state.skill);
    refreshLog();
  } catch (e) { say("I can't reach my brain right now. Try reloading."); $("status").textContent = e.message; }
}
start();
