#!/usr/bin/env python3
"""Generate the Teach Ahmes film (storyline A, "Ahmes's school day").

1. Cut the real proof clips from the v2 Playwright recordings into assets/proof/.
2. Write index.html (scene hosts and the audio mix) and compositions/*.html.

All times below are absolute film seconds; each chapter file gets them relative to its own start.
Run: python3 gen_audio.py && python3 build.py, then `hyperframes check` and `hyperframes render`.
Edits made in the HyperFrames desktop app are overwritten the next time this runs.
"""
from __future__ import annotations

import glob
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).parent
REC = HERE.parent / "out" / "work2" / "raw"
CAPTURE = HERE.parent / "out" / "work2" / "capture.json"
RAW = HERE / "assets" / "audio" / "raw"
NORM = HERE / "assets" / "audio" / "norm"
PROOF = HERE / "assets" / "proof"
COMP = HERE / "compositions"
TOTAL = 151.5
SCREEN_W, SCREEN_H = 1460, 822  # the tablet's screen in px


def probe(path: pathlib.Path) -> float:
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    return float(out.strip())


def rec(key: str) -> str:
    files = glob.glob(str(REC / key / "*.webm"))
    if len(files) != 1:
        raise SystemExit(f"expected one recording in {REC / key}, found {len(files)}")
    return files[0]


# ---------------------------------------------------------------- proof clips (real footage)
def cut(name: str, key: str, parts: list[tuple[float, float, float]], length: float, lead: float = 0.0) -> float:
    """Cut `parts` [(raw_a, raw_b, speed)] from recording `key`, hold the first frame `lead` s and the
    last frame until `length` s. Silent, 30 fps, sized to the tablet screen. Returns `length`."""
    PROOF.mkdir(parents=True, exist_ok=True)
    dest = PROOF / f"{name}.mp4"
    inputs, chains = [], []
    for i, (a, b, speed) in enumerate(parts):
        inputs += ["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", rec(key)]
        chains.append(f"[{i}:v]setpts=(PTS-STARTPTS)/{speed},fps=30,scale={SCREEN_W}:{SCREEN_H}:flags=lanczos,setsar=1[p{i}]")
    joined = "".join(f"[p{i}]" for i in range(len(parts)))
    chains.append(f"{joined}concat=n={len(parts)}:v=1:a=0,"
                  f"tpad=start_mode=clone:start_duration={lead:.3f}:stop_mode=clone:stop_duration={length:.3f},"
                  f"trim=duration={length:.3f},setpts=PTS-STARTPTS,format=yuv420p[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", "[v]",
                    "-an", "-r", "30", "-c:v", "libx264", "-preset", "medium", "-crf", "19", str(dest)], check=True)
    return length


# ---------------------------------------------------------------- audio
AUDIO: list[dict] = []


def voice(name: str, t: float) -> float:
    """Place a normalised voice clip at t; returns its end time."""
    d = probe(NORM / f"{name}.wav")
    AUDIO.append(dict(id=f"vo-{name.replace('_', '-').lower()}", src=f"assets/audio/norm/{name}.wav", t=t, d=d, vol=1.0, rate=1.0))
    return t + d


def sfx(name: str, t: float, vol: float, rate: float = 1.0) -> None:
    d = probe(RAW / f"sfx_{name}.mp3") / rate
    n = sum(1 for a in AUDIO if a["src"].endswith(f"sfx_{name}.mp3")) + 1
    AUDIO.append(dict(id=f"sfx-{name.replace('_', '-')}-{n}", src=f"assets/audio/raw/sfx_{name}.mp3", t=t, d=d, vol=vol, rate=rate))


def assign_tracks(first: int = 10) -> None:
    ends: list[float] = []
    for a in sorted(AUDIO, key=lambda x: x["t"]):
        for i, end in enumerate(ends):
            if end <= a["t"]:
                ends[i] = a["t"] + a["d"]; a["track"] = first + i
                break
        else:
            ends.append(a["t"] + a["d"]); a["track"] = first + len(ends) - 1


# ---------------------------------------------------------------- shared look
AHMES_SVG = """
<svg id="{p}-svg" viewBox="0 0 240 280" aria-label="Ahmes the robot" style="width:100%;height:100%;overflow:visible">
  <defs><radialGradient id="{p}-glow" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#7FF3E6"/><stop offset="100%" stop-color="#1FA39A"/></radialGradient></defs>
  <g id="{p}-spin"><g id="{p}-squash"><g id="{p}-bob">
    <line x1="120" y1="38" x2="120" y2="14" stroke="#16224A" stroke-width="4" stroke-linecap="round"/>
    <path id="{p}-nib" d="M114 16 L120 2 L126 16 Z" fill="#E0A526"/>
    <g id="{p}-head">
      <path d="M58 70 Q60 40 120 38 Q180 40 182 70 L192 128 Q170 120 166 104 L74 104 Q70 120 48 128 Z" fill="#2449A8"/>
      <path d="M62 78 L52 120 M74 72 L64 118 M166 72 L176 118 M178 78 L188 120" stroke="#E0A526" stroke-width="5" stroke-linecap="round"/>
      <rect x="72" y="52" width="96" height="70" rx="22" fill="#16224A"/>
      <g id="{p}-eyes">
        <circle class="{p}-pupil" cx="100" cy="84" r="9" fill="url(#{p}-glow)"/>
        <circle class="{p}-pupil" cx="140" cy="84" r="9" fill="url(#{p}-glow)"/>
        <path class="{p}-happy" d="M91 87 Q100 76 109 87" fill="none" stroke="#7FF3E6" stroke-width="4" stroke-linecap="round" opacity="0"/>
        <path class="{p}-happy" d="M131 87 Q140 76 149 87" fill="none" stroke="#7FF3E6" stroke-width="4" stroke-linecap="round" opacity="0"/>
        <path id="{p}-spiral-l" class="{p}-spiral" d="M100 84 m0 0 a2 2 0 1 1 3 0 a5 5 0 1 1 -8 0 a8 8 0 1 1 13 0" fill="none" stroke="#7FF3E6" stroke-width="2.4" opacity="0"/>
        <path id="{p}-spiral-r" class="{p}-spiral" d="M140 84 m0 0 a2 2 0 1 1 3 0 a5 5 0 1 1 -8 0 a8 8 0 1 1 13 0" fill="none" stroke="#7FF3E6" stroke-width="2.4" opacity="0"/>
      </g>
      <path id="{p}-mouth" d="M108 106 Q120 113 132 106" fill="none" stroke="#7FF3E6" stroke-width="3.5" stroke-linecap="round"/>
    </g>
    <rect x="78" y="134" width="84" height="88" rx="18" fill="#2449A8"/>
    <rect x="94" y="150" width="52" height="40" rx="8" fill="#F7FAFD"/>
    <text x="120" y="181" text-anchor="middle" font-family="Nunito" font-weight="900" font-size="30" fill="#16224A">½</text>
    <circle cx="104" cy="204" r="5" fill="#E0A526"/><circle cx="120" cy="204" r="5" fill="#1FA39A"/><circle cx="136" cy="204" r="5" fill="#E0A526"/>
    <path d="M80 150 Q56 170 60 198" fill="none" stroke="#2449A8" stroke-width="12" stroke-linecap="round"/>
    <path id="{p}-arm" d="M160 150 Q184 170 180 198" fill="none" stroke="#2449A8" stroke-width="12" stroke-linecap="round"/>
    <rect x="92" y="222" width="18" height="34" rx="6" fill="#16224A"/><rect x="130" y="222" width="18" height="34" rx="6" fill="#16224A"/>
  </g></g></g>
</svg>"""

