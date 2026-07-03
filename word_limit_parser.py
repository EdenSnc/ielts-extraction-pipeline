"""
Word-limit instruction parser for IELTS completion-type questions.

Cambridge IELTS uses a small, closed set of canonical phrasings for word-limit
instructions (e.g. "NO MORE THAN TWO WORDS"). This is a lookup-table parser,
not general NLP, matching the same design philosophy as answer_key_parser.py:
small closed format set, fuzzy-matched for OCR noise, tested against real text.

Only applicable to completion-type question_types (short_answer, summary_completion,
sentence_completion, table_completion, flowchart_completion, diagram_label_completion).
Never applies to multiple_choice, true_false_not_given, yes_no_not_given, or
matching_* types.

Writing task minimum-word-count ("at least 150 words") is a SEPARATE, structurally
different concept (minimum, not maximum) — handled by parse_min_word_count(), not
this parser. Do not conflate the two.
"""

import re
from typing import Optional, TypedDict


class AnswerConstraint(TypedDict):
    max_words: Optional[int]   # None only for pure "A NUMBER" with no word component -> 0
    allow_numbers: bool
    raw_instruction_text: str  # the exact matched clause, kept for auditability


_WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    # tolerate common OCR digit/letter confusion on these small number-words
    "0ne": 1, "tw0": 2, "thr33": 3,
}

_WORD_NUM_PATTERN = "|".join(_WORD_NUM.keys())

# Ordered from most specific to least specific — first match wins.
_PATTERNS = [
    # "NO MORE THAN {N} WORDS AND/OR A NUMBER" / "{N} WORD(S) AND/OR A NUMBER"
    (
        re.compile(
            rf"(no more than\s+)?({_WORD_NUM_PATTERN})\s+words?\s+and\s*/?\s*or\s+a\s+number",
            re.IGNORECASE,
        ),
        lambda m: AnswerConstraint(
            max_words=_WORD_NUM[m.group(2).lower()],
            allow_numbers=True,
            raw_instruction_text=m.group(0),
        ),
    ),
    # "NO MORE THAN {N} WORDS" (no number clause)
    (
        re.compile(
            rf"no more than\s+({_WORD_NUM_PATTERN})\s+words?\b",
            re.IGNORECASE,
        ),
        lambda m: AnswerConstraint(
            max_words=_WORD_NUM[m.group(1).lower()],
            allow_numbers=False,
            raw_instruction_text=m.group(0),
        ),
    ),
    # "ONE WORD ONLY"
    (
        re.compile(r"one\s+word\s+only", re.IGNORECASE),
        lambda m: AnswerConstraint(
            max_words=1, allow_numbers=False, raw_instruction_text=m.group(0)
        ),
    ),
    # standalone "A NUMBER" — no word component at all
    (
        re.compile(r"\ba\s+number\b(?!\s*of\s+word)", re.IGNORECASE),
        lambda m: AnswerConstraint(
            max_words=0, allow_numbers=True, raw_instruction_text=m.group(0)
        ),
    ),
]


def parse_word_limit(instruction_text: str) -> Optional[AnswerConstraint]:
    """
    Scan instruction_text for a Cambridge-style word-limit clause.
    Returns None if no recognizable pattern is found — caller should treat
    that as a review-flag trigger for completion-type questions, not a
    silent "no constraint" result.
    """
    for pattern, builder in _PATTERNS:
        match = pattern.search(instruction_text)
        if match:
            return builder(match)
    return None


def parse_min_word_count(instruction_text: str) -> Optional[int]:
    """
    Separate parser for Writing task minimum word counts
    ("Write at least 150 words"). Structurally different from the
    max-word completion constraint above — do not merge the two.
    """
    match = re.search(r"at least\s+(\d+)\s+words?", instruction_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


if __name__ == "__main__":
    # Smoke-test cases — REPLACE/EXTEND with real instruction text pulled
    # from 13.PDF before trusting this against the actual corpus. These are
    # illustrative of the canonical phrase set, not a substitute for testing
    # against real OCR output.
    test_cases = [
        ("Choose NO MORE THAN TWO WORDS from the passage for each answer.",
         {"max_words": 2, "allow_numbers": False}),
        ("Write ONE WORD ONLY.",
         {"max_words": 1, "allow_numbers": False}),
        ("Use NO MORE THAN THREE WORDS AND/OR A NUMBER.",
         {"max_words": 3, "allow_numbers": True}),
        ("Write A NUMBER for each answer.",
         {"max_words": 0, "allow_numbers": True}),
        ("Choose the correct letter, A, B, C or D.",  # multiple choice — no match expected
         None),
    ]
    for text, expected in test_cases:
        result = parse_word_limit(text)
        status = "OK" if (result is None) == (expected is None) and (
            expected is None or (result["max_words"] == expected["max_words"]
                                  and result["allow_numbers"] == expected["allow_numbers"])
        ) else "MISMATCH"
        print(f"[{status}] {text!r} -> {result}")
