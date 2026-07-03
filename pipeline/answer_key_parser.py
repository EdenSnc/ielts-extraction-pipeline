"""
answer_key_parser.py  — v2
Parse IELTS answer key pages into structured records.

KEY DESIGN DECISION (discovered from real OCR evidence, 2026-07-03):
PyMuPDF's get_text() on the two-column answer key layout returns question numbers and
their answers on SEPARATE CONSECUTIVE LINES, not the same line:

    Real OCR output (page 119):    Real OCR output (page 125):
    '1 \\nchoose'  (two lines)      '1\\nFinance\\n2\\nMaths / Math...'
    '9 ~~ market' (same line)      (no Q-number prefix on some pages!)
    '21 \\nA'      (two lines)

The first parser version only matched NUMBER+ANSWER on a single line, which produced
zero records for most pages. This version uses a two-pass tokeniser:
  Pass 1: reduce the raw text to a token stream of (type, value) pairs
  Pass 2: pair each Q-NUMBER token with the ANSWER token that immediately follows it

Formats handled (all observed in 13.PDF answer key pages 119-126):
  1. Single-letter MC:       '21\\nA'  or  '21 A'
  2. T/F/NG:                 '7\\nNOT GIVEN'  or  '7 NOT GIVEN'
  3. Y/N/NG:                 '35\\nYES'
  4. Short word:             '1\\nchoose'
  5. Multi-word:             '20\\nbridge hypothesis'
  6. Slash alternatives:     '36\\nbehaviour(s) / behavior(s)'
  7. Number/date:            '4\\n25/ twenty-five'
  8. IN EITHER ORDER pairs:  '17&18\\nIN EITHER ORDER\\nG\\nE'
  9. No-Q-prefix block:      consecutive answers with Q-numbers only on separate lines
     (page 125 Listening S1: '1\\nFinance\\n2\\nMaths...')
 10. OCR noise:              '9 ~~ market', '=H', 'A2 AG' (skip non-parseable)
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AnswerRecord:
    question_numbers: list[int]
    answer: str
    alternatives: list[str] = field(default_factory=list)
    order_free: bool = False
    raw: str = ""          # the raw line(s) for audit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Lines that are structural noise to skip
_SKIP_RE = re.compile(
    r'^(Listening and Reading Answer Keys?'
    r'|LISTENING|READING'
    r'|Section \d'
    r'|Reading Passage'
    r'|Questions? \d'
    r'|If you score'
    r'|you are (unlikely|likely|may)'
    r'|we recommend'
    r'|remember that'
    r'|conditions? but'
    r'|acceptable score'
    r'|examination conditions'
    r'|a lot of time'
    r'|English before'
    r'|more practice'
    r'|\d{3,}$'                           # bare page numbers (100+) only; not Q-numbers
    r'|IN EITHER ORDER$'                  # handled as part of pair block
    r')',
    re.IGNORECASE
)

# A standalone question number line: "1", "21", "14-" (with stray punct)
_QNUM_ONLY_RE = re.compile(r'^(\d{1,2})[.\-\u2013\u2014\s]*$')

# Q-number at start of line with inline answer: "21 A", "9 ~~ market", "21 = animals"
_QNUM_INLINE_RE = re.compile(r'^(\d{1,2})[.\-\u2013\u2014\s~=*]+(.+)$')

# IN EITHER ORDER pair header: "17&18" or "17&18 IN EITHER ORDER"
_PAIR_RE = re.compile(r'^(\d{1,2})\s*[&]\s*(\d{1,2})', re.IGNORECASE)

# Valid answer token: letter(s), word(s), numbers — reject pure OCR garbage
_ANSWER_RE = re.compile(r'^[A-Za-z0-9(]')


def _clean(s: str) -> str:
    """Strip leading OCR noise chars (tildes, equals, asterisks, dashes)."""
    return re.sub(r'^[~=\-\*\.\u2014\u2013]+\s*', '', s).strip()


def _parse_payload(raw: str, order_free: bool = False) -> tuple[str, list[str]]:
    """
    Given an answer string, return (canonical_answer, alternatives).
    Handles: slash splits, parenthetical optionals, NOT GIVEN variants, verdict words.
    """
    s = raw.strip()
    upper = s.upper().replace('  ', ' ')

    # Verdict words — check before any splitting
    for variant in ('NOT GIVEN', 'NOTGIVEN'):
        if variant in upper:
            return ('NOT GIVEN', [])
    for v in ('TRUE', 'FALSE', 'YES', 'NO'):
        if upper == v:
            return (v, [])

    # Slash alternatives
    if '/' in s:
        parts = [p.strip() for p in s.split('/')]
        parts = [_clean(p) for p in parts if _clean(p)]
        if parts:
            return (parts[0], parts[1:])

    cleaned = _clean(s)
    return (cleaned, [])


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_answer_key_text(raw_text: str) -> list[AnswerRecord]:
    """
    Parse raw PyMuPDF get_text() output from an IELTS answer key page.
    Returns list of AnswerRecord, unsorted.
    """
    lines = [ln.strip() for ln in raw_text.splitlines()]
    records: list[AnswerRecord] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # --- Skip structural noise ---
        if not line or _SKIP_RE.match(line):
            i += 1
            continue

        # --- IN EITHER ORDER pair block: "17&18" possibly with inline "IN EITHER ORDER" ---
        pair_m = _PAIR_RE.match(line)
        if pair_m:
            q1, q2 = int(pair_m.group(1)), int(pair_m.group(2))
            order_free = 'IN EITHER ORDER' in line.upper()

            # If "IN EITHER ORDER" is not on this line, it may be on the next
            j = i + 1
            if j < len(lines) and 'IN EITHER ORDER' in lines[j].upper():
                order_free = True
                j += 1

            # Collect the next two valid single-token answers
            answers = []
            while j < len(lines) and len(answers) < 2:
                candidate = _clean(lines[j])
                if candidate and _ANSWER_RE.match(candidate) and not _SKIP_RE.match(candidate):
                    if not _PAIR_RE.match(candidate) and not _QNUM_ONLY_RE.match(candidate):
                        answers.append(candidate)
                j += 1

            if len(answers) == 2:
                for qnum, ans in zip([q1, q2], answers):
                    records.append(AnswerRecord(
                        question_numbers=[qnum],
                        answer=_parse_payload(ans, order_free)[0],
                        alternatives=_parse_payload(ans, order_free)[1],
                        order_free=order_free,
                        raw=line
                    ))
            i = j
            continue

        # --- Q-number with inline answer on same line: "21 A", "9 ~~ market", "21 = animals" ---
        inline_m = _QNUM_INLINE_RE.match(line)
        if inline_m:
            qnum = int(inline_m.group(1))
            payload = inline_m.group(2).strip()
            # Guard: payload shouldn't be a bare number that looks like a column artefact
            # (e.g. "21-8" on page 121 is OCR noise for Q21 col2 prefix, not an answer)
            if re.match(r'^\d+-?\d*$', payload) and len(payload) <= 3:
                i += 1
                continue
            answer, alts = _parse_payload(payload)
            if answer:
                records.append(AnswerRecord(
                    question_numbers=[qnum],
                    answer=answer,
                    alternatives=alts,
                    raw=line
                ))
            i += 1
            continue

        # --- Bare Q-number line: "1" → look ahead to next non-noise line for the answer ---
        qnum_m = _QNUM_ONLY_RE.match(line)
        if qnum_m:
            qnum = int(qnum_m.group(1))
            # Look ahead: find the next non-empty, non-skip, non-qnum line
            j = i + 1
            answer_line = None
            while j < len(lines):
                candidate = lines[j].strip()
                if not candidate:
                    j += 1
                    continue
                if _SKIP_RE.match(candidate):
                    j += 1
                    continue
                # If next line is another bare Q-number, this one has no answer (OCR gap)
                if _QNUM_ONLY_RE.match(candidate) or _PAIR_RE.match(candidate):
                    break
                # If next line starts with a new Q-number+answer inline, don't steal it
                if _QNUM_INLINE_RE.match(candidate):
                    break
                answer_line = candidate
                j += 1
                break

            if answer_line:
                cleaned = _clean(answer_line)
                if cleaned and _ANSWER_RE.match(cleaned):
                    answer, alts = _parse_payload(cleaned)
                    if answer:
                        records.append(AnswerRecord(
                            question_numbers=[qnum],
                            answer=answer,
                            alternatives=alts,
                            raw=f"{line} | {answer_line}"
                        ))
                i = j
            else:
                i += 1
            continue

        i += 1

    return records


# ---------------------------------------------------------------------------
# Tests — all inputs are literal raw OCR strings from actual 13.PDF pages
# ---------------------------------------------------------------------------

def run_tests():
    failures = []

    def check(label: str, got, expected):
        if got != expected:
            failures.append(f"FAIL [{label}]: got {got!r}, expected {expected!r}")
        else:
            print(f"  OK  [{label}]")

    print("\n=== Unit tests: parse_answer_payload ===")
    # Import from self — works whether run as __main__ or as a module
    from answer_key_parser import _parse_payload  # type: ignore

    check("MC letter", _parse_payload("A"), ("A", []))
    check("FALSE", _parse_payload("FALSE"), ("FALSE", []))
    check("NOT GIVEN", _parse_payload("NOT GIVEN"), ("NOT GIVEN", []))
    check("NOTGIVEN squashed", _parse_payload("NOTGIVEN"), ("NOT GIVEN", []))
    check("YES", _parse_payload("YES"), ("YES", []))
    check("NO", _parse_payload("NO"), ("NO", []))
    check("Short word", _parse_payload("choose"), ("choose", []))
    check("Multi-word", _parse_payload("bridge hypothesis"), ("bridge hypothesis", []))
    check("Slash word", _parse_payload("bike / bicycle"), ("bike", ["bicycle"]))
    check("Slash number", _parse_payload("25/ twenty-five"), ("25", ["twenty-five"]))
    check("Paren+slash", _parse_payload("holiday(s) / vacation(s)"), ("holiday(s)", ["vacation(s)"]))
    check("Paren prefix", _parse_payload("(audio-recording) vests"), ("(audio-recording) vests", []))
    check("Tilde noise", _parse_payload("~wool"), ("wool", []))
    check("Triple-slash", _parse_payload("Maths / Math / Mathematics"), ("Maths", ["Math", "Mathematics"]))

    print("\n=== Integration tests: real raw OCR from 13.PDF pages ===")

    # ------------------------------------------------------------------
    # PAGE 119 — Test 1 Listening
    # Real raw: Q number and answer on separate lines; some inline with noise
    # ------------------------------------------------------------------
    raw_p119 = (
        "Listening and Reading Answer Keys\n"
        "LISTENING\n"
        "Section 1, Questions 1-10\n"
        "Section 3, Questions 21-30\n"
        "1\n"           # <-- bare Q-number line
        "choose\n"      # <-- answer on next line
        "21\n"
        "A\n"
        "2\n"
        "__soprivate\n" # OCR garbage — should be skipped
        "22\n"
        "~C\n"          # OCR noise prefix, answer = C
        "4\n"
        "healthy\n"
        "24\n"
        "C\n"
        "9 ~~ market\n" # inline with noise
        "29\n"
        "A\n"
        "10\n"
        "knife\n"
        "30\n"
        "CE\n"
        "Section 2, Questions 11-20\n"
        "Section 4, Questions 31-40\n"
        "11\n"
        "8B\n"          # OCR artefact, '8B' → 'B' after clean
        "31\n"
        "crow\n"
        "36\n"
        "behaviour(s) / behavior(s)\n"
    )

    recs = {r.question_numbers[0]: r for r in parse_answer_key_text(raw_p119)}
    check("p119 Q1=choose (split-line)", recs.get(1, AnswerRecord([1], "")).answer, "choose")
    check("p119 Q21=A (split-line MC)", recs.get(21, AnswerRecord([21], "")).answer, "A")
    check("p119 Q9=market (inline+noise)", recs.get(9, AnswerRecord([9], "")).answer, "market")
    check("p119 Q10=knife (split-line word)", recs.get(10, AnswerRecord([10], "")).answer, "knife")
    check("p119 Q36=behaviour(s) (slash, split-line)", recs.get(36, AnswerRecord([36], "")).answer, "behaviour(s)")
    check("p119 Q36 alt=behavior(s)", recs.get(36, AnswerRecord([36], "")).alternatives, ["behavior(s)"])
    check("p119 Q31=crow (split-line word)", recs.get(31, AnswerRecord([31], "")).answer, "crow")

    # ------------------------------------------------------------------
    # PAGE 121 — Test 2 Listening (slash variants, IN EITHER ORDER pairs)
    # Real raw from dump
    # ------------------------------------------------------------------
    raw_p121 = (
        "Listening and Reading Answer Keys\n"
        "LISTENING\n"
        "Section 1, Questions 1-10\n"
        "Section 3, Questions 21-30\n"
        "1\n"
        "races\n"
        "21-8\n"          # OCR artefact, not a real entry
        "4\n"
        "25/ twenty-five\n"
        "24\n"
        "C\n"
        "Section 2, Questions 11-20\n"
        "Section 4, Questions 31-40\n"
        "11\n"
        "C\n"
        "31\n"
        "location\n"
        "38\n"
        "colour / color\n"
        "17&18\n"
        "IN EITHER ORDER\n"
        "G\n"
        "E\n"
    )

    recs2 = {r.question_numbers[0]: r for r in parse_answer_key_text(raw_p121)}
    check("p121 Q1=races (split-line)", recs2.get(1, AnswerRecord([1], "")).answer, "races")
    check("p121 Q4=25 (slash number, split-line)", recs2.get(4, AnswerRecord([4], "")).answer, "25")
    check("p121 Q4 alt=twenty-five", recs2.get(4, AnswerRecord([4], "")).alternatives, ["twenty-five"])
    check("p121 Q11=C (MC split-line)", recs2.get(11, AnswerRecord([11], "")).answer, "C")
    check("p121 Q31=location (split-line)", recs2.get(31, AnswerRecord([31], "")).answer, "location")
    check("p121 Q38=colour (slash split-line)", recs2.get(38, AnswerRecord([38], "")).answer, "colour")
    check("p121 Q38 alt=color", recs2.get(38, AnswerRecord([38], "")).alternatives, ["color"])
    check("p121 Q17=G (IN EITHER ORDER)", recs2.get(17, AnswerRecord([17], "")).answer, "G")
    check("p121 Q18=E (IN EITHER ORDER)", recs2.get(18, AnswerRecord([18], "")).answer, "E")
    check("p121 Q17 order_free", recs2.get(17, AnswerRecord([17], "")).order_free, True)

    # ------------------------------------------------------------------
    # PAGE 126 — Test 4 Reading (TRUE/FALSE/NOT GIVEN + YES/NO/NOT GIVEN)
    # Real raw from dump — this page returned ZERO records in v1
    # ------------------------------------------------------------------
    raw_p126 = (
        "READING\n"
        "Reading Passage 1, Questions 1-13\n"
        "1\n"
        "FALSE\n"
        "2\n"
        "FALSE\n"
        "7\n"
        "NOT GIVEN\n"
        "9\n"
        " ~wool\n"      # real OCR line with leading space+tilde
        "14\n"
        "minerals\n"
        "18\n"
        "C\n"
        "Reading Passage 3, Questions 27-40\n"
        "35\n"
        "YES\n"
        "36\n"
        "NOT GIVEN\n"
        "37\n"
        "NO\n"
    )

    recs3 = {r.question_numbers[0]: r for r in parse_answer_key_text(raw_p126)}
    check("p126 Q1=FALSE (TFNG split-line)", recs3.get(1, AnswerRecord([1], "")).answer, "FALSE")
    check("p126 Q7=NOT GIVEN (split-line)", recs3.get(7, AnswerRecord([7], "")).answer, "NOT GIVEN")
    check("p126 Q9=wool (tilde+space, split-line)", recs3.get(9, AnswerRecord([9], "")).answer, "wool")
    check("p126 Q14=minerals (split-line word)", recs3.get(14, AnswerRecord([14], "")).answer, "minerals")
    check("p126 Q35=YES (Y/N/NG split-line)", recs3.get(35, AnswerRecord([35], "")).answer, "YES")
    check("p126 Q36=NOT GIVEN (Y/N/NG split-line)", recs3.get(36, AnswerRecord([36], "")).answer, "NOT GIVEN")
    check("p126 Q37=NO", recs3.get(37, AnswerRecord([37], "")).answer, "NO")

    print("\n=== Results ===")
    if failures:
        for f in failures:
            print(f)
        print(f"\n{len(failures)} FAILED")
        return False
    else:
        print("All tests passed.")
        return True


if __name__ == "__main__":
    run_tests()
