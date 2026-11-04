"""Four Year 6 skills (National Curriculum in England), each starting from a documented wrong rule.

Each skill registers: its problems (one kind per trick), the true rule for exact grading, Ahmes's
wrong starting brain, the known wrong rules (for his reasons and the read-out), what he says
about one answer, a short note for the compiler about the input format, and a sentence that
describes the picture (for Thoth's hints). Everything is exact integer maths; no floats.
"""
from __future__ import annotations

import random
from fractions import Fraction
from typing import Callable, Sequence

from .skills import Skill

OPS = {1: "+", 2: "−", 3: "×", 4: "÷"}


def apply(op: int, x: int, y: int) -> Fraction:
    """Exact: one operation. ÷ by zero raises, like the sandbox helper."""
    x, y = Fraction(x), Fraction(y)
    return x + y if op == 1 else x - y if op == 2 else x * y if op == 3 else x / y


def _whole(v: Fraction) -> int | None:
    return int(v) if v.denominator == 1 else None


# ---------- 1. multiply by 10, 100, 1,000 ----------

def tens_text(digits: int, places: int) -> str:
    if places < 0:                       # digits moved past the ones place: 45 with places -1 is 450
        digits, places = digits * 10 ** -places, 0
    if places == 0:
        return f"{digits:,}"
    return f"{digits // 10 ** places:,}.{str(digits % 10 ** places).zfill(places)}"


def tens_value(a: Sequence[int]) -> Fraction:
    d, p, z = a
    return Fraction(d, 10 ** p) * 10 ** z


def tens_out_value(out: object) -> Fraction | None:
    if isinstance(out, (list, tuple)) and len(out) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in out):
        d, p = out
        if 0 <= d < 10 ** 15 and -12 <= p <= 12:
            return Fraction(d, 10 ** p) if p >= 0 else Fraction(d * 10 ** -p)
    return None


TENS_START = '''def solve(digits, places, zeros):
    if places > 0:
        return (pad(digits, places, places + zeros), places + zeros)
    return (pad(digits, 0, zeros), 0)
'''


def tens_kind(a: Sequence[int]) -> str:
    _, p, z = a
    return "whole" if p == 0 else "still_decimal" if p > z else "exact" if p == z else "past"


def tens_problems(seed: int, n: int = 40) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    out: list[tuple[int, ...]] = []
    while len(out) < n:
        kind = len(out) % 4
        if kind == 0:
            p, z = 0, rng.randrange(1, 4)
        elif kind == 1:
            p = rng.choice([2, 3]); z = rng.randrange(1, p)
        elif kind == 2:
            z = rng.randrange(1, 4); p = z
        else:
            p = rng.choice([1, 2]); z = rng.randrange(p + 1, 4)
        d = rng.randrange(2, 10 ** max(p, 2) * (10 if p == 0 else 1))
        if p and d % 10 == 0:
            d += 1
        out.append((d, p, z))
    return out


def _tens_show(a: Sequence[int]) -> str:
    d, p, z = a
    return f"{tens_text(d, p)} × {10 ** z:,}"


def _tens_answer(a: Sequence[int], out: object) -> str:
    if tens_out_value(out) is None:
        return "no answer"
    return tens_text(out[0], out[1])  # type: ignore[index]


def _tens_grade(a: Sequence[int], out: object) -> bool:
    return tens_out_value(out) == tens_value(a)


TENS_HYP: dict[str, tuple[str, Callable]] = {
    "correct": ("moves every digit the right number of places", tens_value),
    "add_zeros": ("still adds zeros on the end", lambda a: Fraction(a[0], 10 ** a[1]) * (1 if a[1] else 10 ** a[2])),
    "divide_instead": ("moves the digits the wrong way", lambda a: Fraction(a[0], 10 ** a[1]) / 10 ** a[2]),
    "one_place": ("always moves the digits just one place", lambda a: Fraction(a[0], 10 ** a[1]) * 10),
}


def tens_why(key: str, a: Sequence[int], out: object, ans: str) -> str:
    z = a[2]
    return {"add_zeros": f"{ans}! Times {10 ** z:,} means add {z} zero{'s' if z > 1 else ''} on the end.",
            "divide_instead": f"{ans}! I moved the digits the other way.",
            "one_place": f"{ans}! I moved the digits one place."}.get(key, "")


def tens_picture(a: Sequence[int]) -> str:
    d, p, z = a
    v = tens_value(a)
    return (f"in the place-value chart every digit of {tens_text(d, p)} moves {z} place{'s' if z > 1 else ''} to the left, "
            f"so it becomes {_frac_text(v)}")


