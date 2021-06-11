import copy
import random
from collections import Counter
from dataclasses import dataclass, replace
from math import sqrt
from typing import Dict, Iterable, List, Optional, Tuple, TypeVar, Union

import bs4
from bs4 import BeautifulSoup
from leginorma import ArticleStatus, LegifranceArticle, LegifranceSection, LegifranceText

from envinorma.from_legifrance.numbering_exceptions import EXCEPTION_PREFIXES, MAX_PREFIX_LEN
from envinorma.io.parse_html import extract_table
from envinorma.models.arrete_ministeriel import ArreteMinisteriel, standardize_title_date
from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import EnrichedString, Link, Table
from envinorma.structure import split_alineas_in_sections
from envinorma.title_detection import NumberingPattern, detect_patterns_if_exists, is_mainly_upper, is_probably_title


@dataclass
class TableReference:
    table: Table
    reference: str


@dataclass
class LinkReference:
    reference: str
    target: str
    text: str


def _clean_title(str_: EnrichedString) -> EnrichedString:
    return replace(str_, text=str_.text.strip().replace('\r\n', ' ').replace('\n', ' '))


def keep_visa_string(visas: List[str]) -> List[str]:
    return [visa for visa in visas if visa[:2].lower() == 'vu']


def split_in_non_empty_html_line(html: str) -> List[str]:
    return [x for x in html.split('<br/>') if x]


def _extract_visa(visa_raw: str) -> List[EnrichedString]:
    return [_extract_links(str_) for str_ in keep_visa_string(split_in_non_empty_html_line(visa_raw))]


def remove_empty(strs: List[str]) -> List[str]:
    stripped = [str_.strip() for str_ in strs]
    return [str_ for str_ in stripped if str_]


def extract_alineas(html_text: str) -> List[str]:
    soup = BeautifulSoup(html_text, 'html.parser')
    for tag_type in ['sup', 'sub', 'font', 'strong', 'b', 'i', 'em']:
        for tag in soup.find_all(tag_type):
            tag.unwrap()
    return [str(sstr) for sstr in BeautifulSoup(str(soup), 'html.parser').stripped_strings]


def _extract_placeholder_positions(text: str, placeholder: str) -> Tuple[str, List[int]]:
    pieces = text.split(placeholder)
    lengths = [len(piece) for piece in pieces]
    cumulative_lengths = cumsum(lengths)
    return ''.join(pieces), cumulative_lengths[:-1]


def secure_zip(*lists: List) -> Iterable[Tuple]:
    lengths = [len(list_) for list_ in lists]
    if len(set(lengths)) != 1:
        raise ValueError(f'Lists have different lengths: {lengths}')
    return zip(*lists)


_BR_PLACEHOLDER = '{{BR_PLACEHOLDER}}'


def _remove_tables(text: str) -> Tuple[str, List[TableReference]]:
    soup = BeautifulSoup(text, 'html.parser')
    tables: List[Table] = []
    references: List[str] = []
    for div in soup.find_all('table'):
        reference = _generate_reference()
        tables.append(extract_table(str(div)))
        div.replace_with(f'{_BR_PLACEHOLDER}{reference}{_BR_PLACEHOLDER}')
        references.append(reference)
    table_refs = [TableReference(table, reference) for table, reference in zip(tables, references)]
    return str(soup).replace(_BR_PLACEHOLDER, '<br/>'), table_refs


def _remove_links(text: str) -> Tuple[str, List[LinkReference]]:
    soup = BeautifulSoup(text, 'html.parser')
    links: List[LinkReference] = []
    for tag in soup.find_all('a'):
        if 'href' not in tag.attrs:
            continue
        reference = _generate_reference()
        links.append(LinkReference(reference, _BASE_LEGIFRANCE_URL + tag['href'], tag.text))
        tag.replace_with(reference)
    return str(soup), links


def remove_empty_enriched_str(strs: List[EnrichedString]) -> List[EnrichedString]:
    return [str_ for str_ in strs if str_.text or str_.table]


TP = TypeVar('TP')


def _extract_first_non_null_elt(elements: List[TP]) -> Optional[TP]:
    for element in elements:
        if element is not None:
            return element
    return None


