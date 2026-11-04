"use strict";
// The child's game, one screen at a time:
// check his homework -> see why -> teach him (talk or type) -> he tries again -> quiz -> next homework.
// Every answer Ahmes gives comes from his code running in a Vultr sandbox; the pictures are exact maths.

const IDEAS = {
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
const SCREENS = ["check", "proof", "teach", "think", "retry", "oops", "quiz", "win"];
const PATH_OF = { check: "check", proof: "check", teach: "teach", think: "teach", retry: "retry", oops: "teach", quiz: "quiz", win: "quiz" };

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

function show(name) {
  SCREENS.forEach((s) => { $(`s-${s}`).hidden = s !== name; });
  const at = ["check", "teach", "retry", "quiz"].indexOf(PATH_OF[name]);
  document.querySelectorAll("#path li").forEach((li, i) => {
    li.classList.toggle("done", i < at); li.classList.toggle("now", i === at);
    li.toggleAttribute("aria-current", i === at);
  });
  $("stamp").hidden = name !== "oops" || !$("stamp").dataset.on;
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
  $("check-problem").innerHTML = problemHTML(state.skill, card.args, card.out, "his");
  setRobot(); say(card.why, card.voice);
  show("check");
}

function markHomework(childSaysRight) {
  const hw = sk().homework;
  const p = proofFor(state.skill, hw.args, hw.out);
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
    say(childSaysRight ? "Wait, really? Let's look at the picture." : "Oh no, am I wrong? Can you teach me?");
  }
  show("proof");
}

// ---------- step 2: teach ----------
function teachScreen(again) {
  $("teach-title").textContent = again ? "Teach him again, another way" : "How should Ahmes do it?";
  $("teach-err").hidden = true;
  $("starters").innerHTML = IDEAS[state.skill].map((s) => `<button class="starter" type="button">${esc(s)}</button>`).join("");
  $("starters").querySelectorAll(".starter").forEach((b) => b.addEventListener("click", () => {
    $("sentence").value = b.textContent; $("sentence").focus(); $("teach-err").hidden = true;
  }));
  setRobot(); say(again ? "I'm listening. Tell me step by step!" : "Teach me! Tell me a rule that works every time.");
  show("teach");
}

function thinking(stage) {
  document.querySelectorAll("#think li").forEach((li) => {
    const order = ["listen", "code", "box"], i = order.indexOf(li.dataset.t), at = order.indexOf(stage);
    li.classList.toggle("done", i < at); li.classList.toggle("now", i === at);
  });
}

async function teach() {
  const sentence = $("sentence").value.trim();
  if (!sentence) { $("teach-err").textContent = "Tell Ahmes the rule first: talk or type it."; $("teach-err").hidden = false; $("sentence").focus(); return; }
  if (state.busy) return;
  state.busy = true;
  const previous = sk().current || sk().code;
  show("think"); thinking("listen"); setRobot("is-thinking");
  const t1 = setTimeout(() => thinking("code"), 700);
  const t2 = setTimeout(() => { thinking("box"); setRobot("is-thinking", "is-running"); }, 2200);
  try {
    const d = await api("/api/teach", { sid: state.sid, skill: state.skill, sentence, homework: sk().homework.args });
    clearTimeout(t1); clearTimeout(t2);
    showTeachInHow(d, sentence, previous);
    if (d.outcome === "partial" || d.outcome === "cured") return afterTeach(d, sentence);
    oops(d);
  } catch (e) {
    clearTimeout(t1); clearTimeout(t2);
    oops({ outcome: "offline", say: "Oops, my brain is offline for a moment.", reason: e.message });
  } finally { state.busy = false; }
}

// ---------- step 3: he tries again ----------
function quoteLine(steps, sentence) {
  const qs = (steps || []).map((s) => s.quote).filter(Boolean);
  return qs.length ? `You told me: ${qs.map((q) => `“${q}”`).join(", ")}` : `You told me: “${sentence}”`;
}

