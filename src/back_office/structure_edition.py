import json
import os
import traceback
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
from lib.utils import get_structured_text_filename, get_structured_text_wip_folder, jsonify

from back_office.utils import ID_TO_AM_MD, div

_LEVEL_OPTIONS = [{'label': f'Titre {i}', 'value': i} for i in range(1, 11)] + [{'label': 'Alinea', 'value': -1}]
_DROPDOWN_STYLE = {'width': '100px', 'margin-right': '10px'}


def _make_dropdown(level: int, disabled: bool = False) -> Component:
    return dcc.Dropdown(value=level, options=_LEVEL_OPTIONS, clearable=False, style=_DROPDOWN_STYLE, disabled=disabled)


def _add_dropdown(component: Component, level: int, disabled: bool = False) -> Component:
    dropdown = _make_dropdown(level, disabled=disabled)
    return div([dropdown, component], style={'display': 'flex', 'vertical-align': 'text-top', 'margin-top': '10px'})


def _cell_to_component(cell: Cell) -> Component:
    return html.Td([html.P(cell.content.text)], colSpan=cell.colspan, rowSpan=cell.rowspan)


def _row_to_component(row: Row) -> Component:
    cls_ = html.Th if row.is_header else html.Tr
    return cls_([_cell_to_component(cell) for cell in row.cells])


def _table_to_component(table: Table) -> Component:
    return _add_dropdown(html.Table([_row_to_component(row) for row in table.rows]), -1, disabled=True)


def _get_html_heading_classname(level: int) -> type:
    if level <= 6:
        return getattr(html, f'H{level}')
    return html.H6


def _title_to_component(title: Title) -> Component:
    if title.level == 0:
        return html.Header(title.text)
    title_component = _get_html_heading_classname(title.level)(title.text)
    return _add_dropdown(title_component, title.level)


def _str_to_component(str_: str) -> Component:
    return _add_dropdown(html.P(str_), -1)


def _make_form_component(element: TextElement) -> Component:
    if isinstance(element, Table):
        return _table_to_component(element)
    if isinstance(element, Title):
        return _title_to_component(element)
    if isinstance(element, str):
        return _str_to_component(element)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _text_to_elements(text: StructuredText) -> List[TextElement]:
    return structured_text_to_text_elements(text, 0)


def _get_title_ranks(elements: List[TextElement]) -> List[int]:
    res: List[int] = []
    rank = 0
    for element in elements:
        if isinstance(element, Title):
            res.append(rank)
            rank += 1
            continue
        res.append(0)
    return res


def _structure_edition_component(text: StructuredText) -> Component:
    text_elements = _text_to_elements(text)
    components = [_make_form_component(element) for element in text_elements]
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


def _time(func):
    def new_func(*args, **kwargs):
        from time import time

        start = time()
        res = func(*args, **kwargs)
        print(f'Elapsed: {time() - start}s.')
        return res

    return new_func


def _get_toc_str(text: StructuredText, level: int = 0, rank: int = 0) -> str:
    trunc_title = (level * '| ' + ' ' + text.title.text)[:120]
    return '\n'.join(
        [
            f'{trunc_title}',
            *[_get_toc_str(sec, level + 1, rank + i + 1) for i, sec in enumerate(text.sections)],
        ]
    )


def _get_md_toc(text: StructuredText) -> Component:
    return dcc.Markdown(f'```txt\n{_get_toc_str(text)}\n```')


def _get_toc(text: StructuredText, level: int = 0, rank: int = 0) -> Component:
    trunc_title = (level * '| ' + ' ' + text.title.text)[:120]
    return div(
        [
            dcc.Link(
                trunc_title,
                href=f'#TITLE_{rank}',
                style={'color': 'black', 'text-decoration': 'none', 'font-family': '"DM Mono", monospace'},
            ),
            *[_get_toc(sec, level + 1, rank + i + 1) for i, sec in enumerate(text.sections)],
        ]
    )


def _submit_button() -> Component:
    return html.Button(
        'Enregistrer',
        id='submit-val-structure-edition',
        className='btn btn-primary center',
        style={'margin-right': '10px'},
    )


def _go_back_button(parent_page: str) -> Component:
    return dcc.Link(
        html.Button('Annuler', id='submit-val-structure-edition', className='btn btn-primary center'), href=parent_page
    )