CSS = """
#root { position: absolute; inset: 0; font-family: "Nunito", sans-serif; color: #16224A; overflow: hidden; }
.card { position: absolute; left: 1010px; top: 170px; width: 760px; height: 440px; z-index: 2; }
.card-in { position: absolute; inset: 0; background: #FFFFFF; border: 2px solid #C9D7EA; border-radius: 28px; }
.card-ask { position: absolute; left: 0; right: 0; top: 40px; text-align: center; font-weight: 800; font-size: 44px; color: #4E5B80; }
.num { position: absolute; top: 170px; width: 340px; text-align: center; font-weight: 900; font-size: 140px; line-height: 1; font-variant-numeric: tabular-nums; }
.marks { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
.cross { position: absolute; left: 60px; top: 120px; width: 300px; text-align: center; font-weight: 900; font-size: 230px; line-height: 1; color: #C6432A; opacity: 0; }
.fracs { position: absolute; left: 0; right: 0; top: 130px; display: flex; justify-content: center; align-items: center; gap: 40px; }
.frac { display: flex; flex-direction: column; align-items: center; min-width: 140px; font-weight: 900; font-size: 96px; line-height: 1.05; font-variant-numeric: tabular-nums; }
.frac .bar { width: 100%; height: 8px; background: #16224A; border-radius: 4px; margin: 6px 0; }
.plus { font-weight: 900; font-size: 96px; }
.slot { position: absolute; left: 1010px; top: 670px; width: 760px; height: 236px; z-index: 4; }
.bubble { position: absolute; inset: 0; background: #FFFFFF; border: 5px solid #E0A526; border-radius: 34px;
  display: flex; align-items: center; padding: 0 44px; font-weight: 800; font-size: 46px; line-height: 1.25; }
.bubble.long { font-size: 38px; line-height: 1.25; }
.bubble::after { content: ""; position: absolute; left: 90px; bottom: -44px; border: 22px solid transparent; border-top: 22px solid #E0A526; }
.bubble .w { opacity: 0; }
.code { position: absolute; inset: 0; background: #16224A; border-radius: 28px; padding: 30px 40px; font-family: "JetBrains Mono", monospace;
  font-size: 30px; line-height: 1.45; color: #E6EEFF; white-space: pre; font-variant-ligatures: none; font-feature-settings: "calt" 0, "liga" 0; }
.code .c { color: #7FF3E6; }
.code .ln { display: block; clip-path: inset(0 100% 0 0); }
.spark { position: absolute; width: 26px; height: 26px; background: #E0A526; border-radius: 4px; opacity: 0; }
.tab { position: absolute; left: 310px; top: 118px; width: 1500px; height: 844px; z-index: 5; }
.tab-in { position: absolute; inset: 0; background: #16224A; border-radius: 44px; }
.screen { position: absolute; left: 20px; top: 11px; width: 1460px; height: 822px; border-radius: 26px; overflow: hidden; background: #F7FAFD; }
.screen video, .screen img { position: absolute; left: 0; top: 0; width: 1460px; height: 822px; object-fit: cover; }
.badge { position: absolute; right: -40px; top: -50px; width: 250px; height: 250px; border-radius: 50%; background: #E0A526; border: 10px solid #FFFFFF;
  display: flex; flex-direction: column; align-items: center; justify-content: center; color: #16224A; z-index: 3; }
.badge b { font-weight: 900; font-size: 84px; line-height: 0.9; }
.badge span { font-weight: 800; font-size: 30px; }
.receipt { position: absolute; left: -50px; padding: 16px 30px; background: #FFFFFF; border: 6px solid #C6432A; border-radius: 18px;
  color: #C6432A; font-weight: 900; font-size: 50px; z-index: 8; }
.receipt small { display: block; font-weight: 800; font-size: 28px; color: #4E5B80; }
"""

