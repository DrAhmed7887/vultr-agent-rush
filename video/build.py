#!/usr/bin/env python3
"""Assemble teach-ahmes-demo.mp4 from raw captures, audio clips, diagram frames and caption PNGs.

Run order: tts.py -> capture.mjs (A,B,C) -> render_assets.mjs -> build.py
Everything lands in out/ (git-ignored).
"""
import glob, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "out"
W = OUT / "work"
AUD = W / "audio"
FR = W / "frames"
CAPS = W / "caps"
CLIPS = W / "clips"
for d in (CAPS, CLIPS):
    d.mkdir(parents=True, exist_ok=True)

cap = json.loads((W / "capture.json").read_text())
raw = {k: sorted(glob.glob(str(W / "raw" / k / "*.webm")), key=os.path.getmtime)[-1] for k in "ABC"}

def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]).strip())

def says(scene, kind):
    return [s["d"] for s in cap["says"][scene] if s["url"].endswith(kind)]

sess = says("A", "/session")[0]
A_WELCOME = sess["skills"]["compare_decimals"]["welcome"]
t_A = [d for d in says("A", "/teach")]
A_RESP1, A_RESP2 = t_A[0]["say"], t_A[1]["say"]
A_DIZZY = says("B", "/teach")[0]["say"]
A_OOM = says("C", "/chip")[0]["say"]

# ---------- audio catalogue: key -> (file, speaker, caption text, tempo)
def L(name):
    return json.loads((ROOT / "lines.json").read_text())[name][1]

AUDIO = {
    "a_welcome": ("a_welcome.mp3", "Ahmes", A_WELCOME, 1.0),
    "a_resp1": ("a_resp1.mp3", "Ahmes", A_RESP1, 1.12),
    "a_resp2": ("a_resp2.mp3", "Ahmes", A_RESP2, 1.0),
    "a_dizzy": ("a_dizzy.mp3", "Ahmes", A_DIZZY, 1.0),
    "a_oom": ("a_oom.mp3", "Ahmes", A_OOM, 1.0),
    "c1": ("c1.mp3", "Child", L("c1"), 1.0),
    "c2": ("c2.mp3", "Child", L("c2"), 1.0),
    "c3": ("c3.mp3", "Child", L("c3"), 1.0),
}
for k in ["n1", "n2", "n3a", "n3b", "n4", "n5a", "n5b", "n6a", "n6b", "n6c", "n6d", "n7", "n8", "n9"]:
    AUDIO[k] = (f"{k}.mp3", "", L(k), 1.0)

def adur(k):
    f, _, _, tempo = AUDIO[k]
    return dur(AUD / f) / tempo

# ---------- beats
M = cap["marks"]
beats = []

def beat(name, video, audio, D=None, pan=False, tail=0.35):
    """video: ('raw', scene, a, b) or ('img', png). audio: [(key, offset)]. D defaults to end of last audio + tail."""
    ends = [off + adur(k) for k, off in audio]
    if D is None:
        D = max(ends) + tail
    beats.append(dict(name=name, video=video, audio=audio, D=D, pan=pan))

