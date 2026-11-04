#!/usr/bin/env python3
"""v2 demo: assemble out/teach-ahmes-demo.mp4 from the capture2.mjs scenes, Ahmes's real voice clips,
ElevenLabs narration (lines2.json), score badges and stills. Order follows the director's notes:
hook, cure, dizzy stop, judges' evidence, Thoth, refusal, full cure, breadth, architecture, report, close.

Run: node capture2.mjs -> tts.py (AHMES_LINES=lines2.json) -> node render_assets2.mjs -> python3 build2.py
"""
import glob, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "out"
W = OUT / "work2"
AUD, FR, CAPS, CLIPS = W / "audio", W / "frames", W / "caps", W / "clips"
for d in (CAPS, CLIPS):
    d.mkdir(parents=True, exist_ok=True)

cap = json.loads((W / "capture.json").read_text())
M = cap["marks"]
raw = {k: sorted(glob.glob(str(W / "raw" / k / "*.webm")), key=os.path.getmtime)[-1] for k in "DFYH"}
LINES = json.loads((ROOT / "lines2.json").read_text())


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).strip())


# ---------- what Ahmes said in each captured clip (voice id -> text), from the API replies
said: dict[str, str] = {}
def walk(x):
    if isinstance(x, dict):
        v = x.get("voice")
        if isinstance(v, dict) and v.get("id"):
            said[v["id"]] = x.get("say") or x.get("why") or said.get(v["id"], "")
        for y in x.values():
            walk(y)
    elif isinstance(x, list):
        for y in x:
            walk(y)
for sc in cap["api"].values():
    for a in sc:
        walk(a["d"])

def clip(scene, near):
    """Ahmes's clip fetched closest to raw time `near` in a scene: (key, raw time)."""
    v = min(cap["voice"][scene], key=lambda c: abs(c["t"] - near))
    key = f"ah_{scene}_{v['t']:.1f}"
    AUDIO[key] = (v["file"], "Ahmes", said.get(v["id"], ""), 1.0)
    return key, v["t"]


AUDIO = {}
for k, (who, text) in LINES.items():
    AUDIO[k] = (str(AUD / f"{k}.mp3"), {"narr": "", "child": "Child", "thoth": "Thoth"}[who], text, 1.0)

def adur(k):
    return dur(AUDIO[k][0]) / AUDIO[k][3]


beats = []
def beat(name, video, audio, D=None, tail=0.35, overlays=()):
    """video: ('raw', scene, a, b) | ('img', png). audio: [(key, offset)]. overlays: [(png, start, end)] in beat time."""
    ends = [off + adur(k) for k, off in audio] or [0]
    beats.append(dict(name=name, video=video, audio=audio, D=D if D is not None else max(ends) + tail, overlays=list(overlays)))

def ah(scene, near, a):
    """Ahmes's clip near raw time `near`, offset into a beat that starts at raw time `a` (1x speed)."""
    k, t = clip(scene, near)
    return (k, max(t - a, 0) + 0.15)

D, F, Y, H = M["D"], M["F"], M["Y"], M["H"]
B24, B40 = str(FR / "badge24.png"), str(FR / "badge40.png")