def _frac_text(v: Fraction) -> str:
    p = 0
    while (v * 10 ** p).denominator != 1:
        p += 1
    return tens_text(int(v * 10 ** p), p)


# ---------- 2. compare fractions ----------

CMP_START = '''def solve(top1, bottom1, top2, bottom2):
    if bottom1 > bottom2:
        return 1
    if bottom2 > bottom1:
        return 2
    if top1 > top2:
        return 1
    if top2 > top1:
        return 2
    return 0
'''


def cmp_truth(a: Sequence[int]) -> int:
    x, y = Fraction(a[0], a[1]), Fraction(a[2], a[3])
    return 1 if x > y else 2 if y > x else 0


def cmp_kind(a: Sequence[int]) -> str:
    t1, b1, t2, b2 = a
    if Fraction(t1, b1) == Fraction(t2, b2):
        return "equal"
    return "same_bottom" if b1 == b2 else "same_top" if t1 == t2 else "different"


def cmp_problems(seed: int, n: int = 40) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    out: list[tuple[int, ...]] = []
    while len(out) < n:
        kind = len(out) % 4
        if kind == 0:
            b = rng.randrange(3, 13); t1, t2 = rng.sample(range(1, b), 2); p = (t1, b, t2, b)
        elif kind == 1:
            t = rng.randrange(1, 6); b1, b2 = rng.sample(range(t + 1, 13), 2); p = (t, b1, t, b2)
        elif kind == 2:
            b = rng.randrange(2, 7); t = rng.randrange(1, b); k = rng.randrange(2, 5)
            p = (t, b, t * k, b * k) if rng.random() < .5 else (t * k, b * k, t, b)
        else:
            b1, b2 = rng.sample(range(2, 13), 2)
            t1, t2 = rng.randrange(1, b1 + 3), rng.randrange(1, b2 + 3)
            p = (t1, b1, t2, b2)
            if t1 == t2 or Fraction(t1, b1) == Fraction(t2, b2):
                continue
        out.append(p)
    return out


def _cmp_show(a: Sequence[int]) -> str:
    return f"{a[0]}/{a[1]} or {a[2]}/{a[3]}"


def _cmp_answer(a: Sequence[int], out: object) -> str:
    return {1: f"{a[0]}/{a[1]} is bigger", 2: f"{a[2]}/{a[3]} is bigger", 0: "they're equal"}.get(out, "no answer")  # type: ignore[arg-type]


def _cmp_grade(a: Sequence[int], out: object) -> bool:
    return isinstance(out, int) and not isinstance(out, bool) and out == cmp_truth(a)


def _by(f1, f2) -> int:
    return 1 if f1 > f2 else 2 if f2 > f1 else 0


CMP_HYP: dict[str, tuple[str, Callable]] = {
    "correct": ("compares fractions like a maths teacher", cmp_truth),
    "bigger_bottom": ("still thinks the bigger bottom wins", lambda a: _by(a[1], a[3]) or _by(a[0], a[2])),
    "tops_only": ("only looks at the tops", lambda a: _by(a[0], a[2])),
    "smaller_bottom": ("thinks the smaller bottom always wins", lambda a: _by(a[3], a[1]) or _by(a[0], a[2])),
}


def cmp_why(key: str, a: Sequence[int], out: object, ans: str) -> str:
    if out == 0:
        return "They're equal! They look the same to me."
    pick = f"{a[0]}/{a[1]}" if out == 1 else f"{a[2]}/{a[3]}"
    b, other = (a[1], a[3]) if out == 1 else (a[3], a[1])
    return {"bigger_bottom": f"{pick}! {b} is a bigger bottom than {other}.",
            "tops_only": f"{pick}! It has the bigger top.",
            "smaller_bottom": f"{pick}! Smaller bottoms mean bigger pieces."}.get(key, "")


def cmp_picture(a: Sequence[int]) -> str:
    t = cmp_truth(a)
    if t == 0:
        return "the two fraction bars are the same length, so they're equal"
    bigger = f"{a[0]}/{a[1]}" if t == 1 else f"{a[2]}/{a[3]}"
    return f"the fraction bar for {bigger} is longer"


# ---------- 3. order of operations ----------

OPS_START = '''def solve(a, op1, b, op2, c, brackets):
    first = apply(op1, a, b)
    return apply(op2, first, c)
'''


def ops_truth(a: Sequence[int]) -> Fraction:
    x, o1, y, o2, z, br = a
    if br == 2:
        return apply(o1, x, apply(o2, y, z))
    if br == 1 or not (o2 >= 3 and o1 <= 2):
        return apply(o2, apply(o1, x, y), z)
    return apply(o1, x, apply(o2, y, z))


