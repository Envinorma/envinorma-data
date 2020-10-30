from lib.structure_detection import (
    _pattern_is_increasing,
    NumberingPattern,
    _is_valid,
    _detect_longest_matched_pattern,
    NumberingPattern,
    prefixes_are_continuous,
    PATTERN_NAME_TO_LIST,
)
from lib.numbering_exceptions import MAX_PREFIX_LEN, EXCEPTION_PREFIXES


def test_pattern_is_increasing():
    assert _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'd) '])
    assert not _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'd) ', 'a) '])
    assert _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'x) ', 'y) '])


def test_prefixes_are_continuous():
    prefixes = PATTERN_NAME_TO_LIST[NumberingPattern.NUMERIC_D1]
    assert prefixes_are_continuous(prefixes, prefixes)
    assert not prefixes_are_continuous(prefixes, prefixes[1:5])


def test_is_valid():
    assert not _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar ;'])
    assert _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar :'])
    assert not _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar :', 'a) Pi', 'b) Pa'])


def test_detect_longest_matched_pattern():
    assert _detect_longest_matched_pattern('1. 1. bnjr') == NumberingPattern.NUMERIC_D2_SPACE
    assert _detect_longest_matched_pattern('1. 2. 3. bnjr') == NumberingPattern.NUMERIC_D3_SPACE
    assert _detect_longest_matched_pattern('1. 2.3. bnjr') == NumberingPattern.NUMERIC_D1
    assert _detect_longest_matched_pattern('1.') is None
    assert _detect_longest_matched_pattern('') is None


def text_exceptions():
    for exc in EXCEPTION_PREFIXES:
        assert len(exc) <= MAX_PREFIX_LEN
