import re
from lib.structure_detection import (
    NumberingPattern,
    detect_longest_matched_pattern,
    detect_longest_matched_string,
    detect_patterns_if_exists,
    prefixes_are_continuous,
    _pattern_is_increasing,
    _is_valid,
    _smart_detect_pattern,
    PATTERN_NAME_TO_LIST,
    NUMBERING_PATTERNS,
)
from lib.numbering_exceptions import MAX_PREFIX_LEN, EXCEPTION_PREFIXES


def test_pattern_is_increasing():
    assert _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'd) '])
    assert not _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'd) ', 'a) '])
    assert _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'x) ', 'y) '])


def test_regex():
    for key in PATTERN_NAME_TO_LIST:
        assert key in NUMBERING_PATTERNS
    for pattern_name, pattern in NUMBERING_PATTERNS.items():
        for elt in PATTERN_NAME_TO_LIST[pattern_name]:
            assert re.match(pattern, elt)


def test_prefixes_are_continuous():
    prefixes = PATTERN_NAME_TO_LIST[NumberingPattern.NUMERIC_D1]
    assert prefixes_are_continuous(prefixes, prefixes)
    assert not prefixes_are_continuous(prefixes, prefixes[1:5])


def test_is_valid():
    assert not _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar ;'])
    assert _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar :'])
    assert not _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar :', 'a) Pi', 'b) Pa'])


def test_detect_longest_matched_pattern():
    assert detect_longest_matched_pattern('1. 1. bnjr') == NumberingPattern.NUMERIC_D2_SPACE
    assert detect_longest_matched_pattern('1. 2. 3. bnjr') == NumberingPattern.NUMERIC_D3_SPACE
    assert detect_longest_matched_pattern('1. 2.3. bnjr') == NumberingPattern.NUMERIC_D1
    assert detect_longest_matched_pattern('1.') is None
    assert detect_longest_matched_pattern('') is None


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


def test_detect_longest_matched_string():
    titles_to_target = {
        'I. First title': 'I. ',
        'A. First section': 'A. ',
        'B. Second section': 'B. ',
        'H. H-th section': 'H. ',
        'I. ― Les aires de chargement et de déchargement des produits': 'I. ',
        '1.1. Bonjour': '1.1. ',
        '1. 15. Bonjour': '1. 15. ',
    }

    for title, target in titles_to_target.items():
        assert detect_longest_matched_string(title) == target
