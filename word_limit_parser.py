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
    must_be_from_text: bool    # True when instruction says "from the passage/text"
                               # -> grading must strict-match; synonyms not acceptable
    raw_instruction_text: str  # the exact matched clause, kept for auditability


_WORD_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    # tolerate common OCR digit/letter confusion on these small number-words
    "0ne": 1, "tw0": 2, "thr33": 3,
}

_WORD_NUM_PATTERN = "|".join(_WORD_NUM.keys())

# Detects Cambridge phrasings that restrict answers to exact passage text.
# Synonyms are NOT acceptable when this matches.
_FROM_TEXT_RE = re.compile(
    r"from\s+the\s+(passage|text|article|reading|recording)",
    re.IGNORECASE,
)

# Ordered from most specific to least specific — first match wins.
# Each entry: (compiled_pattern, max_words_extractor, allow_numbers)
# must_be_from_text is detected separately on the full instruction string.
_PATTERNS: list[tuple] = [
    # "NO MORE THAN {N} WORDS AND/OR A NUMBER"
    (
        re.compile(
            rf"(no more than\s+)?({_WORD_NUM_PATTERN})\s+words?\s+and\s*/?\s*or\s+a\s+number",
            re.IGNORECASE,
        ),
        lambda m: _WORD_NUM[m.group(2).lower()],  # max_words
        True,                                       # allow_numbers
    ),
    # "NO MORE THAN {N} WORDS" (no number clause)
    (
        re.compile(
            rf"no more than\s+({_WORD_NUM_PATTERN})\s+words?\b",
            re.IGNORECASE,
        ),
        lambda m: _WORD_NUM[m.group(1).lower()],
        False,
    ),
    # "ONE WORD ONLY"
    (
        re.compile(r"one\s+word\s+only", re.IGNORECASE),
        lambda m: 1,
        False,
    ),
    # standalone "A NUMBER" — no word component at all
    (
        re.compile(r"\ba\s+number\b(?!\s*of\s+word)", re.IGNORECASE),
        lambda m: 0,
        True,
    ),
]


def parse_word_limit(instruction_text: str) -> Optional[AnswerConstraint]:
    """
    Scan instruction_text for a Cambridge-style word-limit clause.
    Returns None if no recognizable pattern is found — caller should treat
    that as a review-flag trigger for completion-type questions, not a
    silent "no constraint" result.

    must_be_from_text is True when the instruction contains a phrase like
    "from the passage / text / recording" — grading downstream must
    strict-match; synonyms are not acceptable.
    """
    must_be_from_text = bool(_FROM_TEXT_RE.search(instruction_text))
    for pattern, max_words_fn, allow_numbers in _PATTERNS:
        match = pattern.search(instruction_text)
        if match:
            return AnswerConstraint(
                max_words=max_words_fn(match),
                allow_numbers=allow_numbers,
                must_be_from_text=must_be_from_text,
                raw_instruction_text=match.group(0),
            )
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
    # Tests against canonical Cambridge phrasings.
    # must_be_from_text column added — verify it fires only when expected.
    test_cases = [
        # (instruction_text, expected_max_words, expected_allow_numbers, expected_must_be_from_text)
        ("Choose NO MORE THAN TWO WORDS from the passage for each answer.",
         2, False, True),
        ("Write ONE WORD ONLY from the text.",
         1, False, True),
        ("Use NO MORE THAN THREE WORDS AND/OR A NUMBER.",
         3, True, False),
        ("Write A NUMBER for each answer.",
         0, True, False),
        ("Choose ONE WORD ONLY.",
         1, False, False),
        ("Choose the correct letter, A, B, C or D.",  # MC — no match
         None, None, None),
    ]
    all_ok = True
    for text, exp_mw, exp_an, exp_mft in test_cases:
        result = parse_word_limit(text)
        if exp_mw is None:
            ok = result is None
        else:
            ok = (
                result is not None
                and result["max_words"] == exp_mw
                and result["allow_numbers"] == exp_an
                and result["must_be_from_text"] == exp_mft
            )
        status = "OK" if ok else "MISMATCH"
        if not ok:
            all_ok = False
        print(f"[{status}] {text!r}")
        if result is not None:
            print(f"       max_words={result['max_words']} allow_numbers={result['allow_numbers']} "
                  f"must_be_from_text={result['must_be_from_text']}")
    print()
    print("All tests passed." if all_ok else "FAILURES above — fix before proceeding.")

