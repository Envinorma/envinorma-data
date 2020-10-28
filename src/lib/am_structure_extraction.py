import bs4
import copy
import json
import os
import random
import re
from bs4 import BeautifulSoup
from collections import Counter
from dataclasses import dataclass, field
from math import sqrt
from typing import Any, Dict, Iterable, List, Tuple, Optional, Union
from tqdm import tqdm


class AMStructurationError(Exception):
    pass


def _check_format(var: Any, type_: Union[type, Tuple], var_name: str) -> None:
    if not isinstance(var, type_):
        raise AMStructurationError(f'type of {var_name} is {type(var)}, nor {type_}')


def _check_dict_field(
    dict_: Dict[str, Any], key: str, expected_type: Union[type, Tuple], var_name: str, check_is_digit: bool = False
) -> None:
    if key not in dict_:
        raise AMStructurationError(f'Expecting key {key} in {var_name}')
    _check_format(dict_[key], expected_type, key)
    if check_is_digit:
        if not str.isdigit(dict_[key]):
            raise AMStructurationError(f'{var_name}[{key}] is not a digit, but {dict_[key]}')


def _check_lf_visa(legifrance_dict: Dict[str, Any]) -> None:
    _check_dict_field(legifrance_dict, 'visa', str, 'legifrance_dict')


def _check_lf_title(legifrance_dict: Dict[str, Any]) -> None:
    _check_dict_field(legifrance_dict, 'title', str, 'legifrance_dict')


def _check_lf_article(article: Dict[str, Any]) -> None:
    if 'title' in article:
        raise AMStructurationError('article should not have "title"')
    if 'sections' in article:
        raise AMStructurationError('article should not have "sections"')
    _check_dict_field(article, 'num', (type(None), str), 'legifrance.article')
    _check_dict_field(article, 'intOrdre', int, 'legifrance.article')
    _check_dict_field(article, 'id', str, 'legifrance.article')
    _check_dict_field(article, 'content', str, 'legifrance.article')


def _check_lf_articles(legifrance_dict: Dict[str, Any], depth: int = 0) -> None:
    _check_dict_field(legifrance_dict, 'articles', list, f'legifrance_dict_depth_{depth}')
    articles = legifrance_dict['articles']
    for article in articles:
        _check_lf_article(article)


def _check_lf_section(section: Dict[str, Any], depth: int = 0) -> None:
    _check_dict_field(section, 'title', str, 'legifrance.section')
    _check_dict_field(section, 'intOrdre', int, 'legifrance.section')
    _check_dict_field(section, 'sections', list, 'legifrance.section')
    _check_lf_sections(section, depth + 1)
    _check_lf_articles(section, depth + 1)


def _check_lf_sections(legifrance_dict: Dict[str, Any], depth: int = 0) -> None:
    _check_dict_field(legifrance_dict, 'sections', list, f'legifrance_dict_depth_{depth}')
    sections = legifrance_dict['sections']
    for section in sections:
        _check_lf_section(section, depth)


def _article_nb_null_num(dict_) -> int:
    return 1 if dict_['num'] is None else 0


def _text_nb_null_num_in_arrete(dict_) -> int:
    nb_null_in_articles = [_article_nb_null_num(article) for article in dict_['articles']]
    nb_null_in_sections = [_text_nb_null_num_in_arrete(section) for section in dict_['sections']]
    return sum(nb_null_in_articles + nb_null_in_sections)


def _get_total_nb_articles_in_arrete(dict_) -> int:
    return sum([len(dict_['articles'])] + [_get_total_nb_articles_in_arrete(section) for section in dict_['sections']])


def _get_proportion_of_null_articles(dict_) -> Tuple[int, int]:
    return _text_nb_null_num_in_arrete(dict_), _get_total_nb_articles_in_arrete(dict_)


def _check_proportion_of_null_articles(dict_) -> None:
    nb_null, total = _get_proportion_of_null_articles(dict_)
    if nb_null / total >= 0.5:
        raise AMStructurationError(f'Too many articles have null num: {nb_null}/{total}')


def _check_legifrance_dict(legifrance_dict: Dict[str, Any]) -> None:
    _check_lf_visa(legifrance_dict)
    _check_lf_title(legifrance_dict)
    _check_lf_articles(legifrance_dict)
    _check_lf_sections(legifrance_dict)
    _check_proportion_of_null_articles(legifrance_dict)


@dataclass
class LegifranceSection:
    intOrdre: int
    title: str
    articles: List['LegifranceArticle']
    sections: List['LegifranceSection']


@dataclass
class LegifranceArticle:
    id: str
    content: str
    intOrdre: int
    num: Optional[str]


