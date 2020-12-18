import bs4
from copy import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional
from bs4 import BeautifulSoup
from zipfile import ZipFile

from lib.data import Cell, EnrichedString, Row, StructuredText, Table
from lib.structure_extraction import Linebreak, TextElement, Title, build_structured_text


def _extract_title(tag: bs4.Tag) -> Title:
    level_str = tag.attrs.get(ODFXMLAttributes.TITLE_LEVEL.value)
    if not isinstance(level_str, str) or not level_str.isdigit():
        raise ValueError(
            f'Expecting {ODFXMLAttributes.TITLE_LEVEL.value} attribute to be a string digit, received: {level_str}'
        )
    return Title(tag.text.strip(), int(level_str))


class ODFXMLTagNames(Enum):
    TABLE_COLUMN = 'table:table-column'
    TABLE_ROW = 'table:table-row'
    TABLE_TABLE = 'table:table'
    TABLE_HEADER = 'table:table-header-rows'
    TABLE_COVERED_CELL = 'table:covered-table-cell'
    TABLE_CELL = 'table:table-cell'
    TEXT_SOFT_PAGE_BREAK = 'text:soft-page-break'
    TEXT_LIST = 'text:list'
    TEXT_LIST_ITEM = 'text:list-item'
    TEXT_LIST_HEADER = 'text:list-header'
    TEXT_H = 'text:h'
    TEXT_SECTION = 'text:section'
    TEXT_P = 'text:p'
    TEXT_TRACKED_CHANGES = 'text:tracked-changes'
    TEXT_SEQUENCE_DECLS = 'text:sequence-decls'
    TEXT_TOC = 'text:table-of-content'
    TEXT_BOOKMARK_START = 'text:bookmark-start'
    TEXT_BOOKMARK_END = 'text:bookmark-end'
    OFFICE_ANNOTATION = 'office:annotation'


class ODFXMLAttributes(Enum):
    TITLE_LEVEL = 'text:outline-level'
    TABLE_ROW_SPAN = 'table:number-rows-spanned'
    TABLE_COL_SPAN = 'table:number-columns-spanned'


def _descriptor(tag: bs4.Tag) -> str:
    return f'{tag.prefix}:{tag.name}'


def _extract_string_from_tag(tag: Any) -> str:
    if not isinstance(tag, (bs4.Tag, bs4.NavigableString)):
        raise ValueError(f'Expecting tag or NavigableString as input, received element of type {type(tag)}')
    if isinstance(tag, bs4.NavigableString):
        return str(tag).strip()
    if _descriptor(tag) == ODFXMLTagNames.TEXT_P.value:
        return _extract_string_from_tags(list(tag.children)) + '\n'
    return _extract_string_from_tags(list(tag.children))


def _remove_last_line_break(str_: str) -> str:
    if not str_:
        return str_
    if str_[-1] == '\n':
        return str_[:-1]
    return str_


def _extract_string_from_tags(tags: List[Any]) -> str:
    return _remove_last_line_break(''.join([_extract_string_from_tag(tag) for tag in tags]))


def _extract_cell(tag: Any) -> Optional[Cell]:
    if not isinstance(tag, bs4.Tag):
        raise ValueError(f'Expecting tag as input, received element of type {type(tag)}')
    _expected_names = (
        ODFXMLTagNames.TABLE_CELL.value,
        ODFXMLTagNames.TABLE_COVERED_CELL.value,
    )
    if _descriptor(tag) not in _expected_names:
        raise ValueError(f'Expecting tag with name in {_expected_names}, tag with name {_descriptor(tag)}')
    if _descriptor(tag) == ODFXMLTagNames.TABLE_COVERED_CELL.value:
        return None
    row_span = int(tag.attrs.get(ODFXMLAttributes.TABLE_ROW_SPAN.value, 1))
    col_span = int(tag.attrs.get(ODFXMLAttributes.TABLE_COL_SPAN.value, 1))
    return Cell(EnrichedString(_extract_string_from_tags(list(tag.children))), colspan=col_span, rowspan=row_span)


def _extract_cells(tags: List[Any]) -> List[Cell]:
    cells: List[Cell] = []
    for tag in tags:
        cell = _extract_cell(tag)
        if cell:
            cells.append(cell)
    return cells


