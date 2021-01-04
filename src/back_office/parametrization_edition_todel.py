import json
import os
from dataclasses import replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component
from lib.config import STORAGE
from lib.data import ArreteMinisteriel, Cell, Row, StructuredText, Table, am_to_text
from lib.structure_extraction import TextElement, Title, build_structured_text, structured_text_to_text_elements
from lib.utils import get_parametrization_filename, get_structured_text_filename, jsonify

from back_office.utils import ID_TO_AM_MD


def _make_form(titles: List[Title]) -> Component:
    options = [{'label': title.text, 'value': i} for i, title in enumerate(titles)]
    dropdown_source = dcc.Dropdown(options=options, clearable=True)
    return html.Div(
        [html.P('Condition de non application'), html.P('Source:'), dropdown_source],
        className='applicability-form',
    )


def _add_form(component: Component, titles: List[Title]) -> Component:
    form = _make_form(titles)
    return div(
        [
            div([component]),
            div([form]),
        ]
    )


def div(children: List[Component], style: Optional[Dict[str, Any]] = None) -> Component:
    return html.Div(children, style=style)


def _cell_to_component(cell: Cell) -> Component:
    return html.Td([html.P(cell.content.text)], colSpan=cell.colspan, rowSpan=cell.rowspan)


def _row_to_component(row: Row) -> Component:
    cls_ = html.Th if row.is_header else html.Tr
    return cls_([_cell_to_component(cell) for cell in row.cells])


def _table_to_component(table: Table) -> Component:
    return html.Table([_row_to_component(row) for row in table.rows])


def _get_html_heading_classname(level: int) -> type:
    if level <= 6:
        return getattr(html, f'H{level}')
    return html.H6


def _title_to_component(title: Title, all_titles: List[Title]) -> Component:
    if title.level == 0:
        return html.Header(title.text)
    return _add_form(_get_html_heading_classname(title.level)(title.text), all_titles)


def _str_to_component(str_: str) -> Component:
    return html.P(str_)


def _make_form_component(element: TextElement, all_titles: List[Title]) -> Component:
    if isinstance(element, Table):
        return _table_to_component(element)
    if isinstance(element, Title):
        return _title_to_component(element, all_titles)
    if isinstance(element, str):
        return _str_to_component(element)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _text_to_elements(text: StructuredText) -> List[TextElement]:
    return structured_text_to_text_elements(text, 0)


def _filter_titles(elements: List[TextElement]) -> List[Title]:
    return [el for el in elements if isinstance(el, Title)]


def _structure_edition_component(text: StructuredText) -> Component:
    text_elements = _text_to_elements(text)
    titles = _filter_titles(text_elements)
    components = [_make_form_component(element, titles) for element in text_elements]
    return div(components)


def _am_not_found_component(am_id: str) -> Component:
    return html.P(f'L\'arrêté ministériel avec id {am_id} n\'a pas été trouvé.')


def _load_am_from_file(am_id: str) -> ArreteMinisteriel:
    path = get_structured_text_filename(am_id)
    return ArreteMinisteriel.from_dict(json.load(open(path)))


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    am_md = ID_TO_AM_MD.get(am_id)
    if not am_md:
        return None
    return _load_am_from_file(am_md.nor or am_md.cid)


def make_am_parametrization_edition_component_todel(am_id: str) -> Component:
    am = _load_am(am_id)
    if not am:
        return _am_not_found_component(am_id)
    text = am_to_text(am)
    return div(
        [
            _structure_edition_component(text),
            html.Div(id='form-output-param-edition'),
            html.Button('Submit', id='submit-val-param-edition'),
            html.P(am_id, hidden=True, id='am-id-param-edition'),
        ]
    )


def _make_list(candidate: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not candidate:
        return []
    if isinstance(candidate, list):
        return candidate
    return [candidate]


def _extract_dropdown_values(components: List[Dict[str, Any]]) -> List[Optional[int]]:
    res: List[Optional[int]] = []
    for component in components:
        if isinstance(component, str):
            continue
        assert isinstance(component, dict)
        if component['type'] == 'Dropdown':
            res.append(component['props'].get('value'))
        else:
            res.extend(_extract_dropdown_values(_make_list(component['props'].get('children'))))
    return res


class _FormHandlingError(Exception):
    pass


def _update_element(element: TextElement, title_level: Optional[int]) -> TextElement:
    if isinstance(element, str):
        if title_level is None:
            return element
        return Title(element, level=title_level)
    if isinstance(element, Table):
        if title_level is None:
            return element
        raise _FormHandlingError(f'Unexpected title_level value {title_level}: should be None for table element.')
    if isinstance(element, Title):
        if title_level is None:
            return element.text
        return Title(element.text, level=title_level)
    raise NotImplementedError(f'Not implemented for element with type {type(element)}')


def _modify_elements_with_new_title_levels(
    elements: List[TextElement], title_levels: List[Optional[int]]
) -> List[TextElement]:
    if len(elements) != len(title_levels):
        raise _FormHandlingError(
            f'There should be as many elements as title_levels' f'(resp. {len(elements)} and {len(title_levels)}).'
        )
    return [_update_element(element, title_level) for element, title_level in zip(elements, title_levels)]


def _ensure_no_outer_alineas(text: StructuredText) -> None:
    if len(text.outer_alineas) != 0:
        raise _FormHandlingError(f'There should be no alineas at toplevel, found {len(text.outer_alineas)}.')


def _ensure_title(element: TextElement) -> Title:
    if not isinstance(element, Title):
        raise ValueError(f'Expecting title, received {type(element)}')
    return element


def _structure_text(am_id: str, title_levels: List[Optional[int]]) -> ArreteMinisteriel:
    am = _load_am(am_id)
    if not am:
        raise _FormHandlingError(f'am with id {am_id} not found, which should not happen')
    text = am_to_text(am)
    elements = _text_to_elements(text)
    main_title = _ensure_title(elements[0])
    new_elements = _modify_elements_with_new_title_levels(elements[1:], title_levels)
    new_text = build_structured_text(main_title, new_elements)
    _ensure_no_outer_alineas(new_text)
    return replace(am, sections=new_text.sections)


def _write_file(content: str, filename: str):
    if STORAGE != 'local':
        raise ValueError(f'Unhandled storage value {STORAGE}')
    with open(filename, 'w') as file_:
        file_.write(content)


def _save_text(am_id: str, title_levels: List[Optional[int]]) -> str:
    new_version = datetime.now().strftime('%y%m%d_%H%M')
    filename = os.path.join(get_parametrization_filename(am_id), new_version + '.json')
    text = _structure_text(am_id, title_levels)
    json_ = jsonify(text.to_dict())
    _write_file(json_, filename)
    return f'Enregistrement réussi. (Filename={filename})'


def _extract_form_values(component_values: Dict[str, Any]) -> List[Optional[int]]:
    return _extract_dropdown_values(_make_list(component_values['props']['children']))


def add_parametrization_edition_callbacks(app: dash.Dash):
    def update_output(_, am_id, children):
        form_values = _extract_form_values(children)
        return html.P(datetime.now().strftime('%y%m%d_%H%M'))

    app.callback(
        dash.dependencies.Output('form-output-param-edition', 'children'),
        [
            dash.dependencies.Input('submit-val-param-edition', 'n_clicks'),
            dash.dependencies.Input('am-id-param-edition', 'children'),
        ],
        [dash.dependencies.State('page-content', 'children')],
    )(update_output)
