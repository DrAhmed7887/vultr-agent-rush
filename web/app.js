"use strict";
// The child's game, one screen at a time:
// check his homework -> see why -> teach him (talk or type) -> he tries again -> quiz -> next homework.
// Every answer Ahmes gives comes from his code running in a Vultr sandbox; the pictures are exact maths.

const SCREENS = ["map", "check", "proof", "teach", "think", "retry", "oops", "quiz", "win"];
const PATH_OF = { map: "", check: "check", proof: "check", teach: "teach", think: "teach", retry: "retry", oops: "teach", quiz: "quiz", win: "quiz" };

const state = { sid: null, skill: "compare_decimals", skills: {}, voice: true, audio: new Audio(), busy: false };
const sk = () => state.skills[state.skill];

function setRobot(...cls) {
  const r = $("ahmes");
  r.classList.remove("is-thinking", "is-running", "is-dizzy", "is-happy", "is-confused", "is-full");
  cls.forEach((c) => c && r.classList.add(c));
}
function say(text, voice) {
  $("bubble").textContent = text;
  if (state.voice && voice && voice.id) { state.audio.src = `/audio/${voice.id}.mp3`; state.audio.play().catch(() => {}); }
}
window.kidReact = (cls, text, voice) => { setRobot(cls); say(text, voice); };
// one of Ahmes's fixed screen lines, with its pre-recorded voice
const line = (key) => { const l = (state.lines || {})[key]; if (l) say(l.say, l.voice); };

function show(name) {
  SCREENS.forEach((s) => { $(`s-${s}`).hidden = s !== name; });
  const at = ["check", "teach", "retry", "quiz"].indexOf(PATH_OF[name]);
  $("path").hidden = name === "map";
  document.querySelector(".tricks").hidden = name === "map";
  document.querySelectorAll("#path li").forEach((li, i) => {
    li.classList.toggle("done", i < at); li.classList.toggle("now", i === at);
    li.toggleAttribute("aria-current", i === at);
  });
  $("stamp").hidden = name !== "oops" || !$("stamp").dataset.on;
  $("thoth").hidden = true;
  const h = $(`s-${name}`).querySelector("h1"); if (h && name !== "think") { h.tabIndex = -1; h.focus({ preventScroll: true }); }
}

function renderTricks(tricks) {
  if (!tricks) return;
  sk().tricks = tricks;
  const known = tricks.filter((t) => t.learned).length;
  $("tricks-title").textContent = `Tricks Ahmes knows: ${known} of ${tricks.length}`;
  $("cartouches").innerHTML = tricks.map((t) => `<li class="cartouche${t.learned ? " learned" : ""}" title="${esc(t.name)}">
    <span class="c-name">${esc(t.name)}</span><span class="c-ex">${esc(t.example)}</span></li>`).join("");
}

// ---------- step 1: check his homework ----------
function homework(card) {
  sk().homework = card;
  $("check-problem").innerHTML = problemForView(sk().view, card.args, card.out, "his");
  setRobot(); say(card.why, card.voice);
  show("check");
}

function markHomework(childSaysRight) {
  const hw = sk().homework;
  const p = proofForView(sk().view, hw.args, hw.out);
  $("proof-visual").innerHTML = p.svg + (p.zoom ? `<p class="zoom">${esc(p.zoom)}</p>` : "");
  if (hw.ok) {
    $("proof-title").textContent = childSaysRight ? "Yes! He got this one right" : "Look again: he's right this time";
    $("proof-text").textContent = p.caption;
    $("go-teach").textContent = "Quiz him on more";
    $("go-teach").dataset.next = "quiz";
  } else {
    $("proof-title").textContent = childSaysRight ? "Look again: Ahmes is wrong" : "Good eye! Ahmes is wrong";
    $("proof-text").textContent = p.caption;
    $("go-teach").textContent = "Teach him the rule";
    $("go-teach").dataset.next = "teach";
    setRobot("is-confused");
    line(childSaysRight ? "marked_right_but_wrong" : "marked_wrong");
  }
  show("proof");
}