# 1. Hook: his homework mistake, marked wrong, the number line
a = D["check"] - 0.3
beat("hook", ("raw", "D", a, D["marked"] + 3.6), [ah("D", D["check"], a), ("n1", 3.3)], D=9.2)
# 2. The cure, part one
a = D["teach_screen"]
beat("teach1", ("raw", "D", a, D["t1_shown"]), [("c1", 1.0), ("n2", 3.0)], tail=0.2)
a = D["t1_shown"]
beat("retry1", ("raw", "D", a, D["q1_click"]), [ah("D", D["t1_shown"], a)], D=3.4)
# 3. The quiz shows what she didn't say: 24 / 40
beat("quiz1", ("raw", "D", D["q1_click"], D["hw2"] - 0.5), [("n3", 0.5)], tail=0.6, overlays=[(B24, 1.2, 99)])
# 4. A rule that never ends: the sandbox stops him
a = F["t1_typed"] - 2.6
beat("dizzy_type", ("raw", "F", a, F["t1_click"] + 0.2), [("c3", 0.3)], D=3.4)
beat("dizzy_wait", ("raw", "F", F["t1_click"] + 0.2, F["t1_resp"] - 0.1), [], D=2.6)   # the box runs for 3 s: sped up
a = F["t1_resp"] - 0.1
dz = ah("F", F["t1_shown"], a)
beat("dizzy", ("raw", "F", a, F["end"]), [dz, ("n4", dz[1] + adur(dz[0]) + 0.3)], tail=0.5)
# 5. For the judges: the Vultr calls, then try to break him
beat("pipeline", ("raw", "H", H["pipeline"] - 1.0, H["hood"]), [("n5", 0.3)], tail=0.4)
beat("break", ("raw", "H", H["hood"] - 0.3, H["log"] + 1.5), [("n6", 0.4)], tail=0.6)
# 6. Thoth steps in when she's stuck
beat("stuck", ("raw", "D", D["hw2"], D["t3_resp"]), [("n7", 0.3)], tail=0.2)
beat("thoth", ("raw", "D", D["t3_resp"], D["t3_shown"] + 6.0), [("thoth", 0.6)], tail=0.8)
# 7. An answer is not a rule
beat("refuse", ("raw", "D", D["t_ans_typed"] - 1.6, D["no_rule"] + 3.0), [("c_ans", 0.2), ("n8", 3.4)], tail=0.4)
# 8. The full rule: 40 / 40 and the seal
a = D["t4_typed"] - 3.3
beat("teach4", ("raw", "D", a, D["t4_shown"]), [("c4", 0.2)], D=7.5)
# played at 1x so Ahmes's lines stay in step with the screen; the narration fits between his two lines
a = D["t4_shown"]
r4, won = ah("D", D["t4_shown"], a), ah("D", D["q2_done"] + 0.5, a)
beat("cured", ("raw", "D", a, D["win"] + 2.0), [r4, ("n9", max(r4[1] + adur(r4[0]) + 0.3, won[1] - adur("n9") - 0.3)), won],
     D=min(D["win"] + 2.0 - a, won[1] + adur(won[0]) + 0.9), overlays=[(B40, D["q2_done"] - a, 99)])
# 9. Breadth, architecture, report
beat("year6", ("raw", "Y", Y["map"] - 0.5, Y["end"]), [("n10", 0.3)], tail=0.5)
beat("arch", ("img", str(FR / "diagram.png")), [("n_arch", 0.4)], tail=0.8)
beat("report", ("raw", "D", D["report"] - 0.8, D["end"]), [("n11", 0.3)], tail=0.5)
# 10. Close on the receipt, then the URL
beat("receipt", ("raw", "H", H["facts"] + 0.2, H["facts"] + 0.3, (200, 300, 960, 540)), [("n12", 0.6)], tail=1.2)
beat("url", ("img", str(FR / "end_url.png")), [], D=3.2)


def chunks(text, maxlen=92):
    sents = re.split(r"(?<=[.!?:])[\"”]?\s+", text)
    out = []
    for s in (x.strip() for x in sents if x.strip()):
        if out and len(out[-1]) + len(s) + 1 <= maxlen:
            out[-1] += " " + s
        else:
            out.append(s)
    final = []
    for c in out:
        while len(c) > maxlen + 20:
            cut = c.rfind(",", 0, maxlen + 10)
            cut = cut if cut > 30 else c.rfind(" ", 0, maxlen)
            final.append(c[:cut + 1].strip()); c = c[cut + 1:].strip()
        final.append(c)
    return final


T = 0.0
for b in beats:
    b["T0"] = T; T += b["D"]
TOTAL = T

caps = []
for b in beats:
    for k, off in b["audio"]:
        g = b["T0"] + off
        _, who, text, _ = AUDIO[k]
        if not text:
            continue
        shown = text.replace("sixty-four megabytes", "64 MB").replace("Twenty-four out of forty", "24 out of 40").replace("Forty out of forty", "40 out of 40")
        parts = chunks(f"“{shown}”", 78) if who else chunks(shown)
        d, tot, t = adur(k), sum(len(p) for p in parts), g
        for p in parts:
            seg = d * len(p) / tot
            caps.append((who, p, t, min(t + seg, b["T0"] + b["D"])))
            t += seg

