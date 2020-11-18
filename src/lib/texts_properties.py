import re
from dataclasses import dataclass
from typing import Optional, Tuple, Union, List

from bs4 import BeautifulSoup

from lib.am_structure_extraction import (
    ArreteMinisteriel,
    ArticleStatus,
    EnrichedString,
    StructuredText,
    LegifranceText,
    LegifranceSection,
    LegifranceArticle,
    split_in_non_empty_html_line,
    keep_visa_string,
)
from lib.structure_detection import (
    NUMBERING_PATTERNS,
    get_first_match,
    detect_first_pattern,
    PATTERN_NAME_TO_LIST,
    prefixes_are_increasing,
    prefixes_are_continuous,
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
        etat = ' (abrogé)' if elt.etat == ArticleStatus.ABROGE else ''
        if isinstance(elt, LegifranceArticle):
            res += [f'{prefix}Article {elt.num}{etat}']
        elif isinstance(elt, LegifranceSection):
            res += [(f'{prefix}Section {elt.title}{etat}')] + _extract_text_structure(elt, f'|--{prefix}')
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


_TREE_DEPTH_PREFIX = '|--'


def extract_am_structure(
    am: Union[ArreteMinisteriel, StructuredText], paths: Optional[List[int]] = None, with_paths: bool = False
) -> List[str]:
    res: List[str] = []
    paths = paths or []
    prefix = len(paths) * _TREE_DEPTH_PREFIX
    for i, section in enumerate(am.sections):
        section_title = f'{prefix}{section.title.text}' + (' ' + str(paths + [i]) if with_paths else '')
        res += [section_title] + extract_am_structure(section, paths + [i], with_paths)
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


@dataclass
class PrefixPattern:
    found: bool
    increasing: bool
    continuous: bool


def _compute_prefix_pattern(titles: List[str], prefixes: List[str]) -> PrefixPattern:
    first_match = get_first_match(titles[0], prefixes)
    if first_match == -1:
        return PrefixPattern(False, False, False)
    if not prefixes_are_increasing(prefixes, titles):
        return PrefixPattern(True, False, False)
    if not prefixes_are_continuous(prefixes[first_match:], titles):
        return PrefixPattern(True, True, False)
    return PrefixPattern(True, True, True)


def _detect_inconsistency_in_numbering(
    titles: List[str], parent_title: str, prefixes: List[str]
) -> Optional[TitleInconsistency]:
    prefix_pattern = _compute_prefix_pattern(titles, prefixes)
    if not prefix_pattern.found:
        return TitleInconsistency(titles, parent_title, 'Numerotation non détectée dans le 1er titre')
    if not prefix_pattern.increasing:
        return TitleInconsistency(titles, parent_title, 'Numérotation décroissante')
    if not prefix_pattern.continuous:
        return TitleInconsistency(titles, parent_title, 'Numérotation discontinue')
    return None


def _detect_inconsistency(titles: List[str], context: str = '') -> Optional[TitleInconsistency]:
    if len(titles) <= 1:
        return None
    pattern_name = detect_first_pattern(titles)
    if not pattern_name:
        return None
    no_match = [title for title in titles if not re.match(NUMBERING_PATTERNS[pattern_name], title)]
    if no_match:
        return TitleInconsistency(titles, context, f'Numérotation manquante dans certains titres')
    return _detect_inconsistency_in_numbering(titles, context, PATTERN_NAME_TO_LIST[pattern_name])


def _extract_section_inconsistencies(text: StructuredText) -> List[TitleInconsistency]:
    titles = [section.title.text for section in text.sections]
    inconsistency = _detect_inconsistency(titles, text.title.text)
    result = [inconsistency] if inconsistency else []
    return result + [inc for section in text.sections for inc in _extract_section_inconsistencies(section)]


def extract_inconsistencies(am: ArreteMinisteriel) -> List[TitleInconsistency]:
    return [inc for section in am.sections for inc in _extract_section_inconsistencies(section)]


def _extract_alineas_with_neighbours(alineas: List[EnrichedString], position: int) -> str:
    start = max(position - 1, 0)
    end = min(position + 1, len(alineas))
    return '\n'.join([x.text for x in alineas[start:end]])


def _fetch_term_in_alineas(term: str, alineas: List[EnrichedString]) -> List[str]:
    res = []
    for i, alinea in enumerate(alineas):
        if alinea.text.lower().strip()[: len(term)] == term:
            res.append(_extract_alineas_with_neighbours(alineas, i))
    return res


def _fetch_term_in_text(term: str, text: StructuredText) -> List[str]:
    in_title = _fetch_term_in_alineas(term, [text.title])
    in_alineas = _fetch_term_in_alineas(term, text.outer_alineas)
    in_sections = [result for section in text.sections for result in _fetch_term_in_text(term, section)]
    return in_title + in_alineas + in_sections


def _fetch_term(term: str, am: ArreteMinisteriel) -> List[str]:
    return [result for section in am.sections for result in _fetch_term_in_text(term, section)]


def _compute_am_properties(am: ArreteMinisteriel) -> AMProperties:
    return AMProperties(
        '\n'.join(extract_am_structure(am)),
        count_sections(am),
        count_articles_in_am(am),
        count_tables(am),
        count_nb_empty_articles(am),
        extract_inconsistencies(am),
    )


@dataclass
class TextProperties:
    legifrance: LegifranceTextProperties
    am: Optional[AMProperties]


def compute_properties(text: LegifranceText, am: Optional[ArreteMinisteriel]) -> TextProperties:
    return TextProperties(_compute_lf_properties(text), _compute_am_properties(am) if am else None)


def detect_upper_case_first_lines(text: StructuredText, ascendant_titles: List[str]) -> None:
    found = False
    for title in ascendant_titles:
        if 'annexe' in title.lower():
            found = True
    if not found:
        for section in text.sections:
            detect_upper_case_first_lines(section, ascendant_titles + [section.title.text])
    else:
        for str_ in text.outer_alineas[:2]:
            if str_.text.isupper():
                print(str_.text)
            else:
                break


def detect_upper_case(text: ArreteMinisteriel) -> None:
    for section in text.sections:
        detect_upper_case_first_lines(section, [])


def _compare_texts(text_1: str, text_2: str) -> str:
    import difflib

    lines_1 = text_1.splitlines()
    lines_2 = text_2.splitlines()
    diff = difflib.unified_diff(lines_1, lines_2, fromfile='file1', tofile='file2', lineterm='', n=0)
    lines = list(diff)[2:]
    return '\n'.join(lines)


def compute_am_diffs(am_1: ArreteMinisteriel, am_2: ArreteMinisteriel) -> str:
    from lib.am_to_markdown import am_to_markdown

    markdown_am_1 = am_to_markdown(am_1)
    markdown_am_2 = am_to_markdown(am_2)
    return _compare_texts(markdown_am_1, markdown_am_2)

