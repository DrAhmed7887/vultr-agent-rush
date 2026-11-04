"""Make the opening's voices, sound effects and music with ElevenLabs.

The key is read at runtime from the Keychain item ELEVENLABS_API_KEY (it has the
sound-effects and music permissions), falling back to ~/.elevenlabs_key. It is never printed.
Existing files are kept; pass --force to remake them.
"""
import json
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request


def read_key() -> str:
    found = subprocess.run(
        ["security", "find-generic-password", "-s", "ELEVENLABS_API_KEY", "-w"],
        capture_output=True, text=True,
    )
    if found.returncode == 0 and found.stdout.strip():
        return found.stdout.strip()
    return pathlib.Path.home().joinpath(".elevenlabs_key").read_text().strip()


KEY = read_key()
OUT = pathlib.Path(__file__).parent / "assets" / "audio"
API = "https://api.elevenlabs.io/v1"

AHMES = "IKne3meq5aSn9XLyUdCD"  # "Charlie", Ahmes's in-app voice
CHILD = "jBpfuIE2acCO8z3wKNLl"  # stock voice, synthetic child; never a real child

VOICE = {
    "a1": (AHMES, "Easy! Forty-five is more than five, so zero point four five is bigger."),
    "c1": (CHILD, "Look at the tenths first."),
    "a2": (AHMES, "Ohh! Five tenths beats four tenths."),
    "c2": (CHILD, "Keep doubling both bottoms until they're the same."),
    "a3": (AHMES, "Whoa, I got dizzy! My brain kept going round and round."),
}

SFX = {
    "pen": ("A felt-tip marker quickly drawing a circle on paper, short and close", 1.2),
    "stamp": ("Loud close-up thud of a teacher slamming a big rubber stamp onto paper on a desk, one hit", 1.0),
    "glyphs": ("Soft magical paper rustle swirling upward, light and quick", 1.5),
    "spin": ("Cartoon robot spinning faster and faster, wobbling mechanical whirr", 3.0),
    "lock": ("A heavy glass box slamming shut and locking with a solid clunk", 1.0),
    "lift": ("A glass lid lifting off with a short airy whoosh", 0.8),
}

MUSIC_PROMPT = (
    "Playful curious children's cartoon underscore, pizzicato strings and marimba, "
    "light and bouncy at 104 bpm, no vocals, gentle build, ends on a resolved bar"
)


def post(path: str, body: dict, dest: pathlib.Path) -> bool:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode(),
        headers={"xi-api-key": KEY, "Content-Type": "application/json"},
    )
    try:
        dest.write_bytes(urllib.request.urlopen(req, timeout=180).read())
        return True
    except urllib.error.HTTPError as e:
        print(f"failed {dest.name}: HTTP {e.code} {e.read()[:200]!r}", file=sys.stderr)
        return False


def wanted(dest: pathlib.Path) -> bool:
    return "--force" in sys.argv or not dest.exists()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, (voice, text) in VOICE.items():
        dest = OUT / f"{name}.mp3"
        if wanted(dest):
            body = {
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.35},
            }
            print(name, post(f"/text-to-speech/{voice}?output_format=mp3_44100_128", body, dest))
    for name, (prompt, secs) in SFX.items():
        dest = OUT / f"sfx_{name}.mp3"
        if wanted(dest):
            body = {"text": prompt, "duration_seconds": secs, "prompt_influence": 0.6}
            print(name, post("/sound-generation", body, dest))
    dest = OUT / "music.mp3"
    if wanted(dest):
        body = {"prompt": MUSIC_PROMPT, "music_length_ms": 26000}
        print("music", post("/music", body, dest))


if __name__ == "__main__":
    main()
