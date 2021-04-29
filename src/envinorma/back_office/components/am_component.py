from typing import List, Optional, Tuple

import dash_html_components as html
from dash.development.base_component import Component

from envinorma.back_office.components import replace_line_breaks
from envinorma.back_office.components.summary_component import summary_component
from envinorma.data import ArreteMinisteriel, StructuredText, Table, am_to_text
from envinorma.data.text_elements import Cell, Row, TextElement, Title
from envinorma.structure import structured_text_to_text_elements
from envinorma.topics.topics import TopicOntology


def _cell_to_component(cell: Cell, ontology: Optional[TopicOntology], header: bool) -> Component:
    if ontology and ontology.parse(cell.content.text):
        style = {'background-color': '#EEEEEE'}
    else:
        style = {}
    cls_ = html.Th if header else html.Td
    return cls_(replace_line_breaks(cell.content.text), colSpan=cell.colspan, rowSpan=cell.rowspan, style=style)


def _row_to_component(row: Row, ontology: Optional[TopicOntology]) -> Component:
    return html.Tr([_cell_to_component(cell, ontology, row.is_header) for cell in row.cells])


def _split_in_header_and_body_rows(rows: List[Row]) -> Tuple[List[Row], List[Row]]:
    nb_headers = 0
    for row in rows:
        if not row.is_header:
            break
        nb_headers += 1
    return rows[:nb_headers], rows[nb_headers:]


def table_to_component(table: Table, ontology: Optional[TopicOntology]) -> Component:
    header_rows, body_rows = _split_in_header_and_body_rows(table.rows)
    return html.Table(
        [
            html.Thead([_row_to_component(row, ontology) for row in header_rows]),
            html.Tbody([_row_to_component(row, ontology) for row in body_rows]),
        ],
        className='table table-bordered',
    )


def _get_html_heading_classname(level: int) -> type:
    if level <= 6:
        return getattr(html, f'H{level}')
    return html.H6


def _title_to_component(title: Title, ontology: Optional[TopicOntology], smallest_level: int) -> Component:
    if title.level == 0:
        return html.P(title.text)
    cls_ = _get_html_heading_classname(title.level + smallest_level - 1)
    if title.id:
        title_component = cls_(title.text, id=title.id)
    else:
        title_component = cls_(title.text)
    if ontology and ontology.parse(title.text):
        return html.Div(title_component, style={'background-color': '#EEEEEE'})
    return title_component


def _str_to_component(str_: str, ontology: Optional[TopicOntology]) -> Component:
    if ontology and ontology.parse(str_):
        return html.P(str_, style={'background-color': '#EEEEEE'})
    return html.P(str_)


def _make_component(element: TextElement, ontology: Optional[TopicOntology], smallest_level: int) -> Component:
    if isinstance(element, Table):
        return table_to_component(element, ontology)
    if isinstance(element, Title):
        return _title_to_component(element, ontology, smallest_level)
    if isinstance(element, str):
        return _str_to_component(element, ontology)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _text_to_elements(text: StructuredText) -> List[TextElement]:
    return structured_text_to_text_elements(text, 0)


def structured_text_component(text: StructuredText, emphasized_words: List[str], first_level: int = 1) -> Component:
    elements = _text_to_elements(text)
    ontology = TopicOntology.monotopic(emphasized_words) if emphasized_words else None
    return html.Div([_make_component(el, ontology, first_level) for el in elements])


def am_component(am: ArreteMinisteriel, emphasized_words: List[str], first_level: int = 1) -> Component:
    text = am_to_text(am)
    return structured_text_component(text, emphasized_words, first_level)


def summary_and_content(content: Component, summary: Component, height: int = 75) -> Component:
    style = {'max-height': f'{height}vh', 'overflow-y': 'auto'}
    return html.Div(
        html.Div([html.Div(summary, className='col-3'), html.Div(content, className='col-9')], className='row'),
        style=style,
    )


def am_with_summary_component(am: ArreteMinisteriel, height: int = 75, first_level: int = 1) -> Component:
    return summary_and_content(am_component(am, [], first_level), summary_component(am_to_text(am), True), height)
