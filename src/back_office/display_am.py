import traceback
from datetime import datetime
from typing import Any, Counter, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from lib.am_enriching import detect_and_add_topics
from lib.data import ArreteMinisteriel, Regime, StructuredText, random_id
from lib.parametric_am import apply_parameter_values_to_am, extract_parameters_from_parametrization
from lib.parametrization import Parameter, ParameterEnum, ParameterType, Parametrization
from lib.topics.patterns import Topic, TopicName
from lib.topics.topics import TOPIC_ONTOLOGY

from back_office.app_init import app
from back_office.components import error_component
from back_office.components.parametric_am import parametric_am_component
from back_office.fetch_data import load_initial_am, load_parametrization, load_structured_am
from back_office.utils import ID_TO_AM_MD

_PREFIX = __file__.split('/')[-1].replace('.py', '').replace('_', '-')
_AM = _PREFIX + '-am'
_SUBMIT = _PREFIX + '-submit'
_AM_ID = _PREFIX + '-am-id'
_FORM_OUTPUT = _PREFIX = '-form-output'


def _store(parameter_id: Any) -> Dict[str, Any]:
    return {'type': _PREFIX + '-store', 'key': parameter_id}


def _input(parameter_id: Any) -> Dict[str, Any]:
    return {'type': _PREFIX + '-input', 'key': parameter_id}


def _am_component(am: ArreteMinisteriel) -> Component:
    return parametric_am_component(am, _PREFIX)


def _am_component_with_toc(am: ArreteMinisteriel) -> Component:
    return html.Div(_am_component(am), id=_AM)


def _extract_name(parameter: Parameter) -> str:
    if parameter == ParameterEnum.DATE_AUTORISATION.value:
        return 'Date d\'autorisation'
    if parameter == ParameterEnum.DATE_ENREGISTREMENT.value:
        return 'Date d\'enregistrement'
    if parameter == ParameterEnum.DATE_DECLARATION.value:
        return 'Date de déclaration'
    if parameter == ParameterEnum.DATE_INSTALLATION.value:
        return 'Date de mise en service'
    if parameter == ParameterEnum.REGIME.value:
        return 'Régime'
    raise NotImplementedError(parameter)


def _build_input(id_: str, parameter_type: ParameterType) -> str:
    if parameter_type == ParameterType.BOOLEAN:
        return dbc.Checklist(options=[{'label': '', 'value': 1}], switch=True, value=1, id=_input(id_))
    if parameter_type == ParameterType.DATE:
        return dcc.DatePickerSingle(style={'padding': '0px', 'width': '100%'}, id=_input(id_))
    if parameter_type == ParameterType.REGIME:
        options = [{'value': reg.value, 'label': reg.value} for reg in Regime]
        return dcc.Dropdown(options=options, id=_input(id_))
    raise NotImplementedError(parameter_type)


def _build_parameter_input(parameter: Parameter) -> Component:
    parameter_name = _extract_name(parameter)
    return html.Div(
        [
            html.Label(parameter_name, htmlFor=(id_ := random_id())),
            _build_input(id_, parameter.type),
            dcc.Store(data=parameter.id, id=_store(parameter.id)),
        ],
        className='col-md-12',
    )


def _parametrization_form(parametrization: Parametrization) -> Component:
    parameters = extract_parameters_from_parametrization(parametrization)
    if not parameters:
        return html.P('Pas de paramètres pour cet arrêté.')
    sorted_parameters = sorted(list(parameters), key=lambda x: x.id)
    return html.Div(
        [
            *[_build_parameter_input(parameter) for parameter in sorted_parameters],
            html.Div(id=_FORM_OUTPUT, style={'margin-top': '10px', 'margin-bottom': '10px'}),
            html.Div(
                html.Button('Valider', className='btn btn-primary', id=_SUBMIT),
                className='col-12',
                style={'margin-top': '10px', 'margin-bottom': '10px'},
            ),
        ],
        className='row g-3',
    )


def _parametrization_component(am_id: str) -> Component:
    parametrization = load_parametrization(am_id)
    if not parametrization:
        content = html.Div('Paramétrage non défini pour cet arrêté.')
    else:
        content = _parametrization_form(parametrization)
    return html.Div([html.H2('Paramétrage'), content])


