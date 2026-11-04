"""Ahmes's two skills: their signatures, his starting (buggy) brain, the true rule, and test problems.

Everything here is trusted code that runs on the VM, never inside the sandbox.
Numbers are exact: decimals are (whole, digits, places) and fractions are (top, bottom) integer pairs.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Callable, Sequence

# ---------- decimals ----------

DEC_ARGS = ("whole1", "digits1", "places1", "whole2", "digits2", "places2")

AHMES_DECIMALS = '''def solve(whole1, digits1, places1, whole2, digits2, places2):
    if whole1 > whole2:
        return 1
    if whole2 > whole1:
        return 2
    if digits1 > digits2:
        return 1
    if digits2 > digits1:
        return 2
    return 0
'''


def dec_value(whole: int, digits: int, places: int) -> Fraction:
    return Fraction(whole) + Fraction(digits, 10 ** places)


def dec_text(whole: int, digits: int, places: int) -> str:
    return f"{whole}.{str(digits).zfill(places)}"


def dec_truth(args: Sequence[int]) -> int:
    a, b = dec_value(*args[:3]), dec_value(*args[3:])
    return 1 if a > b else 2 if b > a else 0


def dec_problems(seed: int, n: int = 40) -> list[tuple[int, ...]]:
    """Stratified decimal pairs, chosen so each known wrong rule fails somewhere different.

    0: tenths differ, the longer one is smaller (0.45 vs 0.5)      -> breaks "longer is larger"
    1: tenths tie, the longer one is smaller (0.405 vs 0.41)       -> breaks "tenths only"
    2: equal values written differently (0.5 vs 0.50)              -> breaks both
    3: same length (every rule gets these right)
    4: mixed, random
    """
    rng = random.Random(seed)
    out: list[tuple[int, ...]] = []
    while len(out) < n:
        kind = len(out) % 5
        if kind == 0:
            t1 = rng.randrange(1, 9)
            a, b = (0, t1 * 10 + rng.randrange(1, 10), 2), (0, rng.randrange(t1 + 1, 10), 1)
        elif kind == 1:
            t, h1 = rng.randrange(1, 10), rng.randrange(0, 9)
            a = (0, t * 100 + h1 * 10 + rng.randrange(1, 10), 3)
            b = (0, t * 10 + rng.randrange(h1 + 1, 10), 2)
        elif kind == 2:
            t = rng.randrange(1, 10)
            a, b = (0, t, 1), (0, t * 10, 2)
        elif kind == 3:
            p = rng.choice([1, 2])
            lo = 10 ** (p - 1)
            a, b = (0, rng.randrange(lo, 10 ** p), p), (0, rng.randrange(lo, 10 ** p), p)
        else:
            pa, pb = rng.choice([1, 2, 3]), rng.choice([1, 2, 3])
            a = (0, rng.randrange(10 ** (pa - 1), 10 ** pa), pa)
            b = (0, rng.randrange(10 ** (pb - 1), 10 ** pb), pb)
        if rng.random() < 0.5:
            a, b = b, a
        out.append(a + b)
    return out


# ---------- fractions ----------

FRAC_ARGS = ("top1", "bottom1", "top2", "bottom2")

AHMES_FRACTIONS = '''def solve(top1, bottom1, top2, bottom2):
    return (top1 + top2, bottom1 + bottom2)
'''


def frac_truth(args: Sequence[int]) -> Fraction:
    t1, b1, t2, b2 = args
    return Fraction(t1, b1) + Fraction(t2, b2)


def frac_problems(seed: int, n: int = 40) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    out: list[tuple[int, ...]] = []
    while len(out) < n:
        b1 = rng.randrange(2, 11)
        b2 = b1 if len(out) % 4 == 0 else rng.randrange(2, 11)   # about 25% same-bottom
        out.append((rng.randrange(1, b1), b1, rng.randrange(1, b2), b2))
    return out


# ---------- registry ----------

@dataclass(frozen=True)
class Skill:
    name: str
    title: str
    args: tuple[str, ...]
    start_code: str
    problems: Callable[[int, int], list[tuple[int, ...]]]
    grade: Callable[[Sequence[int], object], bool]
    show: Callable[[Sequence[int]], str]
    show_answer: Callable[[Sequence[int], object], str]


def _grade_dec(args: Sequence[int], out: object) -> bool:
    return isinstance(out, int) and not isinstance(out, bool) and out == dec_truth(args)


def _grade_frac(args: Sequence[int], out: object) -> bool:
    if not (isinstance(out, (list, tuple)) and len(out) == 2):
        return False
    top, bottom = out
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (top, bottom)) or bottom == 0:
        return False
    return Fraction(top, bottom) == frac_truth(args)


def _show_dec(args: Sequence[int]) -> str:
    return f"{dec_text(*args[:3])} vs {dec_text(*args[3:])}"


def _ans_dec(args: Sequence[int], out: object) -> str:
    a, b = dec_text(*args[:3]), dec_text(*args[3:])
    return {1: f"{a} is bigger", 2: f"{b} is bigger", 0: "they're equal"}.get(out, "no answer")  # type: ignore[arg-type]


def _show_frac(args: Sequence[int]) -> str:
    t1, b1, t2, b2 = args
    return f"{t1}/{b1} + {t2}/{b2}"


def _ans_frac(args: Sequence[int], out: object) -> str:
    if isinstance(out, (list, tuple)) and len(out) == 2:
        return f"{out[0]}/{out[1]}"
    return "no answer"


SKILLS: dict[str, Skill] = {
    "compare_decimals": Skill("compare_decimals", "Which decimal is bigger?", DEC_ARGS, AHMES_DECIMALS,
                              dec_problems, _grade_dec, _show_dec, _ans_dec),
    "add_fractions": Skill("add_fractions", "Adding fractions", FRAC_ARGS, AHMES_FRACTIONS,
                           frac_problems, _grade_frac, _show_frac, _ans_frac),
}
