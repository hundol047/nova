"""Lexical uncertainty markers: hypotheses are not affirmative observations.

This intentionally does not infer probabilities or interpret negative tests.
"""
import re

_UNCERTAIN = re.compile(
    r"\b(?:possible|possibly|suspected|suspicious for|question of|uncertain|"
    r"cannot (?:exclude|rule out)|can't (?:exclude|rule out)|"
    r"(?:cannot|can't) be (?:excluded|ruled out)|not (?:excluded|ruled out)|"
    r"rule out|may (?:be|represent|indicate)|might (?:be|represent|indicate))\b",
    re.I,
)


def is_uncertain(clause: str) -> bool:
    return bool(_UNCERTAIN.search(clause))