def select_alineas_for_splitting(alineas: List[str], pattern_names: List[Optional[NumberingPattern]]) -> List[bool]:
    if len(alineas) != len(pattern_names):
        raise ValueError(f'Expecting same lengths, received {len(alineas)} and {len(pattern_names)}')
    first_pattern = _extract_first_non_null_elt(pattern_names)
    if first_pattern is None:
        return [False] * len(alineas)
    return [pattern == first_pattern for pattern in pattern_names]


def _build_structured_text(
    title: str, alineas: List[str], pattern_names: List[Optional[NumberingPattern]]
) -> StructuredText:
    if len(alineas) != len(pattern_names):
        raise ValueError(f'{len(pattern_names)} pattern_names != {len(alineas)} alineas')
    if not any(pattern_names):
        outer_alineas = alineas
        grouped_alineas: List[List[str]] = []
        grouped_pattern_names: List[List[Optional[NumberingPattern]]] = []
    else:
        selected_alineas_for_section = select_alineas_for_splitting(alineas, pattern_names)
        outer_alineas, grouped_alineas = split_alineas_in_sections(alineas, selected_alineas_for_section)
        _, grouped_pattern_names = split_alineas_in_sections(pattern_names, selected_alineas_for_section)
    return StructuredText(
        _clean_title(_extract_links(title)),
        remove_empty_enriched_str([_extract_links(al) for al in outer_alineas]),
        [
            _build_structured_text(alinea_group[0], alinea_group[1:], pattern_name_group[1:])
            for alinea_group, pattern_name_group in zip(grouped_alineas, grouped_pattern_names)
        ],
        None,
    )


def extract_pattern_names(alineas: List[str]) -> List[Optional[NumberingPattern]]:
    return detect_patterns_if_exists(alineas, (MAX_PREFIX_LEN, EXCEPTION_PREFIXES))


def _structure_text(title: str, alineas: List[str]) -> StructuredText:
    pattern_names = extract_pattern_names(alineas)
    return _build_structured_text(title, alineas, pattern_names)


REF = TypeVar('REF', bound=Union[TableReference, LinkReference])


def _find_reference(str_: EnrichedString, references: List[REF], exact_match: bool = True) -> Optional[REF]:
    for reference in references:
        if reference.reference in str_.text:
            if exact_match and str_.text != reference.reference:
                raise ValueError(f'There is sth else than a reference in this string: {str_}')
            return reference
    return None


def _find_references(str_: EnrichedString, references: List[REF]) -> List[REF]:
    return [reference for reference in references if reference.reference in str_.text]


def _add_table_if_any(str_: EnrichedString, tables: List[TableReference]) -> EnrichedString:
    match = _find_reference(str_, tables)
    if not match:
        return copy.deepcopy(str_)
    return EnrichedString('', [], match.table)


def _put_tables_back(text: StructuredText, tables: List[TableReference]) -> StructuredText:
    clean_title = _add_table_if_any(text.title, tables)

    return StructuredText(
        _clean_title(clean_title),
        [_add_table_if_any(alinea, tables) for alinea in text.outer_alineas],
        [_put_tables_back(section, tables) for section in text.sections],
        None,
    )


_LINK_PLACEHOLDER = '{{LINK}}'


def _add_links_if_any(str_: EnrichedString, links: List[LinkReference]) -> EnrichedString:
    matches = _find_references(str_, links)
    str_copy = copy.deepcopy(str_)
    for match in matches:
        str_copy.text = str_copy.text.replace(match.reference, f'{_LINK_PLACEHOLDER}{match.text}{_LINK_PLACEHOLDER}')
    str_copy.text, positions = _extract_placeholder_positions(str_copy.text, _LINK_PLACEHOLDER)
    for match, start, end in zip(matches, positions[::2], positions[1::2]):
        str_copy.links.append(Link(match.target, start, end - start))
    return str_copy


def _put_links_back(text: StructuredText, links: List[LinkReference]) -> StructuredText:
    clean_title = _add_links_if_any(text.title, links)

    return StructuredText(
        _clean_title(clean_title),
        [_add_links_if_any(alinea, links) for alinea in text.outer_alineas],
        [_put_links_back(section, links) for section in text.sections],
        None,
    )


