import re
from enum import Enum
from typing import Dict, List, Optional, Set

from envinorma.structure.numbering_exceptions import EXCEPTION_PREFIXES, MAX_PREFIX_LEN


class NumberingPattern(Enum):
    ROMAN = 'roman'
    ROMAN_DASH = 'roman-dash'
    NUMERIC_D1 = 'numeric-d1'
    NUMERIC_D2 = 'numeric-d2'
    NUMERIC_D3 = 'numeric-d3'
    NUMERIC_D1_PAREN = 'numeric-d1-paren'
    NUMERIC_D2_SPACE = 'numeric-d2-space'
    NUMERIC_D2_DASH = 'numeric-d2-dash'
    NUMERIC_D3_DASH = 'numeric-d3-dash'
    NUMERIC_D3_SPACE = 'numeric-d3-space'
    NUMERIC_D4_SPACE = 'numeric-d4-space'
    NUMERIC_CIRCLE = 'numeric-circle'
    LETTERS = 'letters'
    CAPS = 'caps'
    ANNEXE = 'annexe'
    ANNEXE_ROMAN = 'annexe-roman'


ROMAN_PATTERN = '(?=[XVI])(X{0,3})(I[XV]|V?I{0,3})'

NUMBERING_PATTERNS = {
    NumberingPattern.ROMAN_DASH: rf'^{ROMAN_PATTERN}\.-',
    NumberingPattern.ROMAN: rf'^{ROMAN_PATTERN}\. ',
    NumberingPattern.NUMERIC_D1: r'^[0-9]+\. ',
    NumberingPattern.NUMERIC_D2: r'^([0-9]+\.){2} ',
    NumberingPattern.NUMERIC_D3: r'^([0-9]+\.){3} ',
    NumberingPattern.NUMERIC_D1_PAREN: r'^[0-9]+\) ',
    NumberingPattern.NUMERIC_D2_SPACE: r'^([0-9]+\. ){2}',
    NumberingPattern.NUMERIC_D2_DASH: r'^[0-9]+\-[0-9]+\. ',
    NumberingPattern.NUMERIC_D3_SPACE: r'^([0-9]+\. ){3}',
    NumberingPattern.NUMERIC_D3_DASH: r'^[0-9]+\-[0-9]+\-[0-9]+\. ',
    NumberingPattern.NUMERIC_D4_SPACE: r'^([0-9]+\. ){4}',
    NumberingPattern.NUMERIC_CIRCLE: r'^[0-9]+° ',
    NumberingPattern.LETTERS: r'^[a-z]\)',
    NumberingPattern.CAPS: r'^[A-Z]\. ',
    NumberingPattern.ANNEXE: r'^ANNEXE [0-9]+',
    NumberingPattern.ANNEXE_ROMAN: rf'^ANNEXE {ROMAN_PATTERN}',
}

INCREASING_PATTERNS = {
    NumberingPattern.ROMAN,
    NumberingPattern.ROMAN_DASH,
    NumberingPattern.NUMERIC_D1,
    NumberingPattern.NUMERIC_D2,
    NumberingPattern.NUMERIC_D2_DASH,
    NumberingPattern.NUMERIC_D3,
    NumberingPattern.NUMERIC_D3_DASH,
    NumberingPattern.NUMERIC_CIRCLE,
    NumberingPattern.LETTERS,
    NumberingPattern.CAPS,
}

SHOULD_HAVE_SEMICOLON_PATTERNS = {NumberingPattern.LETTERS}


def _match_size(match: re.Match) -> int:
    x, y = match.span()
    return y - x


def detect_longest_matched_pattern(string: str) -> Optional[NumberingPattern]:
    max_size = -1
    argmax = None
    for pattern_name, pattern in NUMBERING_PATTERNS.items():
        match = re.match(pattern, string)
        if not match:
            continue
        size = _match_size(match)
        if _match_size(match) > max_size:
            argmax = pattern_name
            max_size = size
    return argmax


