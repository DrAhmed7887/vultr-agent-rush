"""What Ahmes says back. Templates only: no model writes his words, so ElevenLabs only ever
receives Ahmes's own lines, never the child's."""
from __future__ import annotations

from typing import Sequence

from .skills import SKILLS

FIXED = {
    "dizzy": "Whoa, I got dizzy! My brain kept going round and round. Can you explain it another way?",
    "too_full": "My head got too full! That was too much to remember. Can you explain it more simply?",
    "blocked": "Hmm, that word isn't in my brain dictionary. Can you say it with numbers?",
    "no_rule": "Okay, but next time I see a new one, what do I do? Tell me the rule, not just the answer!",
    "rejected": "Wait, I think I heard more than you said. Can you tell me step by step?",
    "busy": "My brain is busy right now. Try again in a second!",
    "welcome_compare_decimals": "Hi, I'm Ahmes! I'm great at decimals. 0.45 is bigger than 0.5, because it has more digits!",
    "welcome_add_fractions": "Hi, I'm Ahmes! Adding fractions is easy. One half plus one third is two fifths!",
    "cured": "I got them all right! Thank you, teacher!",
    "unkind": "Let's keep it kind, and about maths! And don't tell me things about you, like where you live. What's the rule?",
}

ECHO = {
    "compare_decimals": {
        "longer_is_larger": "So I still pick the one with more digits? Like {a}?",
        "tenths_only": "So I look at the tenths first. But when the tenths are the same, I still pick the longer one, like {a}?",
        "two_places": "So I check the tenths, then the hundredths. But after that I pick the longer one, like {a}?",
        "shorter_is_larger": "So now the shorter one is bigger? Like {a}?",
        "unknown": "I'm doing something new now, but {a} still trips me up.",
    },
    "add_fractions": {
        "add_across": "So I add the tops and add the bottoms? Like {a}?",
        "raw_tops": "So I multiply the bottoms, and add the tops just as they are? Like {a}?",
        "same_bottom_only": "So when the bottoms match I'm right, but other times I still add across? Like {a}?",
        "max_bottom": "So I add the tops and keep the bigger bottom? Like {a}?",
        "unknown": "I'm doing something new now, but {a} still trips me up.",
    },
}


from .skills_y6 import Y6  # noqa: E402

for _k, _v in Y6.items():
    FIXED[f"welcome_{_k}"] = _v["welcome"]
    ECHO[_k] = {**_v["echo"], "unknown": "I'm doing something new now, but {a} still trips me up."}


def echo(skill: str, behaves_like: str, probe: Sequence[int] | None, answer: object) -> str:
    if behaves_like == "correct":
        return FIXED["cured"]
    sk = SKILLS[skill]
    example = f"{sk.show(probe)}: {sk.show_answer(probe, answer)}" if probe is not None else "that one"
    return ECHO[skill].get(behaves_like, ECHO[skill]["unknown"]).format(a=example)


def score_line(right: int, total: int) -> str:
    if right == total:
        return f"I got all {total} right!"
    if right == 0:
        return f"I got 0 out of {total}."
    return f"I got {right} out of {total}."


# ---------- Ahmes explains one answer, in his own (wrong) words ----------
# Which known rule reproduces exactly this answer decides what he says, so the reason is a
# true description of what his code did on this problem, never an AI's guess.

_DEC_WHY = {
    "longer_is_larger": "{pick}! {big} is more than {small}, so it's bigger.",
    "tenths_only": "{pick}! The tenths are the same, so the longer one wins.",
    "two_places": "{pick}! Tenths and hundredths match, so the longer one wins.",
    "shorter_is_larger": "{pick}! Shorter numbers are bigger.",
}
_FRAC_WHY = {
    "add_across": "I add the tops and add the bottoms. {ans}!",
    "raw_tops": "I multiply the bottoms and add the tops just as they are. {ans}!",
    "max_bottom": "I add the tops and keep the bigger bottom. {ans}!",
    "same_bottom_only": "I add the tops and add the bottoms. {ans}!",
}


def explain(skill: str, args: Sequence[int], out: object, prefer: str = "") -> str:
    """prefer: the rule the read-out says he follows overall, tried first when several fit."""
    from . import classifier
    sk = SKILLS[skill]
    if out is None:
        return "Hmm, I didn't get an answer for that one."
    if sk.grade(args, out):
        if skill in Y6:
            return f"{sk.show_answer(args, out)}!"
        if skill == "compare_decimals":
            return "They're equal!" if out == 0 else f"{sk.show_answer(args, out).replace(' is bigger', '')} is bigger!"
        return f"It's {sk.show_answer(args, out)}!"
    hyps = classifier.HYPOTHESES[skill]
    want = classifier._norm(skill, out)
    if skill in Y6:
        ans = sk.show_answer(args, out)
        for key in sorted(hyps, key=lambda k: k != prefer):
            if key == "correct":
                continue
            try:
                if want is not None and classifier._norm_truth(skill, hyps[key][1](args)) == want:
                    line = Y6[skill]["why"](key, args, out, ans)
                    if line:
                        return line
            except ZeroDivisionError:
                continue
        return f"I said {ans}. I'm not sure why!"
    for key in sorted(hyps, key=lambda k: k != prefer):
        if key == "correct":
            continue
        if want is not None and classifier._norm_truth(skill, hyps[key][1](args)) == want:
            if skill == "compare_decimals":
                _, d1, p1, _, d2, p2 = args
                pick = sk.show_answer(args, out).replace(" is bigger", "")
                if out == 0:
                    return "They're equal! The digits look the same to me."
                big, small = (d1, d2) if out == 1 else (d2, d1)
                return _DEC_WHY[key].format(pick=pick, big=big, small=small)
            return _FRAC_WHY[key].format(ans=sk.show_answer(args, out))
    return f"I said {sk.show_answer(args, out)}. I'm not sure why!"
