"""
answer_key_parser.py
Parse IELTS answer key pages into structured records.

Formats found in 13.PDF answer keys (pages 119-126) that a parser must handle:

1. SINGLE LETTER MC:     "21 A", "22 B", "1 C"
2. MULTI-LETTER MC:      "17&18 IN EITHER ORDER / G / E"  (two answers, order-free)
3. SHORT WORD:           "1 choose", "2 insurance", "31 location"
4. MULTI-WORD TEXT:      "20 bridge hypothesis", "22 (audio-recording) vests", "18 recording devices"
5. NUMBER/DATE:          "4 25/ twenty-five", "4 30/ thirty", "1 17 / seventeen"
6. WORD WITH VARIANT:    "2 bike / bicycle", "5 holiday(s) / vacation(s)", "32 universities / university"
7. TRUE/FALSE/NG:        "1 FALSE", "7 NOT GIVEN", "10 TRUE", "39 YES", "37 NO"
   (IELTS uses both TRUE/FALSE/NOT GIVEN and YES/NO/NOT GIVEN depending on question type)
8. ROMAN/LETTER HEADING: "27 C" (where C is a heading label, not distinguishable from MC by format alone — must rely on question-type context)
9. PARENTHETICAL ALTS:   "22 (audio-recording) vests"  — parenthetical part is optional
10. MULTI-NUMERAL GROUPS: "27&28 IN EITHER ORDER / B / C / D / E"

NOTE: OCR artifacts from the PDF layout are significant — the PDF columns cause items from
two separate columns to be interleaved in extracted text (e.g. "1 choose\n21 A\n2 insurance\n22 B"
is actually col1: Q1, Q2... and col2: Q21, Q22...). The parser must handle this interleaving.
"""

import re
from dataclasses import dataclass, field
from typing import Optional


VERDICT_WORDS = frozenset(["TRUE", "FALSE", "NOT GIVEN", "NOTGIVEN", "YES", "NO"])


@dataclass
class AnswerRecord:
    question_numbers: list[int]       # may be >1 for "17&18 IN EITHER ORDER"
    answer: str                        # canonical answer string (normalised)
    alternatives: list[str] = field(default_factory=list)  # from "/" splits
    order_free: bool = False           # True when "IN EITHER ORDER" present
    raw: str = ""                      # original unparsed text for audit


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

def normalise_verdict(s: str) -> str:
    """Collapse OCR variants of verdict answers."""
    s = s.strip().upper()
    if s in ("NOT GIVEN", "NOTGIVEN", "NOT  GIVEN"):
        return "NOT GIVEN"
    return s


def clean_token(s: str) -> str:
    s = s.strip()
    # Strip stray leading punctuation from OCR artefacts (e.g. "=##H" → skip, "~wool" → "wool")
    s = re.sub(r'^[=~\-\*\.]+', '', s).strip()
    return s


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

# Match lines like:  "21 A", "1 choose", "20 bridge hypothesis", "4 25/ twenty-five"
# Optionally prefixed with a period or dash from OCR noise: "31." or "35�"
_LINE_RE = re.compile(
    r'^(\d+)(?:[\.&\-\u2013\u2014\s]*)(\d+)?\s*'   # Q number(s)
    r'(IN EITHER ORDER\s*)?'                          # optional order-free marker
    r'(.+)?$',                                        # answer payload
    re.IGNORECASE
)

# "17&18 IN EITHER ORDER\nG\nE" — multi-line pair
_PAIR_RE = re.compile(r'(\d+)\s*[&]\s*(\d+)', re.IGNORECASE)


def parse_answer_payload(payload: str, order_free: bool = False) -> tuple[str, list[str], bool]:
    """
    Given the answer payload string (after the question number), return:
      (canonical_answer, alternatives, order_free)

    Handles:
     - "A"                     → ("A", [], False)
     - "FALSE"                  → ("FALSE", [], False)
     - "NOT GIVEN"              → ("NOT GIVEN", [], False)
     - "bike / bicycle"         → ("bike", ["bicycle"], False)
     - "25/ twenty-five"        → ("25", ["twenty-five"], False)
     - "(audio-recording) vests"→ ("(audio-recording) vests", [], False)  kept as-is
     - "G\nE" after IN EITHER ORDER → ("G", ["E"], True)
    """
    payload = payload.strip()

    # Check for verdict words first (before splitting on "/")
    upper = payload.upper().replace("  ", " ")
    for v in ("NOT GIVEN", "NOTGIVEN"):
        if v in upper:
            return ("NOT GIVEN", [], order_free)
    for v in ("TRUE", "FALSE", "YES", "NO"):
        if upper == v:
            return (v, [], order_free)

    # Slash-separated alternatives (e.g. "bike / bicycle", "25/ twenty-five")
    if "/" in payload:
        parts = [clean_token(p) for p in payload.split("/")]
        parts = [p for p in parts if p]  # remove empty
        if parts:
            return (parts[0], parts[1:], order_free)

    cleaned = clean_token(payload)
    return (cleaned, [], order_free)