JS_HELPERS = """
const show = (sel, on, t, d = 0.12) => tl.to(sel, { opacity: on ? 1 : 0, duration: d, ease: "none" }, t);
const typeWords = (sel, t0, gap) => gsap.utils.toArray(sel).forEach((w, i) => tl.to(w, { opacity: 1, duration: 0.08, ease: "none" }, t0 + i * gap));
const bubbleIn = (sel, t) => tl.fromTo(sel, { y: 300 }, { y: 0, duration: 0.6, ease: "expo.out" }, t);
const bubbleInto = (sel, t) => tl.to(sel, { x: -880, y: -640, scale: 0.05, rotation: -20, backgroundColor: "#E0A526", duration: 0.55, ease: "power3.in" }, t);
const sparks = (sel, t) => {
  tl.fromTo(sel, { opacity: 1, scale: 0.2, x: 0, y: 0 }, { scale: 1, x: (i) => [-40, 0, 40][i], y: (i) => [-30, -50, -24][i], rotation: 45, duration: 0.35, ease: "expo.out", stagger: 0.03 }, t);
  tl.to(sel, { opacity: 0, duration: 0.2, ease: "none" }, t + 0.3);
};
const codeIn = (sel, t) => {
  tl.fromTo(sel, { opacity: 0, scale: 0.9, filter: "blur(8px)" }, { opacity: 1, scale: 1, filter: "blur(0px)", duration: 0.3, ease: "expo.out" }, t);
  gsap.utils.toArray(sel + " .ln").forEach((ln, i) => tl.to(ln, { clipPath: "inset(0 0% 0 0)", duration: 0.32, ease: "none" }, t + 0.15 + i * 0.3));
};
const blurIn = (sel, t) => tl.fromTo(sel, { opacity: 0, filter: "blur(8px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.18, ease: "expo.out" }, t);
const blurOut = (sel, t) => tl.to(sel, { opacity: 0, filter: "blur(8px)", duration: 0.18, ease: "power2.in" }, t);
const stampIn = (sel, t, rot = -8) => tl.fromTo(sel, { opacity: 0, scale: 1.7, rotation: rot - 10 }, { opacity: 1, scale: 1, rotation: rot, duration: 0.2, ease: "power4.out" }, t);
const pop = (sel, t) => tl.fromTo(sel, { opacity: 0, scale: 0.3 }, { opacity: 1, scale: 1, duration: 0.45, ease: "back.out(1.8)" }, t);
const TAB = { full: { x: 0, y: 0, scale: 1 }, col: { x: 700, y: 52, scale: 0.5067 }, offR: { x: 1700, y: 52, scale: 0.5067 }, box: { x: -230, y: 90, scale: 0.55 } };
const tabSet = (sel, s, t) => tl.set(sel, { ...TAB[s], transformOrigin: "0 0" }, t);
const tabTo = (sel, s, t, d, ease) => tl.to(sel, { ...TAB[s], transformOrigin: "0 0", duration: d, ease }, t);
"""


def r(x: float) -> str:
    return f"{x:.3f}".rstrip("0").rstrip(".")


class Chapter:
    def __init__(self, cid: str, start: float, end: float):
        self.id, self.start, self.end = cid, start, end
        self.html: list[str] = []
        self.js: list[str] = []

    def t(self, x: float) -> str:
        return r(x - self.start)

    def clip(self, eid: str, a: float, b: float, cls: str, inner: str, track: int, extra: str = "") -> None:
        self.html.append(f'<div id="{eid}" class="{cls} clip" data-start="{self.t(a)}" data-duration="{r(b - a)}" data-track-index="{track}" {extra}>{inner}</div>')

    def video(self, eid: str, src: str, a: float, d: float) -> str:
        return f'<video id="{eid}" class="clip" src="{src}" muted playsinline data-start="{self.t(a)}" data-duration="{r(d)}" data-track-index="9"></video>'

    def tl(self, line: str) -> None:
        self.js.append(line)

    def write(self) -> None:
        body = "\n    ".join(self.html)
        script = "\n      ".join(self.js)
        COMP.mkdir(exist_ok=True)
        (COMP / f"{self.id}.html").write_text(f"""<template>
  <style>{CSS}</style>
  <div id="root" data-composition-id="{self.id}" data-width="1920" data-height="1080">
    {body}
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      {JS_HELPERS}
      {script}
      window.__timelines["{self.id}"] = tl;
    }})();
  </script>
</template>
""")


def words(text: str) -> str:
    return "".join(f'<span class="w">{w} </span>' for w in text.split())


def bubble(cls: str, text: str, inner_id: str) -> str:
    return f'<div id="{inner_id}" class="bubble {cls}"><span>“{words(text)}”</span></div>'


def code(lines: list[str], inner_id: str) -> str:
    out = []
    for i, ln in enumerate(lines):
        c = ' c' if ln.startswith("#") else ''
        out.append(f'<span class="ln{c}">{ln.replace("&", "&amp;").replace("<", "&lt;")}</span>')
    return f'<div id="{inner_id}" class="code" style="opacity: 0">{"".join(out)}</div>'


SPARKS = '<div class="spark" style="left: 462px; top: 140px"></div><div class="spark" style="left: 512px; top: 120px"></div><div class="spark" style="left: 560px; top: 146px"></div>'


def tablet(pfx: str, screen: str, extras: str = "") -> str:
    return f'<div id="{pfx}-tab" class="tab"><div id="{pfx}-tab-in" class="tab-in"><div class="screen">{screen}</div>{extras}</div></div>'


