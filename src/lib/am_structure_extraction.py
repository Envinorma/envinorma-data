import copy
import json
import os
import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple, Optional, Union
from tqdm import tqdm
from bs4 import BeautifulSoup
import bs4


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


# @dataclass
# class Article:
#     id: str
#     num: str
#     text: StructuredText


@dataclass
class StructuredArreteMinisteriel:
    title: EnrichedString
    sections: List[StructuredText]
    visa: List[EnrichedString]


@dataclass
class TableReference:
    table: Table
    reference: str


def _keep_visa_string(visas: List[str]) -> List[str]:
    return [visa for visa in visas if visa[:2].lower() == 'vu']


def _extract_visa(visa_raw: str) -> List[EnrichedString]:
    return [_extract_links(str_) for str_ in _keep_visa_string((visa_raw).split('<br/>'))]


def remove_empty(strs: List[str]) -> List[str]:
    stripped = [str_.strip() for str_ in strs]
    return [str_ for str_ in stripped if str_]


def extract_alineas(html_text: str) -> List[str]:
    return remove_empty(
        html_text.replace('<br />', '<br/>')
        .replace('<p>', '<br/>')
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


def _extract_outer_text_and_sections(alineas: List[str], depth: int) -> Tuple[List[str], List[StructuredText]]:
    if depth >= 3:
        return alineas, []
    pattern = '^' + r'[0-9]+\.' * depth + ' '
    matches = [re.match(pattern, line) is not None for line in alineas]
    outer_alineas, grouped_alineas = _split_alineas_in_sections(alineas, matches)
    return (
        outer_alineas,
        [_make_section_from_alineas(sub_alineas[0], sub_alineas[1:], depth + 1) for sub_alineas in grouped_alineas],
    )


ROMAN_PATTERN = '(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})'

ALL_PATTERNS = {
    'roman': rf'^{ROMAN_PATTERN}\. ',
    'numeric-d1': r'^[0-9]+\. ',
    'numeric-d2': r'^([0-9]+\.){2} ',
    'numeric-d3': r'^([0-9]+\.){3} ',
    'letters': r'^[a-z]\) ',
    'caps': r'^[A-Z]\. ',
}


def _detect_matched_pattern(string: str) -> Optional[str]:
    for pattern_name, pattern in ALL_PATTERNS.items():
        if re.match(pattern, string):
            return pattern_name
    return None


def _detect_patterns(strings: List[str]) -> List[str]:
    matched_patterns = [_detect_matched_pattern(string) for string in strings]
    return [pattern for pattern in matched_patterns if pattern]


def _structure_text(title: str, alineas: List[str]) -> StructuredText:
    patterns = _detect_patterns(alineas)
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


def _make_section_from_alineas(title: str, alineas: List[str], depth: int) -> StructuredText:
    outer_text, sub_sections = _extract_outer_text_and_sections(alineas, depth)
    return StructuredText(_extract_links(title), [_extract_links(line) for line in outer_text], sub_sections, None)


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


def _html_to_structured_text(html: str) -> StructuredText:
    html_without_tables, tables = _remove_tables(html)
    alineas = extract_alineas(html_without_tables)
    return _put_tables_back(_structure_text('', alineas), tables)


def sort_with_int_ordre(elts: List[Dict]) -> List[Dict]:
    return sorted(elts, key=lambda x: x['intOrdre'])


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
    return EnrichedString(f'Article {article.id}')


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


def transform_arrete_ministeriel(input_text: LegifranceText) -> StructuredArreteMinisteriel:
    visa = _extract_visa(input_text.visa)
    sections = _extract_sections(input_text.articles, input_text.sections)
    return StructuredArreteMinisteriel(EnrichedString(input_text.title), sections, visa)


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


def _extract_text_structure(text: Union[LegifranceText, LegifranceSection], prefix: str = '') -> List[str]:
    raw_elts: List[Union[LegifranceArticle, LegifranceSection]] = [*text.articles, *text.sections]
    elts = sorted(raw_elts, key=lambda x: x.intOrdre)
    res: List[str] = []
    for elt in elts:
        if isinstance(elt, LegifranceArticle):
            res += [f'{prefix}Article {elt.intOrdre}']
        elif isinstance(elt, LegifranceSection):
            res += [(f'{prefix}Section {elt.intOrdre}')] + _extract_text_structure(elt, f'|--{prefix}')
        else:
            raise ValueError('')
    return res