def parse_answer_key_text(raw_text: str) -> list[AnswerRecord]:
    """
    Parse raw OCR text from an IELTS answer key page into AnswerRecord objects.

    Handles column interleaving: the PDF has two columns so lines alternate
    between column 1 and column 2 question numbers.

    Returns list of AnswerRecord, unsorted (caller should sort by question_numbers[0]).
    """
    records = []
    lines = [l.strip() for l in raw_text.splitlines()]

    i = 0
    pending_pair: Optional[tuple[int, int]] = None  # (q1, q2) waiting for answers

    while i < len(lines):
        line = lines[i]

        # Skip section headers and boilerplate
        if re.match(r'^(Section|Listening|Reading|LISTENING|READING|Questions|If you score|you are|we recommend|you may|remember|ANSWER KEY)', line, re.IGNORECASE):
            i += 1
            continue
        if not line or re.match(r'^[0-9]{2,3}$', line):  # page numbers
            i += 1
            continue

        # "17&18 IN EITHER ORDER" — look ahead for the two answer lines
        pair_m = _PAIR_RE.match(line)
        if pair_m:
            q1, q2 = int(pair_m.group(1)), int(pair_m.group(2))
            order_free = 'IN EITHER ORDER' in line.upper()
            # collect next non-empty non-header lines as answers
            answers = []
            j = i + 1
            while j < len(lines) and len(answers) < 2:
                candidate = clean_token(lines[j])
                if candidate and re.match(r'^[A-Z]$', candidate):
                    answers.append(candidate)
                elif candidate and not re.match(r'^(Section|Listening|Reading|IN EITHER)', candidate, re.I):
                    answers.append(candidate)
                j += 1
            if len(answers) >= 2:
                records.append(AnswerRecord(
                    question_numbers=[q1],
                    answer=answers[0],
                    alternatives=[],
                    order_free=order_free,
                    raw=line
                ))
                records.append(AnswerRecord(
                    question_numbers=[q2],
                    answer=answers[1],
                    alternatives=[],
                    order_free=order_free,
                    raw=line
                ))
            i = j
            continue

        # Standard "NUMBER answer" line
        # Match: "21 A", "1 choose", "20 bridge hypothesis", "4 25/ twenty-five", "9 FALSE"
        m = re.match(r'^(\d+)[\.\u2013\u2014\s�]+(.+)$', line)
        if m:
            qnum = int(m.group(1))
            payload = m.group(2).strip()
            answer, alts, order_free = parse_answer_payload(payload)
            if answer:  # skip OCR garbage (e.g. "=##H" cleaned to empty)
                records.append(AnswerRecord(
                    question_numbers=[qnum],
                    answer=answer,
                    alternatives=alts,
                    order_free=order_free,
                    raw=line
                ))
            i += 1
            continue

        i += 1

    return records


# ---------------------------------------------------------------------------
# Test cases derived from actual 13.PDF answer key text (pages 119-126)
# ---------------------------------------------------------------------------

