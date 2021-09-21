import re
import unicodedata
from dataclasses import replace
from typing import List, Optional, Tuple

from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.structured_text import Reference, StructuredText
from envinorma.title_detection import ROMAN_PATTERN, detect_longest_matched_string


def _any_alphanumeric(candidate: str) -> bool:
    return len([c for c in candidate if c.isalnum()]) > 0


def _is_probably_section_number(candidate: str) -> bool:
    if not _any_alphanumeric(candidate):
        return False
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
        return 'Article'
    if split[1].lower() == 'annexe':
        return _extract_annexe_prefix(' '.join(split[1:]))
    article_number = split[1]
    if _is_probably_section_number(article_number):
        return 'Article ' + article_number
    return 'Article'


def _extract_annexe_prefix(title: str) -> Optional[str]:
    split = title.split(' ')
    if len(split) == 0:
        return None
    if len(split) == 1:
        return 'Annexe'
    annexe_number = split[1]
    if _is_probably_section_number(annexe_number):
        return 'Annexe ' + annexe_number
    return 'Annexe'


def _extract_special_prefix(title: str) -> Optional[str]:
    if title.lower().startswith('article'):
        return _extract_article_prefix(title)
    if title.lower().startswith('annexe'):
        return _extract_annexe_prefix(title)
    return None


def _extract_raw_number_prefix(title: str) -> Tuple[bool, Optional[str]]:
    special_prefix = _extract_special_prefix(title)
    if special_prefix:
        return True, special_prefix
    return False, detect_longest_matched_string(title, _NUMBERING_PATTERNS)


def _extract_prefix(title: str) -> Optional[str]:
    special, raw_prefix = _extract_raw_number_prefix(title)
    return raw_prefix.replace(' ', '') if raw_prefix and not special else raw_prefix


def _clean_suffix(suffix: str) -> str:
    stripped = suffix.strip()
    for char in '-:':
        if stripped.startswith(char):
            stripped = stripped[1:].strip()
        if stripped.endswith(char):
            stripped = stripped[:-1].strip()
    return stripped


_SPECIAL_WORDS = ['titre', 'chapitre', 'section', 'annexes', 'annexe', 'article']


def _remove_special_words(title: str) -> str:
    new_title = title
    for word in _SPECIAL_WORDS:
        if new_title.lower().startswith(word):
            new_title = new_title[len(word) :].strip()
    if new_title != title:
        return _remove_special_words(new_title)
    return new_title


def _remove_special_words_and_numbering(title: str) -> str:
    new_title = _remove_special_words(title)
    if new_title == title:
        return title
    words = new_title.split()
    if not words:
        return new_title
    if _is_probably_section_number(words[0]):
        return new_title[len(words[0]) :].strip()
    return new_title


def _extract_suffix(title: str) -> Optional[str]:
    clean_title = _remove_special_words_and_numbering(title)
    raw_prefix = detect_longest_matched_string(clean_title, _NUMBERING_PATTERNS)
    if raw_prefix:
        clean_title = clean_title[len(raw_prefix) :]
    return _clean_suffix(clean_title)


_VERBOSE_NUMBERING_PATTERNS = [
    r'^[0-9]+\.',
    r'^[0-9]+\.[0-9]+',
    r'^([0-9]+\.){2}',
    r'^([0-9]+\.){3}',
    r'^([0-9]+\. ){3}',
    r'^([0-9]+\. ){4}',
    r'^[0-9]+\-[0-9]+\.',
    r'^[0-9]+\-[0-9]+\-[0-9]+\.',
    rf'^{ROMAN_PATTERN}\-[0-9]+\.',
    rf'^{ROMAN_PATTERN}\-[0-9]+\.[0-9]+\.',
]
_NUMBERING_PATTERNS = _VERBOSE_NUMBERING_PATTERNS + [
    rf'^{ROMAN_PATTERN}',
    rf'^{ROMAN_PATTERN}\.',
    rf'^{ROMAN_PATTERN}\-',
    rf'^{ROMAN_PATTERN}\-[0-9]+\.',
    rf'^{ROMAN_PATTERN}\-[0-9]+\.[0-9]+\.',
    r'^[0-9]+\)',
    r'^([0-9]+\. ){2}',
    r'^[0-9]+\-[0-9]+\.',
    r'^([0-9]+\. ){3}',
    r'^[0-9]+\-[0-9]+\-[0-9]+\.',
    r'^([0-9]+\.){4}',
    r'^[0-9]+°',
    r'^[a-z]\)',
    r'^[A-Z]\.',
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
_ANNEXE_OR_ARTICLE = ('annexe', 'article')


def _annexe_or_article(title: str) -> bool:
    for prefix in _ANNEXE_OR_ARTICLE:
        if title.lower().startswith(prefix):
            return True
    return False


def _cut_before_annexe_or_article(titles: List[str]) -> List[str]:
    cut_at = 0
    for i, title in enumerate(titles):
        if _annexe_or_article(title):
            cut_at = i
    return titles[cut_at:]


def _remove_empty(elements: List[str]) -> List[str]:
    return [el for el in elements if el]


def _merge_prefixes(prefixes: List[Optional[str]]) -> str:
    if not prefixes:
        raise ValueError('prefixes cannot be empty')
    first_prefix = prefixes[0] or ''
    if len(prefixes) == 1:
        return first_prefix or ''
    if _is_prefix(first_prefix, prefixes[1]):
        return _merge_prefixes(prefixes[1:])
    separator = ' > ' if _annexe_or_article(first_prefix) else _PREFIX_SEPARATOR
    to_merge = _remove_empty([first_prefix, _merge_prefixes(prefixes[1:])])
    return separator.join(to_merge)


def _last_suffix(titles: List[Optional[str]]) -> Optional[str]:
    for title in reversed(titles):
        if title:
            return title
    return None


def _extract_reference(titles: List[str]) -> Reference:
    if len(titles) == 0:
        raise ValueError('should have at least one prefix')
    clean_titles = [unicodedata.normalize('NFKD', title).strip() for title in titles]
    filtered_titles = _cut_before_annexe_or_article(clean_titles)
    if len(filtered_titles) == 0:
        return Reference('', '')
    prefixes = [_extract_prefix(title) for title in filtered_titles]
    suffixes = [_extract_suffix(title) for title in clean_titles]
    return Reference(_merge_prefixes(prefixes), _last_suffix(suffixes) or '')


def _add_references_in_section(text: StructuredText, titles: List[str]) -> StructuredText:
    titles = titles + [text.title.text]
    return replace(
        text,
        reference=_extract_reference(titles),
        sections=[_add_references_in_section(section, titles) for section in text.sections],
    )


def add_references(am: ArreteMinisteriel) -> ArreteMinisteriel:
    return replace(am, sections=[_add_references_in_section(section, []) for section in am.sections])
