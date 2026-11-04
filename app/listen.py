"""A child's voice and words, checked on Vultr Serverless Inference before anything else.

hear(): Nemotron omni turns a short recording into text. It is told the child is explaining
maths, which is why it hears "tenths" where plain speech-to-text heard "tents".
safe(): Nemotron content safety screens the sentence (personal details, unkind words)
before the compiler sees it. Both run on Vultr; neither result is stored.
"""
from __future__ import annotations

import base64
import os

import httpx

from .compiler import BASE_URL, _api_key

OMNI_MODEL = os.environ.get("VULTR_OMNI_MODEL", "nemotron-3-nano-omni-30b-a3b-reasoning")
SAFETY_MODEL = os.environ.get("VULTR_SAFETY_MODEL", "nemotron-3.5-content-safety")
MAX_AUDIO_BYTES = 640_000          # about 20 s of 16 kHz mono 16-bit WAV

HEAR_PROMPT = ("You transcribe a child explaining a maths rule (decimals or fractions) to a robot. "
               "Maths words they may use: tenths, hundredths, thousandths, digits, decimal point, dot, "
               "tops, bottoms, numerator, denominator, multiply, add, same, bigger, smaller, equal. "
               "Write exactly the words said, nothing else. If nothing is said, write nothing.")


def hear(wav: bytes) -> str:
    """Return what the child said, or raise ValueError for audio we won't send."""
    if len(wav) > MAX_AUDIO_BYTES or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        raise ValueError("Send a short WAV recording.")
    body = {"model": OMNI_MODEL, "temperature": 0, "max_tokens": 400, "reasoning_effort": "low",
            "messages": [{"role": "system", "content": HEAR_PROMPT},
                         {"role": "user", "content": [{"type": "input_audio", "input_audio": {
                             "data": base64.b64encode(wav).decode(), "format": "wav"}}]}]}
    r = httpx.post(f"{BASE_URL}/chat/completions", json=body, timeout=25,
                   headers={"Authorization": f"Bearer {_api_key()}"})
    r.raise_for_status()
    text = (r.json()["choices"][0]["message"].get("content") or "").strip().strip('"')
    return " ".join(text.split())[:500]


def safe(sentence: str) -> str:
    """'safe', 'unsafe', or 'unchecked' if the safety model can't be reached (the guard and
    sandbox still apply either way)."""
    try:
        r = httpx.post(f"{BASE_URL}/chat/completions", timeout=10,
                       headers={"Authorization": f"Bearer {_api_key()}"},
                       json={"model": SAFETY_MODEL, "max_tokens": 40, "messages": [{"role": "user", "content": sentence}]})
        r.raise_for_status()
        verdict = (r.json()["choices"][0]["message"].get("content") or "").lower()
    except Exception:  # noqa: BLE001
        return "unchecked"
    return "unsafe" if "user safety: unsafe" in verdict else "safe"
