from typing import List, Optional, Set

import dash_html_components as html
from dash.development.base_component import Component

from dash_text_components.diff import (
    AddedLine,
    DiffLine,
    Mask,
    ModifiedLine,
    RemovedLine,
    TextDifferences,
    UnchangedLine,
)
from envinorma.back_office.components import surline_text


def _positions_to_surline(mask: Mask) -> Set[int]:
    return {i for i, el in enumerate(mask.elements) if el != el.UNCHANGED}


def _diff_rows(diff_line: DiffLine) -> List[html.Tr]:
    if isinstance(diff_line, UnchangedLine):
        return [html.Tr([html.Td(diff_line.content)] * 2)]
    if isinstance(diff_line, AddedLine):
        return [html.Tr([html.Td(''), html.Td(diff_line.content, className='table-success')])]
    if isinstance(diff_line, RemovedLine):
        return [html.Tr([html.Td(diff_line.content, className='table-danger'), html.Td('')])]
    if isinstance(diff_line, ModifiedLine):
        green = {'background-color': '#ff95a2'}
        text_before = surline_text(diff_line.content_before, _positions_to_surline(diff_line.mask_before), green)
        red = {'background-color': '#80da96'}
        text_after = surline_text(diff_line.content_after, _positions_to_surline(diff_line.mask_after), red)
        row_1 = html.Tr(
            [html.Td(text_before, className='table-danger'), html.Td(text_after, className='table-success')]
        )
        return [row_1]
    raise NotImplementedError(f'Unhandled type {diff_line}')


def diff_component(diff: TextDifferences, title_left: str, title_right: str) -> Component:
    header: List[Component] = [html.Thead([html.Tr([html.Th(title_left), html.Th(title_right)])])]
    rows: List[Component] = [row for line in diff.diff_lines for row in _diff_rows(line)]
    return html.Table(header + rows, className='table table-sm table-borderless diff')