def _ltr(a): return apply(a[3], apply(a[1], a[0], a[2]), a[4])


def _precedence_no_brackets(a):
    x, o1, y, o2, z, _ = a
    return apply(o1, x, apply(o2, y, z)) if (o2 >= 3 and o1 <= 2) else _ltr(a)


def _brackets_then_ltr(a):
    x, o1, y, o2, z, br = a
    return apply(o1, x, apply(o2, y, z)) if br == 2 else _ltr(a)


def ops_kind(a: Sequence[int]) -> str:
    _, o1, _, o2, _, br = a
    if br == 2:
        return "brackets"
    if (o1 <= 2) == (o2 <= 2):
        return "same_level"
    return "times_first" if o1 >= 3 else "plus_then_times"


def ops_problems(seed: int, n: int = 40) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    out: list[tuple[int, ...]] = []
    while len(out) < n:
        kind = len(out) % 4
        if kind == 0:
            o1, o2 = (rng.choice([1, 2]), rng.choice([1, 2])) if rng.random() < .6 else (rng.choice([3, 4]), rng.choice([3, 4]))
            br = 0
        elif kind == 1:
            o1, o2, br = rng.choice([3, 4]), rng.choice([1, 2]), 0
        elif kind == 2:
            o1, o2, br = rng.choice([1, 2]), rng.choice([3, 4]), 0
        else:
            o1, o2, br = rng.choice([3, 4]), rng.choice([1, 2]), 2
        x, y, z = rng.randrange(1, 21), rng.randrange(1, 13), rng.randrange(1, 13)
        p = (x, o1, y, o2, z, br)
        try:
            vals = [ops_truth(p), _ltr(p), _precedence_no_brackets(p), _brackets_then_ltr(p),
                    apply(o2, y, z), apply(o1, x, y)]
        except ZeroDivisionError:
            continue
        if any(v.denominator != 1 or v < 0 or v > 999 for v in vals):
            continue
        if kind in (2, 3) and ops_truth(p) == _ltr(p):
            continue
        out.append(p)
    return out


def ops_text(a: Sequence[int]) -> str:
    x, o1, y, o2, z, br = a
    s1, s2 = OPS[o1], OPS[o2]
    if br == 2:
        return f"{x} {s1} ({y} {s2} {z})"
    if br == 1:
        return f"({x} {s1} {y}) {s2} {z}"
    return f"{x} {s1} {y} {s2} {z}"


def _ops_answer(a: Sequence[int], out: object) -> str:
    return str(out) if isinstance(out, int) and not isinstance(out, bool) else "no answer"


def _ops_grade(a: Sequence[int], out: object) -> bool:
    return isinstance(out, int) and not isinstance(out, bool) and Fraction(out) == ops_truth(a)


OPS_HYP: dict[str, tuple[str, Callable]] = {
    "correct": ("does brackets, then times and divide, then plus and take away", ops_truth),
    "left_to_right": ("still works from left to right", _ltr),
    "times_first_no_brackets": ("does times and divide first, but ignores brackets", _precedence_no_brackets),
    "brackets_only": ("does brackets first, then goes left to right", _brackets_then_ltr),
}


def ops_why(key: str, a: Sequence[int], out: object, ans: str) -> str:
    x, o1, y, o2, z, _ = a
    if key == "left_to_right":
        first = apply(o1, x, y)
        return f"{x} {OPS[o1]} {y} is {_whole(first)}, then {OPS[o2]} {z} makes {ans}. Left to right!"
    return {"times_first_no_brackets": f"{ans}! I do times and divide first.",
            "brackets_only": f"{ans}! I do the brackets, then go left to right."}.get(key, "")


def ops_picture(a: Sequence[int]) -> str:
    x, o1, y, o2, z, br = a
    if br == 2 or (o2 >= 3 and o1 <= 2):
        inner = apply(o2, y, z)
        return f"done the right way: first {y} {OPS[o2]} {z} = {_whole(inner)}, then {x} {OPS[o1]} {_whole(inner)} = {_whole(ops_truth(a))}"
    return f"done the right way: {ops_text(a)} = {_whole(ops_truth(a))}"


# ---------- 4. intervals across zero ----------

INT_START = '''def solve(start, end):
    return abs(abs(end) - abs(start))
'''


def int_kind(a: Sequence[int]) -> str:
    s, e = a
    if s >= 0:
        return "both_positive"
    if e <= 0:
        return "both_negative"
    return "across_small" if -s <= e else "across_big"


