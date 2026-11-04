"""The literal compiler: a child's words become Ahmes's new solve() function.

It runs on Vultr Serverless Inference. It is told it knows no maths, may only implement
what the child said, and must tie each step to an exact quote. A deterministic quote check
then rejects steps that smuggle in maths the child never said.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from dataclasses import dataclass, field

import httpx

BASE_URL = os.environ.get("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1")
MODEL = os.environ.get("VULTR_MODEL", "qwen3.8-27b")
FALLBACK_MODEL = os.environ.get("VULTR_MODEL_FALLBACK", "glm-5.3")


def _api_key() -> str:
    key = os.environ.get("VULTR_INFERENCE_API_KEY", "")
    if key:
        return key
    try:  # local development on the Mac: read from Keychain
        return subprocess.run(["security", "find-generic-password", "-s", "VULTR_INFERENCE_API_KEY", "-w"],
                              capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


SYSTEM = """You are Ahmes's brain compiler. Ahmes is a robot who knows NO maths.
A child is teaching Ahmes. Rewrite Ahmes's function solve() so it does EXACTLY what the child's words say, and nothing more.

Rules:
- Change only the steps the child's words state. Keep the OLD code for anything the child did not say how to do.
- Never add a step, a check, or a maths idea the child did not say, even if the result is wrong. Wrong is fine: Ahmes is learning.
- Every part of the child's sentence becomes a step. If the child says what the answer is in some case (for example "they're equal"), return that answer right there, so old code cannot override it.
- If the child mentions a specific number from an example, replace it with the input it came from.
- If the child only gives an answer and no rule (for example "it's 0.5" or "the answer is 5/6"), return {"no_rule": true}.
- Allowed: if/else, while, for over range(), return, + - * // %, comparisons, and the helpers below. No imports, no strings, no lists, no "/".
- Keep the exact function name and inputs.

Helpers you may call:
  digit(digits, places, k)  -> the k-th digit after the decimal point (k=1 is tenths); 0 if k > places
  pad(digits, places, to)   -> digits with zeros added on the right to reach `to` places
  gcd(a, b)                 -> greatest common divisor
A decimal like 0.45 is given as whole=0, digits=45, places=2. A fraction 3/4 is top=3, bottom=4.

Reply with JSON only:
{"steps": [{"quote": "<exact words copied from the child>", "code": "<1-3 lines>"}],
 "kept_old": ["<old line kept>"],
 "code": "def solve(...):\\n    ..."}
"""

FEW_SHOTS = [
    # a full fix, compiled literally
    ("add_fractions",
     "def solve(top1, bottom1, top2, bottom2):\n    return (top1 + top2, bottom1 + bottom2)\n",
     "Multiply the bottoms together. Multiply each top by the other bottom, then add the tops.",
     {"steps": [{"quote": "Multiply the bottoms together", "code": "bottom = bottom1 * bottom2"},
                {"quote": "Multiply each top by the other bottom", "code": "a = top1 * bottom2\nb = top2 * bottom1"},
                {"quote": "then add the tops", "code": "top = a + b"}],
      "kept_old": [],
      "code": "def solve(top1, bottom1, top2, bottom2):\n    bottom = bottom1 * bottom2\n    a = top1 * bottom2\n    b = top2 * bottom1\n    top = a + b\n    return (top, bottom)\n"}),
    # a partial fix: only what was said
    ("add_fractions",
     "def solve(top1, bottom1, top2, bottom2):\n    return (top1 + top2, bottom1 + bottom2)\n",
     "Make the bottoms the same by multiplying them, then add the tops.",
     {"steps": [{"quote": "Make the bottoms the same by multiplying them", "code": "bottom = bottom1 * bottom2"},
                {"quote": "then add the tops", "code": "top = top1 + top2"}],
      "kept_old": [],
      "code": "def solve(top1, bottom1, top2, bottom2):\n    bottom = bottom1 * bottom2\n    top = top1 + top2\n    return (top, bottom)\n"}),
    # a wrong rule, kept wrong
    ("compare_decimals",
     "def solve(whole1, digits1, places1, whole2, digits2, places2):\n    if digits1 > digits2:\n        return 1\n    if digits2 > digits1:\n        return 2\n    return 0\n",
     "The one with fewer numbers after the dot is bigger.",
     {"steps": [{"quote": "The one with fewer numbers after the dot is bigger", "code": "if places1 < places2:\n    return 1\nif places2 < places1:\n    return 2"}],
      "kept_old": ["if digits1 > digits2: return 1", "if digits2 > digits1: return 2", "return 0"],
      "code": "def solve(whole1, digits1, places1, whole2, digits2, places2):\n    if places1 < places2:\n        return 1\n    if places2 < places1:\n        return 2\n    if digits1 > digits2:\n        return 1\n    if digits2 > digits1:\n        return 2\n    return 0\n"}),
]


@dataclass
class Compiled:
    ok: bool
    code: str = ""
    steps: list = field(default_factory=list)
    no_rule: bool = False
    reason: str = ""
    model: str = ""
    usage: dict = field(default_factory=dict)


def _messages(current: str, sentence: str) -> list[dict]:
    msgs = [{"role": "system", "content": SYSTEM}]
    for _, old, said, answer in FEW_SHOTS:
        msgs.append({"role": "user", "content": f"CURRENT CODE:\n{old}\nCHILD SAID:\n{said}"})
        msgs.append({"role": "assistant", "content": json.dumps(answer)})
    msgs.append({"role": "user", "content": f"CURRENT CODE:\n{current}\nCHILD SAID:\n{sentence}"})
    return msgs


def _norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower()).split())


_SWAP = {ast.Gt: ast.Lt, ast.Lt: ast.Gt, ast.GtE: ast.LtE, ast.LtE: ast.GtE}


def _key(n: ast.AST) -> str:
    """A pattern's text; a > b and b < a (and the mirrored pair a > b / b > a) count as one idea."""
    if isinstance(n, ast.Compare) and len(n.ops) == 1:
        l, r = ast.unparse(n.left), ast.unparse(n.comparators[0])
        return " ? ".join(sorted([l, r]))
    if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Mult)):
        l, r = ast.unparse(n.left), ast.unparse(n.right)
        return f"{type(n.op).__name__}(" + ",".join(sorted([l, r])) + ")"
    return ast.unparse(n)


