import re
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional, Tuple, Union, List

from lib.am_structure_extraction import (
    ArreteMinisteriel,
    StructuredText,
    LegifranceText,
    LegifranceSection,
    LegifranceArticle,
    detect_patterns,
    ALL_PATTERNS,
    split_in_non_empty_html_line,
    keep_visa_string,
)


@dataclass
class LegifranceTextProperties:
    structure: str
    nb_articles: int
    nb_non_numbered_articles: int
    nb_lost_vu_lines: int


def _count_articles(text: Union[LegifranceText, LegifranceSection]) -> int:
    return len(text.articles) + sum([_count_articles(section) for section in text.sections])


def _count_non_numbered_articles(text: Union[LegifranceText, LegifranceSection]) -> int:
    tmp = len([article for article in text.articles if article.num is not None])
    return tmp + sum([_count_articles(section) for section in text.sections])


def _extract_text_structure(text: Union[LegifranceText, LegifranceSection], prefix: str = '') -> List[str]:
    raw_elts: List[Union[LegifranceArticle, LegifranceSection]] = [*text.articles, *text.sections]
    elts = sorted(raw_elts, key=lambda x: x.intOrdre)
    res: List[str] = []
    for elt in elts:
        if isinstance(elt, LegifranceArticle):
            res += [f'{prefix}Article {elt.num}']
        elif isinstance(elt, LegifranceSection):
            res += [(f'{prefix}Section {elt.title}')] + _extract_text_structure(elt, f'|--{prefix}')
        else:
            raise ValueError('')
    return res


def _extract_article_nums(text: Union[LegifranceText, LegifranceSection]) -> List[str]:
    raw_elts: List[Union[LegifranceArticle, LegifranceSection]] = [*text.articles, *text.sections]
    elts = sorted(raw_elts, key=lambda x: x.intOrdre)
    res: List[str] = []
    for elt in elts:
        if isinstance(elt, LegifranceArticle):
            res.append(str(elt.num))
        elif isinstance(elt, LegifranceSection):
            res.extend(['|'] + _extract_article_nums(elt) + ['|'])
    return res


def _extract_sorted_articles(text: Union[LegifranceText, LegifranceSection]) -> List[LegifranceArticle]:
    raw_elts: List[Union[LegifranceArticle, LegifranceSection]] = [*text.articles, *text.sections]
    elts = sorted(raw_elts, key=lambda x: x.intOrdre)
    res: List[LegifranceArticle] = []
    for elt in elts:
        if isinstance(elt, LegifranceArticle):
            res.append(elt)
        elif isinstance(elt, LegifranceSection):
            res.extend(_extract_sorted_articles(elt))
    return res


def _extract_article_num_list(text: LegifranceText) -> str:
    articles = _extract_sorted_articles(text)
    return '\n'.join([str(article.num) for article in articles])


def _count_nb_lost_vu_lines(text: LegifranceText) -> int:
    visa_lines_before = split_in_non_empty_html_line(text.visa)
    visa_lines_after_ = keep_visa_string(visa_lines_before)
    return len(visa_lines_after_) - len(visa_lines_before)


def _compute_lf_properties(text: LegifranceText) -> LegifranceTextProperties:
    return LegifranceTextProperties(
        '\n'.join(_extract_text_structure(text)),
        _count_articles(text),
        _count_non_numbered_articles(text),
        _count_nb_lost_vu_lines(text),
    )


def _html_to_str(html: str) -> str:
    return BeautifulSoup(html, 'html.parser').text


def _get_consecutive_with_one_none(articles: List[LegifranceArticle]) -> List[Tuple[str, str]]:
    previous_is_not_none = False
    pairs: List[Tuple[str, str]] = []
    for i, article in enumerate(articles):
        if article.num is not None:
            previous_is_not_none = True
        else:
            if previous_is_not_none:
                pairs.append((_html_to_str(articles[i - 1].content), _html_to_str(article.content)))
            previous_is_not_none = False
    return pairs


@dataclass
class TitleInconsistency:
    titles: List[str]
    parent_section_title: str
    inconsistency: str


@dataclass
class AMProperties:
    structure: str
    nb_sections: int
    nb_articles: int
    nb_tables: int
    nb_empty_articles: int
    title_inconsistencies: List[TitleInconsistency]


def _extract_am_structure(am: Union[ArreteMinisteriel, StructuredText], prefix: str = '') -> List[str]:
    res: List[str] = []
    for section in am.sections:
        res += [(f'{prefix}{section.title.text}')] + _extract_am_structure(section, f'|--{prefix}')
    return res


def count_sections(am: Union[ArreteMinisteriel, StructuredText]) -> int:
    if not am.sections:
        return 1
    return sum([count_sections(section) for section in am.sections])


def _count_structured_text_tables(text: StructuredText) -> int:
    nb_tables = len([al for al in text.outer_alineas if al.table])
    return nb_tables + sum([_count_structured_text_tables(section) for section in text.sections])


