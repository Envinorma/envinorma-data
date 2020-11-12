import re
from copy import copy
from dataclasses import replace
from typing import Dict, List, Optional, Set

from lib.data import Annotations, ArreteMinisteriel, StructuredText, Topic
from lib.parametric_am import Ints
from lib.structure_detection import (
    NUMBERING_PATTERNS,
    NumberingPattern,
    PATTERN_NAME_TO_LIST,
    ROMAN_PATTERN,
    detect_longest_matched_string,
)


def _add_topic_in_text(text: StructuredText, topics: Dict[Ints, Topic], path: Ints) -> StructuredText:
    result = copy(text)
    if path in topics:
        result.annotations = replace(text.annotations or Annotations(), topic=topics[path])
    result.sections = [_add_topic_in_text(sec, topics, path + (i,)) for i, sec in enumerate(text.sections)]
    return result


def add_topics(am: ArreteMinisteriel, topics: Dict[Ints, Topic]) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [_add_topic_in_text(sec, topics, (i,)) for i, sec in enumerate(am.sections)]
    return result


def _add_prescriptive_power_in_text(
    text: StructuredText, non_prescriptive_sections: Set[Ints], path: Ints
) -> StructuredText:
    result = copy(text)
    if path in non_prescriptive_sections:
        result.annotations = replace(text.annotations or Annotations(), prescriptive=False)
    result.sections = [
        _add_prescriptive_power_in_text(sec, non_prescriptive_sections, path + (i,))
        for i, sec in enumerate(text.sections)
    ]
    return result


def remove_prescriptive_power(am: ArreteMinisteriel, non_prescriptive_sections: Set[Ints]) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [
        _add_prescriptive_power_in_text(sec, non_prescriptive_sections, (i,)) for i, sec in enumerate(am.sections)
    ]
    return result


def _is_probably_section_number(candidate: str) -> bool:
    if not candidate.isalpha():
        return True
    if len(candidate) <= 2:
        return True
    if re.match(ROMAN_PATTERN, candidate):
        return True
    return False


def _extract_article_prefix(title: str) -> Optional[str]:
    article_number = title.split(' ')[1]
    if _is_probably_section_number(article_number):
        return 'Art. ' + article_number
    return 'Art. ?'


def _extract_annexe_prefix(title: str) -> Optional[str]:
    annexe_number = title.split(' ')[1]
    if _is_probably_section_number(annexe_number):
        return 'Annexe ' + annexe_number
    return 'Annexe ?'


def _extract_special_prefix(title: str) -> Optional[str]:
    if title.lower()[:7] == 'article':
        return _extract_article_prefix(title)
    if title.lower()[:6] == 'annexe':
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
    candidate_strip = candidate.replace(' ', '')
    long_word_strip = long_word.replace(' ', '')
    return _are_consecutive_verbose_numbering(candidate_strip, long_word_strip)


_PREFIX_SEPARATOR = ' '


def _merge_prefix_list(prefixes: List[Optional[str]]) -> str:
    if len(prefixes) == 0:
        raise ValueError('should have at least one prefix')
    if len(prefixes) == 1:
        return prefixes[0] or '?'
    if _is_prefix(prefixes[0], prefixes[1]):
        return _merge_prefix_list(prefixes[1:])
    return (prefixes[0] or '?') + _PREFIX_SEPARATOR + _merge_prefix_list(prefixes[1:])


def add_references_in_section(section: StructuredText, previous_prefixes: List[Optional[str]]) -> StructuredText:
    result = copy(section)
    del section
    prefixes = previous_prefixes + [_extract_prefix(result.title.text)]
    result.reference_str = _merge_prefix_list(prefixes)
    result.sections = [add_references_in_section(subsection, prefixes) for subsection in result.sections]
    return result


def add_references(am: ArreteMinisteriel) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [add_references_in_section(section, []) for section in am.sections]
    return result
