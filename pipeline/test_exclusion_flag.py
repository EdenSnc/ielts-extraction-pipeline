"""
Unit tests for has_exclusion_pattern() helper function.

Tests that the function correctly identifies exclusion patterns while
ignoring false positives.
"""

import sys
import os

# Add parent directory to path to import answer_key_expander
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from answer_key_expander import has_exclusion_pattern


def test_exclusion_pattern():
    """Test that has_exclusion_pattern correctly identifies exclusion patterns."""
    
    # Test cases that SHOULD return True (exclusion patterns)
    positive_cases = [
        "bridge (not wooden bridge)",  # space after 'not'
        "bridge (not)",  # immediately closed
        "bridge (not-wooden)",  # hyphen after 'not'
        "answer (not acceptable)",  # another space case
        "(not) simple",  # just the pattern
        "(not-)",  # hyphen pattern
        "something (not something else)",  # case insensitive
        "SOMETHING (NOT SOMETHING)",  # uppercase
        "Something (Not Something)",  # mixed case
    ]
    
    # Test cases that SHOULD return False (false positives)
    negative_cases = [
        "notation",  # no parentheses at all
        "(notation)",  # has parentheses but no 'not'
        "(nothing)",  # contains 'not' as part of 'nothing'
        "something (note)",  # 'note' not 'not'
        "another (knot)",  # 'knot' not 'not'
        "ignore (notable)",  # 'notable' not 'not'
        "test (annotate)",  # 'annotate' not 'not'
        "plain text",  # no pattern
        "( not )",  # space before 'not' - should not match
        "not (something)",  # 'not' before paren - should not match
    ]
    
    print("Testing positive cases (should return True):")
    all_positive_passed = True
    for case in positive_cases:
        result = has_exclusion_pattern(case)
        status = "PASS" if result else "FAIL"
        if not result:
            all_positive_passed = False
        print(f"  [{status}] {case!r} -> {result}")
    
    print("\nTesting negative cases (should return False):")
    all_negative_passed = True
    for case in negative_cases:
        result = has_exclusion_pattern(case)
        status = "PASS" if not result else "FAIL"
        if result:
            all_negative_passed = False
        print(f"  [{status}] {case!r} -> {result}")
    
    print("\n" + "="*60)
    if all_positive_passed and all_negative_passed:
        print("ALL TESTS PASSED")
        return 0
    else:
        print("SOME TESTS FAILED")
        if not all_positive_passed:
            print("  - Some positive cases failed (returned False when True expected)")
        if not all_negative_passed:
            print("  - Some negative cases failed (returned True when False expected)")
        return 1


if __name__ == "__main__":
    exit_code = test_exclusion_pattern()
    sys.exit(exit_code)
