import os
import traceback
from dataclasses import replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import dash
import dash_core_components as dcc
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from lib.data import ArreteMinisteriel, Cell, Row, StructuredText, Table, am_to_text
from lib.structure_extraction import TextElement, Title, build_structured_text, structured_text_to_text_elements
from lib.utils import get_structured_text_wip_folder, jsonify

from back_office.utils import assert_str, div, dump_am_state, load_am, load_am_state, write_file

_LEVEL_OPTIONS = [{'label': f'Titre {i}', 'value': i} for i in range(1, 11)] + [{'label': 'Alinea', 'value': -1}]
_DROPDOWN_STYLE = {'width': '100px', 'margin-right': '10px'}
_TOC_COMPONENT = 'structure-edition-toc'
_TEXT_AREA_COMPONENT = 'structure-edition-text-area-component'
_PREVIEW_BUTTON = 'structure-editition-preview-button'


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


def _element_to_str(element: TextElement) -> str:
    if isinstance(element, Title):
        return '#' * element.level + ' ' + element.text
    if isinstance(element, str):
        return element
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _element_to_component(rank: int, element: TextElement) -> Component:
    if isinstance(element, Table):
        return html.P(f'Tableau numéro {rank} non reproduit', className='alert alert-dark')
    if isinstance(element, Title):
        return html.P(html.Strong('#' * element.level + ' ' + element.text))
    if isinstance(element, str):
        return html.P(element)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _prepare_text_area_components(elements: List[TextElement]) -> List[Component]:
    return [_element_to_component(i, element) for i, element in enumerate(elements)]


def _prepare_text_area_value(elements: List[TextElement]) -> str:
    table_rank = 0
    strs: List[str] = []
    for element in elements:
        if isinstance(element, Table):
            strs.append(f'{_TABLEAU_PREFIX}{table_rank} non reproduit - ne pas modifier!!')
            table_rank += 1
        else:
            strs.append(_element_to_str(element))
    return '\n\n'.join(strs)


def _structure_edition_component(text: StructuredText) -> Component:
    text_elements = _text_to_elements(text)[1:]  # Don't modify main title.
    # style = {'padding': '10px', 'border': '1px solid rgba(0,0,0,.1)', 'border-radius': '5px'}
    # children=html.Div(_prepare_text_area_value(text_elements), contentEditable='true', style=style),
    return dcc.Textarea(
        id=_TEXT_AREA_COMPONENT,
        value=_prepare_text_area_value(text_elements),
        className='form-control',
        style={'height': '100vh'},
    )


def _get_toc_component() -> Component:
    return html.Div(
        html.Div(id=_TOC_COMPONENT),
        style={
            'overflow-y': 'auto',
            'position': 'sticky',
            'border-left': '2px solid #007bff',
            'font-size': '.8em',
            'padding-left': '5px',
            'height': '100vh',
        },
    )


def _get_truncated_title(title: str) -> str:
    _max_len = 80
    trunc_title = title[:_max_len]
    if len(title) > _max_len:
        return trunc_title[:-5] + '[...]'
    return trunc_title


def _submit_button() -> Component:
    return html.Button(
        'Enregistrer',
        id='submit-val-structure-edition',
        className='btn btn-primary center',
        n_clicks=0,
        style={'margin-right': '10px'},
    )


def _preview_button() -> Component:
    return html.Button(
        'Actualiser le sommaire',
        id=_PREVIEW_BUTTON,
        className='btn btn-primary center',
        n_clicks=0,
        hidden=True,
        style={'margin-right': '10px'},
    )


def _go_back_button(parent_page: str) -> Component:
    return dcc.Link(html.Button('Annuler', className='btn btn-link center'), href=parent_page)


def _footer_buttons(parent_page: str) -> Component:
    style = {'display': 'inline-block'}
    return div([_preview_button(), _submit_button(), _go_back_button(parent_page)], style)


def _fixed_footer(parent_page: str) -> Component:
    output = div(html.Div(id='form-output-structure-edition'), style={'display': 'inline-block'})
    content = div([output, html.Br(), _footer_buttons(parent_page)])
    return div(
        content,
        {
            'position': 'fixed',
            'bottom': '0px',
            'width': '80%',
            'text-align': 'center',
            'background-color': 'white',
            'padding-bottom': '35px',
            'padding-top': '35px',
        },
    )


