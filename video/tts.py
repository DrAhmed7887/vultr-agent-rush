"""Generate narrator + child clips with ElevenLabs. Key is read at runtime from ~/.elevenlabs_key, never printed."""
import json, pathlib, sys, urllib.request, urllib.error
KEY = pathlib.Path.home().joinpath(".elevenlabs_key").read_text().strip()
import os
OUT = pathlib.Path(__file__).parent / os.environ.get("AHMES_AUDIO_OUT", "out/work/audio")
VOICES = {"narr": ["JBFqnCBsd6RMkjVDRZzb", "nPczCjzI2devNBz1zQrb"], "child": ["jBpfuIE2acCO8z3wKNLl"], "thoth": ["onwK4e9ZLuTAKqWW03F9", "nPczCjzI2devNBz1zQrb"]}
LINES = json.loads(pathlib.Path(__file__).with_name(os.environ.get("AHMES_LINES", "lines.json")).read_text())

def synth(voice_ids, text, dest):
    for vid in voice_ids:
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{vid}?output_format=mp3_44100_128",
            data=json.dumps({"text": text, "model_id": "eleven_multilingual_v2",
                             "voice_settings": {"stability": 0.55, "similarity_boost": 0.75}}).encode(),
            headers={"xi-api-key": KEY, "Content-Type": "application/json"})
        try:
            dest.write_bytes(urllib.request.urlopen(req, timeout=60).read()); return vid
        except urllib.error.HTTPError as e:
            print("voice failed", vid, e.code, file=sys.stderr)
    return None

OUT.mkdir(parents=True, exist_ok=True)
for name, (who, text) in LINES.items():
    dest = OUT / f"{name}.mp3"
    if dest.exists() and "--force" not in sys.argv: continue
    print(name, who, synth(VOICES[who], text, dest))
