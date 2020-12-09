import bs4
from copy import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional, Union
from bs4 import BeautifulSoup

from lib.am_structure_extraction import split_alineas_in_sections
from lib.data import Cell, EnrichedString, Row, StructuredText, Table


@dataclass
class ODFTitle:
    text: str
    level: int


def _extract_title(tag: bs4.Tag) -> ODFTitle:
    level_str = tag.attrs.get(ODFXMLAttributes.TITLE_LEVEL.value)
    if not isinstance(level_str, str) or not level_str.isdigit():
        raise ValueError(
            f'Expecting {ODFXMLAttributes.TITLE_LEVEL.value} attribute to be a string digit, received: {level_str}'
        )
    return ODFTitle(tag.text.strip(), int(level_str))


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


class Linebreak:
    pass


_Element = Union[Table, str, ODFTitle, Linebreak]


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


def _merge_children(all_elements: List[List[_Element]], can_be_merged_list: List[bool]) -> List[_Element]:
    final_elements: List[_Element] = []
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


def _extract_flattened_elements(tag: Any, group_children: bool = False) -> List[_Element]:
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


def _build_enriched_alineas(alineas: List[_Element]) -> List[EnrichedString]:
    result: List[EnrichedString] = []
    for alinea in alineas:
        if isinstance(alinea, Table):
            result.append(EnrichedString('', table=alinea))
        elif isinstance(alinea, str):
            result.append(EnrichedString(alinea))
        elif isinstance(alinea, Linebreak):
            continue
        else:
            raise ValueError(f'Unexpected element type {type(alinea)} here.')
    return result


def _extract_highest_title_level(elements: List[_Element]) -> int:
    levels = [element.level for element in elements if isinstance(element, ODFTitle)]
    return min(levels) if levels else -1


def _build_structured_text(title: Optional[_Element], elements: List[_Element]) -> StructuredText:
    if title and not isinstance(title, ODFTitle):
        raise ValueError(f'Expecting title to be of type ODFTitle not {type(title)}')
    built_title = EnrichedString('' if not title or not isinstance(title, ODFTitle) else title.text)
    highest_level = _extract_highest_title_level(elements)
    matches = [bool(isinstance(elt, ODFTitle) and elt.level == highest_level) for elt in elements]
    outer, subsections = split_alineas_in_sections(elements, matches)
    outer_alineas = _build_enriched_alineas(outer)
    built_subsections = [
        _build_structured_text(
            alinea_group[0],
            alinea_group[1:],
        )
        for alinea_group in subsections
    ]
    return StructuredText(
        built_title,
        outer_alineas,
        built_subsections,
        None,
        None,
    )


def _add_title_default_numbering(text: StructuredText, prefix: str = '', rank: int = 0) -> StructuredText:
    text = copy(text)
    new_prefix = prefix + f'{rank+1}.'
    text.title.text = f'{new_prefix} {text.title.text}'
    text.sections = [_add_title_default_numbering(section, new_prefix, i) for i, section in enumerate(text.sections)]
    return text


def _build_structured_text_from_soup(tag: bs4.Tag) -> StructuredText:
    elements = _extract_flattened_elements(tag)
    text = _build_structured_text(None, elements)
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


def _load_and_transform(filename: str) -> StructuredText:
    from zipfile import ZipFile

    return _transform_odt(ZipFile(filename).read('content.xml').decode())
    # return _transform_odt(odf2xhtml.load(filename).xml())