# ---------------------------------------------------------------- the film
def build() -> None:
    marks = json.loads(CAPTURE.read_text())["marks"]
    D, F, Y, H = marks["D"], marks["F"], marks["Y"], marks["H"]
    stage: list[str] = []  # Ahmes's acting, absolute times

    # ---- chapter 1: the bug, the first rule, 24/40 on the tablet
    c1 = Chapter("ch1", 0.0, 33.9)
    voice("a1", 0.3); sfx("pen", 2.82, 0.6); sfx("stamp", 5.16, 0.8)
    n1_end = voice("v2_n1", 5.9)
    stage += ['point(0.7, 3.4);', 'face("happy", 3.85); hop(3.85);', 'confused(5.35);']
    c1.clip("c1-card", 0, 19.6, "card", '<div id="c1-card-in" class="card-in"><div class="card-ask">Which is bigger?</div>'
            '<div class="num" style="left: 30px">0.45</div><div class="num" style="left: 390px">0.5</div>'
            '<svg class="marks" viewBox="0 0 760 440"><path id="c1-ring" opacity="0" d="M200 150 C330 150 350 330 200 335 C70 338 50 160 190 148" fill="none" stroke="#2449A8" stroke-width="9" stroke-linecap="round" pathLength="100" stroke-dasharray="100" stroke-dashoffset="100"/></svg>'
            '<div id="c1-cross" class="cross" data-layout-allow-overlap>✗</div></div>', 2)
    c1.tl(f'tl.set("#c1-ring", {{ opacity: 1 }}, {c1.t(2.95)}); tl.to("#c1-ring", {{ strokeDashoffset: 0, duration: 0.85, ease: "power1.inOut" }}, {c1.t(2.95)});')
    c1.tl(f'stampIn("#c1-cross", {c1.t(5.0)});')
    c1.tl(f'tl.fromTo("#c1-card-in", {{ x: 0 }}, {{ keyframes: {{ x: [0, -10, 8, -4, 0] }}, duration: 0.3, ease: "none" }}, {c1.t(5.2)});')
    b1 = n1_end - 0.2
    c1_txt = "Look at the tenths first."
    c1.clip("c1-bub", b1 - 0.1, b1 + 2.5, "slot", bubble("", c1_txt, "c1-bub-in"), 3)
    voice("c1", b1 + 0.3)
    c1.tl(f'bubbleIn("#c1-bub-in", {c1.t(b1)}); typeWords("#c1-bub-in .w", {c1.t(b1 + 0.4)}, 0.21); bubbleInto("#c1-bub-in", {c1.t(b1 + 1.9)});')
    sfx("glyphs", b1 + 1.76, 0.45)
    c1.clip("c1-sparks", b1 + 2.3, b1 + 3.2, "", SPARKS, 4, "data-layout-ignore")
    c1.tl(f'sparks("#c1-sparks .spark", {c1.t(b1 + 2.45)});')
    stage += [f'tl.to("#s-head", {{ rotation: -4, svgOrigin: "120 100", duration: 0.4, ease: "power2.inOut" }}, {r(b1 + 0.4)});',
              f'nib({r(b1 + 2.45)}); mouth("wow", {r(b1 + 2.45)});',
              f'tl.to("#s-head", {{ rotation: 0, svgOrigin: "120 100", duration: 0.3, ease: "power2.out" }}, {r(b1 + 2.5)});']
    c1.clip("c1-code", b1 + 2.4, 19.6, "slot", code(['# "look at the tenths first"', 'return bigger_tenths(a, b)'], "c1-code-in"), 3)
    c1.tl(f'codeIn("#c1-code-in", {c1.t(b1 + 2.5)});')
    voice("v2_n2", b1 + 2.7)
    # the tablet slides in over the card and fills the frame: the real retry and quiz
    c1.tl(f'blurOut("#c1-card-in", {c1.t(19.3)}); blurOut("#c1-code-in", {c1.t(19.3)});')
    sfx("whoosh_a", 19.3, 0.5)
    lead = 20.5 - 19.35
    retry_len = cut("retry", "D", [(22.1, 25.0, 1.0), (28.3, 33.0, 1.0)], 33.9 - 19.35, lead)
    c1.html.append(tablet("c1", c1.video("c1-v", "assets/proof/retry.mp4", 19.35, retry_len),
                          '<div id="c1-badge" class="badge" style="opacity: 0"><b>24</b><span>out of 40</span></div>'))
    c1.tl('tabSet("#c1-tab", "offR", 0);')
    c1.tl(f'tabTo("#c1-tab", "col", {c1.t(19.35)}, 0.5, "expo.out"); tabTo("#c1-tab", "full", {c1.t(19.95)}, 0.55, "power2.inOut");')
    stage += ['watch(19.9);', 'face("normal", 19.9); mouth("smile", 19.9);']
    voice("app_D_04", 20.5 + (23.4 - 22.1) + 0.15)
    stage += ['face("happy", 21.95); hop(22.0);', 'face("normal", 24.5);']
    q1_done = 20.5 + (25.0 - 22.1) + (D["q1_done"] - 28.3)
    c1.tl(f'pop("#c1-badge", {c1.t(q1_done + 0.1)});'); sfx("pop", q1_done + 0.08, 0.6)
    voice("v2_n3", q1_done - 0.1)
    stage += [f'tl.to("#s-head", {{ rotation: 7, svgOrigin: "120 100", duration: 0.4, ease: "back.out(1.6)" }}, {r(q1_done + 0.3)});',
              f'tl.to("#s-head", {{ rotation: 0, svgOrigin: "120 100", duration: 0.4, ease: "power2.inOut" }}, 33.2);']
    c1.tl(f'tabTo("#c1-tab", "col", {c1.t(33.0)}, 0.45, "power2.inOut"); tabTo("#c1-tab", "offR", {c1.t(33.45)}, 0.4, "power3.in");')
    sfx("whoosh_b", 33.1, 0.5)
    stage += ['home(33.2);']
    c1.write()

    # ---- chapter 2: the dizzy rule, the sandbox, the real stop
    c2 = Chapter("ch2", 33.5, 56.6)
    c2.clip("c2-card", 33.6, 41.95, "card", '<div id="c2-card-in" class="card-in" style="opacity: 0"><div class="card-ask">Add them</div>'
            '<div class="fracs"><div class="frac"><span>1</span><span class="bar"></span><span id="c2-den-a">2</span></div><div class="plus">+</div>'
            '<div class="frac"><span>1</span><span class="bar"></span><span id="c2-den-b">3</span></div></div></div>', 2)
    c2.tl(f'blurIn("#c2-card-in", {c2.t(33.8)});')
    c2_txt = "Keep doubling both bottoms until they’re the same."
    c2.clip("c2-bub", 33.9, 37.45, "slot", bubble("", c2_txt, "c2-bub-in"), 3)
    voice("c2", 34.3)
    c2.tl(f'bubbleIn("#c2-bub-in", {c2.t(34.0)}); typeWords("#c2-bub-in .w", {c2.t(34.4)}, 0.27); bubbleInto("#c2-bub-in", {c2.t(36.85)});')
    sfx("glyphs", 36.71, 0.4, 0.92)
    c2.clip("c2-sparks", 37.3, 38.1, "", SPARKS, 4, "data-layout-ignore")
    c2.tl(f'sparks("#c2-sparks .spark", {c2.t(37.4)});')
    c2.clip("c2-code", 37.35, 41.95, "slot", code(['# "keep doubling both bottoms"', 'while a.bottom != b.bottom:', '    a.bottom *= 2', '    b.bottom *= 2'], "c2-code-in"), 3)
    c2.tl(f'codeIn("#c2-code-in", {c2.t(37.45)});')
    c2.clip("c2-box", 37.4, 42.0, "", '<div id="c2-box-in" style="position:absolute;inset:0">'
            '<div style="position:absolute;left:0;top:64px;right:0;bottom:0;border:8px solid #12857D;border-radius:36px;background:rgba(18,133,125,0.08)"></div>'
            '<div style="position:absolute;left:36px;top:0;height:72px;padding:0 28px;background:#12857D;border-radius:18px 18px 0 0;display:flex;align-items:center;gap:24px;color:#FFFFFF;font-weight:900;font-size:38px">'
            'Sandbox <span id="c2-timer" style="font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:34px;min-width:110px">0.0 s</span></div>'
            '<div id="c2-stopped" style="position:absolute;left:230px;top:720px;padding:10px 30px;border:7px solid #C6432A;border-radius:16px;color:#C6432A;font-weight:900;font-size:64px;background:#F7FAFD;opacity:0">Stopped</div>'
            '</div>', 6, 'style="position:absolute;left:70px;top:64px;width:860px;height:936px;z-index:6"')
    c2.tl(f'tl.fromTo("#c2-box-in", {{ y: -1100 }}, {{ y: 0, duration: 0.35, ease: "power3.in" }}, {c2.t(37.45)});')
    sfx("lock", 37.78, 0.45); sfx("spin", 37.9, 0.22)
    c2.tl(f"""const T0 = {c2.t(37.9)}, T1 = {c2.t(40.9)};
      const timer = document.getElementById("c2-timer"), dA = document.getElementById("c2-den-a"), dB = document.getElementById("c2-den-b");
      const counters = (t) => {{ const p = Math.min(Math.max((t - T0) / (T1 - T0), 0), 1); const k = Math.floor(p * p * 12);
        dA.textContent = String(2 * 2 ** k); dB.textContent = String(3 * 2 ** k); timer.textContent = (p * 3).toFixed(1) + " s"; }};
      tl.to({{}}, {{ duration: {r(56.6 - 33.5)}, ease: "none", onUpdate: () => counters(tl.time()) }}, 0); counters(0);""")
    c2.tl(f'stampIn("#c2-stopped", {c2.t(40.88)}, -7);'); sfx("stamp", 40.86, 0.8, 0.9)
    c2.tl(f'tl.to("#c2-box-in", {{ y: -1150, duration: 0.4, ease: "power3.in" }}, {c2.t(41.5)});'); sfx("lift", 41.33, 0.9)
    c2.tl(f'blurOut("#c2-card-in", {c2.t(41.6)}); blurOut("#c2-code-in", {c2.t(41.6)});')
    stage += ['tl.to("#s-head", { rotation: -4, svgOrigin: "120 100", duration: 0.4, ease: "power2.inOut" }, 34.4);',
              'nib(37.4); tl.to("#s-head", { rotation: 0, svgOrigin: "120 100", duration: 0.3 }, 37.4);',
              'face("dizzy", 37.85); mouth("wow", 37.85); spin(37.9, 40.9);', 'watch(41.7);', 'face("normal", 44.2); mouth("frown", 44.2);']
    dizzy_len = cut("dizzy", "F", [(23.2, F["end"], 1.0)], 56.6 - 41.9, 42.5 - 41.9)
    c2.html.append(tablet("c2", c2.video("c2-v", "assets/proof/dizzy.mp4", 41.9, dizzy_len)))
    c2.tl('tabSet("#c2-tab", "box", 0); tl.set("#c2-tab", { opacity: 0 }, 0);')
    c2.tl(f'tl.to("#c2-tab", {{ opacity: 1, duration: 0.15, ease: "none" }}, {c2.t(41.9)}); tabTo("#c2-tab", "full", {c2.t(41.9)}, 0.6, "power2.inOut");')
    sfx("whoosh_a", 41.85, 0.45, 0.9)
    voice("app_F_04", 42.5 + (24.0 - 23.2) + 0.15)
    voice("v2_n4", 48.5)
    c2.write()

    # ---- chapter 3: the judges' evidence on the tablet, then Thoth
    c3 = Chapter("ch3", 56.6, 100.0)
    pipe = cut("pipeline", "H", [(H["pipeline"] - 1.0, H["hood"], 1.0)], H["hood"] - H["pipeline"] + 1.0)
    brk_a, brk_b, sp = H["hood"] - 0.3, H["log"] + 1.5, 2.2
    brk = cut("break", "H", [(brk_a, brk_b, sp)], 74.6 - (56.6 + pipe))
    th_a = 62.5
    thoth = cut("thoth", "D", [(th_a, D["t3_shown"] + 6.0, 1.0)], 90.8 - 74.6)
    refuse = cut("refuse", "D", [(70.9, 77.8, 1.0)], 100.0 - 90.8)
    t_brk = 56.6 + pipe
    screens = (c3.video("c3-v1", "assets/proof/pipeline.mp4", 56.6, pipe) + c3.video("c3-v2", "assets/proof/break.mp4", t_brk, brk)
               + c3.video("c3-v3", "assets/proof/thoth.mp4", 74.6, thoth) + c3.video("c3-v4", "assets/proof/refuse.mp4", 90.8, refuse))
    c3.html.append(tablet("c3", screens))
    oom = max(t_brk + (H["oom_done"] - brk_a) / sp, 67.6)
    net = t_brk + (H["net_done"] - brk_a) / sp
    c3.clip("c3-r1", oom - 0.05, 74.5, "receipt", 'Killed at 64 MB<small>out of memory, from the real receipt</small>', 7, 'style="left: 1130px; top: 170px; opacity: 0"')
    c3.clip("c3-r2", net - 0.05, 74.5, "receipt", 'Network unreachable<small>no internet inside the box</small>', 7, 'style="left: 1130px; top: 400px; opacity: 0"')
    c3.tl('tabSet("#c3-tab", "full", 0);')
    c3.tl(f'stampIn("#c3-r1", {c3.t(oom)}, -5); stampIn("#c3-r2", {c3.t(net)}, 4); blurOut("#c3-r1", {c3.t(74.2)}); blurOut("#c3-r2", {c3.t(74.2)});')
    sfx("stamp", oom - 0.02, 0.7); sfx("stamp", net - 0.02, 0.7, 0.9)
    voice("v2_n5", 56.8); voice("v2_n6", t_brk + 0.2)
    voice("v2_n7", 74.8); voice("v2_thoth", 83.8)
    voice("v2_c_ans", 90.85); voice("app_D_10", 90.8 + (74.8 - 70.9) + 0.15)
    stage += [f'surprised({r(oom)}); surprised({r(net)});', 'face("normal", 75.0); mouth("smile", 75.0);',
              'tl.to("#s-head", { rotation: 8, svgOrigin: "120 100", duration: 0.4, ease: "back.out(1.6)" }, 84.0);',
              'tl.to("#s-head", { rotation: 0, svgOrigin: "120 100", duration: 0.4, ease: "power2.inOut" }, 90.0);']
    c3.write()

    # ---- chapter 4: the full rule, 40/40
    c4 = Chapter("ch4", 100.0, 123.6)
    c4.html.append(tablet("c4", "", '<div id="c4-badge" class="badge" style="opacity: 0"><b>40</b><span>out of 40</span></div>'))
    c4.tl('tabSet("#c4-tab", "full", 0);')
    c4.tl(f'tabTo("#c4-tab", "col", 0, 0.45, "power2.inOut"); tabTo("#c4-tab", "offR", 0.45, 0.4, "power3.in");')
    sfx("whoosh_b", 100.05, 0.5, 1.1)
    stage += ['home(100.3);']
    c4_end = voice("v2_c4", 101.8)
    t_in = c4_end + 4.0  # the code holds long enough to read
    c4.clip("c4-card", 100.7, t_in, "card", '<div id="c4-card-in" class="card-in" style="opacity: 0"><div class="card-ask">Which is bigger?</div>'
            '<div class="num" style="left: 20px; font-size: 128px">0.943</div><div class="num" style="left: 400px; font-size: 128px">0.96</div>'
            '<div id="c4-cross" class="cross" data-layout-allow-overlap>✗</div></div>', 2)
    c4.tl(f'blurIn("#c4-card-in", {c4.t(100.9)}); stampIn("#c4-cross", {c4.t(101.1)});'); sfx("stamp", 101.08, 0.6, 1.1)
    stage += ['confused(101.2);']
    c4_txt = "If the tenths are the same, check the next place, and if every place is the same, they’re equal."
    n_words = len(c4_txt.split())
    c4.clip("c4-bub", 101.4, c4_end + 0.3, "slot", bubble("long", c4_txt, "c4-bub-in"), 3, 'style="height: 270px; top: 640px"')
    gap = (c4_end - 101.95 - 0.3) / (n_words - 1)
    c4.tl(f'bubbleIn("#c4-bub-in", {c4.t(101.5)}); typeWords("#c4-bub-in .w", {c4.t(101.95)}, {r(gap)}); bubbleInto("#c4-bub-in", {c4.t(c4_end - 0.25)});')
    sfx("glyphs", c4_end - 0.39, 0.45, 1.05)
    c4.clip("c4-sparks", c4_end + 0.2, c4_end + 1.0, "", SPARKS, 4, "data-layout-ignore")
    c4.tl(f'sparks("#c4-sparks .spark", {c4.t(c4_end + 0.3)});')
    stage += [f'tl.to("#s-head", {{ rotation: -4, svgOrigin: "120 100", duration: 0.4, ease: "power2.inOut" }}, 101.9);',
              f'nib({r(c4_end + 0.3)}); mouth("wow", {r(c4_end + 0.3)}); tl.to("#s-head", {{ rotation: 0, svgOrigin: "120 100", duration: 0.3 }}, {r(c4_end + 0.3)});']
    c4.clip("c4-code", c4_end + 0.25, t_in, "slot", code(['# "check the next place"', 'for p in places(a, b):', '    if a[p] != b[p]: pick(p)', 'return "equal"'], "c4-code-in"), 3)
    c4.tl(f'codeIn("#c4-code-in", {c4.t(c4_end + 0.35)});')
    c4.tl(f'blurOut("#c4-card-in", {c4.t(t_in - 0.3)}); blurOut("#c4-code-in", {c4.t(t_in - 0.3)});')
    shown = t_in + 1.1  # the footage starts moving once the tablet is full
    cut_a, cut_b = 93.9, 95.4  # drop 1.5 s of quiz cards dealing
    cure = cut("cure", "D", [(89.4, cut_a, 1.0), (cut_b, 99.4, 1.0)], 123.6 - t_in, shown - t_in)
    at = lambda raw_t: shown + (raw_t - 89.4 if raw_t <= cut_a else (cut_a - 89.4) + (raw_t - cut_b))
    c4.html[0] = tablet("c4", c4.video("c4-v", "assets/proof/cure.mp4", t_in, cure), '<div id="c4-badge" class="badge" style="opacity: 0"><b>40</b><span>out of 40</span></div>')
    c4.tl(f'tabTo("#c4-tab", "col", {c4.t(t_in)}, 0.5, "expo.out"); tabTo("#c4-tab", "full", {c4.t(t_in + 0.55)}, 0.55, "power2.inOut");')
    sfx("whoosh_a", t_in - 0.05, 0.45, 1.05)
    stage += [f'watch({r(t_in + 0.4)});', f'face("normal", {r(t_in + 0.4)}); mouth("smile", {r(t_in + 0.4)});']
    said = voice("app_D_12", at(89.7) + 0.15)
    q2 = at(D["q2_done"])
    c4.tl(f'pop("#c4-badge", {c4.t(q2 + 0.05)});'); sfx("pop", q2 + 0.03, 0.6, 0.9)
    won = at(96.9) + 0.15
    won_end = voice("app_D_13", won)
    n9_end = voice("v2_n9", won_end + 0.2)
    assert n9_end < 123.6, n9_end
    stage += [f'face("happy", {r(said - 1.4)}); hop({r(said - 1.35)});', f'hop({r(won + 0.05)}); hop({r(won + 0.75)});']
    c4.write()

    # ---- chapter 5: six lessons, the machine, the report
    c5 = Chapter("ch5", 123.6, 146.7)
    lessons = cut("lessons", "Y", [(Y["map"] - 0.5, Y["end"], 3.5)], 130.9 - 123.6)
    report = cut("report", "D", [(D["report"] - 0.8, D["end"], 1.8)], 146.7 - 139.9)
    screens = (c5.video("c5-v1", "assets/proof/lessons.mp4", 123.6, lessons)
               + f'<img id="c5-arch" class="clip" src="assets/proof/diagram.png" data-start="{c5.t(130.9)}" data-duration="9" data-track-index="8">'
               + c5.video("c5-v2", "assets/proof/report.mp4", 139.9, report))
    c5.html.append(tablet("c5", screens))
    c5.tl('tabSet("#c5-tab", "full", 0);')
    c5.tl(f'tabTo("#c5-tab", "col", {c5.t(145.8)}, 0.45, "power2.inOut"); tabTo("#c5-tab", "offR", {c5.t(146.25)}, 0.4, "power3.in");')
    sfx("whoosh_b", 145.85, 0.5)
    voice("v2_n10", 123.8); voice("v2_n_arch", 131.1); voice("v2_n11", 140.1)
    stage += ['face("normal", 124.0);', 'home(146.0);']
    c5.write()

    # ---- chapter 6: the name
    c6 = Chapter("ch6", 146.4, TOTAL)
    letters = "".join(f"<span>{ch if ch != ' ' else '&nbsp;'}</span>" for ch in "Teach Ahmes")
    c6.clip("c6-title", 146.6, TOTAL, "", f'<div class="t-name" style="font-weight:900;font-size:128px;line-height:1;letter-spacing:-0.02em;white-space:nowrap">{letters}</div>'
            '<div id="c6-sub" style="margin-top:36px;font-weight:800;font-size:46px;line-height:1.3;color:#4E5B80;opacity:0">Children teach.<br><b style="color:#12857D;font-weight:900">A sandbox keeps it safe.</b></div>'
            '<div id="c6-url" style="margin-top:40px;font-family:\'JetBrains Mono\',monospace;font-weight:700;font-size:32px;color:#2449A8;opacity:0">64-177-33-215.sslip.io</div>'
            '<div id="c6-by" style="margin-top:14px;font-weight:800;font-size:30px;color:#4E5B80;opacity:0">Built on Vultr for Agent Rush</div>',
            6, 'style="position:absolute;left:1010px;top:300px;width:820px"')
    c6.tl(f'tl.fromTo("#c6-title .t-name span", {{ opacity: 0.3, filter: "blur(6px)" }}, {{ opacity: 1, filter: "blur(0px)", duration: 0.13, ease: "power2.out", stagger: 0.06 }}, {c6.t(146.6)});')
    c6.tl(f'blurIn("#c6-sub", {c6.t(147.3)}); blurIn("#c6-url", {c6.t(147.9)}); blurIn("#c6-by", {c6.t(148.1)});')
    c6.tl('tl.set("#c6-title .t-name span", { opacity: 0.3 }, 0);')
    voice("v2_n12", 146.8)
    stage += ['face("happy", 146.6);', 'wave(147.0);']
    c6.write()

    write_stage(stage)
    AUDIO.append(dict(id="score", src="assets/audio/raw/score.mp3", t=0.0, d=min(probe(RAW / "score.mp3"), TOTAL), vol=0.16, rate=1.0, fade=2.0))
    assign_tracks()
    write_index([c1, c2, c3, c4, c5, c6])


