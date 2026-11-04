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


def test_tricks_and_his_reasons():
    from app.replies import explain
    from app.skills import KIND, SKILLS, tricks, valid_problem
    sk = SKILLS["compare_decimals"]
    probs = sk.problems(11, 40)
    t = tricks(sk.name, probs, [True] * 40)
    assert [x["learned"] for x in t] == [True] * 4 and sum(x["total"] for x in t) == 40
    assert KIND[sk.name]((0, 3, 1, 0, 30, 2)) == "equal"
    # his reason describes what his rule did on this exact problem
    assert explain(sk.name, (0, 45, 2, 0, 5, 1), 1) == "0.45! 45 is more than 5, so it's bigger."
    assert "tenths are the same" in explain(sk.name, (0, 606, 3, 0, 61, 2), 1, prefer="tenths_only")
    assert explain("add_fractions", (1, 2, 1, 3), [2, 5]).startswith("I add the tops and add the bottoms")
    assert valid_problem(sk.name, (0, 45, 2, 0, 5, 1)) and not valid_problem(sk.name, (0, 450, 2, 0, 5, 1))
    assert not valid_problem("add_fractions", (1, 0, 1, 3))


def test_thoth_steps_in_only_when_both_checks_agree(monkeypatch):
    from app import teacher
    said = "If the tenths are the same, check the next place, and if every place is the same, they're equal."
    answers = iter([{"faithful": False, "missed": "if every place is the same, they're equal", "added": "", "ms": 5},
                    {"faithful": True, "missed": "", "added": "", "ms": 6}])
    monkeypatch.setattr(teacher, "_audit_once", lambda user, sentence: next(answers))
    assert teacher.audit(said, "", "")["faithful"] is True            # one noisy check is not enough
    both = {"faithful": False, "missed": "if every place is the same, they're equal", "added": "", "ms": 5}
    monkeypatch.setattr(teacher, "_audit_once", lambda user, sentence: dict(both))
    a = teacher.audit(said, "", "")
    assert a["faithful"] is False and a["missed"].startswith("if every place")
    # a quote the child never said is dropped
    monkeypatch.setattr(teacher, "_audit_once", lambda user, sentence: None)
    assert teacher.audit(said, "", "")["faithful"] is None


def test_thoth_hints_only_when_stuck(monkeypatch):
    from app import main, teacher
    from app.skills import SKILLS
    sk = SKILLS["compare_decimals"]
    monkeypatch.setattr(teacher, "hint", lambda *a: "Look at the picture again: which one is further along?")
    hw = (0, 606, 3, 0, 61, 2)
    wrong = {"ok": False, "his_answer": "0.606 is bigger", "why": "x"}
    assert main._thoth(sk, hw, ["one try"], wrong, "", {"faithful": True}) is None
    assert main._thoth(sk, hw, ["one", "two"], wrong, "", {"faithful": True})["kind"] == "hint"
    assert main._thoth(sk, hw, ["one", "two"], {**wrong, "ok": True}, "", {"faithful": True}) is None
    audit = {"faithful": False, "missed": "they're equal", "added": ""}
    t = main._thoth(sk, hw, ["one"], wrong, "", audit)
    assert t["kind"] == "audit" and t["action"] == "listen_again" and "they're equal" in t["say"]


CORRECT_Y6 = {
    "times_tens": "def solve(digits, places, zeros):\n    if places >= zeros:\n        return (digits, places - zeros)\n    return (pad(digits, places, zeros), 0)\n",
    "compare_fractions": "def solve(top1, bottom1, top2, bottom2):\n    a = top1 * bottom2\n    b = top2 * bottom1\n    if a > b:\n        return 1\n    if b > a:\n        return 2\n    return 0\n",
    "order_of_operations": ("def solve(a, op1, b, op2, c, brackets):\n    if brackets == 2 or (brackets == 0 and op2 >= 3 and op1 <= 2):\n"
                            "        return apply(op1, a, apply(op2, b, c))\n    return apply(op2, apply(op1, a, b), c)\n"),
    "intervals": "def solve(start, end):\n    return end - start\n",
}


def _run_local(code, probs):
    """Trusted test code only (ours, never a child's): runs with the sandbox's helpers."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("runner", "sandbox/runner.py")
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    env = {"digit": runner.digit, "pad": runner.pad, "gcd": runner.gcd, "apply": runner.apply}
    exec(code, env)
    return [env["solve"](*p) for p in probs]


def test_year6_skills_start_wrong_and_can_be_cured():
    from app import guard
    from app.skills import KIND, SKILLS, tricks
    from app.skills_y6 import Y6
    for name, correct in CORRECT_Y6.items():
        sk = SKILLS[name]
        probs = sk.problems(11, 40)
        assert guard.check(sk.start_code, sk.args).ok and guard.check(correct, sk.args).ok, name
        start = tricks(name, probs, [sk.grade(p, o) for p, o in zip(probs, _run_local(sk.start_code, probs))])
        assert any(t["learned"] for t in start) and not all(t["learned"] for t in start), (name, start)
        cured = [sk.grade(p, o) for p, o in zip(probs, _run_local(correct, probs))]
        assert all(cured), name
        hw = Y6[name]["homework"]
        assert not sk.grade(hw, _run_local(sk.start_code, [hw])[0]), name   # his first homework is wrong
        assert KIND[name](hw) in [k for k, _, _ in Y6[name]["tricks"]]


def test_year6_reasons_describe_his_rule():
    from app.replies import explain
    assert explain("times_tens", (45, 2, 1), (450, 3)) == "0.450! Times 10 means add 1 zero on the end."
    assert explain("compare_fractions", (1, 4, 1, 8), 2) == "1/8! 8 is a bigger bottom than 4."
    assert explain("order_of_operations", (2, 1, 3, 3, 4, 0), 20) == "2 + 3 is 5, then × 4 makes 20. Left to right!"
    assert explain("intervals", (-4, 7), 3) == "3 degrees! I take 4 away from 7. Minus signs don't matter."
    assert explain("intervals", (-4, 7), 11) == "11 degrees!"


def test_shortened_quotes_must_still_be_the_childs_words():
    from app.compiler import _norm, _quoted
    said = _norm("Count up from the first number to the second number, going through zero.")
    assert _quoted("Count up from the first number to... zero", said)
    assert not _quoted("zero... Count up", said)                 # wrong order
    assert not _quoted("Count up from the first number to... ten", said)
