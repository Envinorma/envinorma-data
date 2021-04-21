from typing import Union

import dash_html_components as html
from dash.development.base_component import Component

from envinorma.back_office.components.am_component import (
    _get_html_heading_classname,
    _split_in_header_and_body_rows,
    table_to_component,
)
from envinorma.data import Cell, Row, Table, estr
from envinorma.io.parse_html import extract_table


def test_get_html_heading_classname():
    assert isinstance(_get_html_heading_classname(1)(), html.H1)
    assert isinstance(_get_html_heading_classname(6)(), html.H6)
    assert isinstance(_get_html_heading_classname(7)(), html.H6)


def test_split_in_header_and_body_rows():
    assert _split_in_header_and_body_rows([]) == ([], [])
    header_row = Row([], True)
    body_row = Row([], False)
    assert _split_in_header_and_body_rows([header_row]) == ([header_row], [])
    assert _split_in_header_and_body_rows([header_row, header_row]) == ([header_row, header_row], [])
    assert _split_in_header_and_body_rows([header_row, body_row]) == ([header_row], [body_row])
    assert _split_in_header_and_body_rows([header_row, header_row, body_row]) == ([header_row, header_row], [body_row])
    assert _split_in_header_and_body_rows([body_row]) == ([], [body_row])
    assert _split_in_header_and_body_rows([body_row, header_row]) == ([], [body_row, header_row])
    assert _split_in_header_and_body_rows([header_row, body_row, header_row]) == ([header_row], [body_row, header_row])


def _cell(text: str) -> Cell:
    return Cell(estr(text), 1, 1)


def _component_name(component: Component) -> str:
    return component.__class__.__name__.lower()


def _component_to_html(component: Union[Component, str]) -> str:
    if isinstance(component, Component):
        if component.children is None:
            child_str = ''
        elif isinstance(component.children, list):
            child_str = ''.join([_component_to_html(child) for child in component.children])
        else:
            child_str = _component_to_html(component.children)
        component_name = _component_name(component)
        return f'<{component_name}>{child_str}</{component_name}>'
    else:
        return component


def test_component_to_html():
    assert _component_to_html('test') == 'test'
    assert _component_to_html(html.H1('test')) == '<h1>test</h1>'
    assert _component_to_html(html.H1([html.B('TE'), 'st'])) == '<h1><b>TE</b>st</h1>'


def _remove_ids(table: Table) -> Table:
    for row in table.rows:
        for cell in row.cells:
            cell.content.id = ''
    return table


def test_table_to_component():
    table = Table([Row([_cell('test\ntest')], True), Row([_cell('test\ntest')], False)])
    res = table_to_component(table, None)
    assert isinstance(res.children[0].children[0].children[0].children[1], html.Br)

    new_table = extract_table(_component_to_html(res))
    assert _remove_ids(new_table) == _remove_ids(table)