def _patterns_tree(tree: ast.AST) -> set[str]:
    return {_key(n) for n in ast.walk(tree) if isinstance(n, (ast.BinOp, ast.Compare))}


def _patterns(code: str) -> set[str]:
    try:
        return _patterns_tree(ast.parse(code))
    except SyntaxError:
        return set()


def _step_patterns(step_code: str) -> set[str]:
    """Patterns in one step's snippet. A snippet can be a bare header such as "while a != b:",
    so give any line ending in a colon an empty body before parsing."""
    lines = [l for l in step_code.splitlines() if l.strip()]
    out: list[str] = []
    for i, line in enumerate(lines):
        out.append(line)
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.rstrip().endswith(":") and len(nxt) - len(nxt.lstrip()) <= len(line) - len(line.lstrip()):
            out.append(line[: len(line) - len(line.lstrip())] + "    pass")
    body = "\n".join("    " + line for line in out) or "    pass"
    try:
        return _patterns_tree(ast.parse(f"def _f():\n{body}\n"))
    except SyntaxError:
        return set().union(*(_patterns(l.strip().rstrip(":")) for l in lines)) if lines else set()


MAX_PATTERNS_PER_STEP = 3
MAX_OPS_PER_EXPRESSION = 2


def _busiest_expression(code: str) -> int:
    """The most arithmetic operations inside a single expression (a*b + c*d counts 3)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return 0
    best = 0
    for n in ast.walk(tree):
        if isinstance(n, (ast.Assign, ast.AugAssign, ast.Return)) and n.value is not None:
            best = max(best, sum(isinstance(m, ast.BinOp) for m in ast.walk(n.value)))
    return best


def quote_check(sentence: str, current: str, steps: list, code: str) -> str:
    """Return "" if the patch is honest, or the reason it was rejected."""
    said = _norm(sentence)
    if not steps:
        return "no step ties the change to the child's words"
    declared: set[str] = set()
    for st in steps:
        q = _norm(str(st.get("quote", "")))
        if not q or q not in said:
            return f"a step quotes words the child didn't say: {st.get('quote')!r}"
        pats = _step_patterns(str(st.get("code", "")))
        if len(pats - _patterns(current)) > MAX_PATTERNS_PER_STEP:
            return f"one step does more maths than its words say: {st.get('quote')!r}"
        declared |= pats
    if _busiest_expression(code) > MAX_OPS_PER_EXPRESSION:
        return "one line packs several maths steps together; each step must come from the child's own words"
    sneaked = _patterns(code) - _patterns(current) - declared
    if sneaked:
        return "the new code has maths no step explains: " + ", ".join(sorted(sneaked))[:120]
    return ""


def _call(model: str, messages: list[dict], timeout: float) -> tuple[dict, dict, str]:
    body = {"model": model, "temperature": 0, "max_tokens": 6000, "reasoning_effort": "low",
            "messages": messages, "response_format": {"type": "json_object"}}
    r = httpx.post(f"{BASE_URL}/chat/completions", json=body, timeout=timeout,
                   headers={"Authorization": f"Bearer {_api_key()}"})
    r.raise_for_status()
    data = r.json()
    text = data["choices"][0]["message"].get("content") or ""
    return json.loads(text[text.find("{"): text.rfind("}") + 1]), data.get("usage", {}), text


def compile_sentence(current: str, sentence: str, model: str | None = None, timeout: float = 25.0) -> Compiled:
    """Two attempts: a rejected patch is retried with the reason; if the main model's call fails,
    the second attempt uses the fallback model on the same Vultr endpoint."""
    model = model or MODEL
    messages = _messages(current, sentence)
    last = Compiled(False, reason="not run", model=model)
    for attempt in range(2):
        try:
            obj, usage, _ = _call(model, messages, timeout)
        except Exception as e:  # noqa: BLE001
            last = Compiled(False, reason=f"compiler unavailable: {type(e).__name__}", model=model)
            model = FALLBACK_MODEL
            continue
        if obj.get("no_rule"):
            return Compiled(True, no_rule=True, model=model, usage=usage)
        code = str(obj.get("code", ""))
        steps = obj.get("steps", []) if isinstance(obj.get("steps"), list) else []
        problem = quote_check(sentence, current, steps, code)
        if not problem:
            return Compiled(True, code=code, steps=steps, model=model, usage=usage)
        last = Compiled(False, code=code, steps=steps, reason=problem, model=model, usage=usage)
        messages = messages + [{"role": "assistant", "content": json.dumps(obj)},
                               {"role": "user", "content": f"Rejected: {problem}. Compile again, literally. "
                                "Split into small steps, one idea per step, each quoting the child's exact words. "
                                "Do not add maths the child did not say."}]
    return last
