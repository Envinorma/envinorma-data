from typing import Any, List, Union

import bs4
from bs4 import BeautifulSoup

from envinorma.models.text_elements import Cell, EnrichedString, Linebreak, Row, Table, TextElement, Title


def _ensure_str(element: TextElement) -> str:
    if not isinstance(element, str):
        raise ValueError(f'Expecting str, received {type(element)}')
    return element


def _ensure_strs_and_join(elements: List[TextElement]) -> str:
    return '\n'.join([_ensure_str(x).strip() for x in elements])


def _extract_cell_data(cell: bs4.Tag) -> EnrichedString:
    return EnrichedString(_ensure_strs_and_join(merge_between_linebreaks(_extract_text_elements_with_linebreaks(cell))))


def _is_header(row: bs4.Tag) -> bool:
    return row.find('th') is not None


def _extract_row_data(row: bs4.Tag) -> Row:
    cell_iterator = row.find_all('td' if row.find('td') else 'th')
    res = [
        Cell(_extract_cell_data(cell), int(cell.get('colspan') or 1), int(cell.get('rowspan') or 1))
        for cell in cell_iterator
    ]
    return Row(res, _is_header(row))


def extract_table_from_soup(soup: Union[BeautifulSoup, bs4.Tag]) -> Table:
    row_iterator = soup.find_all('tr')
    table_data = [_extract_row_data(row) for row in row_iterator]
    return Table(table_data)


def extract_table(html: str) -> Table:
    soup = BeautifulSoup(html, 'html.parser')
    return extract_table_from_soup(soup)


def _extract_text_elements_with_linebreaks(content: Any) -> List[TextElement]:
    if isinstance(content, str):
        return [content]
    if isinstance(content, bs4.Tag):
        if content.name in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            return [Title(' '.join(content.stripped_strings), level=int(content.name[1]), id=content.get('id'))]
        if content.name == 'br':
            return [Linebreak()]
        if content.name == 'table':
            return [extract_table_from_soup(content)]
        children = [element for tag in content.children for element in _extract_text_elements_with_linebreaks(tag)]
        if content.name in ('p', 'div'):
            children = [Linebreak(), *children, Linebreak()]
        return children
    if content is None:
        return []
    raise ValueError(f'Unexpected type {type(content)}')


def merge_between_linebreaks(elements: List[TextElement]) -> List[TextElement]:
    res: List[TextElement] = []
    current_str = ''
    for element in elements:
        if isinstance(element, str):
            current_str += element
        elif isinstance(element, (Table, Title)):
            if current_str:
                res.append(current_str)
            current_str = ''
            res.append(element)
        else:
            assert isinstance(element, Linebreak)
            if current_str:
                res.append(current_str)
            current_str = ''
    if current_str:
        res.append(current_str)
    return res


def extract_text_elements(content: Any) -> List[TextElement]:
    return merge_between_linebreaks(_extract_text_elements_with_linebreaks(content))
