"""Black-box read-out: which known rule does Ahmes's *patched* brain behave like?

It only sees his answers from the sandbox, never his code. The hypotheses are known
partial fixes, plus an "unknown rule" bucket, so it never claims certainty it doesn't have.
This is a game read-out of the robot's rule, not an assessment of the child.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Callable, Sequence

from .skills import dec_truth, frac_truth


def _digit(d: int, p: int, k: int) -> int:
    return d // 10 ** (p - k) % 10 if 1 <= k <= p else 0


def _longer(a: Sequence[int]) -> int:
    w1, d1, _, w2, d2, _ = a
    if w1 != w2:
        return 1 if w1 > w2 else 2
    return 1 if d1 > d2 else 2 if d2 > d1 else 0


def _shorter(a: Sequence[int]) -> int:
    w1, d1, p1, w2, d2, p2 = a
    if w1 != w2:
        return 1 if w1 > w2 else 2
    if p1 != p2:
        return 1 if p1 < p2 else 2
    return 1 if d1 > d2 else 2 if d2 > d1 else 0


def _tenths_then_longer(a: Sequence[int]) -> int:
    w1, d1, p1, w2, d2, p2 = a
    if w1 != w2:
        return 1 if w1 > w2 else 2
    t1, t2 = _digit(d1, p1, 1), _digit(d2, p2, 1)
    if t1 != t2:
        return 1 if t1 > t2 else 2
    return _longer(a)


def _tenths_hundredths_then_longer(a: Sequence[int]) -> int:
    w1, d1, p1, w2, d2, p2 = a
    if w1 != w2:
        return 1 if w1 > w2 else 2
    for k in (1, 2):
        x, y = _digit(d1, p1, k), _digit(d2, p2, k)
        if x != y:
            return 1 if x > y else 2
    return _longer(a)


DEC_HYPOTHESES: dict[str, tuple[str, Callable[[Sequence[int]], object]]] = {
    "correct": ("compares place by place, like a maths teacher", dec_truth),
    "longer_is_larger": ("still picks the one with more digits", _longer),
    "tenths_only": ("looks at the tenths, then falls back to “more digits wins”", _tenths_then_longer),
    "two_places": ("checks tenths and hundredths, then falls back to “more digits wins”", _tenths_hundredths_then_longer),
    "shorter_is_larger": ("thinks the shorter decimal is bigger", _shorter),
}


def _frac(top: int, bottom: int) -> Fraction | None:
    return Fraction(top, bottom) if bottom else None


FRAC_HYPOTHESES: dict[str, tuple[str, Callable[[Sequence[int]], object]]] = {
    "correct": ("adds fractions like a maths teacher", frac_truth),
    "add_across": ("adds the tops and adds the bottoms", lambda a: _frac(a[0] + a[2], a[1] + a[3])),
    "raw_tops": ("multiplies the bottoms but adds the tops as they are", lambda a: _frac(a[0] + a[2], a[1] * a[3])),
    "same_bottom_only": ("gets same-bottom sums right, adds across otherwise",
                         lambda a: frac_truth(a) if a[1] == a[3] else _frac(a[0] + a[2], a[1] + a[3])),
    "max_bottom": ("adds the tops and keeps the bigger bottom", lambda a: _frac(a[0] + a[2], max(a[1], a[3]))),
}

HYPOTHESES = {"compare_decimals": DEC_HYPOTHESES, "add_fractions": FRAC_HYPOTHESES}


def _norm(skill: str, out: object) -> object:
    if skill == "add_fractions":
        if isinstance(out, (list, tuple)) and len(out) == 2 and all(isinstance(x, int) for x in out) and out[1]:
            return Fraction(out[0], out[1])
        return None
    return out if isinstance(out, int) and not isinstance(out, bool) else None


def classify(skill: str, probes: Sequence[Sequence[int]], outputs: Sequence[object]) -> dict:
    """Return the best-matching known behaviour, every hypothesis's match count, and an unknown share."""
    hyps = HYPOTHESES[skill]
    n = len(probes)
    matches = {}
    for key, (_, fn) in hyps.items():
        matches[key] = sum(1 for a, o in zip(probes, outputs) if _norm(skill, o) is not None and _norm(skill, o) == _norm_truth(skill, fn(a)))
    best = max(matches, key=lambda k: (matches[k], k == "correct"))
    unknown = 1 - matches[best] / n if n else 1.0
    if matches[best] < 0.8 * n:
        best_label, best_key = "a rule I don't recognise yet", "unknown"
    else:
        best_key, best_label = best, hyps[best][0]
    return {"behaves_like": best_key, "label": best_label, "matches": matches, "n": n, "unknown": round(unknown, 2)}


def _norm_truth(skill: str, v: object) -> object:
    if skill == "add_fractions":
        return v if isinstance(v, Fraction) else None
    return v


def next_probe(skill: str, behaves_like: str, pool: Sequence[Sequence[int]]) -> Sequence[int] | None:
    """Pick a problem where the leading wrong rule and the correct rule disagree: Ahmes's next trap."""
    hyps = HYPOTHESES[skill]
    if behaves_like in ("correct",):
        return None
    wrong = hyps.get(behaves_like, (None, None))[1]
    truth = hyps["correct"][1]
    for a in pool:
        if wrong is None:
            return a
        if _norm_truth(skill, wrong(a)) != _norm_truth(skill, truth(a)):
            return a
    return None