STAGE_JS = """
const mouths = { smile: "M108 106 Q120 113 132 106", frown: "M108 111 Q120 103 132 111", wow: "M112 107 Q120 114 128 107" };
const face = (s, t) => { show(".s-pupil", s === "normal", t); show(".s-happy", s === "happy", t); show(".s-spiral", s === "dizzy", t); };
const mouth = (m, t) => tl.to("#s-mouth", { attr: { d: mouths[m] }, duration: 0.18, ease: "power2.out" }, t);
const point = (t, hold) => { tl.fromTo("#s-arm", { rotation: 0 }, { rotation: -78, svgOrigin: "160 150", duration: 0.35, ease: "back.out(1.6)" }, t);
  tl.to("#s-arm", { rotation: 0, svgOrigin: "160 150", duration: 0.3, ease: "power2.inOut" }, t + hold); };
const hop = (t) => { tl.to("#s-squash", { scaleY: 0.9, scaleX: 1.05, svgOrigin: "120 256", duration: 0.12, ease: "power2.out" }, t);
  tl.to("#s-squash", { scaleY: 1.06, scaleX: 0.97, y: -26, svgOrigin: "120 256", duration: 0.22, ease: "power3.out" }, t + 0.12);
  tl.to("#s-squash", { scaleY: 1, scaleX: 1, y: 0, svgOrigin: "120 256", duration: 0.35, ease: "back.out(1.6)" }, t + 0.34); };
const surprised = (t) => { tl.to("#s-squash", { scaleY: 0.92, svgOrigin: "120 256", duration: 0.1, ease: "power2.out" }, t);
  tl.to("#s-squash", { scaleY: 1, svgOrigin: "120 256", duration: 0.4, ease: "back.out(1.6)" }, t + 0.1); mouth("wow", t); mouth("smile", t + 1.2); };
const confused = (t) => { tl.to("#s-squash", { scaleY: 0.93, svgOrigin: "120 256", duration: 0.12, ease: "power2.out" }, t);
  tl.to("#s-squash", { scaleY: 1, svgOrigin: "120 256", duration: 0.4, ease: "back.out(1.6)" }, t + 0.12);
  face("normal", t + 0.12); mouth("frown", t + 0.15); tl.to("#s-head", { rotation: 9, svgOrigin: "120 100", duration: 0.45, ease: "back.out(1.6)" }, t + 0.2); };
const blink = (t) => tl.to("#s-eyes", { scaleY: 0.1, svgOrigin: "120 84", duration: 0.06, yoyo: true, repeat: 1, ease: "power1.inOut" }, t);
const nib = (t) => tl.fromTo("#s-nib", { scale: 1 }, { scale: 1.6, svgOrigin: "120 10", duration: 0.12, yoyo: true, repeat: 1, ease: "power2.out" }, t);
const home = (t) => tl.to("#s-svg", { x: 0, y: 0, scale: 1, transformOrigin: "0 0", duration: 0.6, ease: "power2.inOut" }, t);
const watch = (t) => tl.to("#s-svg", { x: -130, y: 570, scale: 0.35, transformOrigin: "0 0", duration: 0.6, ease: "power2.inOut" }, t);
const spin = (a, b) => { tl.fromTo("#s-spiral-l", { rotation: 0 }, { rotation: 1800, svgOrigin: "100 84", duration: b - a + 1.5, ease: "none" }, a);
  tl.fromTo("#s-spiral-r", { rotation: 0 }, { rotation: 1800, svgOrigin: "140 84", duration: b - a + 1.5, ease: "none" }, a);
  tl.fromTo("#s-spin", { rotation: 0 }, { rotation: 1440, svgOrigin: "120 150", duration: b - a, ease: "power2.in" }, a);
  tl.to("#s-spin", { keyframes: { rotation: [1440, 1456, 1430, 1446, 1437, 1440] }, svgOrigin: "120 150", duration: 0.7, ease: "none" }, b); };
const wave = (t) => tl.fromTo("#s-arm", { rotation: 0 }, { keyframes: { rotation: [0, -130, -105, -130, -105, -120] }, svgOrigin: "160 150", duration: 1.4, ease: "power1.inOut" }, t);
"""


