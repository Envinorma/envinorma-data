import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component
from lib.config import STORAGE
from lib.data import ArreteMinisteriel, StructuredText, am_to_text
from lib.utils import get_structured_text_filename

from back_office.utils import ID_TO_AM_MD, div

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


def _make_non_application_form(options: _Options) -> Component:
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
            html.H2('Nouvelle condition de non application'),
            html.H4('Description (visible par l\'utilisateur)'),
            dcc.Textarea(value=''),
            html.H4('Source'),
            dropdown_source,
            html.H4('Paragraphe visé'),
            dropdown_target,
            html.H4('Alineas visés'),
            dropdown_alineas,
            html.H4('Condition'),
            html.H4(''),
            html.P('Opération :'),
            dropdown_condition_merge,
            html.P('Nombre de conditions :'),
            dropdown_nb_conditions,
            html.P('Liste de conditions :'),
            html.Div(id='nac-conditions'),
            html.Div(id='form-output-param-edition'),
            html.Button('Submit', id='submit-val-param-edition'),
            # html.H3(am_id, hidden=True, id='am-id-param-edition'),
        ]
    )


def _extract_cut_titles(text: StructuredText, level: int = 0) -> List[str]:
    return [('#' * level + ' ' + text.title.text)[:60]] + [
        title for sec in text.sections for title in _extract_cut_titles(sec, level + 1)
    ]


def _extract_paragraph_reference_dropdown_values(text: StructuredText) -> _Options:
    title_references = _extract_cut_titles(text)
    return [{'label': title, 'value': i} for i, title in enumerate(title_references)]


def _structure_edition_component(text: StructuredText) -> Component:
    dropdown_values = _extract_paragraph_reference_dropdown_values(text)
    return _make_non_application_form(dropdown_values)


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


def make_am_parametrization_edition_component(am_id: str) -> Component:
    am = _load_am(am_id)
    if not am:
        return _am_not_found_component(am_id)
    text = am_to_text(am)
    return div(_structure_edition_component(text))


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


# def _save_text(am_id: str, title_levels: List[Optional[int]]) -> str:
#     new_version = datetime.now().strftime('%y%m%d_%H%M')
#     filename = os.path.join(get_parametrization_filename(am_id), new_version + '.json')
#     text = _structure_text(am_id, title_levels)
#     json_ = jsonify(text.to_dict())
#     _write_file(json_, filename)
#     return f'Enregistrement réussi. (Filename={filename})'


def _extract_form_values(component_values: Dict[str, Any]) -> List[Optional[int]]:
    return _extract_dropdown_values(_make_list(component_values['props']['children']))


def add_parametrization_edition_callbacks(app: dash.Dash):
    # def update_output(_, am_id, children):
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
