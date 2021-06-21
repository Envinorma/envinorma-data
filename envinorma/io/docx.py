import os
import random
import re
import shutil
import string
import tempfile
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from zipfile import ZipFile

import bs4
from bs4 import BeautifulSoup

from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import Cell, EnrichedString, Row, Table, TextElement, Title
from envinorma.structure import build_structured_text


def extract_all_xml_tags_from_tag(tag: bs4.Tag) -> List[str]:
    return [tag.prefix + ':' + tag.name] + [
        name for child in tag.children if isinstance(child, bs4.Tag) for name in extract_all_xml_tags_from_tag(child)
    ]


def extract_all_xml_tags(soup: BeautifulSoup) -> List[str]:
    return [
        name for child in soup.children if isinstance(child, bs4.Tag) for name in extract_all_xml_tags_from_tag(child)
    ]


TABLE_TAG = 'tbl'


def extract_random_table(soup: BeautifulSoup) -> bs4.Tag:
    return random.choice(list(soup.find_all(TABLE_TAG)))  # noqa: S311


def find_table_containing_text(soup: BeautifulSoup, text: str) -> Optional[bs4.Tag]:
    for table in soup.find_all(TABLE_TAG):
        if text in table.text:
            return table
    return None


def write_xml(tag: bs4.Tag, filename: str) -> None:
    to_write = tag.prettify()
    if isinstance(to_write, bytes):
        raise ValueError('Expecting str')
    open(filename, 'w').write(to_write)


@dataclass(frozen=True, eq=True)
class Style:
    bold: bool
    italic: bool
    size: int
    font_name: str
    color: str


def _extract_property_value(properties: bs4.Tag, tag_name: str, attribute_name: str = 'w:val') -> Optional[str]:
    tag = properties.find(tag_name)
    if not tag:
        raise ValueError(f'Tag {tag_name} not found in {properties}')
    if not isinstance(tag, bs4.Tag):
        raise ValueError(f'Expected type bs4.Tag, received {type(tag)}')
    return tag.attrs.get(attribute_name)


def _extract_bool_property_value(properties: bs4.Tag, tag_name: str) -> bool:
    if not properties.find(tag_name):
        return False
    value = _extract_property_value(properties, tag_name)
    if not value:
        return True
    return value != '0'


def _extract_bold(properties: bs4.Tag) -> bool:
    return _extract_bool_property_value(properties, 'b')


def _extract_italic(properties: bs4.Tag) -> bool:
    return _extract_bool_property_value(properties, 'i')


def _extract_size(properties: bs4.Tag) -> int:
    value = _extract_property_value(properties, 'sz')
    if not value or not value.isdigit():
        raise ValueError(f'Expecting digit string, got {value}.')
    return int(value)


def _extract_font_name(properties: bs4.Tag) -> str:
    value = _extract_property_value(properties, 'rFonts', 'w:ascii')
    if not value:
        raise ValueError('Expecting non empty string.')
    return value


def _extract_color(properties: bs4.Tag) -> str:
    value = _extract_property_value(properties, 'color')
    if not value or len(value) != 6:
        raise ValueError(f'Expecting 6-digit string. Got {value}.')
    return value


def extract_w_tag_style(tag: bs4.Tag) -> Optional[Style]:
    properties = tag.find('rPr')
    if not properties:
        return None
    if not isinstance(properties, bs4.Tag):
        raise ValueError(f'Expecting type bs4.Tag, received type {type(properties)}')
    return Style(
        _extract_bold(properties),
        _extract_italic(properties),
        _extract_size(properties),
        _extract_font_name(properties),
        _extract_color(properties),
    )


def _estimate_text_length(tag: bs4.Tag) -> int:
    return len(tag.text.replace('\n', ' '))


def extract_all_word_styles(soup: BeautifulSoup) -> List[Tuple[Style, int]]:
    res: List[Tuple[Style, int]] = []
    for tag in soup.find_all('r'):
        style = extract_w_tag_style(tag)
        if style:
            res.append((style, _estimate_text_length(tag)))
    return res


def extract_styles_to_nb_letters(soup: BeautifulSoup) -> Dict[Style, int]:
    res: Dict[Style, int] = {}
    for style, nb_letters in extract_all_word_styles(soup):
        if style not in res:
            res[style] = 0
        res[style] += nb_letters
    return res