// ---------- step 2: teach ----------
function teachScreen(again) {
  $("teach-title").textContent = again ? "Teach him again, another way" : "How should Ahmes do it?";
  $("teach-err").hidden = true;
  $("starters").innerHTML = sk().ideas.map((s) => `<button class="starter" type="button">${esc(s)}</button>`).join("");
  $("starters").querySelectorAll(".starter").forEach((b) => b.addEventListener("click", () => {
    $("sentence").value = b.textContent; $("sentence").focus(); $("teach-err").hidden = true;
  }));
  setRobot(); line(again ? "teach_again" : "teach_me");
  show("teach");
}

function thinking(stage) {
  document.querySelectorAll("#think li").forEach((li) => {
    const order = ["listen", "code", "box", "thoth"], i = order.indexOf(li.dataset.t), at = order.indexOf(stage);
    li.classList.toggle("done", i < at); li.classList.toggle("now", i === at);
  });
}

function thoth(t) {
  if (!t) return;
  $("thoth-say").textContent = t.say;
  $("thoth-act").hidden = t.action !== "listen_again";
  // Thoth steps in on the screen the child is looking at, just above its buttons
  const screen = [...document.querySelectorAll(".screen")].find((el) => !el.hidden);
  const before = screen && (screen.querySelector(".row") || screen.querySelector(".big"));
  if (before) before.before($("thoth"));
  $("thoth").hidden = false;
  $("thoth").classList.remove("pop-in"); void $("thoth").offsetWidth; $("thoth").classList.add("pop-in");
}

async function teach(listenAgain) {
  listenAgain = listenAgain === true;
  const sentence = listenAgain ? state.lastSentence : $("sentence").value.trim();
  if (!sentence) { $("teach-err").textContent = "Tell Ahmes the rule first: talk or type it."; $("teach-err").hidden = false; $("sentence").focus(); return; }
  if (state.busy) return;
  state.busy = true;
  const previous = sk().current || sk().code;
  show("think"); thinking("listen"); setRobot("is-thinking");
  const t1 = setTimeout(() => thinking("code"), 700);
  const t2 = setTimeout(() => { thinking("box"); setRobot("is-thinking", "is-running"); }, 2200);
  const t3 = setTimeout(() => thinking("thoth"), 2900);
  try {
    const d = await api("/api/teach", { sid: state.sid, skill: state.skill, sentence, homework: sk().homework.args, listen_again: listenAgain });
    clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
    state.lastSentence = sentence;
    showTeachInHow(d, sentence, previous, listenAgain ? 0 : state.heardMs);
    state.heardMs = 0;
    if (d.outcome === "partial" || d.outcome === "cured") { afterTeach(d, sentence); thoth(d.teacher); return; }
    oops(d); thoth(d.teacher);
  } catch (e) {
    clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
    oops({ outcome: "offline", say: "Oops, my brain is offline for a moment.", reason: e.message });
  } finally { state.busy = false; }
}

// ---------- step 3: he tries again ----------
function quoteLine(steps, sentence) {
  const qs = (steps || []).map((s) => s.quote).filter(Boolean);
  return qs.length ? `You told me: ${qs.map((q) => `“${q}”`).join(", ")}` : `You told me: “${sentence}”`;
}

function afterTeach(d, sentence) {
  const r = d.retry;
  sk().lastRetry = r;
  if (d.kept === false) {   // Thoth said the code doesn't match the words, so Ahmes keeps his old brain
    $("you-said").textContent = quoteLine(d.steps, sentence);
    $("retry-problem").innerHTML = problemForView(sk().view, r.args, r.out, r.ok ? "ok" : "bad");
    $("retry-title").textContent = "Thoth stopped this brain";
    $("retry-text").textContent = "Ahmes's new code didn't match your words, so he kept his old brain. Ask him to listen again, or teach him another way.";
    $("retry-next").textContent = "Teach him again"; $("retry-next").dataset.next = "teach";
    $("retry-why").hidden = true;
    setRobot("is-confused"); say(r.why, r.voice); show("retry");
    return;
  }
  sk().current = d.code;
  renderTricks(d.tricks);
  $("you-said").textContent = quoteLine(d.steps, sentence);
  $("retry-problem").innerHTML = problemForView(sk().view, r.args, r.out, r.ok ? "ok" : "bad");
  $("retry-why").hidden = r.ok;
  if (r.ok) {
    $("retry-title").textContent = "He got his homework right!";
    $("retry-text").textContent = "Now let's see if it sticks on problems he's never seen.";
    $("retry-next").textContent = "Quiz him";
    $("retry-next").dataset.next = "quiz";
    setRobot("is-happy");
  } else {
    $("retry-title").textContent = "Still wrong. He needs more help";
    $("retry-text").textContent = "What did he miss? Look at the picture, then teach him again.";
    $("retry-next").textContent = "Teach him again";
    $("retry-next").dataset.next = "teach";
    setRobot("is-confused");
  }
  say(r.why, r.voice);
  show("retry");
}

