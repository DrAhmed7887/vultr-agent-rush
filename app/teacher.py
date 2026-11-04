"""Thoth, the teacher: a second, open model on Vultr Serverless Inference that watches every
lesson and steps in when needed.

audit(): after the compiler writes Ahmes's new code, Thoth checks it against the child's words.
         If the code ignores some of the words, or does maths the child never said, Thoth says so,
         and the child can ask Ahmes to listen again (the compiler retries with Thoth's note).
hint():  when the child is stuck (the same homework is still wrong after two tries, or Ahmes keeps
         getting dizzy), Thoth asks one short question that points at the picture. Never the answer.

Thoth runs on a different model family (GLM) from the compiler (Qwen), so the code is checked
by a model that didn't write it. Anything Thoth quotes must really be in the child's sentence.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import time

import httpx

from .compiler import BASE_URL, _api_key, _norm

TEACHER_MODEL = os.environ.get("VULTR_TEACHER_MODEL", "glm-5.3")

AUDIT_SYSTEM = """You are Thoth, the teacher watching a child teach a robot called Ahmes. A compiler turned the child's words into Ahmes's Python code.
Check ONE thing: does the NEW code do what the child's words say, no more and no less? Ignore whether the maths is correct; wrong rules are fine if the child said them. Code kept from OLD CODE for things the child didn't mention is fine.
Only flag a difference that would change what Ahmes answers on some problem. In this game every decimal has whole number 0, so where the whole-number check sits never matters. If the new code clearly has a step for some words, those words are not missed.
Before deciding, try the new code in your head on two or three small examples that the child's words talk about (for example equal-looking numbers if the child mentions "equal" or "the same"), and compare with what the words say should happen.
Reply JSON only: {"faithful": true|false, "missed": "<exact words of the child that the new code ignores, or empty>", "added": "<short plain description of anything the new code does that the child never said, or empty>"}"""

HINT_SYSTEM = """You are Thoth, a kind teacher helping a 10-year-old who is teaching a robot called Ahmes. The child is stuck.
Write ONE short hint for the child (at most 25 words): a question or a nudge that points at the picture or at the place where Ahmes goes wrong.
Never give the whole rule or the answer. Never write code. Use simple words a 10-year-old knows. Reply with the hint only."""


def _chat(system: str, user: str, json_mode: bool, max_tokens: int) -> tuple[str, int]:
    body = {"model": TEACHER_MODEL, "temperature": 0, "max_tokens": max_tokens, "reasoning_effort": "low",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    t0 = time.monotonic()
    r = httpx.post(f"{BASE_URL}/chat/completions", json=body, timeout=20, headers={"Authorization": f"Bearer {_api_key()}"})
    r.raise_for_status()
    return (r.json()["choices"][0]["message"].get("content") or "").strip(), int((time.monotonic() - t0) * 1000)


def _audit_once(user: str, sentence: str) -> dict | None:
    try:
        text, ms = _chat(AUDIT_SYSTEM, user, True, 1500)
        obj = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception:  # noqa: BLE001
        return None
    missed = str(obj.get("missed") or "").strip().strip('"“”')[:200]
    if missed and _norm(missed) not in _norm(sentence):   # Thoth may only quote what the child really said
        missed = ""
    added = re.sub(r"\s+", " ", str(obj.get("added") or "")).strip()[:200]
    return {"faithful": bool(obj.get("faithful")) and not missed and not added, "missed": missed, "added": added, "ms": ms}


def audit(sentence: str, old: str, new: str, steps: list | None = None) -> dict:
    """{"faithful", "missed", "added", "ms", "model", "checks"}. Thoth checks twice, in parallel, and
    only says the code doesn't match when both checks agree, so one noisy answer can't make him
    step in. faithful=None if he couldn't check."""
    mapping = "\n".join(f"- \"{st.get('quote', '')}\" became: {st.get('code', '')}" for st in (steps or []))
    user = f"OLD CODE:\n{old}\nCHILD SAID:\n{sentence}\nTHE COMPILER SAYS THESE WORDS BECAME THIS CODE:\n{mapping or '- (none)'}\nNEW CODE:\n{new}"
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        results = [r for r in ex.map(lambda _: _audit_once(user, sentence), range(2)) if r]
    if not results:
        return {"faithful": None, "missed": "", "added": "", "ms": 0, "model": TEACHER_MODEL, "checks": 0}
    ms = max(r["ms"] for r in results)
    if len(results) == 2 and not results[0]["faithful"] and not results[1]["faithful"]:
        missed = next((r["missed"] for r in results if r["missed"]), "")
        added = "" if missed else next((r["added"] for r in results if r["added"]), "")
        if missed or added:
            return {"faithful": False, "missed": missed, "added": added, "ms": ms, "model": TEACHER_MODEL, "checks": 2}
    return {"faithful": True, "missed": "", "added": "", "ms": ms, "model": TEACHER_MODEL, "checks": len(results)}


def hint(problem: str, his_answer: str, his_reason: str, attempts: list[str], picture: str) -> str:
    """One short nudge for a stuck child, or "" if Thoth couldn't think of one."""
    tried = "\n".join(f"- {a}" for a in attempts[-3:]) or "- (nothing yet)"
    user = (f"THE PROBLEM: {problem}\nAHMES ANSWERS: {his_answer}\nAHMES SAYS: {his_reason}\n"
            f"WHAT THE PICTURE SHOWS: {picture}\nWHAT THE CHILD HAS TRIED TEACHING HIM:\n{tried}")
    try:
        text, _ = _chat(HINT_SYSTEM, user, False, 800)
    except Exception:  # noqa: BLE001
        return ""
    text = " ".join(text.replace("```", "").split()).strip('"“”')
    if not text or len(text.split()) > 32 or "def " in text or "return" in text:
        return ""
    return text
