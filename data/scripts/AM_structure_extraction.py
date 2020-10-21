import copy
import random
import json
import re
from typing import Dict, Iterable, List, Tuple, Optional
from dataclasses import dataclass, field

from bs4 import BeautifulSoup
import bs4


@dataclass
class Link:
    target: str
    position: int
    content_size: int


@dataclass
class Cell:
    content: 'EnrichedString'
    colspan: int


@dataclass
class Row:
    cells: List[Cell]


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


@dataclass
class Article:
    id: str
    num: str
    text: StructuredText


@dataclass
class StructuredArreteMinisteriel:
    title: EnrichedString
    articles: List[Article]
    sections: List[StructuredText]
    visa: List[EnrichedString]


@dataclass
class TableReference:
    table: Table
    reference: str


def table_to_markdown(table: Table) -> str:
    return 'Pas | Encore\n--- | ------\nImplé | menté'


def enriched_string_to_markdown(str_: EnrichedString) -> str:
    if str_.table:
        return table_to_markdown(str_.table)
    return str_.text  # TODO: add link


def extract_markdown_title(title: EnrichedString) -> List[str]:
    return [f'# {enriched_string_to_markdown(title)}']


def extract_markdown_visa(visa: List[EnrichedString]) -> List[str]:
    return ['## Visa'] + [enriched_string_to_markdown(vu) for vu in visa]


def extract_markdown_text(text: StructuredText, level: int) -> List[str]:
    return [
        '#' * level + f' {enriched_string_to_markdown(text.title)}',
        *[enriched_string_to_markdown(alinea) for alinea in text.outer_alineas],
        *[line for section in text.sections for line in extract_markdown_text(section, level + 1)],
    ]


def extract_markdown_article(article: Article) -> List[str]:
    return [f'## Article {article.num}'] + extract_markdown_text(article.text, 3)


def extract_markdown_articles(articles: List[Article]) -> List[str]:
    return [line for article in articles for line in extract_markdown_article(article)]


def am_to_markdown(am: StructuredArreteMinisteriel) -> str:
    lines = [
        *extract_markdown_title(am.title),
        *extract_markdown_visa(am.visa),
        *extract_markdown_articles(am.articles),
        *[line for section in am.sections for line in extract_markdown_text(section, 2)],
    ]
    return '\n'.join(lines)


def markdown_transform_and_write_am(input_filename: str, output_filename: str):
    input_ = json.load(open(input_filename))
    output = am_to_markdown(transform_arrete_ministeriel(input_))
    json.dump(output, open(output_filename, 'w'))


def _keep_visa_string(visas: List[str]) -> List[str]:
    return [visa for visa in visas if visa[:2].lower() == 'vu']


def _extract_visa(text: Dict) -> List[EnrichedString]:
    return [_extract_links(str_) for str_ in _keep_visa_string((text.get('visa') or '').split('<br/>'))]


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
    return _extract_links(cell.replace('<br />', '\n').replace('<br/>', '\n'))


def _extract_row_data(row: bs4.Tag) -> Row:
    cell_iterator = row.find_all('td' if row.find('td') else 'th')
    res = [Cell(_extract_cell_data(str(cell)), int(cell.get('colspan') or 1)) for cell in cell_iterator]
    return Row(res)


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
        return StructuredText(_extract_links(title), list(map(_extract_links, alineas)), [])
    pattern_name = patterns[0]
    matches = [re.match(ALL_PATTERNS[pattern_name], line) is not None for line in alineas]
    outer_alineas, grouped_alineas = _split_alineas_in_sections(alineas, matches)
    return StructuredText(
        _extract_links(title),
        list(map(_extract_links, outer_alineas)),
        [_structure_text(alinea_group[0], alinea_group[1:]) for alinea_group in grouped_alineas],
    )


def _make_section_from_alineas(title: str, alineas: List[str], depth: int) -> StructuredText:
    outer_text, sub_sections = _extract_outer_text_and_sections(alineas, depth)
    return StructuredText(_extract_links(title), [_extract_links(line) for line in outer_text], sub_sections)


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
    )


def _html_to_structured_text(html: str) -> StructuredText:
    html_without_tables, tables = _remove_tables(html)
    alineas = extract_alineas(html_without_tables)
    return _put_tables_back(_structure_text('', alineas), tables)


def sort_with_int_ordre(elts: List[Dict]) -> List[Dict]:
    return sorted(elts, key=lambda x: x['intOrdre'])


def _extract_structured_text_from_section(section: Dict) -> StructuredText:
    if section.get('sections'):
        if section.get('articles'):
            raise NotImplementedError()
        return StructuredText(
            _extract_links(section.get('title') or ''),
            outer_alineas=[],
            sections=[
                _extract_structured_text_from_section(subsection)
                for subsection in sort_with_int_ordre(section['sections'])
            ],
        )
    return StructuredText(
        _extract_links(section.get('title') or ''),
        [],
        [_html_to_structured_text(article['content']) for article in sort_with_int_ordre(section['articles'])],
    )


def extract_sections(text: Dict) -> List[StructuredText]:
    return [_extract_structured_text_from_section(section) for section in sort_with_int_ordre(text['sections'])]


def extract_articles(text: Dict) -> List[Article]:
    return [
        Article(article['id'], article['num'], _html_to_structured_text(article['content']))
        for article in sort_with_int_ordre(text['articles'])
    ]


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


def _replace_link(link_tag: bs4.Tag, placeholder: str) -> Tuple[str, int]:  # side effects
    link_text = link_tag.text
    link_tag.replace_with(placeholder + link_text)
    return link_tag['href'], len(link_text)


def _extract_links(text: str) -> EnrichedString:
    soup = BeautifulSoup(text, 'html.parser')
    placeholder = '{{{LINK}}}'
    raw_links = [_replace_link(tag, placeholder) for tag in soup.find_all('a')]
    final_text, positions = _extract_placeholder_positions(soup.text, placeholder)
    links = [Link(target, position, size) for (target, size), position in secure_zip(raw_links, positions)]
    return EnrichedString(final_text, links)


def transform_arrete_ministeriel(input_text: Dict) -> StructuredArreteMinisteriel:
    visa = _extract_visa(input_text)
    title: str = input_text['title']
    articles = extract_articles(input_text)
    sections = extract_sections(input_text)
    return StructuredArreteMinisteriel(EnrichedString(title), articles, sections, visa)


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
        except Exception as exc:
            print(str(exc))
            file_to_error[file_] = traceback.format_exc()


if __name__ == '__main__':
    test()