def int_problems(seed: int, n: int = 40) -> list[tuple[int, ...]]:
    rng = random.Random(seed)
    out: list[tuple[int, ...]] = []
    while len(out) < n:
        kind = len(out) % 4
        if kind == 0:
            s = rng.randrange(0, 15); e = rng.randrange(s + 1, 21)
        elif kind == 1:
            s = rng.randrange(-20, -1); e = rng.randrange(s + 1, 0)
        elif kind == 2:
            s = -rng.randrange(1, 10); e = rng.randrange(-s, 21)
        else:
            s = -rng.randrange(3, 21); e = rng.randrange(1, -s)
        out.append((s, e))
    return out


def deg(v: int) -> str:
    return f"−{-v}" if v < 0 else str(v)


def _int_show(a: Sequence[int]) -> str:
    return f"{deg(a[0])}°C up to {deg(a[1])}°C"


def _int_answer(a: Sequence[int], out: object) -> str:
    return f"{out} degrees" if isinstance(out, int) and not isinstance(out, bool) else "no answer"


def _int_grade(a: Sequence[int], out: object) -> bool:
    return isinstance(out, int) and not isinstance(out, bool) and out == a[1] - a[0]


INT_HYP: dict[str, tuple[str, Callable]] = {
    "correct": ("counts up through zero, like a maths teacher", lambda a: a[1] - a[0]),
    "ignore_signs": ("still ignores the minus signs and takes away", lambda a: abs(abs(a[1]) - abs(a[0]))),
    "add_without_signs": ("adds the two numbers without the minus signs", lambda a: abs(a[0]) + abs(a[1])),
}


def int_why(key: str, a: Sequence[int], out: object, ans: str) -> str:
    s, e = abs(a[0]), abs(a[1])
    return {"ignore_signs": f"{ans}! I take {min(s, e)} away from {max(s, e)}. Minus signs don't matter.",
            "add_without_signs": f"{ans}! I add {s} and {e}."}.get(key, "")


def int_picture(a: Sequence[int]) -> str:
    s, e = a
    if s < 0 < e:
        return f"on the number line, from {deg(s)} up to 0 is {-s}, then from 0 up to {e} is {e}"
    return f"on the number line, from {deg(s)} up to {deg(e)} is {e - s} steps"


# ---------- registry ----------

