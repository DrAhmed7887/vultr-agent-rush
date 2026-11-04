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