_WEIRD_ANNEXE = 'A N N E X E'
_ROMAN_REPLACERS: List[Tuple[str, str]] = [
    ('I X', 'IX'),
    ('V I I I', 'VIII'),
    ('V I I', 'VII'),
    ('V I', 'VI'),
    ('I V', 'IV'),
    ('I I I', 'III'),
    ('I I', 'II'),
]
_ROMAN_ANNEXES = [(f'{_WEIRD_ANNEXE} {_BEF}', f'ANNEXE {_AF}') for _BEF, _AF in _ROMAN_REPLACERS]
_ANNEXE_REPLACERS = [(f'{_WEIRD_ANNEXE} S', 'ANNEXES'), *_ROMAN_ANNEXES] + [(_WEIRD_ANNEXE, 'ANNEXE')]


def _replace_weird_annexe_words(str_: str) -> str:
    res = str_
    for bef, aft in _ANNEXE_REPLACERS:
        res = res.replace(bef, aft)
    return res


def remove_summaries(alineas: List[str]) -> List[str]:
    i = 0
    found = False
    for i, alinea in enumerate(alineas):
        if alinea == 'SOMMAIRE' and i + 1 < len(alineas) and alineas[i + 1] == 'Annexe I.':
            found = True
            break
    if not found:
        return alineas
    for j in range(i + 1, len(alineas)):
        if alineas[j] == 'Modalités de calcul du dimensionnement du plan d\'épandage.':
            return alineas[:i] + alineas[j + 1 :]
    return alineas


def _html_to_structured_text(html: str, extract_structure: bool = False) -> StructuredText:
    html_with_correct_annexe = _replace_weird_annexe_words(html)
    html_without_tables, tables = _remove_tables(html_with_correct_annexe)
    html_without_links, links = _remove_links(html_without_tables)
    alineas = extract_alineas(html_without_links)
    filtered_alineas = remove_summaries(alineas)
    if extract_structure:
        final_text = _structure_text('', filtered_alineas)
    else:
        final_text = _build_structured_text('', filtered_alineas, [None for _ in range(len(filtered_alineas))])
    return _put_tables_back(_put_links_back(final_text, links), tables)


def print_structured_text(text: StructuredText, prefix: str = '') -> None:
    print(f'{prefix}{text.title}')
    new_prefix = f'\t{prefix}'
    print(new_prefix + f'\n{new_prefix}'.join([alinea.text for alinea in text.outer_alineas]))
    for section in text.sections:
        print_structured_text(section, new_prefix)


def cumsum(ints: List[int]) -> List[int]:
    if not ints:
        return []
    res = [ints[0]]
    for int_ in ints[1:]:
        res.append(res[-1] + int_)
    return res


_ALPHABET = '0123456789ABCDEF'


def _generate_random_string(size: int) -> str:
    return ''.join([random.choice(_ALPHABET) for _ in range(size)])


_REF_SIG_LEFT = '$$REF_L$$'
_REF_SIG_RIGHT = '$$REF_R$$'


def _generate_reference() -> str:
    return f'{_REF_SIG_LEFT}{_generate_random_string(6)}{_REF_SIG_RIGHT}'


_BASE_LEGIFRANCE_URL = 'https://www.legifrance.gouv.fr'


def _replace_link(link_tag: bs4.Tag, placeholder: str, add_legifrance_prefix: bool) -> Tuple[str, int]:  # side effects
    link_text = link_tag.text
    link_tag.replace_with(placeholder + link_text)
    return (_BASE_LEGIFRANCE_URL if add_legifrance_prefix else '') + link_tag['href'], len(link_text)


def _extract_links(text: str, add_legifrance_prefix: bool = True) -> EnrichedString:
    soup = BeautifulSoup(text, 'html.parser')
    placeholder = '{{{LINK}}}'
    raw_links = [_replace_link(tag, placeholder, add_legifrance_prefix) for tag in soup.find_all('a')]
    final_text, positions = _extract_placeholder_positions(soup.text, placeholder)
    links = [Link(target, position, size) for (target, size), position in secure_zip(raw_links, positions)]
    return EnrichedString(final_text, links)


def _move_first_2_upper_alineas_to_title_in_annexe(alineas: List[EnrichedString]) -> Tuple[str, List[EnrichedString]]:
    first_lines = []
    for i in [0, 1]:
        if len(alineas) > i and is_mainly_upper(alineas[i].text):
            first_lines.append(alineas[i].text)
        else:
            break
    return ' '.join(first_lines), alineas[len(first_lines) :]


def _move_first_2_upper_alineas_to_title_in_article(alineas: List[EnrichedString]) -> Tuple[str, List[EnrichedString]]:
    if not alineas:
        return '', []
    if is_probably_title(alineas[0].text):
        return alineas[0].text, alineas[1:]
    return '', alineas