// ---------- when the robot gets dizzy, full, or confused ----------
const OOPS = {
  timeout: ["Ahmes got dizzy!", "Your rule made him go round and round forever. The safe box stopped him after 3 seconds, and he kept his old brain."],
  oom: ["His head got too full!", "Your rule made him remember too much. The safe box stopped him at 64 MB, and he kept his old brain."],
  blocked: ["That isn't maths", "The code guard stopped it before it ran. Try a rule with numbers."],
  no_rule: ["That's an answer, not a rule", "Ahmes needs to know what to do on a new problem, not just this one."],
  rejected: ["He heard more than you said", "Say it step by step, one idea at a time."],
  unkind: ["Let's keep it kind", "Keep it about maths, and don't share things about yourself, like where you live."],
  offline: ["Ahmes's brain is offline", "Wait a moment, then try again."],
};
function oops(d) {
  const [title, sub] = OOPS[d.outcome] || OOPS.rejected;
  const stopped = d.outcome === "timeout" || d.outcome === "oom";
  $("stamp").dataset.on = stopped ? "1" : "";
  if (stopped) $("stamp-time").textContent = d.outcome === "timeout" ? `${(d.run.elapsed_ms / 1000).toFixed(1)} s` : "64 MB";
  $("oops-title").textContent = title;
  $("oops-text").textContent = d.say || "";
  $("oops-sub").textContent = sub;
  setRobot(d.outcome === "timeout" ? "is-dizzy" : d.outcome === "oom" ? "is-full" : "is-confused");
  say(d.say, d.voice);
  show("oops");
}

// ---------- step 4: quiz, one card per trick ----------
async function quiz() {
  if (state.busy) return;
  state.busy = true;
  show("quiz"); $("cards").innerHTML = ""; $("quiz-text").textContent = "Ahmes is taking a brand-new test in a fresh safe box…";
  $("quiz-next").hidden = true; setRobot("is-thinking", "is-running");
  try {
    const d = await api("/api/quiz", { sid: state.sid, skill: state.skill });
    renderGrid(d.grade); refreshLog();
    $("cards").innerHTML = d.cards.map((c, i) => `<li class="qcard ${c.ok ? "ok" : "bad"}" style="--i:${i}">
      <span class="q-trick">${esc(c.trick_name)}</span><span class="q-prob">${esc(c.problem)}</span>
      <span class="q-ans">Ahmes: ${esc(c.his_answer)}</span><span class="q-mark" aria-label="${c.ok ? "right" : "wrong"}">${c.ok ? "✓" : "✗"}</span></li>`).join("");
    setTimeout(() => quizResult(d), 400 + d.cards.length * 450);
  } catch (e) {
    $("quiz-text").textContent = e.message; setRobot(); state.busy = false;
    $("quiz-next").textContent = "Try the quiz again"; $("quiz-next").dataset.retry = "1"; $("quiz-next").hidden = false;
  }
}

function quizResult(d) {
  state.busy = false;
  renderTricks(d.tricks);
  if (!d.next_homework) {
    setRobot("is-happy");
    sk().won = true;
    $("win-title").textContent = `You taught Ahmes every trick in “${sk().title}”!`;
    $("win-sub").textContent = `He got all ${d.grade.total} brand-new problems right, checked in a safe box.`;
    if (d.win) say(d.win.say, d.win.voice);
    return show("win");
  }
  const n = d.next_homework;
  sk().nextHomework = n;
  $("quiz-text").textContent = `This one tricked him: ${n.problem}. He says: “${n.why}”`;
  $("quiz-next").hidden = false;
  setRobot("is-confused"); say(n.why, n.voice);
}

