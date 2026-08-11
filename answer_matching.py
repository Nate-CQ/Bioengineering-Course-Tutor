"""
Lenient matching for fill-in-the-blank answers.

Exact string matching is too strict for a study tool: a student who
types "polymer" when the accepted answer is "polymers" got the concept
completely right and shouldn't be marked wrong over a plural. This module
normalizes both sides, checks singular/plural equivalence, and falls back
to a fuzzy similarity check to absorb small typos, without being so loose
that it accepts genuinely wrong answers.
"""

import difflib
import re

FUZZY_THRESHOLD = 0.85  # similarity ratio (0-1) above which a typo is forgiven


def _normalize(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s]", "", s)   # strip punctuation
    s = re.sub(r"\s+", " ", s)      # collapse whitespace
    return s


def _singular(s: str) -> str:
    """Very small heuristic stemmer, just enough to catch common plural
    forms. Only strips from words long enough that stripping is safe
    (so "gas" or "yes" don't get mangled)."""
    if s.endswith("ies") and len(s) > 4:
        return s[:-3] + "y"
    if s.endswith("es") and len(s) > 4:
        return s[:-2]
    if s.endswith("s") and len(s) > 3:
        return s[:-1]
    return s


def answers_match(user_answer: str, accepted_answers: list) -> bool:
    """True if user_answer should be counted correct against any of the
    accepted answers, allowing for case, punctuation, whitespace, simple
    plural/singular differences, and minor typos."""
    norm_user = _normalize(user_answer)
    if not norm_user:
        return False

    for accepted in accepted_answers:
        norm_accepted = _normalize(accepted)
        if norm_user == norm_accepted:
            return True
        if _singular(norm_user) == _singular(norm_accepted):
            return True
        ratio = difflib.SequenceMatcher(None, norm_user, norm_accepted).ratio()
        if ratio >= FUZZY_THRESHOLD:
            return True
    return False