def _extract_font_size_occurrences(style_occurrences: Dict[Style, int]) -> Dict[int, int]:
    res: Dict[int, int] = {}
    for style, nb_letters in style_occurrences.items():
        if style.size not in res:
            res[style.size] = 0
        res[style.size] += nb_letters
    return res


class DocxError(Exception):
    pass


class DocxNoTextError(DocxError):
    pass


def _guess_body_font_size(soup: BeautifulSoup) -> int:
    font_size_occurrences = _extract_font_size_occurrences(extract_styles_to_nb_letters(soup))
    if not font_size_occurrences:
        strings = '\n'.join(list(soup.stripped_strings))
        raise DocxNoTextError(
            f'Need at least one style tag (rPr) in soup.\nZone: {strings[:280]}\nSoup{str(soup)[:280]}'
        )
    return sorted(font_size_occurrences.items(), key=lambda x: x[1])[-1][0]


def _is_body(style: Style, body_font_size: int) -> bool:
    if style.size > body_font_size:
        return False
    if style.size == body_font_size and style.bold:
        return False
    return True


def _replace_tables_and_body_text_with_empty_p(
    soup: BeautifulSoup, body_font_size: Optional[int] = None
) -> BeautifulSoup:
    soup = _copy_soup(soup)
    body_font_size = _guess_body_font_size(soup) if body_font_size is None else body_font_size
    for tag in soup.find_all('w:tbl'):
        tag.replace_with(soup.new_tag('w:p'))
    for tag in soup.find_all('w:r'):
        style = extract_w_tag_style(tag)
        if style and _is_body(style, body_font_size):
            tag.replace_with(soup.new_tag('w:p'))
    return soup


def remove_empty(strs: List[str]) -> List[str]:
    return [str_ for str_ in strs if str_]


def remove_duplicate_line_break(str_: str) -> str:
    return '\n'.join(remove_empty(str_.split('\n')))


def print_table_properties(tag: bs4.Tag, verbose: bool = False) -> None:
    for i, row in enumerate(tag.find_all('w:tr')):
        if not isinstance(row, bs4.Tag):
            raise ValueError()
        for j, cell in enumerate(row.find_all('w:tc')):
            print(f'Row {i}, cell {j}')
            if verbose:
                print(remove_duplicate_line_break(cell.text))


def _is_header_cell(properties: bs4.Tag) -> bool:
    tag_name = 'w:pStyle'
    if not properties.find(tag_name):
        return False
    return _extract_property_value(properties, tag_name) == 'TableHeading'


def _is_header(cell_tag: bs4.Tag) -> bool:
    properties = cell_tag.find_all('w:pPr')
    if len(properties) == 0:
        return False
    return all([_is_header_cell(prop) for prop in properties])


def extract_cell(cell_tag: bs4.Tag) -> Tuple[bool, Cell, Optional[str]]:
    v_merge = _extract_property_value(cell_tag, 'w:vMerge') if cell_tag.find('w:vMerge') else None
    str_colspan = _extract_property_value(cell_tag, 'w:gridSpan') if cell_tag.find('w:gridSpan') else None
    colspan = int(str_colspan or 1)
    rowspan = 1  # changed globally next using w:vMerge tag
    return _is_header(cell_tag), Cell(EnrichedString(str(cell_tag)), colspan, rowspan), v_merge


def extract_row(row_tag: bs4.Tag) -> Tuple[Row, List[Optional[str]]]:
    cells: List[Cell] = []
    are_header: List[bool] = []
    v_merge_values: List[Optional[str]] = []
    for cell_tag in row_tag.find_all('w:tc'):
        if not isinstance(cell_tag, bs4.Tag):
            raise ValueError(f'Expecting tag, received {type(cell_tag)}')
        is_header, cell, v_merge_value = extract_cell(cell_tag)
        v_merge_values.append(v_merge_value)
        are_header.append(is_header)
        cells.append(cell)
    if all(are_header):
        is_row_header = True
    elif all(map(lambda x: not x, are_header)):
        is_row_header = False
    else:
        raise ValueError(f'Some cells are header, some other are not: {are_header}.')
    return Row(cells, is_row_header), v_merge_values