def _extract_rows(tag: Any, is_header: bool = False) -> List[Row]:
    if not isinstance(tag, bs4.Tag):
        raise ValueError(f'Expecting tag as input, received element of type {type(tag)}')
    _expected_names = (
        ODFXMLTagNames.TABLE_COLUMN.value,
        ODFXMLTagNames.TABLE_ROW.value,
        ODFXMLTagNames.TEXT_SOFT_PAGE_BREAK.value,
        ODFXMLTagNames.TABLE_HEADER.value,
    )
    if _descriptor(tag) not in _expected_names:
        raise ValueError(f'Expecting tag with name in {_expected_names}, tag with name {_descriptor(tag)}')
    if _descriptor(tag) == ODFXMLTagNames.TABLE_HEADER.value:
        return [row for child in tag.children for row in _extract_rows(child, True)]
    if _descriptor(tag) in (ODFXMLTagNames.TABLE_COLUMN.value, ODFXMLTagNames.TEXT_SOFT_PAGE_BREAK.value):
        return []  # <table:column> only contains styles
    return [Row(_extract_cells(list(tag.children)), is_header)]


def _extract_table(tag: bs4.Tag) -> Table:
    if _descriptor(tag) != ODFXMLTagNames.TABLE_TABLE.value:
        raise ValueError(f'Expecting table tag, received tag with name {_descriptor(tag)}')
    rows: List[Row] = []
    for child in tag.children:
        rows.extend(_extract_rows(child))
    return Table(rows)


def _extract_list_item_text(tag: bs4.Tag) -> str:
    _expected = (ODFXMLTagNames.TEXT_LIST_ITEM.value, ODFXMLTagNames.TEXT_LIST_HEADER.value)
    if _descriptor(tag) not in _expected:
        raise ValueError(f'Expecting tag in {_expected}, received tag with name {_descriptor(tag)}')
    return _extract_string_from_tag(tag)


def _extract_list_elements(tag: bs4.Tag) -> List[str]:
    if _descriptor(tag) != ODFXMLTagNames.TEXT_LIST.value:
        raise ValueError(f'Expecting {ODFXMLTagNames.TEXT_LIST.value} tag, received tag with name {_descriptor(tag)}')
    results: List[str] = []
    for child in tag.children:
        text = '- ' + _extract_list_item_text(child)
        results.append(text)
    return results


def _is_independent_element(tag: Any) -> bool:
    if isinstance(tag, bs4.NavigableString):
        return False
    if not isinstance(tag, bs4.Tag):
        raise ValueError(f'Expecting tag as input, received element of type {type(tag)}')
    independent_elements = (
        ODFXMLTagNames.TABLE_TABLE.value,
        ODFXMLTagNames.TEXT_LIST.value,
        ODFXMLTagNames.TEXT_H.value,
        ODFXMLTagNames.TEXT_P.value,
    )
    if _descriptor(tag) in independent_elements:
        return True
    return False


def _merge_children(all_elements: List[List[TextElement]], can_be_merged_list: List[bool]) -> List[TextElement]:
    final_elements: List[TextElement] = []
    current_built_string: List[str] = []
    sep = ''
    for can_be_merged, elements in zip(can_be_merged_list, all_elements):
        if can_be_merged and len(elements) == 1 and isinstance(elements[0], str):
            elt = elements[0]
            if not isinstance(elt, str):  # to alleviate pylance type inference.
                raise ValueError()
            current_built_string.append(elt)
        elif can_be_merged and not elements:
            continue
        else:
            if current_built_string:
                final_elements.append(sep.join(current_built_string))
            current_built_string = []
            final_elements.extend(elements)
    if current_built_string:
        final_elements.append(sep.join(current_built_string))
    return final_elements