def _get_instructions() -> Component:
    return html.Div(
        # className='container',
        children=html.A(
            id='structure-edition-collapse-button',
            children=[
                html.Button('Instructions', className='btn btn-light btn-sm'),
                dbc.Collapse(
                    html.Ul(
                        [
                            html.Li(
                                'Le niveau de titre est indiqué par le nombre de symboles "#" au début de la ligne.'
                            ),
                            html.Li(
                                'Le sommaire peut-être recalculé en cliquant sur le bouton "Actualiser le sommaire".'
                            ),
                            html.Li('Veillez à enregistrer régulièrement pour ne pas perdre le travail effectué.'),
                            html.Li(
                                'Les tableaux présents dans les AM ne sont pas reproduits ici. '
                                'Leur position est signalée par l\'expression'
                                ' "!!Tableau numéro n non reproduit - ne pas modifier!!". '
                                'Ces lignes doivent rester inchangées.'
                            ),
                        ],
                    ),
                    id='structure-edition-collapse',
                ),
            ],
        )
    )


def make_am_structure_edition_component(am_id: str, parent_page: str, am: ArreteMinisteriel) -> Component:
    text = am_to_text(am)
    return div(
        [
            html.Div(className='row', children=_get_instructions()),
            html.Div(
                className='row',
                children=[
                    html.Div(
                        className='col-9',
                        children=[html.H1('Texte'), _structure_edition_component(text)],
                    ),
                    html.Div(
                        className='col-3',
                        children=[html.H1('Sommaire'), _get_toc_component()],
                    ),
                ],
            ),
            _fixed_footer(parent_page),
            html.P(am_id, hidden=True, id='am-id-structure-edition'),
        ],
        {'margin-bottom': '300px'},
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


def _ensure_no_outer_alineas(text: StructuredText) -> None:
    if len(text.outer_alineas) != 0:
        raise _FormHandlingError(f'There should be no alineas at toplevel, found {len(text.outer_alineas)}.')


def _extract_tables(text: StructuredText) -> List[Table]:
    return [al.table for al in text.outer_alineas if al.table] + [
        tb for sec in text.sections for tb in _extract_tables(sec)
    ]


def _build_title(line: str) -> Title:
    nb_hastags = _count_prefix_hashtags(line)
    return Title(line[nb_hastags:].strip(), level=nb_hastags)


_TABLEAU_PREFIX = '!!Tableau numéro '


def _get_correct_table(line: str, tables: List[Table]) -> Table:
    digit_str = line.replace(_TABLEAU_PREFIX, '').split(' ')[0]
    try:
        digit = int(digit_str)
    except ValueError:
        raise _FormHandlingError(
            f'Erreur lors de l\'enregistrement: le numéro du tableau parsé dans une ligne est invalide. '
            f'La ligne: "{line}" ; le numéro candidat "{digit_str}"'
        )
    if digit >= len(tables):
        raise _FormHandlingError(
            f'Erreur lors de l\'enregistrement: le tableau n°{digit} est '
            'renseigné mais n\'existe pas dans l\'AM initial.'
        )
    return tables[digit]


def _make_text_element(line: str, tables: List[Table]) -> TextElement:
    if line.startswith('#'):
        return _build_title(line)
    if line.startswith(_TABLEAU_PREFIX):
        return _get_correct_table(line, tables)
    return line


def _build_new_elements(new_am: str, tables: List[Table]) -> List[TextElement]:
    lines = [x for x in new_am.split('\n') if x.strip()]
    return [_make_text_element(line, tables) for line in lines]


def _keep_tables(elements: List[TextElement]) -> List[TextElement]:
    return [el for el in elements if isinstance(el, Table)]


def _ensure_all_tables_are_found_once(initial_tables: List[Table], new_tables: List[TextElement]) -> None:
    missing_tables = [i for i, table in enumerate(initial_tables) if table not in new_tables]
    if missing_tables:
        raise _FormHandlingError(
            f'Erreur lors de l\'enregistrement: dans le texte de sortie, il manque les tableaux n° {missing_tables}.'
        )
    if len(initial_tables) != len(new_tables):
        raise _FormHandlingError(
            f'Erreur lors de l\'enregistrement: dans le texte de sortie, il y a trop '
            f'de tableaux: {len(new_tables)} contre {len(initial_tables) } dans le texte d\'entrée.'
        )


def _structure_text(am_id: str, new_am: str) -> ArreteMinisteriel:
    am_state = load_am_state(am_id)
    am = load_am(am_id, am_state)
    if not am:
        raise _FormHandlingError(f'am with id {am_id} not found, which should not happen')
    text = am_to_text(am)
    tables = _extract_tables(text)
    new_elements = _build_new_elements(new_am, tables)
    new_tables = _keep_tables(new_elements)
    _ensure_all_tables_are_found_once(tables, new_tables)
    new_text = build_structured_text(Title(text.title.text, 0), new_elements)
    _ensure_no_outer_alineas(new_text)
    return replace(am, sections=new_text.sections)


def _add_filename_to_state(am_id: str, filename: str) -> None:
    am_state = load_am_state(am_id)
    am_state.structure_draft_filenames.append(filename)
    dump_am_state(am_id, am_state)


def _save_text_and_get_message(am_id: str, new_am: str) -> str:
    new_version = datetime.now().strftime('%y%m%d_%H%M')
    filename = new_version + '.json'
    full_filename = os.path.join(get_structured_text_wip_folder(am_id), filename)
    text = _structure_text(am_id, new_am)
    json_ = jsonify(text.to_dict())
    write_file(json_, full_filename)
    _add_filename_to_state(am_id, filename)
    return f'Enregistrement réussi. (Filename={full_filename})'


def _extract_title_levels_from_form(component_values: Dict[str, Any]) -> List[int]:
    return _extract_dropdown_values(_make_list(component_values['props']['children']))


def _replace_line_breaks(message: str) -> List[Component]:
    return [html.P(piece) for piece in message.split('\n')]


def _error_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-danger')


def _success_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-success')


def _extract_form_value_and_save_text(nb_clicks: int, am_id: str, text_area_content: Dict[str, Any]) -> Component:
    new_am = assert_str(text_area_content)
    if nb_clicks == 0:
        return div([])
    try:
        success_message = _save_text_and_get_message(am_id, new_am)
    except Exception:  # pylint: disable=broad-except
        return _error_component(f'Erreur pendant l\'enregistrement. Détails de l\'erreur:\n{traceback.format_exc()}')
    return _success_component(success_message)


def _extract_all_lines_one_element(element: Dict[str, Any]) -> List[str]:
    if not element.get('props', {}).get('children'):
        return []
    children = element.get('props', {}).get('children')
    if isinstance(children, list):
        return _extract_all_lines(children)
    if isinstance(children, str):
        return [children]
    if isinstance(children, dict):
        return _extract_all_lines_one_element(children)
    raise ValueError(f'Unexpected element type type({element})')


def _extract_all_lines(elements: List[Dict[str, Any]]) -> List[str]:
    return [line for element in elements for line in _extract_all_lines_one_element(element)]


def _count_prefix_hashtags(line: str) -> int:
    for i, char in enumerate(line):
        if char != '#':
            return i
    return len(line)


assert _count_prefix_hashtags('') == 0
assert _count_prefix_hashtags('###') == 3
assert _count_prefix_hashtags(' ###') == 0
assert _count_prefix_hashtags('###  ') == 3


def _format_toc_line(line: str) -> Component:
    nb_hashtags = _count_prefix_hashtags(line)
    trunc_title = _get_truncated_title(line[nb_hashtags:])
    trunc_title_component = html.Span(trunc_title) if nb_hashtags > 1 else html.B(trunc_title)

    return html.Span([html.Span(nb_hashtags * '•' + ' ', style={'color': 'grey'}), trunc_title_component, html.Br()])


def _extract_text_area_and_display_toc(content: str) -> Component:
    # lines = _extract_all_lines(text_area_children)
    lines = content.split('\n')
    formatted_lines = [_format_toc_line(line) for line in lines if line.startswith('#')]
    new_title_levels = html.P(formatted_lines)
    return html.P(new_title_levels)


def add_structure_edition_callbacks(app: dash.Dash):
    def update_output(nb_clicks, am_id, state):
        return _extract_form_value_and_save_text(nb_clicks, am_id, state)

    app.callback(
        Output('form-output-structure-edition', 'children'),
        [Input('submit-val-structure-edition', 'n_clicks'), Input('am-id-structure-edition', 'children')],
        [State(_TEXT_AREA_COMPONENT, 'value')],
    )(update_output)

    @app.callback(
        Output(_TOC_COMPONENT, 'children'),
        [Input(_PREVIEW_BUTTON, 'n_clicks'), Input(_TEXT_AREA_COMPONENT, 'value')],
    )
    def _(_, state):
        return _extract_text_area_and_display_toc(state)

    @app.callback(
        Output('structure-edition-collapse', 'is_open'),
        [Input('structure-edition-collapse-button', 'n_clicks')],
        [State('structure-edition-collapse', 'is_open')],
    )
    def __(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return False
