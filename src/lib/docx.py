import bs4
import random

from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Tuple, List, Optional


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