# --- Hook
beat("welcome", ("raw", "A", 3.09, 6.55), [("a_welcome", 0.3)], tail=0.5, pan=True)
beat("n1", ("raw", "A", 6.0, 6.58), [("n1", 0.2)], pan=True)
beat("type1", ("raw", "A", M["A"]["type1_start"] - 0.1, M["A"]["type1_end"] + 0.1), [("c1", 0.1)], D=2.7)
beat("wait1", ("raw", "A", M["A"]["type1_end"] + 0.1, M["A"]["resp1"] - 0.1), [], D=2.6)
beat("resp1", ("raw", "A", M["A"]["resp1"] - 0.1, 19.44), [("a_resp1", 0.25)])
beat("n2", ("raw", "A", 19.44, M["A"]["type2_start"] - 0.1), [("n2", 0.2)])
beat("type2", ("raw", "A", M["A"]["type2_start"] - 0.1, M["A"]["type2_end"] + 0.2), [("c2", 0.1)], D=5.1)
beat("wait2", ("raw", "A", M["A"]["type2_end"] + 0.2, M["A"]["resp2"] - 0.1), [], D=2.4)
beat("resp2", ("raw", "A", M["A"]["resp2"] - 0.1, M["A"]["resp2"] + 3.3), [("a_resp2", 0.25)])
beat("n3a", ("raw", "A", M["A"]["resp2"] + 3.3, M["A"]["brain"] - 1.2), [("n3a", 0.2)], D=3.0)
beat("n3b", ("raw", "A", M["A"]["brain"] - 1.2, M["A"]["end"]), [("n3b", 0.2)], tail=0.6)
# --- Fractions / dizzy
beat("n4", ("raw", "B", 3.05, 7.0), [("n4", 0.25)], tail=0.4)
beat("type3", ("raw", "B", M["B"]["type_start"] - 0.1, M["B"]["type_end"] + 0.2), [("c3", 0.1)], D=2.9)
beat("ring", ("raw", "B", M["B"]["click"], M["B"]["stamp"] - 0.15), [("n5a", 0.3)], D=5.3)
beat("stamp", ("raw", "B", M["B"]["stamp"] - 0.15, M["B"]["end"]), [("a_dizzy", 0.3), ("n5b", 5.5)], tail=0.6)
# --- Try to break
beat("hood", ("raw", "C", 3.1, M["C"]["click_oom"]), [("n6a", 0.2)], tail=0.3)
beat("oom", ("raw", "C", M["C"]["click_oom"], M["C"]["click_net"]), [("a_oom", 0.3), ("n6b", 5.7)], tail=0.5)
beat("net", ("raw", "C", M["C"]["click_net"], 22.0), [("n6c", 0.2)], tail=0.5)
beat("log", ("raw", "C", 22.0, M["C"]["end"]), [("n6d", 0.2)], tail=0.7)
# --- Architecture: diagram steps timed by character position in the narration
n7 = AUDIO["n7"][2]
marks_txt = ["Under the hood: the browser talks to Caddy,", " then a FastAPI app on Vultr Cloud Compute in Madrid,", " which starts one container per task.",
             " Every language model call goes to Vultr Serverless Inference, running qwen three point eight, twenty-seven b.",
             " Ahmes's voice is ElevenLabs, reading only his own lines.", " A sweeper removes strays, and every removal is verified."]
assert "".join(marks_txt) == n7, "n7 text mismatch with diagram steps"
total_chars = len(n7)
nd = adur("n7")
cum, starts = 0, []
for t in marks_txt:
    starts.append(0.25 + nd * cum / total_chars)
    cum += len(t)
starts[0] = 0.0
for i in range(6):
    s_i = starts[i]
    e_i = starts[i + 1] if i < 5 else 0.25 + nd + 0.9
    off = 0.25 - s_i  # n7 offset relative to this beat's start (so the audio clock stays continuous)
    beats.append(dict(name=f"arch{i+1}", video=("img", str(FR / f"diagram{i+1}.png")), audio=[("n7", off)] if i == 0 else [],
                      D=e_i - s_i, pan=False, audio_global_hint=(i == 0)))
# --- Close
beat("quote", ("img", str(FR / "end_quote.png")), [("n8", 0.5)], tail=0.9)
beat("url", ("img", str(FR / "end_url.png")), [("n9", 0.5)], D=adur("n9") + 2.6)

# ---------- caption chunks
def chunks(text, maxlen=92):
    sents = re.split(r"(?<=[.!?:])[\"”]?\s+", text)  # split at sentence ends, never inside 0.45
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

# global timeline
T = 0.0
for b in beats:
    b["T0"] = T
    T += b["D"]
TOTAL = T

events = []   # (key, global_start)
caps = []     # (speaker, text, gstart, gend)
for b in beats:
    for k, off in b["audio"]:
        g = b["T0"] + off
        events.append((k, g))
        f, who, text, tempo = AUDIO[k]
        d = adur(k)
        if who == "Ahmes":
            parts = chunks(f"“{text}”", 78)
        elif who == "Child":
            parts = chunks(f"“{text}”", 78)
        else:
            shown = (text.replace("qwen three point eight, twenty-seven b", "qwen3.8-27b").replace("sixty-four megabytes", "64 megabytes")
                     .replace("at three seconds", "at 3 seconds"))
            parts = chunks(shown)
        tot = sum(len(p) for p in parts)
        t = g
        for p in parts:
            seg = d * len(p) / tot
            caps.append((who, p, t, t + seg))
            t += seg
# the diagram beats carry the n7 audio from beat 1 only; its global start is T0 of arch1 + offset
SPEAKER_NOTE = {"Ahmes": "Ahmes", "Child": "Child types"}

# ---------- render caption PNGs (node + Playwright; the python shim is not installed)
caps_manifest = [dict(i=i, who=who, text=text, a=a, e=e, file=str(CAPS / f"cap{i:03d}.png")) for i, (who, text, a, e) in enumerate(caps)]
(W / "caps.json").write_text(json.dumps(caps_manifest))
r = subprocess.run(["node", str(ROOT / "render_caps.mjs"), str(W / "caps.json")], capture_output=True, text=True, cwd=ROOT)
if r.returncode:
    print(r.stderr[-1500:]); sys.exit(1)