def _extract_matched_str(string: str, match: Optional[re.Match]) -> Optional[str]:
    if not match:
        return None
    return string[match.span()[0] : match.span()[1]]


def detect_longest_matched_string(string: str) -> Optional[str]:
    pattern_name = detect_longest_matched_pattern(string)
    if not pattern_name:
        return None
    pattern = NUMBERING_PATTERNS[pattern_name]
    return _extract_matched_str(string, re.match(pattern, string))


def _smart_detect_pattern(string: str) -> Optional[NumberingPattern]:
    if string[:MAX_PREFIX_LEN] in EXCEPTION_PREFIXES:
        pattern = EXCEPTION_PREFIXES[string[:MAX_PREFIX_LEN]]
        return NumberingPattern(pattern) if pattern else None
    return detect_longest_matched_pattern(string)


def detect_patterns_if_exists(strings: List[str]) -> List[Optional[NumberingPattern]]:
    return [_smart_detect_pattern(string) for string in strings]


def detect_patterns(strings: List[str]) -> List[NumberingPattern]:
    matched_patterns = detect_patterns_if_exists(strings)
    return [pattern for pattern in matched_patterns if pattern]


def detect_first_pattern(strs: List[str]) -> Optional[NumberingPattern]:
    patterns = detect_patterns(strs)
    if not patterns:
        return None
    return patterns[0]


def group_strings_by_pattern(
    patterns: List[Optional[NumberingPattern]], strings: List[str]
) -> Dict[NumberingPattern, List[str]]:
    pattern_to_strings: Dict[NumberingPattern, List[str]] = {}
    for pattern, string in zip(patterns, strings):
        if not pattern:
            continue
        if pattern not in pattern_to_strings:
            pattern_to_strings[pattern] = []
        pattern_to_strings[pattern].append(string)
    return pattern_to_strings


def _any_final_semicolon(strings: List[str]) -> bool:
    return any([':' in string[-2:] for string in strings])


def _starts_with_prefix(string: str, prefix: str) -> bool:
    return string[: len(prefix)] == prefix


def prefixes_are_increasing(prefixes: List[str], strings: List[str]) -> bool:
    i = 0
    for string in strings:
        while True:
            if i >= len(prefixes):
                return False
            if _starts_with_prefix(string, prefixes[i]):
                break
            i += 1
    if i >= len(prefixes):
        return False
    return True


def _pattern_is_increasing(pattern: NumberingPattern, strings: List[str]) -> bool:
    prefixes = PATTERN_NAME_TO_LIST[pattern]
    return prefixes_are_increasing(prefixes, strings)


def prefixes_are_continuous(prefixes: List[str], strings: List[str]) -> bool:
    for prefix, string in zip(prefixes, strings):
        if not _starts_with_prefix(string, prefix):
            return False
    if len(strings) > len(prefixes):
        raise ValueError(
            f'Missing prefixes to check continuity. First prefix: {prefixes[0]}, first string: {strings[0]}'
        )
    return True


def _is_valid(pattern: NumberingPattern, strings: List[str]) -> bool:
    checks: List[bool] = []
    if pattern in INCREASING_PATTERNS:
        checks.append(_pattern_is_increasing(pattern, strings))
    if pattern in SHOULD_HAVE_SEMICOLON_PATTERNS:
        checks.append(_any_final_semicolon(strings))
    return all(checks)


def _deduce_pattern_to_use(
    detected_patterns: List[Optional[NumberingPattern]], pattern_to_strings: Dict[NumberingPattern, List[str]]
) -> Optional[NumberingPattern]:
    invalid_patterns: Set[NumberingPattern] = set()
    for pattern in detected_patterns:
        if not pattern or pattern in invalid_patterns:
            continue
        if _is_valid(pattern, pattern_to_strings[pattern]):
            return pattern
        invalid_patterns.add(pattern)
    return None