def _extract_flattened_elements(tag: Any, group_children: bool = False) -> List[TextElement]:
    if isinstance(tag, bs4.NavigableString):
        return [tag]
    if not isinstance(tag, bs4.Tag):
        raise ValueError(f'Expecting tag as input, received element of type {type(tag)}')
    tags_to_skip_with_line_break = (
        ODFXMLTagNames.TEXT_TRACKED_CHANGES.value,
        ODFXMLTagNames.TEXT_SEQUENCE_DECLS.value,
        ODFXMLTagNames.TEXT_TOC.value,
    )
    if _descriptor(tag) in tags_to_skip_with_line_break:
        return [Linebreak()]
    tags_to_skip = (ODFXMLTagNames.OFFICE_ANNOTATION.value,)
    if _descriptor(tag) in tags_to_skip:
        return []
    if _descriptor(tag) == ODFXMLTagNames.TABLE_TABLE.value:
        return [_extract_table(tag)]
    if _descriptor(tag) == ODFXMLTagNames.TEXT_LIST.value:
        return [*_extract_list_elements(tag)]
    if _descriptor(tag) == ODFXMLTagNames.TEXT_H.value:
        return [_extract_title(tag)]
    if _descriptor(tag) == ODFXMLTagNames.TEXT_P.value:
        group_children = True
    children = list(tag.children)
    children_elements = [_extract_flattened_elements(child, group_children) for child in children]
    if group_children:
        can_be_merged = [not _is_independent_element(child) for child in children]
        return _merge_children(children_elements, can_be_merged)
    return [elt for elts in children_elements for elt in elts]


def _add_title_default_numbering(text: StructuredText, prefix: str = '', rank: int = 0) -> StructuredText:
    text = copy(text)
    new_prefix = prefix + f'{rank+1}.'
    text.title.text = f'{new_prefix} {text.title.text}'
    text.sections = [_add_title_default_numbering(section, new_prefix, i) for i, section in enumerate(text.sections)]
    return text


def _build_structured_text_from_soup(tag: bs4.Tag) -> StructuredText:
    elements = _extract_flattened_elements(tag)
    text = build_structured_text(None, elements)
    text.sections = [_add_title_default_numbering(section, '', i) for i, section in enumerate(text.sections)]
    return text


def _extract_tag_from_soup(soup: BeautifulSoup) -> bs4.Tag:
    tags: List[bs4.Tag] = []
    for child in soup.children:
        if isinstance(child, bs4.element.ProcessingInstruction):
            continue
        if isinstance(child, bs4.element.NavigableString):
            if child.strip():
                raise ValueError(f'Unexpected non-void string at top level of soup: {child.strip()}')
        elif isinstance(child, bs4.Tag):
            tags.append(child)
        else:
            raise ValueError(f'Unexpected bs4 type {type(child)}')
    if len(tags) != 1:
        raise ValueError(f'Expected exactly one tag at toplevel of odt xml. Received {len(tags)}')
    return tags[0]


def _transform_odt(html: str) -> StructuredText:
    soup = BeautifulSoup(html, 'lxml-xml')
    tag = _extract_tag_from_soup(soup)  # expecting exactly one tag, might not hold True
    return _build_structured_text_from_soup(tag)


def load_and_transform(filename: str) -> StructuredText:
    from zipfile import ZipFile

    return _transform_odt(ZipFile(filename).read('content.xml').decode())
    # return _transform_odt(odf2xhtml.load(filename).xml())


def _extract_lines_from_page_element(page_element: Any) -> List[str]:
    if isinstance(page_element, str):
        return [page_element]
    if isinstance(page_element, bs4.Tag):
        return [line for child in page_element.children for line in _extract_lines_from_page_element(child)]
    raise ValueError(f'Unhandled type {type(page_element)}')


def _extract_lines_from_soup(soup: BeautifulSoup) -> List[str]:
    return [line for child in soup.children for line in _extract_lines_from_page_element(child)]


def _extract_lines(filename: str) -> List[str]:
    html = ZipFile(filename).read('content.xml').decode()
    soup = BeautifulSoup(html)
    return _extract_lines_from_soup(soup)


if __name__ == '__main__':
    from lib.am_to_markdown import extract_markdown_text

    _DOC_NAME = 'AP_DDAE_12_2014vcorrigee_cle84ed7d'  # '2020-06-11-AUTO 2001-AP AUTORISATION-Projet_AP_VF'

    FILENAME = f'/Users/remidelbouys/EnviNorma/brouillons/data/icpe_ap_odt/{_DOC_NAME}.odt'
    TEXT = load_and_transform(FILENAME)
    open(f'/Users/remidelbouys/EnviNorma/envinorma.github.io/{_DOC_NAME}.md', 'w').write(
        '\n\n'.join(extract_markdown_text(TEXT, 1))
    )