def count_tables(am: ArreteMinisteriel) -> int:
    return sum([_count_structured_text_tables(section) for section in am.sections])


def _extract_text_articles(text: StructuredText) -> List[StructuredText]:
    base_articles = [text] if text.legifrance_article else []
    return base_articles + [art for section in text.sections for art in _extract_text_articles(section)]


def _extract_articles_from_am(am: ArreteMinisteriel) -> List[StructuredText]:
    return [art for section in am.sections for art in _extract_text_articles(section)]


def count_articles_in_am(am: ArreteMinisteriel) -> int:
    return len(_extract_articles_from_am(am))


def _extract_concatenated_str(text: StructuredText) -> str:
    all_texts = [al.text for al in text.outer_alineas] + [
        _extract_concatenated_str(section) for section in text.sections
    ]
    return '\n'.join(all_texts)


def _text_seems_empty(text: StructuredText) -> bool:
    has_table = _count_structured_text_tables(text) >= 1
    text_is_short = len(_extract_concatenated_str(text)) <= 140
    return bool(text_is_short and not has_table)


def count_nb_empty_articles(am: ArreteMinisteriel) -> int:
    articles = _extract_articles_from_am(am)
    return len([article for article in articles if _text_seems_empty(article)])


def _detect_first_pattern(strs: List[str]) -> Optional[str]:
    patterns = detect_patterns(strs)
    if not patterns:
        return None
    return patterns[0]


_ROMAN_TO_XXX = [
    f'{prefix}{unit}'
    for prefix in ['', 'X', 'XX', 'XXX']
    for unit in ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']
][:-1]
_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

_PATTERN_NAME_TO_LIST = {
    'roman': [f'{x}. ' for x in _ROMAN_TO_XXX],
    'numeric-d1': [f'{x}. ' for x in range(1, 101)],
    'numeric-d2': [f'{x}.{y}. ' for x in range(1, 101) for y in range(1, 21)],
    'numeric-d3': [f'{x}.{y}.{z}. ' for x in range(1, 101) for y in range(1, 21) for z in range(1, 21)],
    'numeric-circle': [f'{x}° ' for x in range(1, 101)],
    'letters': [f'{x}) ' for x in _LETTERS.lower()],
    'caps': [f'{x}. ' for x in _LETTERS],
    'annexe': [f'ANNEXE {x} ' for x in _ROMAN_TO_XXX],
}


def _get_first_match(title: str, prefixes: List[str]) -> int:
    for i, prefix in enumerate(prefixes):
        if title[: len(prefix)] == prefix:
            return i
    return -1


def _detect_inconsistency_in_numbering(
    titles: List[str], parent_title: str, prefixes: List[str]
) -> Optional[TitleInconsistency]:
    first_match = _get_first_match(titles[0], prefixes)
    if first_match == -1:
        return TitleInconsistency(titles, parent_title, f'No prefix found in title "{titles[0]}"')
    for title, prefix in zip(titles, prefixes[first_match:]):
        if title[: len(prefix)] == prefix:
            continue
        return TitleInconsistency(titles, parent_title, f'Title "{title}" is expected to start with prefix "{prefix}"')
    if len(titles) > len(prefixes[first_match:]):
        raise ValueError(f'Missing prefixes in list {prefixes}.')
    return None


def _detect_inconsistency(titles: List[str], parent_title: str) -> Optional[TitleInconsistency]:
    if len(titles) <= 1:
        return None
    pattern_name = _detect_first_pattern(titles)
    if not pattern_name:
        return None
    no_match = [title for title in titles if not re.match(ALL_PATTERNS[pattern_name], title)]
    if no_match:
        no_match_titles = '\n' + '\n'.join(no_match)
        return TitleInconsistency(
            titles, parent_title, f'Some titles do not match pattern {pattern_name}: {no_match_titles}'
        )
    return _detect_inconsistency_in_numbering(titles, parent_title, _PATTERN_NAME_TO_LIST[pattern_name])


def _extract_section_inconsistencies(text: StructuredText) -> List[TitleInconsistency]:
    titles = [section.title.text for section in text.sections]
    inconsistency = _detect_inconsistency(titles, text.title.text)
    result = [inconsistency] if inconsistency else []
    return result + [inc for section in text.sections for inc in _extract_section_inconsistencies(section)]


def extract_inconsistencies(am: ArreteMinisteriel) -> List[TitleInconsistency]:
    return [inc for section in am.sections for inc in _extract_section_inconsistencies(section)]


def _compute_am_properties(am: ArreteMinisteriel) -> AMProperties:
    return AMProperties(
        '\n'.join(_extract_am_structure(am)),
        count_sections(am),
        count_articles_in_am(am),
        count_tables(am),
        count_nb_empty_articles(am),
        extract_inconsistencies(am),
    )


@dataclass
class ComputeProperties:
    legifrance: LegifranceTextProperties
    am: AMProperties


def compute_properties(text: LegifranceText, am: ArreteMinisteriel) -> ComputeProperties:
    return ComputeProperties(_compute_lf_properties(text), _compute_am_properties(am))