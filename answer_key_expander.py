"""
Answer-key variant expander for IELTS answer keys.

Cambridge answer keys use a small set of notations to indicate acceptable
variants: parenthetical optional words ((the) hospital), suffix optionals
(holiday(s)), and slash alternatives (hospital / clinic). This expands
those into a flat list of literal acceptable strings, so the downstream
grading engine just checks membership — no notation-parsing needed at
grading time.

Deliberately NOT a general grammar/AST parser (rejected as over-engineering
for this problem — see project notes). Handles the common, high-frequency
cases robustly. Anything more complex (nested optionals, multiple slashes
combined with optionals in the same segment, e.g. "(the) local/regional
bank(s)") is explicitly flagged for human review rather than silently
guessed at — wrong-but-confident is worse than admitting uncertainty here.
"""

import re
from typing import TypedDict


class ExpansionResult(TypedDict):
    variants: list[str]
    needs_review: bool
    review_reason: str | None


def has_exclusion_pattern(line: str) -> bool:
    """
    Check if an answer-key line contains an exclusion pattern.
    
    Returns True if the line contains 'not' acting as a negative constraint
    immediately after an opening parenthesis. Catches:
    - (not     (with space after 'not')
    - (not)    (immediately closed)
    - (not-    (with hyphen after 'not')
    
    Ignores false positives like (notation) and (nothing).
    """
    # Pattern: opening paren, followed by 'not', followed by space, closing paren, or hyphen
    # This ensures 'not' is immediately after the opening paren
    pattern = r"\(not(\s|\)|-)"
    return bool(re.search(pattern, line, re.IGNORECASE))


def _expand_single_segment(segment: str) -> list[str]:
    """Expand one slash-delimited segment's parenthetical optionals."""
    segment = segment.strip()

    # Suffix optional: "holiday(s)" -> ["holiday", "holidays"]
    suffix_match = re.fullmatch(r"(\S+)\((\w+)\)", segment)
    if suffix_match:
        base, suffix = suffix_match.groups()
        return [base, base + suffix]

    # Prefix optional: "(the) hospital" -> ["hospital", "the hospital"]
    prefix_match = re.fullmatch(r"\(([^)]+)\)\s+(.+)", segment)
    if prefix_match:
        optional_prefix, rest = prefix_match.groups()
        return [rest, f"{optional_prefix} {rest}"]

    # No parenthetical — plain segment
    return [segment]


def expand_answer_variants(raw: str) -> ExpansionResult:
    raw = raw.strip()

    # Exclusion notation e.g. "bridge (not wooden bridge)" — don't guess, flag it.
    if has_exclusion_pattern(raw):
        return ExpansionResult(
            variants=[raw], needs_review=True,
            review_reason="exclusion notation '(not ...)' — needs human parsing, not auto-expanded"
        )

    segments = [s.strip() for s in raw.split("/")]

    # Genuine ambiguity: look at the words immediately touching each side of
    # the "/" itself, not just "does this segment contain a paren anywhere."
    # "holiday(s) / vacation(s)" — both words touching the slash carry their
    # own paren directly -> safe, expand independently.
    # "(the) local/regional bank(s)" — "local" and "regional" (the words
    # actually touching the slash) carry NO paren of their own, even though
    # the segment as a whole does elsewhere -> ambiguous, the optional
    # context likely needs to apply across the slash boundary and
    # per-segment expansion would silently produce the wrong phrase.
    has_any_parens = "(" in raw
    if has_any_parens and len(segments) > 1:
        for i in range(len(segments) - 1):
            left_word = segments[i].split()[-1] if segments[i].split() else ""
            right_word = segments[i + 1].split()[0] if segments[i + 1].split() else ""
            left_has_own_paren = "(" in left_word or ")" in left_word
            right_has_own_paren = "(" in right_word or ")" in right_word
            if not left_has_own_paren and not right_has_own_paren:
                return ExpansionResult(
                    variants=[raw], needs_review=True,
                    review_reason="slash connects bare words with no paren of their own, while the phrase has optional context elsewhere — likely needs to apply across the slash boundary, ambiguous to auto-expand"
                )

    variants: list[str] = []
    for seg in segments:
        variants.extend(_expand_single_segment(seg))

    # De-dupe while preserving order
    seen = set()
    deduped = []
    for v in variants:
        if v.lower() not in seen:
            seen.add(v.lower())
            deduped.append(v)

    return ExpansionResult(variants=deduped, needs_review=False, review_reason=None)


if __name__ == "__main__":
    test_cases = [
        ("(the) hospital", ["hospital", "the hospital"]),
        ("hospital / clinic", ["hospital", "clinic"]),
        ("holiday(s) / vacation(s)", ["holiday", "holidays", "vacation", "vacations"]),
        ("bridge (not wooden bridge)", None),  # flagged, not expanded
        ("(the) local/regional bank(s)", None),  # ambiguous, flagged
        ("market", ["market"]),  # plain answer, no notation
    ]
    for raw, expected in test_cases:
        result = expand_answer_variants(raw)
        if expected is None:
            status = "OK" if result["needs_review"] else "MISMATCH"
        else:
            status = "OK" if set(result["variants"]) == set(expected) and not result["needs_review"] else "MISMATCH"
        print(f"[{status}] {raw!r} -> variants={result['variants']} needs_review={result['needs_review']}")