def _generate_article_title(
    article: LegifranceArticle, outer_alineas: List[EnrichedString]
) -> Tuple[EnrichedString, List[EnrichedString]]:
    if article.num and 'annexe' in article.num.lower():
        title, new_outer_alineas = _move_first_2_upper_alineas_to_title_in_annexe(outer_alineas)
        final_title = f'{article.num} - {title}' if title else article.num
        return EnrichedString(final_title), new_outer_alineas
    title, new_outer_alineas = _move_first_2_upper_alineas_to_title_in_article(outer_alineas)
    title_beginning = f'Article {article.num}' if article.num is not None else 'Article'
    title_end = f' - {title}' if title else ''
    return EnrichedString(title_beginning + title_end), new_outer_alineas


_EXISTING_INSTALLATIONS_PATTERN = 'dispositions applicables aux installations existantes'


def _contains_lower(strs: List[str], pattern: str) -> bool:
    for str_ in strs:
        if pattern in str_.lower():
            return True
    return False


def _is_about_existing_installations(article: LegifranceArticle, ascendant_titles: List[str]) -> bool:
    if _contains_lower(ascendant_titles, _EXISTING_INSTALLATIONS_PATTERN):
        return True
    in_annexe = _contains_lower(ascendant_titles + [article.num or ''], 'annexe')
    return in_annexe and _EXISTING_INSTALLATIONS_PATTERN in article.content.lower()


def _extract_structured_text_from_legifrance_article(
    article: LegifranceArticle, ascendant_titles: List[str]
) -> StructuredText:
    structured_text = _html_to_structured_text(
        article.content, not _is_about_existing_installations(article, ascendant_titles)
    )
    if structured_text.title.text:
        raise ValueError(f'Should not happen. Article should not have titles. Article id : {article.id}')
    title, outer_alineas = _generate_article_title(article, structured_text.outer_alineas)
    return StructuredText(_clean_title(title), outer_alineas, structured_text.sections, None)


def _extract_structured_text_from_legifrance_section(
    section: LegifranceSection, ascendant_titles: List[str]
) -> StructuredText:
    return StructuredText(
        _clean_title(_extract_links(section.title)),
        [],
        _extract_sections(section.articles, section.sections, ascendant_titles),
        None,
    )


def _extract_structured_text(
    section_or_article: Union[LegifranceSection, LegifranceArticle], ascendant_titles: List[str]
) -> StructuredText:
    if isinstance(section_or_article, LegifranceSection):
        return _extract_structured_text_from_legifrance_section(
            section_or_article, ascendant_titles + [section_or_article.title]
        )
    return _extract_structured_text_from_legifrance_article(section_or_article, ascendant_titles)


def _extract_sections(
    articles: List[LegifranceArticle], sections: List[LegifranceSection], ascendant_titles: List[str]
) -> List[StructuredText]:
    articles_and_sections: List[Union[LegifranceArticle, LegifranceSection]] = [*articles, *sections]
    return [
        _extract_structured_text(article_or_section, ascendant_titles)
        for article_or_section in sorted(articles_and_sections, key=lambda x: x.int_ordre)
    ]


def _norm_2(dict_: Dict[str, int]) -> float:
    return sqrt(sum([x ** 2 for x in dict_.values()]))


def _normalized_scalar_product(dict_1: Dict[str, int], dict_2: Dict[str, int]) -> float:
    common_keys = {*dict_1.keys(), *dict_2.keys()}
    numerator = sum([dict_1.get(key, 0) * dict_2.get(key, 0) for key in common_keys])
    denominator = (_norm_2(dict_1) * _norm_2(dict_2)) or 1
    return numerator / denominator


def _compute_proximity(str_1: str, str_2: str) -> float:
    tokens_1 = Counter(str_1.split(' '))
    tokens_2 = Counter(str_2.split(' '))
    return _normalized_scalar_product(tokens_1, tokens_2)


def _html_to_str(html: str) -> str:
    return BeautifulSoup(html, 'html.parser').text


def _are_very_similar(article_1: LegifranceArticle, article_2: LegifranceArticle) -> bool:
    return _compute_proximity(_html_to_str(article_1.content), _html_to_str(article_2.content)) >= 0.95


def _particular_case(article_1: LegifranceArticle, article_2: LegifranceArticle) -> bool:
    return article_1.num == 'Annexe I' and article_2.num == 'Annexe I (suite)'