// ---------- voice: record, make a small WAV, Vultr's omni model writes down the words ----------
const mic = { rec: null, chunks: [], timer: null };

async function toWav(blob) {
  const ctx = new (window.AudioContext || window.webkitAudioContext)();
  const buf = await ctx.decodeAudioData(await blob.arrayBuffer());
  const rate = 16000, len = Math.ceil(buf.duration * rate);
  const off = new OfflineAudioContext(1, len, rate);
  const src = off.createBufferSource(); src.buffer = buf; src.connect(off.destination); src.start();
  const pcm = (await off.startRendering()).getChannelData(0);
  const out = new DataView(new ArrayBuffer(44 + pcm.length * 2));
  const w = (o, s) => [...s].forEach((c, i) => out.setUint8(o + i, c.charCodeAt(0)));
  w(0, "RIFF"); out.setUint32(4, 36 + pcm.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  out.setUint32(16, 16, true); out.setUint16(20, 1, true); out.setUint16(22, 1, true);
  out.setUint32(24, rate, true); out.setUint32(28, rate * 2, true); out.setUint16(32, 2, true); out.setUint16(34, 16, true);
  w(36, "data"); out.setUint32(40, pcm.length * 2, true);
  pcm.forEach((v, i) => out.setInt16(44 + i * 2, Math.max(-1, Math.min(1, v)) * 0x7fff, true));
  ctx.close();
  return new Blob([out], { type: "audio/wav" });
}

async function micToggle() {
  if (mic.rec) { mic.rec.stop(); return; }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mic.chunks = []; mic.rec = new MediaRecorder(stream);
    mic.rec.ondataavailable = (e) => mic.chunks.push(e.data);
    mic.rec.onstop = async () => {
      clearTimeout(mic.timer); stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(mic.chunks, { type: mic.rec.mimeType }); mic.rec = null;
      micUI("hearing");
      try {
        const wav = await toWav(blob);
        const t0 = performance.now();
        const r = await fetch(`/api/listen?sid=${encodeURIComponent(state.sid)}`, { method: "POST", headers: { "Content-Type": "audio/wav" }, body: wav });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d.detail || "Ahmes couldn't hear that.");
        if (!d.text) throw new Error("Ahmes didn't hear any words. Try again, a bit closer.");
        $("sentence").value = d.text; $("teach-err").hidden = true; state.heardMs = Math.round(performance.now() - t0);
        line("heard");
      } catch (e) { $("teach-err").textContent = e.message; $("teach-err").hidden = false; }
      micUI("idle");
    };
    mic.rec.start(); micUI("on");
    mic.timer = setTimeout(() => mic.rec && mic.rec.stop(), 15000);
  } catch {
    $("teach-err").textContent = "The microphone isn't available. Type the rule instead."; $("teach-err").hidden = false;
  }
}
function micUI(mode) {
  $("mic").classList.toggle("on", mode === "on"); $("mic").setAttribute("aria-pressed", String(mode === "on"));
  $("mic-label").textContent = mode === "on" ? "Listening… tap to stop" : mode === "hearing" ? "Writing down your words…" : "Tap to talk";
  $("mic").disabled = mode === "hearing";
}

// ---------- lessons, saving, certificate, report ----------
function setSkill(name) {
  state.skill = name;
  $("lesson-name").textContent = sk().title;
  $("sentence").value = "";
  renderTricks(sk().tricks);
  renderCode(sk().current || sk().code); renderWords("", []); renderGrid(null);
  homework(sk().homework);
}

