"""Ahmes's voice: ElevenLabs, cached by a hash of the text. Only Ahmes's template lines are
sent, never the child's words. Falls back to Vultr's TTS if ElevenLabs is unavailable."""
from __future__ import annotations

import hashlib
import os
import threading
import time
from pathlib import Path

import httpx

CACHE = Path(os.environ.get("AHMES_AUDIO_CACHE", "/var/lib/ahmes/audio"))
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "IKne3meq5aSn9XLyUdCD")   # "Charlie", a stock voice
EL_MODEL = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5")
VULTR_TTS_MODEL = os.environ.get("VULTR_TTS_MODEL", "auk-flash")
# A cap on new (uncached) ElevenLabs characters per day, so a flood of unusual answers can't burn
# the quota or fill the disk. Over the cap, new lines use Vultr's TTS; past both caps, no audio.
DAILY_CHARS = int(os.environ.get("AHMES_TTS_DAILY_CHARS", "6000"))   # new lines only; cached lines are free
_spent = {"day": "", "elevenlabs": 0, "vultr": 0}
_spent_lock = threading.Lock()


def _take(provider: str, n: int) -> bool:
    day = time.strftime("%Y-%m-%d", time.gmtime())
    with _spent_lock:
        if _spent["day"] != day:
            _spent.update(day=day, elevenlabs=0, vultr=0)
        if _spent[provider] + n > DAILY_CHARS:
            return False
        _spent[provider] += n
        return True


def _path(text: str) -> tuple[str, Path]:
    h = hashlib.sha256(f"{VOICE_ID}|{text}".encode()).hexdigest()[:20]
    return h, CACHE / f"{h}.mp3"


def speak(text: str) -> dict:
    """Return {"id": hash, "provider": ...} for an mp3 served at /audio/<id>.mp3, or {} on failure."""
    if not text:
        return {}
    CACHE.mkdir(parents=True, exist_ok=True)
    h, path = _path(text)
    if path.exists() and path.stat().st_size > 0:
        return {"id": h, "provider": "cache"}
    if len(text) > 400:
        return {}
    key = os.environ.get("ELEVENLABS_API_KEY", "")
    if key and _take("elevenlabs", len(text)):
        try:
            r = httpx.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_64",
                           headers={"xi-api-key": key}, json={"text": text, "model_id": EL_MODEL}, timeout=20)
            if r.status_code == 200 and r.content:
                path.write_bytes(r.content)
                return {"id": h, "provider": "elevenlabs"}
        except httpx.HTTPError:
            pass
    vkey = os.environ.get("VULTR_INFERENCE_API_KEY", "")
    if vkey and _take("vultr", len(text)):
        try:
            r = httpx.post("https://api.vultrinference.com/v1/audio/speech", headers={"Authorization": f"Bearer {vkey}"},
                           json={"model": VULTR_TTS_MODEL, "input": text, "voice": "default"}, timeout=30)
            if r.status_code == 200 and r.content:
                path.write_bytes(r.content)
                return {"id": h, "provider": "vultr-backup"}
        except httpx.HTTPError:
            pass
    return {}


def file_for(audio_id: str) -> Path | None:
    if not audio_id.isalnum() or len(audio_id) != 20:
        return None
    p = CACHE / f"{audio_id}.mp3"
    return p if p.exists() else None
