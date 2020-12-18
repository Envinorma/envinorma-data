import bs4
import os
import random
import shutil
import tempfile

from bs4 import BeautifulSoup
from dataclasses import dataclass, replace
from typing import Dict, Set, Tuple, List, Optional
from zipfile import ZipFile

from lib.data import Cell, EnrichedString, Row, Table


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

    return random.choice(list(soup.find_all(TABLE_TAG)))


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
        raise ValueError(f'Expecting non empty string.')
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


def _guess_body_font_size(soup: BeautifulSoup) -> int:
    font_size_occurrences = _extract_font_size_occurrences(extract_styles_to_nb_letters(soup))
    if not font_size_occurrences:
        raise ValueError('Need at least one style tag (rPr) in soup.')
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


def _is_table_small(table: Table) -> bool:
    nb_cells = len([0 for row in table.rows for _ in row.cells])
    return nb_cells <= 3


_PREFIX = '''<?xml version="1.0" encoding="utf-8"?>\n<w:document mc:Ignorable="w14 wp14" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'''


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
    for string in strings:
        if _is_title_beginning(string):
            groups.append([])
        groups[-1].append(string)
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