# ---------- video clips per beat
def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(" ".join(map(str, cmd))[:400]); print(r.stderr[-1500:]); sys.exit(1)

clip_files = []
for bi, b in enumerate(beats):
    D = b["D"]
    out = CLIPS / f"b{bi:02d}_{b['name']}.mp4"
    my_caps = [c for c in caps_manifest if c["a"] < b["T0"] + D and c["e"] > b["T0"]]
    inputs, filt = [], []
    if b["video"][0] == "raw":
        _, sc, a, bb = b["video"]
        rl = max(bb - a, 0.1)
        ratio = rl / D           # >1 speed up, <1 slow down
        speed = ratio if ratio >= 0.5 else 0.5   # never slower than 0.5x; freeze the rest
        inputs += ["-ss", f"{a:.3f}", "-t", f"{rl:.3f}", "-i", raw[sc]]
        v = f"[0:v]setpts=PTS/{speed:.4f},fps=30,scale=1920:1080:flags=lanczos"
        if b["pan"]:
            v += f",scale=2016:1134,crop=1920:1080:x='(in_w-out_w)*0.5*t/{D:.2f}':y='(in_h-out_h)*0.1*t/{D:.2f}'"
        v += f",tpad=stop_mode=clone:stop_duration={D:.3f},trim=duration={D:.3f},setpts=PTS-STARTPTS,format=yuv420p[v0]"
        filt.append(v)
    else:
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{D:.3f}", "-i", b["video"][1]]
        filt.append(f"[0:v]scale=1920:1080,fps=30,format=yuv420p[v0]")
    last = "v0"
    for ci, c in enumerate(my_caps):
        inputs += ["-loop", "1", "-framerate", "30", "-t", f"{D:.3f}", "-i", c["file"]]
        s = max(c["a"] - b["T0"], 0); e = min(c["e"] - b["T0"] + 0.1, D)
        filt.append(f"[{last}][{ci+1}:v]overlay=0:0:enable='between(t,{s:.3f},{e:.3f})':format=auto[v{ci+1}]")
        last = f"v{ci+1}"
    filt.append(f"[{last}]format=yuv420p[vout]")
    run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(filt), "-map", "[vout]", "-t", f"{D:.3f}",
         "-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", "-an", str(out)])
    clip_files.append(out)
    print("clip", bi, b["name"], f"{D:.2f}s")

lst = W / "concat.txt"
lst.write_text("".join(f"file '{c}'\n" for c in clip_files))
vid = W / "video_only.mp4"
run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vid)])

# ---------- audio mix
ev = []
for b in beats:
    for k, off in b["audio"]:
        ev.append((k, b["T0"] + off))
# n7 spans the diagram beats: its start is arch1 T0 + (0.25 - starts[0]) = T0 + 0.25
ins, fl, labels = [], [], []
for i, (k, g) in enumerate(ev):
    f, who, _, tempo = AUDIO[k]
    ins += ["-i", str(AUD / f)]
    vol = {"Ahmes": 1.0, "Child": 0.95}.get(who, 1.0)
    chain = f"[{i}:a]aresample=44100,"
    if tempo != 1.0:
        chain += f"atempo={tempo},"
    chain += f"loudnorm=I=-16:TP=-1.5:LRA=7,volume={vol},adelay={int(g*1000)}|{int(g*1000)}[a{i}]"
    fl.append(chain); labels.append(f"[a{i}]")
fl.append("".join(labels) + f"amix=inputs={len(ev)}:normalize=0:dropout_transition=0,apad=whole_dur={TOTAL:.3f},atrim=0:{TOTAL:.3f}[aout]")
aud = W / "mix.wav"
run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fl), "-map", "[aout]", "-ar", "44100", "-ac", "2", str(aud)])

final = OUT / "teach-ahmes-demo.mp4"
run(["ffmpeg", "-v", "error", "-y", "-i", str(vid), "-i", str(aud), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", str(final)])
print("TOTAL", round(TOTAL, 2), "->", final)

# ---------- script manifest for SCRIPT.md
(W / "timeline.json").write_text(json.dumps(dict(
    total=TOTAL,
    beats=[dict(name=b["name"], t0=b["T0"], d=b["D"]) for b in beats],
    captions=[dict(who=c["who"], text=c["text"], a=c["a"], e=c["e"]) for c in caps_manifest]), indent=1))
