#!/usr/bin/env python3
"""4x4 contact sheet of evenly spaced frames from the final video -> out/contact-sheet.png"""
import subprocess, pathlib
root = pathlib.Path(__file__).parent / "out"; v = root / "teach-ahmes-demo.mp4"
d = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",str(v)]))
tmp = root / "work" / "sheet"; tmp.mkdir(exist_ok=True, parents=True)
for i in range(16):
    t = (i + 0.5) * d / 16
    subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{t:.2f}","-i",str(v),"-frames:v","1","-vf","scale=480:270",str(tmp/f"f{i:02d}.png")],check=True)
subprocess.run(["ffmpeg","-v","error","-y","-framerate","1","-i",str(tmp/"f%02d.png"),"-vf","tile=4x4","-frames:v","1",str(root/"contact-sheet.png")],check=True)