def _build_table_with_correct_rowspan(rows: List[Row], v_merge_values: List[List[Optional[str]]]) -> Table:
    col_index_to_main_cell_id: Dict[int, int] = {}
    cells_to_delete: Set[int] = set()
    cells_to_rowspan: Dict[int, int] = {}
    for i, row in enumerate(v_merge_values):
        col_index = 0
        for j, value in enumerate(row):
            cell = rows[i].cells[j]
            col_index += cell.colspan
            if value is None:
                if col_index in col_index_to_main_cell_id:
                    del col_index_to_main_cell_id[col_index]
                continue
            if value == 'restart':
                col_index_to_main_cell_id[col_index] = id(cell)
                cells_to_rowspan[col_index_to_main_cell_id[col_index]] = 1
            elif value == 'continue':
                cells_to_delete.add(id(cell))
                cells_to_rowspan[col_index_to_main_cell_id[col_index]] += 1
            else:
                raise ValueError(f'Unexpected w_merge value {value}')
    return Table(
        [
            Row(
                [
                    replace(cell, rowspan=cells_to_rowspan.get(id(cell), 1))
                    for cell in row.cells
                    if id(cell) not in cells_to_delete
                ],
                row.is_header,
            )
            for row in rows
        ]
    )


def extract_table(tag: bs4.Tag) -> Table:
    rows: List[Row] = []
    v_merge_values: List[List[Optional[str]]] = []
    for row_tag in tag.find_all('w:tr'):
        if not isinstance(row_tag, bs4.Tag):
            raise ValueError(f'Expecting tag, received {type(row_tag)}')
        row, v_merge = extract_row(row_tag)
        rows.append(row)
        v_merge_values.append(v_merge)
    return _build_table_with_correct_rowspan(rows, v_merge_values)


def get_docx_xml(filename: str) -> str:
    return ZipFile(filename).read('word/document.xml').decode()


def get_docx_xml_soup(filename: str) -> BeautifulSoup:
    return BeautifulSoup(get_docx_xml(filename), 'lxml-xml')


def _is_table_small(table: Table) -> bool:
    nb_cells = len([0 for row in table.rows for _ in row.cells])
    return nb_cells <= 3


_PREFIX = (
    '<?xml version="1.0" encoding="utf-8"?>\n<w:document mc:Ignorable="w14 wp14" xmlns:m="http://schemas.o'
    'penxmlformats.org/officeDocument/2006/math" xmlns:mc="http://schemas.openxmlformats.org/markup-compa'
    'tibility/2006" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mv="urn:sch'
    'emas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schema'
    's.openxmlformats.org/officeDocument/2006/relationships" xmlns:v="urn:schemas-microsoft-com:vml" xmln'
    's:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w10="urn:schemas-microsoft-'
    'com:office:word" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wne="http://'
    'schemas.microsoft.com/office/word/2006/wordml" xmlns:wp="http://schemas.openxmlformats.org/drawingml'
    '/2006/wordprocessingDrawing" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessin'
    'gDrawing" xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:wpg="'
    'http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microso'
    'ft.com/office/word/2010/wordprocessingInk" xmlns:wps="http://schemas.microsoft.com/office/word/2010/'
    'wordprocessingShape">'
)


def _extract_p_tags_from_cells(table: Table) -> List[bs4.Tag]:
    cells = [cell for row in table.rows for cell in row.cells]
    tags = [BeautifulSoup(_PREFIX + cell.content.text, 'lxml-xml').find('w:document') for cell in cells]
    p_tags: List[bs4.Tag] = []
    for tag in tags:
        if not isinstance(tag, bs4.Tag):
            raise ValueError()
        for p_tag in tag.find_all('w:p'):
            if not isinstance(p_tag, bs4.Tag):
                raise ValueError()
            p_tags.append(p_tag.extract())
    return p_tags


def _remove_table_inplace(soup: BeautifulSoup, table: Table, tag: bs4.Tag):
    span_tag = soup.new_tag('w:p')
    if not isinstance(span_tag, bs4.Tag):
        raise ValueError(f'Expecting tag, received {type(tag)}')
    tag.wrap(span_tag)
    tag.extract()
    new_tags = _extract_p_tags_from_cells(table)
    for new_tag in new_tags:
        span_tag.append(new_tag)
    span_tag.unwrap()
    return soup


def _copy_soup(soup: BeautifulSoup) -> BeautifulSoup:
    # Hacky, avoid deepcopy and recursion errors
    return BeautifulSoup(str(soup), soup.builder.NAME)