function renderMap(welcomeBack) {
  $("map-title").textContent = welcomeBack ? "Welcome back! Pick a lesson" : "What shall we teach Ahmes?";
  $("lessons").innerHTML = Object.entries(state.skills).map(([k, s]) => {
    const known = s.tricks.filter((t) => t.learned).length;
    const status = s.won ? "Taught" : known > s.start_tricks.filter((t) => t.learned).length ? "In progress" : "New";
    const dots = s.tricks.map((t) => `<span class="dot${t.learned ? " on" : ""}"></span>`).join("");
    return `<li><button class="lesson${s.won ? " won" : ""}" type="button" data-k="${k}">
      <span class="l-title">${esc(s.title)}</span><span class="l-year">Year ${s.year}</span>
      <span class="l-dots" aria-label="${known} of ${s.tricks.length} tricks">${dots}</span><span class="l-status">${status}</span></button></li>`;
  }).join("");
  $("lessons").querySelectorAll(".lesson").forEach((b) => b.addEventListener("click", () => setSkill(b.dataset.k)));
  $("lesson-name").textContent = "Lessons";
  setRobot(); line(welcomeBack ? "map_back" : "map");
  show("map");
}

async function startOver() {
  const d = await api("/api/reset", { sid: state.sid, skill: state.skill });
  Object.assign(sk(), { current: d.code, tricks: sk().start_tricks, homework: sk().start_homework, won: false });
  setSkill(state.skill);
}

// The certificate: drawn on a canvas in the browser, saved as a PNG. No name is asked for.
function certificate() {
  const c = document.createElement("canvas"); c.width = 1200; c.height = 850;
  const g = c.getContext("2d");
  g.fillStyle = "#F7FAFD"; g.fillRect(0, 0, 1200, 850);
  g.strokeStyle = "#D9E6F3"; g.lineWidth = 1;
  for (let x = 0; x < 1200; x += 30) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, 850); g.stroke(); }
  for (let y = 0; y < 850; y += 30) { g.beginPath(); g.moveTo(0, y); g.lineTo(1200, y); g.stroke(); }
  g.strokeStyle = "#E0A526"; g.lineWidth = 10; g.strokeRect(40, 40, 1120, 770);
  g.fillStyle = "#2449A8"; g.textAlign = "center";
  g.font = "800 64px Lexend, sans-serif"; g.fillText("Teacher of Ahmes", 600, 200);
  g.fillStyle = "#16224A"; g.font = "500 34px Lexend, sans-serif";
  g.fillText("This certificate is for the teacher who taught Ahmes", 600, 300);
  g.font = "700 44px Lexend, sans-serif"; g.fillText(`“${sk().title}”`, 600, 380);
  g.font = "500 30px Lexend, sans-serif";
  g.fillText(`Every trick: ${sk().tricks.map((t) => t.name).join(", ")}`.slice(0, 90), 600, 460);
  g.fillText("He then got 40 brand-new problems right, checked by plain arithmetic.", 600, 520);
  g.fillStyle = "#4E5B80"; g.font = "400 26px Lexend, sans-serif";
  g.fillText(new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" }), 600, 700);
  g.beginPath(); g.arc(1010, 660, 90, 0, Math.PI * 2); g.fillStyle = "#E0A526"; g.fill();
  g.fillStyle = "#16224A"; g.font = "800 26px Lexend, sans-serif"; g.fillText("Thoth", 1010, 650); g.fillText("approves", 1010, 684);
  c.toBlob((b) => { const a = document.createElement("a"); a.href = URL.createObjectURL(b); a.download = "teacher-of-ahmes.png"; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 2000); });
}

const OUTCOME = { cured: "cured him", partial: "helped", timeout: "made him dizzy", oom: "filled his head", stopped_by_teacher: "was stopped by Thoth (the code didn't match the words)" };
async function showReport() {
  try {
    const r = await fetch(`/api/report?sid=${encodeURIComponent(state.sid)}`).then((x) => x.json());
    $("report-body").innerHTML = !r.lessons || !r.lessons.length ? `<p class="hint">Nothing taught yet. Teach Ahmes a lesson, then come back.</p>` :
      r.lessons.map((l) => `<section class="card r-lesson"><h3>${esc(l.title)} <span class="l-year">Year ${l.year}</span> ${l.won ? "★ taught" : ""}</h3>
        <p class="hint">Tricks learned: ${l.tricks.filter((t) => t.learned).map((t) => esc(t.name)).join(", ") || "none yet"}</p>
        <ol class="r-turns">${l.turns.map((t) => t.kind === "quiz" ? `<li class="r-quiz">Quiz: ${t.right} of ${t.total} right</li>` :
          `<li><q>${esc(t.sentence)}</q> ${esc(OUTCOME[t.outcome] || t.outcome)}${t.right != null ? ` (${t.right}/40)` : ""}${t.homework ? `; on ${esc(t.homework)} he was ${t.fixed_homework ? "right" : "still wrong"}` : ""}${t.thoth ? `<br><span class="r-thoth">Thoth: ${esc(t.thoth)}</span>` : ""}</li>`).join("")}</ol></section>`).join("");
  } catch { $("report-body").innerHTML = `<p class="hint">The report couldn't load. Try again.</p>`; }
  $("report").hidden = false; $("how").hidden = true; $("report").scrollIntoView({ behavior: "smooth" });
}