def run_tests():
    failures = []

    def check(label, got, expected):
        if got != expected:
            failures.append(f"FAIL [{label}]: got {got!r}, expected {expected!r}")
        else:
            print(f"  OK  [{label}]")

    print("\n=== Unit tests for parse_answer_payload ===")

    # Format 1: single-letter MC
    a, alts, of = parse_answer_payload("A")
    check("MC single-letter", (a, alts, of), ("A", [], False))

    # Format 2: TRUE/FALSE/NOT GIVEN (T/F/NG)
    a, alts, of = parse_answer_payload("FALSE")
    check("TFNG FALSE", (a, alts, of), ("FALSE", [], False))

    a, alts, of = parse_answer_payload("NOT GIVEN")
    check("TFNG NOT GIVEN", (a, alts, of), ("NOT GIVEN", [], False))

    a, alts, of = parse_answer_payload("NOTGIVEN")  # OCR run-together variant
    check("TFNG NOTGIVEN squashed", (a, alts, of), ("NOT GIVEN", [], False))

    # Format 3: YES/NO/NOT GIVEN
    a, alts, of = parse_answer_payload("YES")
    check("Y/N/NG YES", (a, alts, of), ("YES", [], False))

    a, alts, of = parse_answer_payload("NO")
    check("Y/N/NG NO", (a, alts, of), ("NO", [], False))

    # Format 4: short word
    a, alts, of = parse_answer_payload("choose")
    check("Short word", (a, alts, of), ("choose", [], False))

    # Format 5: multi-word text
    a, alts, of = parse_answer_payload("bridge hypothesis")
    check("Multi-word", (a, alts, of), ("bridge hypothesis", [], False))

    # Format 6: slash variants (word)
    a, alts, of = parse_answer_payload("bike / bicycle")
    check("Slash word variant", (a, alts, of), ("bike", ["bicycle"], False))

    # Format 6b: slash variants (number)
    a, alts, of = parse_answer_payload("25/ twenty-five")
    check("Slash number variant", (a, alts, of), ("25", ["twenty-five"], False))

    # Format 6c: parenthetical optional suffix
    a, alts, of = parse_answer_payload("holiday(s) / vacation(s)")
    check("Paren optional+slash", (a, alts, of), ("holiday(s)", ["vacation(s)"], False))

    # Format 6d: multi-word with paren prefix
    a, alts, of = parse_answer_payload("(audio-recording) vests")
    check("Paren prefix multi-word", (a, alts, of), ("(audio-recording) vests", [], False))

    # Format 7: OCR garbage leading chars
    a, alts, of = parse_answer_payload("~wool")
    check("OCR tilde prefix", (a, alts, of), ("wool", [], False))

    # Format 8: "universities / university"
    a, alts, of = parse_answer_payload("universities / university")
    check("Universities variant", (a, alts, of), ("universities", ["university"], False))

    print("\n=== Integration test: parse full answer key block ===")

    # Simulate interleaved two-column text from page 121 (Test 2 Listening)
    sample_page_121 = """Listening and Reading Answer Keys
LISTENING
Section 1, Questions 1-10
Section 3, Questions 21-30
1 races
21-8
2 insurance
22 A
3 Jerriz
2a 72Ge
4 25/ twenty-five
24 C
5 stadium
25 A
6 park
26 A
7 coffee
27 se
8 leader
28 D
9 route
29 G
10 lights
30 8B
Section 2, Questions 11-20
Section 4, Questions 31-40
11 C
31 location
12 B
32 world
13 A
33 personal
14 B
34 attention
15 A
35 name
16 A
36 network
17&18 IN EITHER ORDER
37 frequency
G
38 colour / color
E
39 brain
19&20 IN EITHER ORDER
40 self
B
D"""

    records = parse_answer_key_text(sample_page_121)
    rec_map = {r.question_numbers[0]: r for r in records}

    check("Q1=races", rec_map.get(1, AnswerRecord([1], "")).answer, "races")
    check("Q4=25 (slash variant)", rec_map.get(4, AnswerRecord([4], "")).answer, "25")
    check("Q4 alt=twenty-five", rec_map.get(4, AnswerRecord([4], "")).alternatives, ["twenty-five"])
    check("Q11=C (MC)", rec_map.get(11, AnswerRecord([11], "")).answer, "C")
    check("Q31=location (word)", rec_map.get(31, AnswerRecord([31], "")).answer, "location")
    check("Q38=colour (slash)", rec_map.get(38, AnswerRecord([38], "")).answer, "colour")
    check("Q38 alt=color", rec_map.get(38, AnswerRecord([38], "")).alternatives, ["color"])

    # Simulate page 126 (TRUE/FALSE/NOT GIVEN + YES/NO/NOT GIVEN)
    sample_page_126 = """READING
Reading Passage 1, Questions 1-13
1 FALSE
2 FALSE
3 TRUE
4 TRUE
5 FALSE
6 TRUE
7 NOT GIVEN
8 TRUE
9 wool
10 navigator
11 gale
12 training
13 fire
Reading Passage 3, Questions 27-40
35 YES
36 NOT GIVEN
37 NO
38 NOT GIVEN
39 YES
40 NO"""

    records2 = parse_answer_key_text(sample_page_126)
    rec_map2 = {r.question_numbers[0]: r for r in records2}

    check("Q1=FALSE (TFNG)", rec_map2.get(1, AnswerRecord([1],"")).answer, "FALSE")
    check("Q7=NOT GIVEN", rec_map2.get(7, AnswerRecord([7],"")).answer, "NOT GIVEN")
    check("Q9=wool (short word after TFNG block)", rec_map2.get(9, AnswerRecord([9],"")).answer, "wool")
    check("Q35=YES (Y/N/NG)", rec_map2.get(35, AnswerRecord([35],"")).answer, "YES")
    check("Q36=NOT GIVEN (Y/N/NG)", rec_map2.get(36, AnswerRecord([36],"")).answer, "NOT GIVEN")
    check("Q37=NO", rec_map2.get(37, AnswerRecord([37],"")).answer, "NO")

    print("\n=== Results ===")
    if failures:
        for f in failures:
            print(f)
        print(f"\n{len(failures)} test(s) FAILED")
    else:
        print("All tests passed.")
    return len(failures) == 0


if __name__ == "__main__":
    run_tests()