def _replace_small_tables(soup: BeautifulSoup) -> BeautifulSoup:
    soup = _copy_soup(soup)
    tables = [extract_table(tag) for tag in soup.find_all('w:tbl')]
    for tag, table in zip(soup.find_all('w:tbl'), tables):
        if not isinstance(tag, bs4.Tag):
            raise ValueError(f'Expecting tag, received {type(tag)}')
        if _is_table_small(table):
            _remove_table_inplace(soup, table, tag)
    return soup


def write_new_document(input_filename: str, new_document_xml: str, new_filename: str):
    tmp_dir = tempfile.mkdtemp()
    zip_ = ZipFile(input_filename)
    zip_.extractall(tmp_dir)
    with open(os.path.join(tmp_dir, 'word/document.xml'), 'wb') as f:
        f.write(new_document_xml.encode())
    filenames = zip_.namelist()
    with ZipFile(new_filename, 'w') as docx:
        for filename in filenames:
            docx.write(os.path.join(tmp_dir, filename), filename)
    shutil.rmtree(tmp_dir)


def _is_title_beginning(string: str) -> bool:
    patterns = ['titre', 'article', 'chapitre']
    for pattern in patterns:
        if string[: len(pattern)].lower() == pattern:
            return True
    return False


def _group_strings(strings: List[str]) -> List[str]:
    groups: List[List[str]] = [[]]
    for string_ in strings:
        if _is_title_beginning(string_):
            groups.append([])
        groups[-1].append(string_)
    return [' '.join(group) for group in groups if group]


def _build_headers(soup: BeautifulSoup) -> List[str]:
    res = []
    for tag in soup.find_all('w:p'):
        res.extend(_group_strings(tag.stripped_strings))
    return [x for x in res if x]


def empty_soup(soup: BeautifulSoup) -> bool:
    return ''.join(soup.stripped_strings) == ''


def extract_headers(soup: BeautifulSoup) -> List[str]:
    if empty_soup(soup):
        return []
    clean_soup = _replace_small_tables(soup)
    titles_soup = _replace_tables_and_body_text_with_empty_p(clean_soup)
    return _build_headers(titles_soup)


def _generate_reference() -> str:
    return 'REF_' + ''.join([random.choice(string.ascii_letters) for _ in range(6)])  # noqa: S311


def _is_a_reference(candidate: str) -> bool:
    return len(candidate) == 10 and candidate[:4] == 'REF_'


def _extract_tags(
    soup: BeautifulSoup, tag_finder: Callable[[BeautifulSoup], List[bs4.Tag]]
) -> Tuple[BeautifulSoup, Dict[str, bs4.Tag]]:
    soup = _copy_soup(soup)
    tags = tag_finder(soup)
    reference_to_tag: Dict[str, bs4.Tag] = {}
    for tag in tags:
        ref = _generate_reference()
        str_ = soup.new_string(ref)
        extracted = tag.replace_with(str_)
        if not extracted:
            raise ValueError('Expecting Tag, not None.')
        reference_to_tag[ref] = extracted
        str_.wrap(soup.new_tag('w:r'))
    return soup, reference_to_tag


def _check_is_tag(candidate: Any) -> bs4.Tag:
    if not isinstance(candidate, bs4.Tag):
        raise ValueError(f'Expecting type Tag, not {type(candidate)}')
    return candidate


def _is_tag_body(tag: bs4.Tag, body_font_size: int) -> bool:
    style = extract_w_tag_style(tag)
    if style and _is_body(style, body_font_size):
        return True
    return False


def _find_table_tags(soup: BeautifulSoup) -> List[bs4.Tag]:
    return [_check_is_tag(tag) for tag in soup.find_all('tbl')]


def _find_body_tags(soup: BeautifulSoup) -> List[bs4.Tag]:
    body_font_size = _guess_body_font_size(soup)
    body_tags = [_check_is_tag(tag) for tag in soup.find_all('w:r') if _is_tag_body(_check_is_tag(tag), body_font_size)]
    return body_tags


def _remove_tables_and_bodies(soup: BeautifulSoup) -> Tuple[BeautifulSoup, Dict[str, bs4.Tag], Dict[str, bs4.Tag]]:
    soup, table_references = _extract_tags(soup, _find_table_tags)
    soup, body_references = _extract_tags(soup, _find_body_tags)
    return soup, table_references, body_references


