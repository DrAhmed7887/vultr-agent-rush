"""Make the film's music bed and extra sound effects with ElevenLabs, then loudness-normalise every voice.

The key is read from the Keychain item ELEVENLABS_API_KEY (falling back to ~/.elevenlabs_key) and never printed.
Existing files are kept; pass --force to remake them.
"""
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).parent
RAW = HERE / "assets" / "audio" / "raw"
NORM = HERE / "assets" / "audio" / "norm"
API = "https://api.elevenlabs.io/v1"

SFX = {
    "whoosh_a": ("Quick soft air whoosh of a tablet sliding across a desk", 0.7),
    "whoosh_b": ("Short gentle swish of paper card flying past, light", 0.6),
    "pop": ("Small satisfying cartoon pop of a sticker landing", 0.5),
}
MUSIC_PROMPT = (
    "Playful curious children's cartoon underscore for a short film, pizzicato strings, marimba and soft clarinet, "
    "104 bpm, light and warm, sits under narration, no vocals, a calm tense middle section with ticking, "
    "then bright and happy again, ends on a resolved final bar"
)
MUSIC_MS = 156000


def read_key() -> str:
    found = subprocess.run(["security", "find-generic-password", "-s", "ELEVENLABS_API_KEY", "-w"],
                           capture_output=True, text=True)
    if found.returncode == 0 and found.stdout.strip():
        return found.stdout.strip()
    return pathlib.Path.home().joinpath(".elevenlabs_key").read_text().strip()


def post(key: str, path: str, body: dict, dest: pathlib.Path) -> bool:
    req = urllib.request.Request(f"{API}{path}", data=json.dumps(body).encode(),
                                 headers={"xi-api-key": key, "Content-Type": "application/json"})
    try:
        dest.write_bytes(urllib.request.urlopen(req, timeout=300).read())
        return True
    except urllib.error.HTTPError as e:
        print(f"failed {dest.name}: HTTP {e.code} {e.read()[:200]!r}", file=sys.stderr)
        return False


def wanted(dest: pathlib.Path) -> bool:
    return "--force" in sys.argv or not dest.exists()


def normalise_voices() -> None:
    """Every spoken clip to -16 LUFS, -1.5 dBTP, so the HTML can use data-volume 1."""
    NORM.mkdir(parents=True, exist_ok=True)
    for src in sorted(RAW.glob("*.mp3")):
        if src.stem.startswith(("sfx_", "music", "score")):
            continue
        dest = NORM / f"{src.stem}.wav"
        if wanted(dest):
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af",
                            "loudnorm=I=-16:TP=-1.5:LRA=7", "-ar", "48000", str(dest)], check=True)


def main() -> None:
    key = read_key()
    for name, (prompt, secs) in SFX.items():
        dest = RAW / f"sfx_{name}.mp3"
        if wanted(dest):
            print(name, post(key, "/sound-generation", {"text": prompt, "duration_seconds": secs, "prompt_influence": 0.6}, dest))
    dest = RAW / "score.mp3"
    if wanted(dest):
        print("score", post(key, "/music", {"prompt": MUSIC_PROMPT, "music_length_ms": MUSIC_MS}, dest))
    normalise_voices()


if __name__ == "__main__":
    main()