def write_stage(events: list[str]) -> None:
    blinks = " ".join(f"blink({r(t)});" for t in [1.6, 6.3, 9.8, 15.2, 18.6, 24.0, 28.4, 32.0, 45.6, 50.2, 54.8, 59.3, 63.9, 69.0, 73.4,
                                                     78.0, 82.6, 87.1, 92.8, 97.4, 104.6, 113.5, 121.8, 126.1, 130.6, 135.2, 139.7, 144.3, 149.6])
    js = "\n      ".join(events)
    (COMP / "stage.html").write_text(f"""<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; }}
    #s-ground {{ position: absolute; inset: 0; background-color: #F7FAFD;
      background-image: linear-gradient(#D9E6F3 2px, transparent 2px), linear-gradient(90deg, #D9E6F3 2px, transparent 2px); background-size: 60px 60px; }}
    #s-ahmes {{ position: absolute; left: 170px; top: 150px; width: 660px; height: 770px; }}
  </style>
  <div id="root" data-composition-id="stage" data-width="1920" data-height="1080">
    <div id="s-ground" class="clip" data-start="0" data-duration="{r(TOTAL)}" data-track-index="0"></div>
    <div id="s-ahmes" class="clip" data-start="0" data-duration="{r(TOTAL)}" data-track-index="1">{AHMES_SVG.replace("{p}", "s")}</div>
  </div>
  <script>
    (function () {{
      const tl = gsap.timeline({{ paused: true }});
      const show = (sel, on, t, d = 0.12) => tl.to(sel, {{ opacity: on ? 1 : 0, duration: d, ease: "none" }}, t);
      {STAGE_JS}
      tl.fromTo("#s-bob", {{ y: 0 }}, {{ y: -5, duration: 1.1, ease: "sine.inOut", yoyo: true, repeat: {int(TOTAL / 1.1) - 1} }}, 0);
      {blinks}
      {js}
      window.__timelines["stage"] = tl;
    }})();
  </script>
</template>
""")