function afterTeach(d, sentence) {
  sk().current = d.code;
  renderTricks(d.tricks);
  const r = d.retry;
  $("you-said").textContent = quoteLine(d.steps, sentence);
  $("retry-problem").innerHTML = problemHTML(state.skill, r.args, r.out, r.ok ? "ok" : "bad");
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
  }
}

function quizResult(d) {
  state.busy = false;
  renderTricks(d.tricks);
  if (!d.next_homework) {
    setRobot("is-happy");
    const other = state.skill === "compare_decimals" ? "add_fractions" : "compare_decimals";
    $("win-sub").textContent = `He got all ${d.grade.total} brand-new ${state.skill === "compare_decimals" ? "decimal" : "fraction"} problems right, checked in a safe box.`;
    $("win-next").textContent = other === "add_fractions" ? "Teach him fractions" : "Teach him decimals";
    $("win-next").dataset.skill = other;
    say("I got every one right! You're my teacher!");
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
        const r = await fetch(`/api/listen?sid=${encodeURIComponent(state.sid)}`, { method: "POST", headers: { "Content-Type": "audio/wav" }, body: wav });
        const d = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(d.detail || "Ahmes couldn't hear that.");
        if (!d.text) throw new Error("Ahmes didn't hear any words. Try again, a bit closer.");
        $("sentence").value = d.text; $("teach-err").hidden = true;
        say("Did I hear you right? Fix the words if not, then press Teach Ahmes.");
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

// ---------- skills, start ----------
function setSkill(name) {
  state.skill = name;
  document.querySelectorAll(".skill").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.skill === name)));
  $("sentence").value = "";
  renderTricks(sk().tricks);
  renderCode(sk().current || sk().code); renderWords("", []); renderGrid(null);
  homework(sk().homework);
}

async function startOver() {
  const d = await api("/api/reset", { sid: state.sid, skill: state.skill });
  sk().current = d.code; sk().tricks = sk().startTricks; sk().homework = sk().startHomework;
  setSkill(state.skill);
}

async function start() {
  setupHow();
  if (!(navigator.mediaDevices && window.MediaRecorder)) $("mic").hidden = true;
  document.querySelectorAll(".skill").forEach((b) => b.addEventListener("click", () => !state.busy && setSkill(b.dataset.skill)));
  $("mark-yes").addEventListener("click", () => markHomework(true));
  $("mark-no").addEventListener("click", () => markHomework(false));
  $("go-teach").addEventListener("click", () => ($("go-teach").dataset.next === "quiz" ? quiz() : teachScreen(false)));
  $("teach").addEventListener("click", teach);
  $("mic").addEventListener("click", micToggle);
  $("sentence").addEventListener("input", () => { $("teach-err").hidden = true; });
  $("sentence").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); teach(); } });
  $("retry-next").addEventListener("click", () => ($("retry-next").dataset.next === "quiz" ? quiz() : teachScreen(true)));
  $("retry-why").addEventListener("click", () => {
    const hw = sk().homework; const r = { ...hw };
    $("proof-visual").innerHTML = proofFor(state.skill, r.args, null).svg;
    $("proof-title").textContent = "Here's the right answer"; $("proof-text").textContent = proofFor(state.skill, r.args, null).caption;
    $("go-teach").textContent = "Teach him again"; $("go-teach").dataset.next = "teach"; show("proof");
  });
  $("oops-again").addEventListener("click", () => teachScreen(true));
  $("quiz-next").addEventListener("click", () => homework(sk().nextHomework));
  $("win-next").addEventListener("click", () => setSkill($("win-next").dataset.skill));
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
  try {
    const d = await api("/api/session");
    state.sid = d.sid; state.skills = d.skills;
    Object.values(state.skills).forEach((s) => { s.startTricks = s.tricks; s.startHomework = s.homework; });
    setSkill(state.skill);
    refreshLog();
  } catch (e) { say("I can't reach my brain right now. Try reloading."); }
}
start();
