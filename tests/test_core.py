from fractions import Fraction

from app import classifier, compiler, guard
from app.skills import AHMES_DECIMALS, AHMES_FRACTIONS, DEC_ARGS, FRAC_ARGS, SKILLS, dec_problems, frac_problems


def test_guard_accepts_ahmes_and_rejects_escapes():
    assert guard.check(AHMES_DECIMALS, DEC_ARGS).ok
    assert guard.check(AHMES_FRACTIONS, FRAC_ARGS).ok
    bad = [
        "import os\ndef solve(top1, bottom1, top2, bottom2):\n    return (1, 2)\n",
        "def solve(top1, bottom1, top2, bottom2):\n    return open('/etc/passwd')\n",
        "def solve(top1, bottom1, top2, bottom2):\n    return top1.__class__\n",
        "def solve(top1, bottom1, top2, bottom2):\n    return (top1 / bottom1, 1)\n",
        "def solve(top1, bottom1, top2, bottom2):\n    return [1][0]\n",
        "def solve(a, b):\n    return 1\n",
    ]
    for code in bad:
        assert not guard.check(code, FRAC_ARGS).ok, code


def test_while_is_allowed_on_purpose():
    code = "def solve(top1, bottom1, top2, bottom2):\n    while bottom1 != bottom2:\n        bottom1 = bottom1 * 2\n    return (top1, bottom1)\n"
    assert guard.check(code, FRAC_ARGS).ok


def test_problem_sets_are_deterministic_and_stratified():
    assert dec_problems(5) == dec_problems(5)
    probs = frac_problems(3)
    assert sum(1 for p in probs if p[1] == p[3]) >= 10


def test_classifier_spots_tenths_only():
    sk = SKILLS["compare_decimals"]
    probs = sk.problems(9, 40)
    _, fn = classifier.DEC_HYPOTHESES["tenths_only"]
    res = classifier.classify(sk.name, probs, [fn(p) for p in probs])
    assert res["behaves_like"] == "tenths_only"
    trap = classifier.next_probe(sk.name, "tenths_only", sk.problems(10, 60))
    assert trap is not None and fn(trap) != classifier.DEC_HYPOTHESES["correct"][1](trap)


def test_classifier_marks_unknown_rules():
    sk = SKILLS["add_fractions"]
    probs = sk.problems(2, 40)
    res = classifier.classify(sk.name, probs, [(7, 3) for _ in probs])
    assert res["behaves_like"] == "unknown"


def test_quote_check_rejects_smuggled_maths():
    current = AHMES_FRACTIONS
    honest = "def solve(top1, bottom1, top2, bottom2):\n    bottom = bottom1 * bottom2\n    top = top1 + top2\n    return (top, bottom)\n"
    steps = [{"quote": "Make the bottoms the same by multiplying", "code": "bottom = bottom1 * bottom2"},
             {"quote": "then add the tops", "code": "top = top1 + top2"}]
    said = "Make the bottoms the same by multiplying, then add the tops."
    assert compiler.quote_check(said, current, steps, honest) == ""
    smuggled = honest.replace("top = top1 + top2", "top = top1 * bottom2 + top2 * bottom1")
    steps2 = [steps[0], {"quote": "then add the tops", "code": "top = top1 * bottom2 + top2 * bottom1"}]
    assert compiler.quote_check(said, current, steps2, smuggled) != ""
    invented = [{"quote": "use the lowest common denominator", "code": "bottom = bottom1 * bottom2"}]
    assert compiler.quote_check(said, current, invented, honest) != ""


def test_grading_is_exact():
    sk = SKILLS["add_fractions"]
    assert sk.grade((1, 2, 1, 3), (5, 6))
    assert sk.grade((1, 2, 1, 3), (10, 12))
    assert not sk.grade((1, 2, 1, 3), (2, 5))
    assert not sk.grade((1, 2, 1, 3), (5, 0))
    assert Fraction(1, 2) + Fraction(1, 3) == Fraction(5, 6)


def test_header_only_step_is_declared():
    from app.compiler import quote_check
    current = "def solve(top1, bottom1, top2, bottom2):\n    return (top1 + top2, bottom1 + bottom2)\n"
    code = ("def solve(top1, bottom1, top2, bottom2):\n    while bottom1 != bottom2:\n"
            "        bottom1 = bottom1 * 2\n        bottom2 = bottom2 * 2\n    return (top1 + top2, bottom1 + bottom2)\n")
    steps = [{"quote": "until they're the same", "code": "while bottom1 != bottom2:"},
             {"quote": "keep doubling both bottoms", "code": "bottom1 = bottom1 * 2\nbottom2 = bottom2 * 2"}]
    assert quote_check("Keep doubling both bottoms until they're the same.", current, steps, code) == ""
    assert quote_check("Keep doubling both bottoms.", current, [], code) != ""


def test_trap_is_always_a_problem_he_got_wrong():
    from app import main, sandbox
    from app.skills import SKILLS
    sk = SKILLS["compare_decimals"]
    probs = sk.problems(main.TEACH_SEED, 40)
    # pretend he answered with his starting rule ("more digits wins") on every problem
    def longer(p):
        _, d1, _, _, d2, _ = p
        return 1 if d1 > d2 else 2 if d2 > d1 else 0
    cases = [{"i": i, "status": "ok", "out": longer(p)} for i, p in enumerate(probs)]
    run = sandbox.RunResult("OK", cases, 300, {})
    cls = main._read_out(sk, run, probs)
    assert cls["trap"] is not None
    assert not sk.grade(tuple(cls["trap"]["args"]), cls["trap"]["out"])
