from copy import copy
from dataclasses import replace
from typing import List, Tuple

from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import EnrichedString, Row, Table, table_to_list


def _incorporate(elements: List[str], elements_: List[str]) -> List[str]:
    lines = []
    for elt, elt_ in zip(elements, elements_):
        lines.append(elt)
        lines.append(elt_)
    return lines


def _remove_unnecessary_line_breaks(string: str) -> str:
    pieces = string.split('\n')
    return '\n'.join([x for x in pieces if x])


def _merge_header_and_row(headers: List[str], cell_texts: List[str]) -> str:
    if not headers:
        lines = cell_texts
    else:
        lines = _incorporate(headers, cell_texts)
    return _remove_unnecessary_line_breaks('\n'.join(lines))


def _build_texts_for_inspection_sheet(headers: List[str], rows: List[Row]) -> List[str]:
    all_cell_texts = table_to_list(Table(rows))
    return [_merge_header_and_row(headers, cell_texts) for cell_texts in all_cell_texts]


def _split_rows(rows: List[Row]) -> Tuple[List[Row], List[Row]]:
    if not rows:
        return [], []
    i = 0
    for i, row in enumerate(rows):
        if not row.is_header:
            break
    if rows[i].is_header:
        i += 1
    return rows[:i], rows[i:]


def _extract_headers(rows: List[Row]) -> List[str]:
    if not rows or not rows[0].is_header:
        return []
    return [cell.content.text for cell in rows[0].cells for _ in range(cell.colspan)]


def _add_inspection_sheet_in_table_rows(string: EnrichedString) -> EnrichedString:
    table = string.table
    if not table:
        return string
    headers = _extract_headers(table.rows)
    top_header_rows, other_rows = _split_rows(table.rows)
    texts = [''] * len(top_header_rows) + _build_texts_for_inspection_sheet(headers, other_rows)
    new_rows = [
        replace(row, text_in_inspection_sheet=texts[row_rank]) if not row.is_header else row
        for row_rank, row in enumerate(table.rows)
    ]
    return replace(string, table=replace(table, rows=new_rows))


def _add_table_inspection_sheet_data_in_section(section: StructuredText) -> StructuredText:
    section = copy(section)
    section.outer_alineas = [_add_inspection_sheet_in_table_rows(alinea) for alinea in section.outer_alineas]
    section.sections = [_add_table_inspection_sheet_data_in_section(subsection) for subsection in section.sections]
    return section


def add_table_inspection_sheet_data(am: ArreteMinisteriel) -> ArreteMinisteriel:
    return replace(am, sections=[_add_table_inspection_sheet_data_in_section(subsection) for subsection in am.sections])
