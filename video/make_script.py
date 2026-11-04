#!/usr/bin/env python3
"""Write out/SCRIPT.md (narration + captions with timings) from out/work/timeline.json."""
import json, pathlib
root = pathlib.Path(__file__).parent / "out"
t = json.loads((root / "work" / "timeline.json").read_text())
mmss = lambda s: f"{int(s // 60)}:{s % 60:04.1f}"
scenes = [("Hook", 0, "n3a"), ("Words to code", "n3a", "n4"), ("The dizzy moment", "n4", "hood"),
          ("Try to break Ahmes", "hood", "arch1"), ("Architecture", "arch1", "quote"), ("Close", "quote", None)]
starts = {b["name"]: b["t0"] for b in t["beats"]}
def at(x): return 0 if x == 0 else (t["total"] + 1 if x is None else starts[x])
lines = ["# Teach Ahmes: demo script", "",
         f"Runtime {mmss(t['total'])}. Voices: ElevenLabs only, synthetic. Ahmes = Charlie (the app's own voice, clips from the live app), narrator = George, child = Gigi. Screen = the live site at https://64-177-33-215.sslip.io (light mode), recorded with Playwright. Captions are burned in.", ""]
for name, a, b in scenes:
    lo, hi = at(a), at(b)
    lines += [f"## {name} ({mmss(lo)} to {mmss(min(hi, t['total']))})", "", "| Time | Speaker | Caption / line |", "|---|---|---|"]
    for c in t["captions"]:
        if lo <= c["a"] < hi:
            who = {"Ahmes": "Ahmes", "Child": "Child (typed + voiced)"}.get(c["who"], "Narrator")
            lines.append(f"| {mmss(c['a'])} to {mmss(c['e'])} | {who} | {c['text']} |")
    lines.append("")
lines += ["## Claim check", "",
          "- Scores (24/40, 40/40, 6/40 before the stop, stopped at about 3 s, OOM at 64 MB, Network is unreachable) are the values returned live by the app during recording; they match the README's measured results.",
          "- No use of: proven, cured children, first, safe for kids, HIPAA. The film says prototype; the end card says learning outcomes untested.",
          "- Ahmes lines are the app's own template lines (the app only voices Ahmes). Child and narrator voices are synthetic; no real children or people."]
(root / "SCRIPT.md").write_text("\n".join(lines) + "\n")