@dataclass
class LegifranceText:
    visa: str
    title: str
    articles: List[LegifranceArticle]
    sections: List[LegifranceSection]


def _load_legifrance_article(dict_: Dict[str, Any]) -> LegifranceArticle:
    return LegifranceArticle(dict_['id'], dict_['content'], dict_['intOrdre'], dict_['num'])


def _load_legifrance_section(dict_: Dict[str, Any]) -> LegifranceSection:
    return LegifranceSection(
        dict_['intOrdre'],
        dict_['title'],
        [_load_legifrance_article(article) for article in dict_['articles']],
        [_load_legifrance_section(section) for section in dict_['sections']],
    )


def _load_legifrance_text(dict_: Dict[str, Any]) -> LegifranceText:
    return LegifranceText(
        dict_['visa'],
        dict_['title'],
        [_load_legifrance_article(article) for article in dict_['articles']],
        [_load_legifrance_section(section) for section in dict_['sections']],
    )


@dataclass
class Link:
    target: str
    position: int
    content_size: int


@dataclass
class Cell:
    content: 'EnrichedString'
    colspan: int
    rowspan: int


@dataclass
class Row:
    cells: List[Cell]
    is_header: bool


@dataclass
class Table:
    rows: List[Row]


def empty_link_list() -> List[Link]:
    return []


@dataclass
class EnrichedString:
    text: str
    links: List[Link] = field(default_factory=empty_link_list)
    table: Optional[Table] = None


@dataclass
class StructuredText:
    title: EnrichedString
    outer_alineas: List[EnrichedString]
    sections: List['StructuredText']
    legifrance_article: Optional[LegifranceArticle]


@dataclass
class ArreteMinisteriel:
    title: EnrichedString
    sections: List[StructuredText]
    visa: List[EnrichedString]


@dataclass
class TableReference:
    table: Table
    reference: str


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
    return remove_empty(
        html_text.replace('<br />', '<br/>')
        .replace('<p>', '<br/>')
        .replace("<p align='center'>", '<br/>')
        .replace('<p align=\"center\">', '<br/>')
        .replace('<p align=\"left\">', '<br/>')
        .replace('<p align=\"right\">', '<br/>')
        .replace('<p class=\"note\">', '<br/>')
        .replace('<p class=\"cliche\">', '<br/>')
        .replace('</p>', '<br/>')
        .replace(_REF_SIG_LEFT, f'<br/>{_REF_SIG_LEFT}')
        .replace(_REF_SIG_RIGHT, f'{_REF_SIG_RIGHT}<br/>')
        .split('<br/>')
    )


def _extract_cell_data(cell: str) -> EnrichedString:
    return _extract_links('\n'.join(remove_empty(cell.replace('<br />', '\n').replace('<br/>', '\n').split('\n'))))


def _is_header(row: bs4.Tag) -> bool:
    return row.find('th') is not None


def _extract_row_data(row: bs4.Tag) -> Row:
    cell_iterator = row.find_all('td' if row.find('td') else 'th')
    res = [
        Cell(_extract_cell_data(str(cell)), int(cell.get('colspan') or 1), int(cell.get('rowspan') or 1))
        for cell in cell_iterator
    ]
    return Row(res, _is_header(row))


def _extract_table(html: str) -> Table:
    soup = BeautifulSoup(html, 'html.parser')
    row_iterator = soup.find_all('tr')
    table_data = [_extract_row_data(row) for row in row_iterator]
    return Table(table_data)


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


def _remove_tables(text: str) -> Tuple[str, List[TableReference]]:
    soup = BeautifulSoup(text, 'html.parser')
    tables: List[Table] = []
    references: List[str] = []
    for div in soup.find_all('div'):
        reference = _generate_reference()
        tables.append(_extract_table(str(div)))
        div.replace_with(reference)
        references.append(reference)
    table_refs = [TableReference(table, reference) for table, reference in zip(tables, references)]
    return str(soup), table_refs


def _split_alineas_in_sections(alineas: List[str], matches: List[bool]) -> Tuple[List[str], List[List[str]]]:
    first_match = -1
    for first_match, match in enumerate(matches):
        if match:
            break
    if first_match == -1:
        return alineas, []
    outer_alineas = alineas[:first_match]
    other_matches = [first_match + 1 + idx for idx, match in enumerate(matches[first_match + 1 :]) if match]
    return (
        outer_alineas,
        [alineas[a:b] for a, b in zip([first_match] + other_matches, other_matches + [len(matches)])],
    )


ROMAN_PATTERN = '(?=[MDCLXVI])M*(C[MD]|D?C{0,3})(X[CL]|L?X{0,3})(I[XV]|V?I{0,3})'

