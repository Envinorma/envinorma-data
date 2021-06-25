import re
from enum import Enum
from typing import Dict, List, Optional, Tuple


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


def _detect_longest_matched_pattern(string: str) -> Optional[NumberingPattern]:
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
    pattern_name = _detect_longest_matched_pattern(string)
    if not pattern_name:
        return None
    pattern = NUMBERING_PATTERNS[pattern_name]
    return _extract_matched_str(string, re.match(pattern, string))


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


def _first_word(sentence: str) -> str:
    return sentence.split(' ')[0].split("'")[0]


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


_NumberingExceptions = Tuple[int, Dict[str, Optional[str]]]


def _smart_detect_pattern(
    string: str, numbering_exceptions: Optional[_NumberingExceptions]
) -> Optional[NumberingPattern]:
    if numbering_exceptions:
        max_prefix_len, exceptions = numbering_exceptions
        if string[:max_prefix_len] in exceptions:
            pattern = exceptions[string[:max_prefix_len]]
            return NumberingPattern(pattern) if pattern else None
    return _detect_longest_matched_pattern(string)


def detect_patterns_if_exists(
    strings: List[str], exceptions: Optional[_NumberingExceptions]
) -> List[Optional[NumberingPattern]]:
    return [_smart_detect_pattern(string, exceptions) for string in strings]
