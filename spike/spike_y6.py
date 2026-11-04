"""Gate G1 for the Year 6 skills: the sentence decides what Ahmes does.

Each sentence is compiled from his starting brain on Vultr Serverless Inference, guarded, run in
the sandbox on the fixed 40-problem test, and graded exactly. Expected: "pass" sentences cure
him (40/40), "partial" ones help but don't cure, "fail" ones don't cure, "no_rule" asks for a rule.
"""
from __future__ import annotations

import json
import sys

from app import compiler, guard, sandbox
from app.skills import BRIEF, SKILLS

CASES = [
    ("times_tens", "Move every digit one place to the left for each zero.", "pass"),
    ("times_tens", "Move the decimal point one place to the right for each zero, and fill empty places with zeros.", "pass"),
    ("times_tens", "Move the decimal point one place to the left for each zero.", "fail"),
    ("times_tens", "The answer is 4.5.", "no_rule"),
    ("compare_fractions", "Multiply each top by the other fraction's bottom, then the bigger answer wins.", "pass"),
    ("compare_fractions", "Make the bottoms the same by multiplying, then the bigger top wins.", "partial"),
    ("compare_fractions", "When the tops are the same, the smaller bottom wins.", "partial"),
    ("compare_fractions", "The bigger bottom wins because it's a bigger number.", "fail"),
    ("order_of_operations", "Do brackets first, then times and divide, then plus and take away.", "pass"),
    ("order_of_operations", "Do times and divide before plus and take away.", "partial"),
    ("order_of_operations", "Be careful about the order.", "fail"),
    ("intervals", "Count up from the first number to the second number, going through zero.", "pass"),
    ("intervals", "Add the two numbers without the minus signs.", "partial"),
    ("intervals", "Count carefully.", "fail"),
]


def main() -> None:
    rows = []
    for name, sentence, expect in CASES:
        sk = SKILLS[name]
        c = compiler.compile_sentence(sk.start_code, sentence, brief=BRIEF.get(name, ""))
        result, right = "REJECTED", None
        if c.no_rule:
            result = "NO_RULE"
        elif c.ok:
            g = guard.check(c.code, sk.args)
            if not g.ok:
                result = "BLOCKED"
            else:
                probs = sk.problems(11, 40)
                r = sandbox.run(c.code, [list(p) for p in probs], "spike")
                result = r.verdict
                right = sum(1 for case in r.cases if case.get("status") == "ok" and 0 <= case["i"] < 40
                            and sk.grade(probs[case["i"]], case["out"]))
        ok = {"pass": right == 40, "partial": right is not None and 0 < right < 40,
              "fail": right != 40, "no_rule": result == "NO_RULE"}[expect]
        rows.append({"skill": name, "sentence": sentence, "expect": expect, "result": result, "right": right,
                     "as_expected": ok, "code": c.code})
        print(f"[{'✓' if ok else '✗'}] {expect:8s} {result:9s} {str(right) + '/40' if right is not None else '':7s} {name:20s} {sentence[:60]}", flush=True)
    print("\nG1 (Year 6):", sum(r["as_expected"] for r in rows), "/", len(rows), "as expected")
    with open(sys.argv[1] if len(sys.argv) > 1 else "spike/results-y6.json", "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main()