ALL_PATTERNS = {
    'roman': rf'^{ROMAN_PATTERN}\. ',
    'numeric-d1': r'^[0-9]+\. ',
    'numeric-d2': r'^([0-9]+\.){2} ',
    'numeric-d3': r'^([0-9]+\.){3} ',
    'numeric-circle': r'^[0-9]+° ',
    'letters': r'^[a-z]\) ',
    'caps': r'^[A-Z]\. ',
    'annexe': rf'^ANNEXE [0-9]+',
    'annexe-roman': rf'^ANNEXE {ROMAN_PATTERN}',
}


def _detect_matched_pattern(string: str) -> Optional[str]:
    for pattern_name, pattern in ALL_PATTERNS.items():
        if re.match(pattern, string):
            return pattern_name
    return None


def detect_patterns(strings: List[str]) -> List[str]:
    matched_patterns = [_detect_matched_pattern(string) for string in strings]
    return [pattern for pattern in matched_patterns if pattern]


def _structure_text(title: str, alineas: List[str]) -> StructuredText:
    patterns = detect_patterns(alineas)
    if not patterns:
        return StructuredText(_extract_links(title), [_extract_links(al) for al in alineas], [], None)
    pattern_name = patterns[0]
    matches = [re.match(ALL_PATTERNS[pattern_name], line) is not None for line in alineas]
    outer_alineas, grouped_alineas = _split_alineas_in_sections(alineas, matches)
    return StructuredText(
        _extract_links(title),
        [_extract_links(al) for al in outer_alineas],
        [_structure_text(alinea_group[0], alinea_group[1:]) for alinea_group in grouped_alineas],
        None,
    )


def _add_table_if_any(str_: EnrichedString, tables: List[TableReference]) -> EnrichedString:
    match: Optional[TableReference] = None
    for table in tables:
        if table.reference in str_.text:
            match = table
            break
    if not match:
        return copy.deepcopy(str_)
    if str_.text != match.reference:
        raise ValueError(f'There is sth else than a table in this string: {str_}')
    return EnrichedString('', [], match.table)


def _put_tables_back(text: StructuredText, tables: List[TableReference]) -> StructuredText:
    clean_title = _add_table_if_any(text.title, tables)

    return StructuredText(
        clean_title,
        [_add_table_if_any(alinea, tables) for alinea in text.outer_alineas],
        [_put_tables_back(section, tables) for section in text.sections],
        None,
    )


_WEIRD_ANNEXE = 'A N N E X E'
_ROMAN_REPLACERS = [
    ('I X', 'IX'),
    ('V I I I', 'VIII'),
    ('V I I', 'VII'),
    ('V I', 'VI'),
    ('I V', 'IV'),
    ('I I I', 'III'),
    ('I I', 'II'),
]
_ROMAN_ANNEXES = [(f'{_WEIRD_ANNEXE} {_BEF}', f'ANNEXE {_AF}') for _BEF, _AF in _ROMAN_REPLACERS]
_ANNEXE_REPLACERS = [(f'{_WEIRD_ANNEXE} S', f'ANNEXES')] + _ROMAN_ANNEXES + [(_WEIRD_ANNEXE, 'ANNEXE')]


def _replace_weird_annexe_words(str_: str) -> str:
    res = str_
    for bef, aft in _ANNEXE_REPLACERS:
        res = res.replace(bef, aft)
    return res


def _html_to_structured_text(html: str) -> StructuredText:
    html_with_correct_annexe = _replace_weird_annexe_words(html)
    html_without_tables, tables = _remove_tables(html_with_correct_annexe)
    alineas = extract_alineas(html_without_tables)
    return _put_tables_back(_structure_text('', alineas), tables)


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


def _extract_structured_text_from_legifrance_section(section: LegifranceSection) -> StructuredText:
    return StructuredText(
        _extract_links(section.title), [], _extract_sections(section.articles, section.sections), None
    )


def _generate_article_title(article: LegifranceArticle) -> EnrichedString:
    return EnrichedString(f'Article {article.num}')


def _extract_structured_text_from_legifrance_article(article: LegifranceArticle) -> StructuredText:

    structured_text = _html_to_structured_text(article.content)
    if structured_text.title.text:
        raise ValueError(f'Should not happen. Article should not have titles. Article id : {article.id}')
    return StructuredText(
        _generate_article_title(article), structured_text.outer_alineas, structured_text.sections, article
    )


def _extract_structured_text(section_or_article: Union[LegifranceSection, LegifranceArticle]) -> StructuredText:
    if isinstance(section_or_article, LegifranceSection):
        return _extract_structured_text_from_legifrance_section(section_or_article)
    return _extract_structured_text_from_legifrance_article(section_or_article)


