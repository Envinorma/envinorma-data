import bs4
import random

from bs4 import BeautifulSoup
from dataclasses import dataclass, replace
from typing import Dict, Set, Tuple, List, Optional
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
        return None
    if not isinstance(tag, bs4.Tag):
        raise ValueError(f'Expected type bs4.Tag, received {type(tag)}')
    return tag.attrs.get(attribute_name)


def _extract_bool_property_value(properties: bs4.Tag, tag_name: str) -> bool:
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


def extract_all_word_styles(soup: BeautifulSoup) -> List[Tuple[Style, int]]:
    res: List[Tuple[Style, int]] = []
    for tag in soup.find_all('r'):
        style = extract_w_tag_style(tag)
        if style:
            res.append((style, len(tag.text)))
    return res


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


def _is_header(cell_tag: bs4.Tag) -> bool:
    properties = cell_tag.find_all('w:pPr')
    if len(properties) == 0:
        return False
    return all([_extract_property_value(prop, 'w:pStyle') == 'TableHeading' for prop in properties])


def extract_cell(cell_tag: bs4.Tag) -> Tuple[bool, Cell, Optional[str]]:
    v_merge = _extract_property_value(cell_tag, 'w:vMerge')
    str_colspan = _extract_property_value(cell_tag, 'w:gridSpan')
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