manifest = [dict(i=i, who=w, text=x, a=a, e=e, file=str(CAPS / f"cap{i:03d}.png")) for i, (w, x, a, e) in enumerate(caps)]
(W / "caps.json").write_text(json.dumps(manifest))
r = subprocess.run(["node", str(ROOT / "render_caps2.mjs"), str(W / "caps.json")], capture_output=True, text=True, cwd=ROOT)
if r.returncode:
    print(r.stderr[-1500:]); sys.exit(1)


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(map(str, cmd))[:400]); print(r.stderr[-1500:]); sys.exit(1)


clip_files = []
for bi, b in enumerate(beats):
    Dd = b["D"]
    out = CLIPS / f"b{bi:02d}_{b['name']}.mp4"
    mine = [c for c in manifest if c["a"] < b["T0"] + Dd and c["e"] > b["T0"]]
    inputs, filt = [], []
    if b["video"][0] == "raw":
        _, sc, a, bb, *crop = b["video"]
        rl = max(bb - a, 0.1)
        speed = max(rl / Dd, 0.5)
        inputs += ["-ss", f"{a:.3f}", "-t", f"{rl:.3f}", "-i", raw[sc]]
        zoom = f"crop={crop[0][2]}:{crop[0][3]}:{crop[0][0]}:{crop[0][1]}," if crop else ""
        filt.append(f"[0:v]setpts=PTS/{speed:.4f},fps=30,{zoom}scale=1920:1080:flags=lanczos,tpad=stop_mode=clone:stop_duration={Dd:.3f},"
                    f"trim=duration={Dd:.3f},setpts=PTS-STARTPTS,format=yuv420p[v0]")
    else:
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{Dd:.3f}", "-i", b["video"][1]]
        filt.append("[0:v]scale=1920:1080,fps=30,format=yuv420p[v0]")
    last, n = "v0", 1
    layers = [(png, s, e) for png, s, e in b["overlays"]] + [(c["file"], max(c["a"] - b["T0"], 0), min(c["e"] - b["T0"] + 0.1, Dd)) for c in mine]
    for png, s, e in layers:
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{Dd:.3f}", "-i", png]
        filt.append(f"[{last}][{n}:v]overlay=0:0:enable='between(t,{s:.3f},{min(e, Dd):.3f})':format=auto[v{n}]")
        last = f"v{n}"; n += 1
    filt.append(f"[{last}]format=yuv420p[vout]")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[vout]", "-t", f"{Dd:.3f}",
         "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-an", str(out)])
    clip_files.append(out)
    print(f"clip {bi:02d} {b['name']:12s} {b['T0']:6.1f}s +{Dd:.1f}s")

(W / "concat.txt").write_text("".join(f"file '{c}'\n" for c in clip_files))
vid = W / "video_only.mp4"
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(W / "concat.txt"), "-c", "copy", str(vid)])

ins, fl, labels, i = [], [], [], 0
for b in beats:
    for k, off in b["audio"]:
        g = b["T0"] + off
        f, who, _, tempo = AUDIO[k]
        ins += ["-i", f]
        vol = {"Ahmes": 1.0, "Child": 0.95, "Thoth": 1.0}.get(who, 1.0)
        fl.append(f"[{i}:a]aresample=44100,loudnorm=I=-16:TP=-1.5:LRA=7,volume={vol},adelay={int(g*1000)}|{int(g*1000)}[a{i}]")
        labels.append(f"[a{i}]"); i += 1
fl.append("".join(labels) + f"amix=inputs={i}:normalize=0:dropout_transition=0,apad=whole_dur={TOTAL:.3f},atrim=0:{TOTAL:.3f}[aout]")
aud = W / "mix.wav"
run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fl), "-map", "[aout]", "-ar", "44100", "-ac", "2", str(aud)])

final = OUT / "teach-ahmes-demo.mp4"
run(["ffmpeg", "-v", "error", "-y", "-i", str(vid), "-i", str(aud), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(final)])
(W / "timeline.json").write_text(json.dumps(dict(total=TOTAL, beats=[dict(name=b["name"], t0=b["T0"], d=b["D"]) for b in beats],
                                                 captions=[dict(who=c["who"], text=c["text"], a=c["a"], e=c["e"]) for c in manifest]), indent=1))
print("TOTAL", round(TOTAL, 2), "->", final)