def _remove_xml_tags(str_: str) -> str:
    return ' '.join(BeautifulSoup(str_, 'lxml-xml').stripped_strings)


def _cleanup_cell(cell: Cell) -> Cell:
    return replace(cell, content=EnrichedString(_remove_xml_tags(cell.content.text)))


def _cleanup_row_cells(row: Row) -> Row:
    return replace(row, cells=[_cleanup_cell(cell) for cell in row.cells])


def _cleanup_table_cells(table: Table) -> Table:
    return Table([_cleanup_row_cells(row) for row in table.rows])


def _count_cells(table: Table) -> int:
    return sum([len(row.cells) for row in table.rows])


def _safely_extract_table(tag: bs4.Tag, min_nb_cells: int) -> Table:
    table = _cleanup_table_cells(extract_table(tag))
    nb_cells = _count_cells(table)
    if nb_cells < min_nb_cells:
        raise ValueError(f'Unexpected number of cells {nb_cells}. Expecting at least {min_nb_cells}')
    return table


def _extract_strings(tag: bs4.Tag) -> List[str]:
    return [' '.join(tag.stripped_strings)]


def _build_elements(
    str_: str,
    table_references: Dict[str, bs4.Tag],
    body_references: Dict[str, bs4.Tag],
    titles: List[str],
    title_cursor: Tuple[int, int],
) -> Tuple[List[TextElement], Tuple[int, int]]:
    elements: List[TextElement] = []
    if _is_a_reference(str_):
        if str_ in table_references:
            elements.append(_safely_extract_table(table_references[str_], 3))
        elif str_ in body_references:
            elements.extend(_extract_strings(body_references[str_]))
        else:
            raise ValueError(f'Reference {str_} not found')
    else:
        expected_string = titles[title_cursor[0]][title_cursor[1] :]
        if expected_string[: len(str_)] != str_:
            raise ValueError(f'Expecting string {str_} to be the prefix of {expected_string}')
        if title_cursor[1] == 0:
            elements.append(Title(titles[title_cursor[0]], 1))
        if expected_string == str_:
            title_cursor = (title_cursor[0] + 1, 0)
        else:
            title_cursor = (title_cursor[0], title_cursor[1] + len(str_) + 1)
    return elements, title_cursor


_PATTERNS = [
    r'[0-9]+\.+[0-9]+',
    r'[0-9]+\.+[0-9]+\.[0-9]+',
    r'[0-9]+\.+[0-9]+\.[0-9]+\.[0-9]+',
]


def _guess_title_level(title: str) -> int:
    if 'titre' in title.lower():
        return 1
    for i, pattern in enumerate(_PATTERNS[::-1]):
        if re.findall(pattern, title):
            return 4 - i
    return 1


def _guess_and_add_title_levels(elements: List[TextElement]) -> List[TextElement]:
    return [
        element if not isinstance(element, Title) else replace(element, level=_guess_title_level(element.text))
        for element in elements
    ]


def _extract_elements(soup: BeautifulSoup) -> List[TextElement]:
    titles = extract_headers(soup)
    soup, table_references, body_references = _remove_tables_and_bodies(soup)
    stripped_strings = list(soup.stripped_strings)
    all_elements: List[TextElement] = []
    title_cursor = (0, 0)
    for str_ in stripped_strings:
        elements, title_cursor = _build_elements(str_, table_references, body_references, titles, title_cursor)
        all_elements.extend(elements)
    return _guess_and_add_title_levels(all_elements)


def build_structured_text_from_soup(soup: BeautifulSoup) -> StructuredText:
    clean_soup = _replace_small_tables(soup)
    elements = _extract_elements(clean_soup)
    return build_structured_text(None, elements)


def build_structured_text_from_docx_xml(xml: str) -> StructuredText:
    return build_structured_text_from_soup(BeautifulSoup(xml, 'lxml-xml'))


def extract_text_from_file(filename: str) -> StructuredText:
    return build_structured_text_from_docx_xml(get_docx_xml(filename))


def extract_text(file_content: bytes) -> StructuredText:
    with tempfile.NamedTemporaryFile('wb', prefix='docx_extraction') as file_:
        file_.write(file_content)
        return extract_text_from_file(file_.name)