Y6 = {
    "times_tens": dict(
        skill=Skill("times_tens", "Times 10, 100 and 1,000", ("digits", "places", "zeros"), TENS_START,
                    tens_problems, _tens_grade, _tens_show, _tens_answer),
        kind=tens_kind, homework=(45, 2, 1), view="tens", year=6,
        tricks=[("whole", "Whole numbers", "45 × 10"), ("still_decimal", "Still a decimal", "0.45 × 10"),
                ("exact", "Lands on a whole number", "0.45 × 100"), ("past", "Past the dot", "3.7 × 100")],
        hyp=TENS_HYP, norm=tens_out_value, why=tens_why, picture=tens_picture,
        welcome="Hi, I'm Ahmes! Times 10 is easy: just add a zero. 0.45 times 10 is 0.450!",
        ideas=["Move every digit one place to the left for each zero.",
               "Move the decimal point one place to the right for each zero, and fill empty places with zeros.",
               "Move the decimal point one place to the left for each zero."],
        brief=("A number is given as digits and places: 0.45 is digits=45, places=2; 3.7 is digits=37, places=1; "
               "45 is digits=45, places=0; 450 can also be digits=45, places=-1. Writing a zero on the end of 0.45 gives 0.450, "
               "which is digits=450, places=3. zeros is how many zeros the multiplier has: times 10 is zeros=1, times 100 "
               "is zeros=2, times 1000 is zeros=3. Return the answer in the same form, as a tuple (digits, places). "
               "pad(digits, places, to) adds zeros on the right of digits until it has `to` places."),
        valid=lambda a: len(a) == 3 and 0 <= a[0] < 10 ** 6 and 0 <= a[1] <= 3 and 1 <= a[2] <= 3,
        echo={"add_zeros": "So I still add zeros on the end? Like {a}?",
              "divide_instead": "So I move the digits the other way? Like {a}?",
              "one_place": "So I always move just one place? Like {a}?"},
    ),
    "compare_fractions": dict(
        skill=Skill("compare_fractions", "Which fraction is bigger?", ("top1", "bottom1", "top2", "bottom2"), CMP_START,
                    cmp_problems, _cmp_grade, _cmp_show, _cmp_answer),
        kind=cmp_kind, homework=(1, 4, 1, 8), view="frac_compare", year=6,
        tricks=[("same_bottom", "Same bottoms", "2/5 or 3/5"), ("same_top", "Same tops", "1/4 or 1/8"),
                ("equal", "Same amount, different look", "1/2 or 2/4"), ("different", "Different everything", "3/5 or 2/3")],
        hyp=CMP_HYP, norm=lambda o: o if isinstance(o, int) and not isinstance(o, bool) else None,
        why=cmp_why, picture=cmp_picture,
        welcome="Hi, I'm Ahmes! The fraction with the bigger bottom is bigger. 1/8 beats 1/4, easy!",
        ideas=["Multiply each top by the other fraction's bottom, then the bigger answer wins.",
               "Make the bottoms the same by multiplying, then the bigger top wins.",
               "The bigger bottom wins because it's a bigger number."],
        brief=("Two fractions are given as top1/bottom1 and top2/bottom2. Return 1 if the first fraction is bigger, "
               "2 if the second is bigger, and 0 if they are equal."),
        valid=lambda a: len(a) == 4 and all(0 <= a[i] <= 30 and 1 <= a[i + 1] <= 30 for i in (0, 2)),
        echo={"bigger_bottom": "So the bigger bottom still wins? Like {a}?",
              "tops_only": "So I only look at the tops? Like {a}?",
              "smaller_bottom": "So the smaller bottom always wins? Like {a}?"},
    ),
    "order_of_operations": dict(
        skill=Skill("order_of_operations", "Which sum comes first?", ("a", "op1", "b", "op2", "c", "brackets"), OPS_START,
                    ops_problems, _ops_grade, ops_text, _ops_answer),
        kind=ops_kind, homework=(2, 1, 3, 3, 4, 0), view="ops", year=6,
        tricks=[("same_level", "Same kind of signs", "12 − 5 + 3"), ("times_first", "Times comes first anyway", "4 × 3 + 2"),
                ("plus_then_times", "Plus, then times", "2 + 3 × 4"), ("brackets", "Brackets", "3 × (2 + 5)")],
        hyp=OPS_HYP, norm=lambda o: Fraction(o) if isinstance(o, int) and not isinstance(o, bool) else None,
        why=ops_why, picture=ops_picture,
        welcome="Hi, I'm Ahmes! I always go left to right. 2 plus 3 times 4 is 20!",
        ideas=["Do brackets first, then times and divide, then plus and take away.",
               "Do times and divide before plus and take away.",
               "Be careful about the order."],
        brief=("A sum is given as: a op1 b op2 c. op1 and op2 are codes: 1 means +, 2 means −, 3 means ×, 4 means ÷. "
               "brackets is 0 if there are no brackets, 2 if there are brackets around (b op2 c), 1 if around (a op1 b). "
               "apply(op, x, y) does one operation on two numbers: apply(1, 2, 3) is 5 and apply(3, 2, 3) is 6. "
               "Return the answer as a whole number."),
        valid=lambda a: len(a) == 6 and all(0 <= a[i] <= 99 for i in (0, 2, 4)) and a[1] in OPS and a[3] in OPS and a[5] in (0, 1, 2),
        echo={"left_to_right": "So I still go left to right? Like {a}?",
              "times_first_no_brackets": "So I do times first, but what about brackets? Like {a}?",
              "brackets_only": "So I do brackets, then left to right? Like {a}?"},
    ),
    "intervals": dict(
        skill=Skill("intervals", "Below zero", ("start", "end"), INT_START, int_problems, _int_grade, _int_show, _int_answer),
        kind=int_kind, homework=(-4, 7), view="intervals", year=6,
        tricks=[("both_positive", "Above zero", "3°C up to 9°C"), ("both_negative", "Below zero", "−12°C up to −3°C"),
                ("across_small", "Across zero", "−4°C up to 7°C"), ("across_big", "Across zero, very cold", "−9°C up to 2°C")],
        hyp=INT_HYP, norm=lambda o: o if isinstance(o, int) and not isinstance(o, bool) else None,
        why=int_why, picture=int_picture,
        welcome="Hi, I'm Ahmes! Temperatures are easy. From minus 4 up to 7 is 3 degrees!",
        ideas=["Count up from the first number to the second number, going through zero.",
               "Add the two numbers without the minus signs.",
               "Count carefully."],
        brief=("Two temperatures are given as whole numbers start and end; a number below zero is negative, so minus 4 "
               "is -4. end is warmer than start. Return how many degrees it goes up, as a whole number."),
        valid=lambda a: len(a) == 2 and -40 <= a[0] < a[1] <= 40,
        echo={"ignore_signs": "So I still ignore the minus signs? Like {a}?",
              "add_without_signs": "So I always add without the minus signs? Like {a}?"},
    ),
}
