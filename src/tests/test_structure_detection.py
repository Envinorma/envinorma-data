from lib.structure_detection import (
    _pattern_is_increasing,
    NumberingPattern,
    _is_valid,
    _detect_longest_matched_pattern,
    NumberingPattern,
    prefixes_are_continuous,
    PATTERN_NAME_TO_LIST,
    _smart_detect_pattern,
    detect_patterns_if_exists,
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


def test_exceptions():
    for exc in EXCEPTION_PREFIXES:
        assert len(exc) <= MAX_PREFIX_LEN


def test_smart_detect_pattern():
    pattern = _smart_detect_pattern(
        "1. Les zones d'effets Z1 et Z2 définies par l'arrêté du 20 a erez"
    )  # in EXCEPTION_PREFIXES
    assert pattern is None


def test_structure_extraction():
    patterns = detect_patterns_if_exists(
        [
            "1. Dispositions générales",
            "1. 1. Conformité de l'installation au dossier d'enregistrement",
            "1. 2. Dossier installation classée",
            "2. Risques",
            "2. 1. Généralités",
            "2. 1. 1. Surveillance de l'installation",
            "1. Les zones d'effets Z1 et Z2 définies par l'arrêté du 20 a erez",  # in EXCEPTION_PREFIXES
            "2. 1. 2. Clôture",
        ]
    )
    assert patterns[0] == NumberingPattern.NUMERIC_D1
    assert patterns[1] == NumberingPattern.NUMERIC_D2_SPACE
    assert patterns[6] is None


def test_structure_extraction_2():
    patterns = detect_patterns_if_exists(
        [
            "I. First title",
            "A. First section",
            "B. Second section",
            "H. H-th section",
            "I. ― Les aires de chargement et de déchargement des produits",  # must be letter (exception)
        ]
    )
    assert patterns == [
        NumberingPattern.ROMAN,
        NumberingPattern.CAPS,
        NumberingPattern.CAPS,
        NumberingPattern.CAPS,
        NumberingPattern.CAPS,
    ]