def _extract_sections(articles: List[LegifranceArticle], sections: List[LegifranceSection]) -> List[StructuredText]:
    articles_and_sections: List[Union[LegifranceArticle, LegifranceSection]] = [*articles, *sections]
    return [
        _extract_structured_text(article_or_section)
        for article_or_section in sorted(articles_and_sections, key=lambda x: x.intOrdre)
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
    return _compute_proximity(_html_to_str(article_1.content), _html_to_str(article_2.content)) >= 0.9


_ArticlePair = Tuple[LegifranceArticle, LegifranceArticle]


def _group_articles_to_merge(articles: List[LegifranceArticle]) -> List[Union[LegifranceArticle, _ArticlePair]]:
    previous_is_not_none = False
    groups: List[Union[LegifranceArticle, _ArticlePair]] = []
    for i, article in enumerate(articles):
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
    return groups


def _merge_articles(main_article: LegifranceArticle, article_to_append: LegifranceArticle) -> LegifranceArticle:
    merged_content = main_article.content + '\n<br/>\n' + article_to_append.content
    return LegifranceArticle(
        main_article.id, content=merged_content, intOrdre=main_article.intOrdre, num=main_article.num
    )


def _handle_article_group(group: Union[LegifranceArticle, _ArticlePair]) -> LegifranceArticle:
    if isinstance(group, LegifranceArticle):
        return group
    if _are_very_similar(*group):
        return group[0]
    return _merge_articles(*group)


def _sort_with_int_ordre(articles: List[LegifranceArticle]) -> List[LegifranceArticle]:
    return [art for art in sorted(articles, key=lambda x: x.intOrdre)]


def _delete_or_merge_articles(articles_: List[LegifranceArticle]) -> List[LegifranceArticle]:
    articles = copy.deepcopy(_sort_with_int_ordre(articles_))
    if len(articles) == 1:
        return articles
    grouped_articles = _group_articles_to_merge(articles)
    return [_handle_article_group(group) for group in grouped_articles]


def _clean_section_articles(section: LegifranceSection) -> LegifranceSection:
    return LegifranceSection(
        section.intOrdre,
        section.title,
        _delete_or_merge_articles(section.articles),
        [_clean_section_articles(subsection) for subsection in section.sections],
    )


def _clean_text_articles(text: LegifranceText) -> LegifranceText:
    return LegifranceText(
        text.visa,
        text.title,
        _delete_or_merge_articles(text.articles),
        [_clean_section_articles(section) for section in text.sections],
    )


def transform_arrete_ministeriel(input_text: LegifranceText) -> ArreteMinisteriel:
    visa = _extract_visa(input_text.visa)
    text_with_merged_articles = _clean_text_articles(input_text)
    sections = _extract_sections(text_with_merged_articles.articles, text_with_merged_articles.sections)
    return ArreteMinisteriel(EnrichedString(text_with_merged_articles.title), sections, visa)


def test(filename: Optional[str] = None):
    text = json.load(open(filename or 'data/data/AM/legifrance_texts/DEVP1706393A.json'))
    return transform_arrete_ministeriel(text)


def transform_and_write_test_am(filename: Optional[str] = None, output_filename: Optional[str] = None):
    from dataclasses import asdict

    if not output_filename:
        raise ValueError()
    res = test(filename)
    json.dump(asdict(res), open(output_filename, 'w'), ensure_ascii=False)


def transform_all_available_AM():
    import os
    from tqdm import tqdm
    import traceback

    input_folder = 'data/legifrance_texts'
    output_folder = 'data/structured_texts'
    file_to_error = {}
    for file_ in tqdm(os.listdir(input_folder)):
        try:
            transform_and_write_test_am(f'{input_folder}/{file_}', f'{output_folder}/{file_}')
        except Exception as exc:  # pylint: disable=broad-except
            print(str(exc))
            file_to_error[file_] = traceback.format_exc()


def _check_all_legifrance_dicts() -> None:
    folder = 'data/AM/legifrance_texts'
    for file_ in tqdm(os.listdir(folder)):
        print(file_)
        try:
            _check_legifrance_dict(json.load(open(f'{folder}/{file_}')))
        except AMStructurationError as exc:
            print(exc)


def _load_all_legifrance_texts() -> Dict[str, LegifranceText]:
    folder = 'data/AM/legifrance_texts'
    res: Dict[str, LegifranceText] = {}
    for file_ in tqdm(os.listdir(folder)):
        try:
            text_json = json.load(open(f'{folder}/{file_}'))
            _check_legifrance_dict(text_json)
            res[file_.split('.')[0]] = _load_legifrance_text(text_json)
        except AMStructurationError as exc:
            print(file_, exc)
    return res