def _extract_topics(text: StructuredText) -> List[TopicName]:
    topic = ([ann.topic] if ann.topic else []) if (ann := text.annotations) else []
    children_topics = [top for sec in text.sections for top in _extract_topics(sec)]
    return topic + children_topics


def _extract_topic_count(am: ArreteMinisteriel) -> Dict[TopicName, int]:
    return Counter([topic for section in am.sections for topic in _extract_topics(section)])


def _topic_button(topic: TopicName, count: int) -> Component:
    text = f'{topic.value}  ({count})'
    return html.Button(text, className='btn btn-primary btn-sm', style={'margin': '5px'})


def _topic_buttons(topic_count: Dict[TopicName, int]) -> Component:
    return html.Div([_topic_button(topic, count) for topic, count in sorted(topic_count.items(), key=lambda x: -x[1])])


def _topic_component(am: ArreteMinisteriel) -> Component:
    topic_count = _extract_topic_count(am)
    return html.Div([html.H2('Topics'), _topic_buttons(topic_count)])


def _parametrization_and_topic(am: ArreteMinisteriel) -> Component:
    param = html.Div(_parametrization_component(am.id or ''), className='col-6')
    topic = html.Div(_topic_component(am), className='col-6')
    return html.Div([param, topic], className='row')


def _page(am: ArreteMinisteriel) -> Component:
    style = {'height': '80vh', 'overflow-y': 'auto'}
    am = detect_and_add_topics(am, TOPIC_ONTOLOGY)
    return html.Div(
        [
            _parametrization_and_topic(am),
            html.H2('AM'),
            html.Div(_am_component_with_toc(am), style=style),
            dcc.Store(data=am.id or '', id=_AM_ID),
        ]
    )


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    return load_structured_am(am_id) or load_initial_am(am_id)


def router(_: str, am_id: str) -> Component:
    if am_id not in ID_TO_AM_MD:
        return html.Div('404 - AM inexistant.')
    am = _load_am(am_id)
    if not am:
        return html.Div('404 - AM non initialisé.')
    return _page(am)


class _FormError(Exception):
    pass


def _extract_date(date_: str) -> datetime:
    return datetime.strptime(date_, '%Y-%m-%d')


def _extract_parameter_and_value(id_: str, date: Optional[str], value: Optional[str]) -> Tuple[Parameter, Any]:
    date_params = (
        ParameterEnum.DATE_AUTORISATION,
        ParameterEnum.DATE_ENREGISTREMENT,
        ParameterEnum.DATE_DECLARATION,
        ParameterEnum.DATE_INSTALLATION,
    )
    for param in date_params:
        if id_ == param.value.id:
            return (param.value, _extract_date(date) if date else None)
    if id_ == ParameterEnum.REGIME.value.id:
        return (ParameterEnum.REGIME.value, Regime(value) if value else None)
    raise NotImplementedError()


def _extract_parameter_values(
    ids: List[str], dates: List[Optional[str]], values: List[Optional[str]]
) -> Dict[Parameter, Any]:
    values_with_none = dict(
        _extract_parameter_and_value(id_, date, value) for id_, date, value in zip(ids, dates, values)
    )
    return {key: value for key, value in values_with_none.items() if value is not None}


@app.callback(
    Output(_AM, 'children'),
    Output(_FORM_OUTPUT, 'children'),
    Input(_SUBMIT, 'n_clicks'),
    State(_store(ALL), 'data'),
    State(_input(ALL), 'date'),
    State(_input(ALL), 'value'),
    State(_AM_ID, 'data'),
)
def _apply_parameters(_, parameter_ids, parameter_dates, parameter_values, am_id):
    am = _load_am(am_id)
    if not am:
        raise PreventUpdate
    parametrization = load_parametrization(am_id)
    if not parametrization:
        raise PreventUpdate
    try:
        parameter_values = _extract_parameter_values(parameter_ids, parameter_dates, parameter_values)
        am = apply_parameter_values_to_am(am, parametrization, parameter_values)
    except Exception:
        return html.Div(), error_component(traceback.format_exc())
    return _am_component(am), html.Div()