_ArticlePair = Tuple[LegifranceArticle, LegifranceArticle]
_ArticleGroup = Union[LegifranceArticle, _ArticlePair]


def _check_number_of_articles(groups: List[_ArticleGroup], expected_nb_articles: int) -> None:
    nb_articles = sum([1 if isinstance(group, LegifranceArticle) else 2 for group in groups])
    if nb_articles != expected_nb_articles:
        raise ValueError(f'Expecting {expected_nb_articles} articles, received {nb_articles}.')


def _group_articles_to_merge(articles: List[LegifranceArticle]) -> List[_ArticleGroup]:
    previous_is_not_none = False
    groups: List[_ArticleGroup] = []
    for i, article in enumerate(articles):
        if i and _particular_case(articles[i - 1], article):
            groups.pop()
            groups.append((articles[i - 1], article))
            previous_is_not_none = False
            continue
        if article.num is not None:
            previous_is_not_none = True
            groups.append(article)
        else:
            if previous_is_not_none:
                groups.pop()
                groups.append((articles[i - 1], article))
            else:
                groups.append(article)
            previous_is_not_none = False
    _check_number_of_articles(groups, len(articles))
    return groups


def _merge_articles(main_article: LegifranceArticle, articles_to_append: List[LegifranceArticle]) -> LegifranceArticle:
    merged_content = '\n<br/>\n'.join([main_article.content] + [art.content for art in articles_to_append])
    return LegifranceArticle(
        main_article.id,
        content=merged_content,
        int_ordre=main_article.int_ordre,
        num=main_article.num,
        etat=main_article.etat,
    )


def _handle_article_group(group: _ArticleGroup) -> LegifranceArticle:
    if isinstance(group, LegifranceArticle):
        return group
    if _are_very_similar(*group):
        return group[0]
    return _merge_articles(group[0], [group[1]])


def _sort_with_int_ordre(articles: List[LegifranceArticle]) -> List[LegifranceArticle]:
    return [art for art in sorted(articles, key=lambda x: x.int_ordre)]


def _all_none_articles(articles: List[LegifranceArticle]) -> bool:
    return all([article.num is None for article in articles])


def _delete_or_merge_articles(articles_: List[LegifranceArticle]) -> List[LegifranceArticle]:
    articles = copy.deepcopy(_sort_with_int_ordre(articles_))
    if len(articles) <= 1:
        return articles
    if _all_none_articles(articles):
        return [_merge_articles(articles[0], articles[1:])]
    grouped_articles = _group_articles_to_merge(articles)
    return [_handle_article_group(group) for group in grouped_articles]


def _clean_section_articles(section: LegifranceSection) -> LegifranceSection:
    return LegifranceSection(
        section.int_ordre,
        section.title,
        _delete_or_merge_articles(section.articles),
        [_clean_section_articles(subsection) for subsection in section.sections],
        section.etat,
    )


def _in_force(legifrance_element: Union[LegifranceArticle, LegifranceSection]) -> bool:
    return legifrance_element.etat == ArticleStatus.VIGUEUR


LFTP = TypeVar('LFTP', bound=Union[LegifranceText, LegifranceSection])


def _remove_abrogated(text: LFTP) -> LFTP:
    articles = [article for article in text.articles if _in_force(article)]
    sections = [_remove_abrogated(section) for section in text.sections if _in_force(section)]
    return replace(text, articles=articles, sections=sections)


def _clean_text_articles(text: LegifranceText, keep_abrogated: bool) -> LegifranceText:
    if keep_abrogated:
        input_text = text
    else:
        input_text = _remove_abrogated(text)
    return LegifranceText(
        input_text.visa,
        input_text.title,
        _delete_or_merge_articles(input_text.articles),
        [_clean_section_articles(section) for section in input_text.sections],
        text.last_modification_date,
    )


def legifrance_to_arrete_ministeriel(
    input_text: LegifranceText, keep_abrogated_articles: bool = False, am_id: Optional[str] = None
) -> ArreteMinisteriel:
    visa = _extract_visa(input_text.visa)
    text_with_merged_articles = _clean_text_articles(input_text, keep_abrogated_articles)
    sections = _extract_sections(text_with_merged_articles.articles, text_with_merged_articles.sections, [])
    title = standardize_title_date(text_with_merged_articles.title)
    return ArreteMinisteriel(EnrichedString(title), sections, visa, id=am_id)