async function start() {
  setupHow();
  if (!(navigator.mediaDevices && window.MediaRecorder)) $("mic").hidden = true;
  $("lessons-btn").addEventListener("click", () => !state.busy && renderMap(false));
  $("mark-yes").addEventListener("click", () => markHomework(true));
  $("mark-no").addEventListener("click", () => markHomework(false));
  $("go-teach").addEventListener("click", () => ($("go-teach").dataset.next === "quiz" ? quiz() : teachScreen(false)));
  $("teach").addEventListener("click", () => teach(false));
  $("thoth-act").addEventListener("click", () => teach(true));
  $("mic").addEventListener("click", micToggle);
  $("sentence").addEventListener("input", () => { $("teach-err").hidden = true; });
  $("sentence").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); teach(false); } });
  $("retry-next").addEventListener("click", () => ($("retry-next").dataset.next === "quiz" ? quiz() : teachScreen(true)));
  $("retry-why").addEventListener("click", () => {
    const r = sk().lastRetry || sk().homework;
    const pf = proofForView(sk().view, r.args, r.out);
    $("proof-visual").innerHTML = pf.svg + (pf.zoom ? `<p class="zoom">${esc(pf.zoom)}</p>` : "");
    $("proof-title").textContent = "Here's why he's still wrong"; $("proof-text").textContent = pf.caption;
    $("go-teach").textContent = "Teach him again"; $("go-teach").dataset.next = "teach"; show("proof");
  });
  $("oops-again").addEventListener("click", () => teachScreen(true));
  $("quiz-next").addEventListener("click", () => {
    if ($("quiz-next").dataset.retry) { delete $("quiz-next").dataset.retry; $("quiz-next").textContent = "Make it his homework"; return quiz(); }
    homework(sk().nextHomework);
  });
  $("win-next").addEventListener("click", () => renderMap(false));
  $("win-cert").addEventListener("click", certificate);
  $("report-btn").addEventListener("click", showReport);
  $("report-print").addEventListener("click", () => window.print());
  $("report-close").addEventListener("click", () => { $("report").hidden = true; window.scrollTo({ top: 0, behavior: "smooth" }); });
  $("win-reset").addEventListener("click", startOver);
  $("sound").addEventListener("click", () => {
    state.voice = !state.voice; $("sound").setAttribute("aria-pressed", String(state.voice));
    $("sound").textContent = state.voice ? "Voice on" : "Voice off"; if (!state.voice) state.audio.pause();
  });
  $("how-btn").addEventListener("click", () => {
    const open = $("how").hidden; $("how").hidden = !open; $("how-btn").setAttribute("aria-expanded", String(open));
    $("how-btn").textContent = open ? "Back to Ahmes" : "How it works";
    if (open) { refreshLog(); $("how").scrollIntoView({ behavior: "smooth" }); } else window.scrollTo({ top: 0, behavior: "smooth" });
  });
  let saved = "";
  try { saved = localStorage.getItem("ahmes_sid") || ""; } catch { /* private mode: no saving */ }
  try {
    const d = await api(`/api/session${saved ? `?resume=${encodeURIComponent(saved)}` : ""}`);
    state.sid = d.sid; state.skills = d.skills; state.lines = d.lines;
    try { localStorage.setItem("ahmes_sid", d.sid); } catch { /* fine */ }
    renderMap(d.resumed);
    refreshLog();
  } catch (e) { say("I can't reach my brain right now. Try reloading."); }
}
start();