def guess_numbering_pattern(strings: List[str]) -> Optional[NumberingPattern]:
    return detect_first_pattern(strings)
    # matched_patterns = [_smart_detect_pattern(string) for string in strings]
    # pattern_to_strings = group_strings_by_pattern(matched_patterns, strings)
    # return _deduce_pattern_to_use(matched_patterns, pattern_to_strings)


ROMAN_TO_XXX = [
    f'{prefix}{unit}'
    for prefix in ['', 'X', 'XX', 'XXX']
    for unit in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
][:-1]
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

PATTERN_NAME_TO_LIST = {
    NumberingPattern.ROMAN: [f'{x}. ' for x in ROMAN_TO_XXX],
    NumberingPattern.ROMAN_DASH: [f'{x}.-' for x in ROMAN_TO_XXX],
    NumberingPattern.NUMERIC_D1: [f'{x}. ' for x in range(1, 101)],
    NumberingPattern.NUMERIC_D2: [f'{x}.{y}. ' for x in range(1, 31) for y in range(1, 21)],
    NumberingPattern.NUMERIC_D3: [f'{x}.{y}.{z}. ' for x in range(1, 31) for y in range(1, 21) for z in range(1, 21)],
    NumberingPattern.NUMERIC_D1_PAREN: [f'{x}) ' for x in range(1, 101)],
    NumberingPattern.NUMERIC_D2_SPACE: [f'{x}. {y}. ' for x in range(1, 31) for y in range(1, 21)],
    NumberingPattern.NUMERIC_D2_DASH: [f'{x}-{y}. ' for x in range(1, 101) for y in range(1, 21)],
    NumberingPattern.NUMERIC_D3_DASH: [
        f'{x}-{y}-{z}. ' for x in range(1, 60) for y in range(1, 21) for z in range(1, 11)
    ],
    NumberingPattern.NUMERIC_D3_SPACE: [
        f'{x}. {y}. {z}. ' for x in range(1, 31) for y in range(1, 31) for z in range(1, 21)
    ],
    NumberingPattern.NUMERIC_D4_SPACE: [
        f'{x}. {y}. {z}. {t}. ' for x in range(1, 21) for y in range(1, 21) for z in range(1, 21) for t in range(1, 21)
    ],
    NumberingPattern.NUMERIC_CIRCLE: [f'{x}° ' for x in range(1, 101)],
    NumberingPattern.LETTERS: [f'{x}) ' for x in LETTERS.lower()],
    NumberingPattern.CAPS: [f'{x}. ' for x in LETTERS],
    NumberingPattern.ANNEXE: [f'ANNEXE {x}' for x in range(1, 101)],
    NumberingPattern.ANNEXE_ROMAN: [f'ANNEXE {x}' for x in ROMAN_TO_XXX],
}


def get_first_match(title: str, prefixes: List[str]) -> int:
    for i, prefix in enumerate(prefixes):
        if title[: len(prefix)] == prefix:
            return i
    return -1


def get_matched_strs(strs: List[str], pattern: NumberingPattern) -> List[bool]:
    return [_smart_detect_pattern(str_) == pattern for str_ in strs]


def _first_word(sentence: str) -> str:
    return sentence.split(' ')[0].split('\'')[0]


_NON_TITLE_WORDS = {'le', 'la', 'les', 'l', 'un', 'une', 'pour', 'sur', 'sans'}


def is_mainly_upper(sentence: str) -> bool:
    letters = [x for x in sentence if x.isalpha()]
    nb_upper = len([0 for letter in letters if letter.isupper()])
    if nb_upper / (len(letters) or 1) >= 0.97:
        return True
    return False


def is_probably_title(candidate: str) -> bool:
    if is_mainly_upper(candidate):
        return True
    if _first_word(candidate).lower() in _NON_TITLE_WORDS:
        return False
    if candidate[-1] == ':':
        return False
    if len(candidate.split(' ')) >= 15:
        return False
    return True