def _footer_buttons(parent_page: str) -> Component:
    style = {'display': 'inline-block'}
    return div([_submit_button(), _go_back_button(parent_page)], style)


def _fixed_footer(parent_page: str) -> Component:
    output = div(html.Div(id='form-output-structure-edition'), style={'display': 'inline-block'})
    content = div([output, html.Br(), _footer_buttons(parent_page)])
    return div(
        content,
        {
            'position': 'fixed',
            'width': '80%',
            'bottom': '0px',
            'text-align': 'center',
            'background-color': 'white',
            'padding-bottom': '35px',
            'padding-top': '35px',
        },
    )


def make_am_structure_edition_component(am_id: str, parent_page: str) -> Component:
    am = _load_am(am_id)
    if not am:
        return _am_not_found_component(am_id)
    text = am_to_text(am)
    return div(
        [
            html.H1('Sommaire'),
            _get_md_toc(text),
            html.H1('Texte'),
            _structure_edition_component(text),
            _fixed_footer(parent_page),
            html.P(am_id, hidden=True, id='am-id-structure-edition'),
        ],
        {'margin-bottom': '100px'},
    )


def _make_list(candidate: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not candidate:
        return []
    if isinstance(candidate, list):
        return candidate
    return [candidate]


def _extract_dropdown_values(components: List[Dict[str, Any]]) -> List[int]:
    res: List[int] = []
    for component in components:
        if isinstance(component, str):
            continue
        assert isinstance(component, dict)
        if component['type'] == 'Dropdown':
            value = component['props'].get('value')
            if not isinstance(value, int):
                raise ValueError(f'Expecting int values in dropdown. Received {value}.')
            res.append(value)
        else:
            res.extend(_extract_dropdown_values(_make_list(component['props'].get('children'))))
    return res


class _FormHandlingError(Exception):
    pass


def _update_element(element: TextElement, title_level: int) -> TextElement:
    if isinstance(element, str):
        if title_level == -1:
            return element
        return Title(element, level=title_level)
    if isinstance(element, Table):
        if title_level == -1:
            return element
        raise _FormHandlingError(f'Unexpected title_level value {title_level}: should be None for table element.')
    if isinstance(element, Title):
        if title_level == -1:
            return element.text
        return Title(element.text, level=title_level)
    raise NotImplementedError(f'Not implemented for element with type {type(element)}')


def _modify_elements_with_new_title_levels(elements: List[TextElement], title_levels: List[int]) -> List[TextElement]:
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


def _structure_text(am_id: str, title_levels: List[int]) -> ArreteMinisteriel:
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


def _save_text_and_get_message(am_id: str, title_levels: List[int]) -> str:
    new_version = datetime.now().strftime('%y%m%d_%H%M')
    filename = os.path.join(get_structured_text_wip_folder(am_id), new_version + '.json')
    text = _structure_text(am_id, title_levels)
    json_ = jsonify(text.to_dict())
    _write_file(json_, filename)
    return f'Enregistrement réussi. (Filename={filename})'


def _extract_title_levels_from_form(component_values: Dict[str, Any]) -> List[int]:
    return _extract_dropdown_values(_make_list(component_values['props']['children']))


def _replace_line_breaks(message: str) -> List[Component]:
    return [html.P(piece) for piece in message.split('\n')]


def _error_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-danger')


def _success_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-success')


def _extract_form_value_and_save_text(nb_clicks: int, am_id: str, state: Dict[str, Any]) -> Component:
    if nb_clicks == 0:
        return div([])
    try:
        new_title_levels = _extract_title_levels_from_form(state)
        success_message = _save_text_and_get_message(am_id, new_title_levels)
    except Exception:  # pylint: disable=broad-except
        return _error_component(f'Erreur pendant l\'enregistrement. Détails de l\'erreur:\n{traceback.format_exc()}')
    return _success_component(success_message)


def add_structure_edition_callbacks(app: dash.Dash):
    def update_output(nb_clicks, am_id, state):
        return _extract_form_value_and_save_text(nb_clicks, am_id, state)

    app.callback(
        dash.dependencies.Output('form-output-structure-edition', 'children'),
        [
            dash.dependencies.Input('submit-val-structure-edition', 'n_clicks'),
            dash.dependencies.Input('am-id-structure-edition', 'children'),
        ],
        [dash.dependencies.State('page-content', 'children')],
    )(update_output)
