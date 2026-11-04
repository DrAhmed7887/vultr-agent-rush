"""Gate G1: does what the child says actually change what Ahmes does?

Good explanations should pass, vague or wrong ones should NOT pass, and the doubling sentence
must hang. Every generated patch runs only inside the sandbox on the VM.
Run on the VM:  set -a; . /etc/ahmes.env; python -m spike.spike [model]
"""
from __future__ import annotations

import json
import sys
import time

from app import compiler, guard, sandbox, skills

CASES = [
    # (skill, sentence, expectation: pass | fail | hang | no_rule)
    ("add_fractions", "Multiply the bottoms together, multiply each top by the other bottom, then add the tops.", "pass"),
    ("add_fractions", "You have to find a common bottom. Times the two bottoms, and change each top by multiplying it with the other bottom, then add those tops.", "pass"),
    ("add_fractions", "Make the bottoms the same by multiplying, then add the tops.", "fail"),
    ("add_fractions", "When the bottoms are the same, keep the bottom and add the tops.", "fail"),
    ("add_fractions", "Add the tops and keep the bigger bottom.", "fail"),
    ("add_fractions", "Keep doubling both bottoms until they're the same.", "hang"),
    ("add_fractions", "The answer is 5/6.", "no_rule"),
    ("compare_decimals", "Look at the tenths first. The bigger tenth wins. If the tenths are the same, check the next place, and if every place is the same, they're equal.", "pass"),
    ("compare_decimals", "Compare them place by place starting with the tenths. The first place where they're different decides. If all places match they're equal.", "pass"),
    ("compare_decimals", "Look at the tenths first.", "fail"),
    ("compare_decimals", "The longer number is bigger because it has more digits.", "fail"),
    ("compare_decimals", "Add a zero to the shorter one.", "fail"),
    ("compare_decimals", "0.5 is bigger.", "no_rule"),
]


def main(model: str) -> None:
    rows = []
    for skill_name, sentence, expect in CASES:
        sk = skills.SKILLS[skill_name]
        t0 = time.time()
        c = compiler.compile_sentence(sk.start_code, sentence, model=model)
        dt = round(time.time() - t0, 1)
        row = {"skill": skill_name, "expect": expect, "sentence": sentence, "compile_s": dt}
        if not c.ok:
            row.update(result="REJECTED", reason=c.reason, code=c.code)
        elif c.no_rule:
            row.update(result="NO_RULE")
        else:
            g = guard.check(c.code, sk.args)
            if not g.ok:
                row.update(result="BLOCKED", reason=g.reason, code=c.code)
            else:
                probs = sk.problems(11, 40)
                r = sandbox.run(c.code, [list(p) for p in probs])
                right = sum(1 for case, p in zip(r.cases, probs) if case["status"] == "ok" and sk.grade(p, case["out"]))
                row.update(result=r.verdict, score=f"{right}/40", run_ms=r.elapsed_ms, code=c.code)
        got = row["result"]
        score_ok = row.get("score") == "40/40"
        row["as_expected"] = {
            "pass": got == "OK" and score_ok,
            "fail": not (got == "OK" and score_ok) and got != "NO_RULE",
            "hang": got == "TIMEOUT",
            "no_rule": got == "NO_RULE",
        }[expect]
        rows.append(row)
        print(f"[{'✓' if row['as_expected'] else '✗'}] {expect:7} {got:9} {row.get('score', ''):6} {dt:>4}s  {sentence[:70]}", flush=True)
    good = [r for r in rows if r["expect"] == "pass"]
    bad = [r for r in rows if r["expect"] == "fail"]
    print("\nG1 good passed:", sum(r["as_expected"] for r in good), "/", len(good),
          "| vague/wrong not passed:", sum(r["as_expected"] for r in bad), "/", len(bad),
          "| hang:", [r["result"] for r in rows if r["expect"] == "hang"],
          "| no_rule:", [r["result"] for r in rows if r["expect"] == "no_rule"])
    with open(f"spike/results-{model}.json", "w") as f:
        json.dump(rows, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else compiler.MODEL)
