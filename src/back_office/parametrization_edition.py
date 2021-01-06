from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component
from lib.config import STORAGE
from lib.data import ArreteMinisteriel, StructuredText, am_to_text

from back_office.utils import AMOperation, div

_Options = List[Dict[str, Any]]

_CONDITION_VARIABLES = ['Régime', 'Date d\'autorisation']
_CONDITION_VARIABLE_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_VARIABLES]
_CONDITION_OPERATIONS = ['<', '<=', '=', '>', '>=']
_CONDITION_OPERATION_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_OPERATIONS]


def _get_condition_component() -> Component:
    style = {'width': '200px'}
    dropdown_conditions = [
        dcc.Dropdown(options=_CONDITION_VARIABLE_OPTIONS, clearable=False, value='Date d\'autorisation', style=style),
        dcc.Dropdown(options=_CONDITION_OPERATION_OPTIONS, clearable=False, value='=', style=dict(width='50px')),
        dcc.Input(value='', type='text', style={'padding': '0', 'height': '36px'}),
    ]
    return div([*dropdown_conditions], style=dict(display='flex'))


def _get_condition_components(nb_components: int) -> Component:
    dropdown_conditions = [_get_condition_component() for _ in range(nb_components)]
    return div([*dropdown_conditions])


_ALINEA_TARGETS_OPERATIONS = [*range(1, 51), 'TOUS']
_ALINEA_OPTIONS = [{'label': condition, 'value': condition} for condition in _ALINEA_TARGETS_OPERATIONS]


def _get_main_title(operation: AMOperation) -> Component:
    return (
        html.H3('Nouvelle condition de non-application')
        if operation == operation.ADD_CONDITION
        else html.H3('Nouvelle section alternative')
    )


def _get_description_help(operation: AMOperation) -> Component:
    if operation == operation.ADD_CONDITION:
        return html.P(
            'Ex: "Ce paragraphe ne s\'applique pas aux installations à enregistrement installées avant le 01/01/2008."'
        )
    return html.P(
        'Ex: "Ce paragraphe est modifié pour les installations à enregistrement installées avant le 01/01/2008."'
    )


def _is_condition(operation: AMOperation) -> bool:
    return operation == operation.ADD_CONDITION


def _get_new_section_form() -> Component:
    return div(
        [
            html.H4('Nouvelle version'),
            html.Label('Titre', htmlFor='new-section-title', className='form-label'),
            dcc.Input(id='new-section-title', placeholder='Titre', className='form-control'),
            html.Label('Contenu du paragraphe', htmlFor='new-section-paragraph', className='form-label'),
            div(dcc.Textarea(id='new-section-paragraph', className='form-control')),
        ]
    )


def _go_back_button(parent_page: str) -> Component:
    return dcc.Link(html.Button('Retour', className='btn btn-primary center'), href=parent_page)


def _make_form(options: _Options, operation: AMOperation, parent_page: str) -> Component:
    dropdown_source = dcc.Dropdown(options=options)
    dropdown_target = dcc.Dropdown(options=options)
    dropdown_alineas = dcc.Dropdown(options=_ALINEA_OPTIONS, multi=True, value=['TOUS'])
    dropdown_condition_merge = dcc.Dropdown(
        options=[{'value': 'and', 'label': 'ET'}, {'value': 'or', 'label': 'OU'}], clearable=False, value='and'
    )
    dropdown_nb_conditions = dcc.Dropdown(
        'nac-nb-conditions', options=[{'label': i, 'value': i} for i in range(10)], clearable=False, value=1
    )
    return html.Div(
        [
            _get_main_title(operation),
            html.H4('Description (visible par l\'utilisateur)'),
            _get_description_help(operation),
            dcc.Textarea(value='', className='form-control'),
            html.H4('Source'),
            dropdown_source,
            html.H4('Paragraphe visé'),
            dropdown_target,
            html.H4('Alineas visés') if _is_condition(operation) else html.Div(),
            dropdown_alineas if _is_condition(operation) else html.Div(),
            _get_new_section_form() if not _is_condition(operation) else html.Div(),
            html.H4('Condition'),
            html.P('Opération'),
            dropdown_condition_merge,
            html.P('Nombre de conditions'),
            dropdown_nb_conditions,
            html.P('Liste de conditions'),
            html.Div(id='nac-conditions'),
            html.Div(id='form-output-param-edition'),
            html.Button(
                'Enregistrer', id='submit-val-param-edition', className='btn btn-primary', style={'margin-right': '5px'}
            ),
            _go_back_button(parent_page),
        ]
    )


def _extract_cut_titles(text: StructuredText, level: int = 0) -> List[str]:
    return [('#' * level + ' ' + text.title.text)[:60]] + [
        title for sec in text.sections for title in _extract_cut_titles(sec, level + 1)
    ]


def _extract_paragraph_reference_dropdown_values(text: StructuredText) -> _Options:
    title_references = _extract_cut_titles(text)
    return [{'label': title, 'value': i} for i, title in enumerate(title_references)]


def _structure_edition_component(text: StructuredText, operation: AMOperation, parent_page: str) -> Component:
    dropdown_values = _extract_paragraph_reference_dropdown_values(text)
    return _make_form(dropdown_values, operation, parent_page)


def make_am_parametrization_edition_component(
    am: ArreteMinisteriel, operation: AMOperation, parent_page: str
) -> Component:
    text = am_to_text(am)
    return div(_structure_edition_component(text, operation, parent_page))


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


def _write_file(content: str, filename: str):
    if STORAGE != 'local':
        raise ValueError(f'Unhandled storage value {STORAGE}')
    with open(filename, 'w') as file_:
        file_.write(content)


def _extract_form_values(component_values: Dict[str, Any]) -> List[Optional[int]]:
    return _extract_dropdown_values(_make_list(component_values['props']['children']))


def add_parametrization_edition_callbacks(app: dash.Dash):
    def update_output(n_clicks, state):
        print(n_clicks)
        print(state)
        form_values = _extract_form_values(state)
        print(form_values)
        return html.P(datetime.now().strftime('%y%m%d_%H%M'))

    app.callback(
        dash.dependencies.Output('form-output-param-edition', 'children'),
        [
            dash.dependencies.Input('submit-val-param-edition', 'n_clicks'),
            # dash.dependencies.Input('am-id-param-edition', 'children'),
        ],
        [dash.dependencies.State('page-content', 'children')],
    )(update_output)

    def nb_conditions(value):
        return _get_condition_components(value)

    app.callback(
        dash.dependencies.Output('nac-conditions', 'children'),
        [
            dash.dependencies.Input('nac-nb-conditions', 'value'),
            # dash.dependencies.Input('am-id-param-edition', 'children'),
        ],
        # [dash.dependencies.State('page-content', 'children')],
    )(nb_conditions)