def write_index(chapters: list[Chapter]) -> None:
    hosts = [f'<div id="stage" data-composition-id="stage" data-composition-src="compositions/stage.html" data-start="0" data-duration="{r(TOTAL)}" '
             f'data-track-index="1" data-track-kind="graphics" data-width="1920" data-height="1080" style="z-index: 1"></div>']
    for i, c in enumerate(chapters):
        hosts.append(f'<div id="{c.id}" data-composition-id="{c.id}" data-composition-src="compositions/{c.id}.html" data-start="{r(c.start)}" '
                     f'data-duration="{r(c.end - c.start)}" data-track-index="{2 + i % 2}" data-track-kind="graphics" data-width="1920" data-height="1080" style="z-index: {2 + i}"></div>')
    audio = []
    for a in sorted(AUDIO, key=lambda x: x["t"]):
        rate = f' data-playback-rate="{a["rate"]}"' if a["rate"] != 1.0 else ""
        fade = f' data-fade-out="{a["fade"]}"' if a.get("fade") else ""
        audio.append(f'<audio id="{a["id"]}" class="clip" src="{a["src"]}" data-start="{r(a["t"])}" data-duration="{r(a["d"])}" '
                     f'data-track-index="{a["track"]}" data-volume="{a["vol"]}"{rate}{fade}></audio>')
    nl = "\n      "
    (HERE / "index.html").write_text(f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #F7FAFD; }}
      #root {{ width: 100%; height: 100%; position: relative; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{r(TOTAL)}" data-width="1920" data-height="1080">
      {nl.join(hosts)}

      {nl.join(audio)}
    </div>
    <script>
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
""")


if __name__ == "__main__":
    build()
    print(f"wrote {len(AUDIO)} audio clips; film {TOTAL} s")
