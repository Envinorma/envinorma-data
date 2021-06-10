import re
from dataclasses import replace
from typing import List, Optional

from envinorma.data import ArreteMinisteriel, StructuredText
from envinorma.title_detection import NUMBERING_PATTERNS, ROMAN_PATTERN, NumberingPattern, detect_longest_matched_string


def _is_probably_section_number(candidate: str) -> bool:
    if not candidate.isalpha():
        return True
    if len(candidate) <= 2:
        return True
    if re.match(ROMAN_PATTERN, candidate):
        return True
    return False


def _extract_article_prefix(title: str) -> Optional[str]:
    split = title.split(' ')
    if len(split) == 0:
        return None
    if len(split) == 1:
        return 'Art.'
    if split[1].lower() == 'annexe':
        return _extract_annexe_prefix(' '.join(split[1:]))
    article_number = split[1]
    if _is_probably_section_number(article_number):
        return 'Art. ' + article_number
    return 'Art. ?'


def _extract_annexe_prefix(title: str) -> Optional[str]:
    split = title.split(' ')
    if len(split) == 0:
        return None
    if len(split) == 1:
        return 'Annexe'
    annexe_number = split[1]
    if _is_probably_section_number(annexe_number):
        return 'Annexe ' + annexe_number
    return 'Annexe ?'


def _extract_special_prefix(title: str) -> Optional[str]:
    if title.lower().startswith('article'):
        return _extract_article_prefix(title)
    if title.lower().startswith('annexe'):
        return _extract_annexe_prefix(title)
    return None


def _extract_prefix(title: str) -> Optional[str]:
    special_prefix = _extract_special_prefix(title)
    if special_prefix:
        return special_prefix
    res = detect_longest_matched_string(title)
    return res.replace(' ', '') if res else res


_VERBOSE_NUMBERING_PATTERNS = [
    NUMBERING_PATTERNS[_pat].replace(' ', '')
    for _pat in (
        NumberingPattern.NUMERIC_D1,
        NumberingPattern.NUMERIC_D2,
        NumberingPattern.NUMERIC_D3,
        NumberingPattern.NUMERIC_D3_SPACE,
        NumberingPattern.NUMERIC_D4_SPACE,
        NumberingPattern.NUMERIC_D2_DASH,
        NumberingPattern.NUMERIC_D3_DASH,
    )
]


def _is_verbose_numbering(str_: str) -> bool:
    return any([re.match(pat, str_) for pat in _VERBOSE_NUMBERING_PATTERNS])


def _are_consecutive_verbose_numbering(str_1: str, str_2: str) -> bool:
    return _is_verbose_numbering(str_1) and _is_verbose_numbering(str_1) and str_2[: len(str_1)] == str_1


def _is_prefix(candidate: Optional[str], long_word: Optional[str]) -> bool:
    if not candidate or not long_word:
        return False
    if candidate.lower().startswith('annexe') and long_word.lower().startswith('annexe'):
        return True
    candidate_strip = candidate.replace(' ', '')
    long_word_strip = long_word.replace(' ', '')
    return _are_consecutive_verbose_numbering(candidate_strip, long_word_strip)


_PREFIX_SEPARATOR = ' '
_ANNEXE_OR_ARTICLE = ('annexe', 'article')


def _annexe_or_article(title: str) -> bool:
    for prefix in _ANNEXE_OR_ARTICLE:
        if title.lower().startswith(prefix):
            return True
    return False


def _cut_before_annexe_or_article(titles: List[str]) -> List[str]:
    for i, title in enumerate(titles):
        if _annexe_or_article(title):
            return titles[i:]
    return []


def _remove_empty(elements: List[str]) -> List[str]:
    return [el for el in elements if el]


def _merge_prefixes(prefixes: List[Optional[str]]) -> str:
    if len(prefixes) == 1:
        return prefixes[0] or ''
    if _is_prefix(prefixes[0], prefixes[1]):
        return _merge_prefixes(prefixes[1:])
    to_merge = _remove_empty([prefixes[0] or '', _merge_prefixes(prefixes[1:])])
    return _PREFIX_SEPARATOR.join(to_merge)


def _merge_titles(titles: List[str]) -> str:
    if len(titles) == 0:
        raise ValueError('should have at least one prefix')
    filtered_titles = _cut_before_annexe_or_article(titles)
    if len(filtered_titles) == 0:
        return ''
    prefixes = [_extract_prefix(title) for title in filtered_titles]
    return _merge_prefixes(prefixes)


def _add_references_in_section(text: StructuredText, titles: List[str]) -> StructuredText:
    titles = titles + [text.title.text]
    return replace(
        text,
        reference_str=_merge_titles(titles),
        sections=[_add_references_in_section(section, titles) for section in text.sections],
    )


def add_references(am: ArreteMinisteriel) -> ArreteMinisteriel:
    return replace(am, sections=[_add_references_in_section(section, []) for section in am.sections])
