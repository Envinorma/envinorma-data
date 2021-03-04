import traceback
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from envinorma.back_office.app_init import app
from envinorma.back_office.components import error_component, success_component
from envinorma.back_office.components.am_component import am_component
from envinorma.back_office.fetch_data import load_initial_am, load_parametrization, load_structured_am, remove_parameter
from envinorma.back_office.pages.parametrization_edition.form_handling import (
    FormHandlingError,
    extract_and_upsert_new_parameter,
    extract_selected_section_nb_alineas,
)
from envinorma.back_office.pages.parametrization_edition import page_ids
from envinorma.back_office.routing import build_am_page
from envinorma.back_office.utils import (
    ID_TO_AM_MD,
    AMOperation,
    RouteParsingError,
    get_section,
    get_truncated_str,
    safe_get_section,
    safe_get_subsection,
)
from envinorma.data import (
    ArreteMinisteriel,
    Ints,
    Regime,
    StructuredText,
    am_to_text,
    dump_path,
    ensure_rubrique,
    load_path,
)
from envinorma.parametrization import (
    AlternativeSection,
    NonApplicationCondition,
    ParameterObject,
    Parametrization,
    ParametrizationError,
)
from envinorma.parametrization.conditions import (
    AndCondition,
    Condition,
    Equal,
    Greater,
    Littler,
    MonoCondition,
    OrCondition,
    ParameterEnum,
    ParameterType,
    Range,
    ensure_mono_conditions,
)

_Options = List[Dict[str, Any]]


_CONDITION_VARIABLES = page_ids.CONDITION_VARIABLES
_CONDITION_VARIABLE_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_VARIABLES]
_CONDITION_OPERATIONS = ['<', '=', '>=']
_CONDITION_OPERATION_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_OPERATIONS]


def _get_str_operation(condition: MonoCondition) -> str:
    if isinstance(condition, Equal):
        return '='
    if isinstance(condition, Greater):
        return '>' if condition.strict else '>='
    if isinstance(condition, Littler):
        return '<' if condition.strict else '<='
    raise NotImplementedError(f'Unknown type {type(condition)}')


def _get_str_variable(condition: MonoCondition) -> str:
    for variable_name, variable in _CONDITION_VARIABLES.items():
        if variable.value == condition.parameter:
            return variable_name
    return ''


def _date_to_dmy(date_: Union[date, datetime]) -> str:
    return date_.strftime('%d/%m/%Y')


def _ensure_date(value: Any) -> Union[date, datetime]:
    if isinstance(value, (date, datetime)):
        return value
    raise ValueError(f'Expected type (date, datetime), received type {type(value)}')


def _ensure_regime(value: Any) -> Regime:
    if isinstance(value, Regime):
        return value
    raise ValueError(f'Expected type Regime, received type {type(value)}')


def _ensure_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise ValueError(f'Expected type str, received type {type(value)}')


def _ensure_float(candidate: str) -> float:
    try:
        return float(candidate)
    except ValueError:
        raise ValueError(f'Expected type float, received {candidate} of type {type(candidate)}.')


def _get_str_target(value: Any, parameter_type: ParameterType) -> str:
    if value is None:
        return ''
    if parameter_type == parameter_type.DATE:
        return _date_to_dmy(_ensure_date(value))
    if parameter_type == parameter_type.REGIME:
        return _ensure_regime(value).value
    if parameter_type == parameter_type.REAL_NUMBER:
        return str(_ensure_float(value))
    if parameter_type == parameter_type.RUBRIQUE:
        return ensure_rubrique(value)
    if parameter_type == parameter_type.STRING:
        return _ensure_str(value)
    raise ValueError(f'Unhandled parameter type: {parameter_type.value}')


def _get_condition_component(rank: int, default_condition: Optional[MonoCondition] = None) -> Component:
    default_variable = page_ids.INSTALLATION_DATE_FR if not default_condition else _get_str_variable(default_condition)
    default_operation = '=' if not default_condition else _get_str_operation(default_condition)
    default_target = (
        '' if not default_condition else _get_str_target(default_condition.target, default_condition.parameter.type)
    )
    dropdown_conditions = [
        dcc.Dropdown(
            id=f'{page_ids.CONDITION_VARIABLE}_{rank}',
            options=_CONDITION_VARIABLE_OPTIONS,
            clearable=False,
            value=default_variable,
            style={'width': '195px', 'margin-right': '5px'},
            optionHeight=50,
        ),
        dcc.Dropdown(
            id=f'{page_ids.CONDITION_OPERATION}_{rank}',
            options=_CONDITION_OPERATION_OPTIONS,
            clearable=False,
            value=default_operation,
            style={'width': '45px', 'margin-right': '5px'},
        ),
        dcc.Input(
            id=f'{page_ids.CONDITION_VALUE}_{rank}',
            value=str(default_target),
            type='text',
            className='form-control form-control-sm',
        ),
    ]
    return html.Div(dropdown_conditions, className='small-dropdown', style={'display': 'flex', 'margin-bottom': '5px'})


def _get_condition_components(
    nb_components: int, default_conditions: Optional[List[MonoCondition]] = None
) -> Component:
    if default_conditions:
        dropdown_conditions = [_get_condition_component(i, cd) for i, cd in enumerate(default_conditions)]
    else:
        dropdown_conditions = [_get_condition_component(i) for i in range(nb_components)]
    return html.Div(dropdown_conditions)


def _get_main_title(operation: AMOperation, is_edition: bool, rank: int) -> Component:
    if is_edition:
        return (
            html.H4(f'Condition de non-application n°{rank}')
            if operation == operation.ADD_CONDITION
            else html.H4(f'Paragraphe alternatif n°{rank}')
        )
    return (
        html.H4('Nouvelle condition de non-application')
        if operation == operation.ADD_CONDITION
        else html.H4('Nouveau paragraphe alternatif')
    )


def _is_condition(operation: AMOperation) -> bool:
    return operation == operation.ADD_CONDITION


def _extract_title_and_content(text: StructuredText, level: int = 0) -> Tuple[str, str]:
    title = text.title.text
    contents: List[str] = []
    for alinea in text.outer_alineas:
        contents.append(alinea.text)
    for section in text.sections:
        section_title, section_content = _extract_title_and_content(section, level + 1)
        contents.append('#' * (level + 1) + ' ' + section_title)
        contents.append(section_content)
    return title, '\n'.join(contents)


def _get_new_section_form(default_title: str, default_content: str) -> Component:
    return html.Div(
        [
            html.H5('Nouvelle version'),
            html.Div(dcc.Input(id=page_ids.NEW_TEXT_TITLE, value=default_title), hidden=True),
            html.Label('Contenu du paragraphe', htmlFor=page_ids.NEW_TEXT_CONTENT, className='form-label'),
            html.Div(
                dcc.Textarea(
                    id=page_ids.NEW_TEXT_CONTENT,
                    className='form-control',
                    value=default_content,
                    style={'min-height': '300px'},
                )
            ),
        ],
        id=page_ids.NEW_TEXT,
    )


def _get_new_section_form_from_default(loaded_parameter: Optional[ParameterObject]) -> Component:
    parameter = _ensure_optional_alternative_section(loaded_parameter)
    if parameter:
        default_title, default_content = _extract_title_and_content(parameter.new_text)
    else:
        default_title, default_content = '', ''

    return _get_new_section_form(default_title, default_content)


def _go_back_button(parent_page: str) -> Component:
    return dcc.Link(html.Button('Retour', className='btn btn-link center'), href=parent_page)


def _buttons(parent_page: str) -> Component:
    return html.Div(
        [
            html.Button(
                'Enregistrer',
                id='submit-val-param-edition',
                className='btn btn-primary',
                style={'margin-right': '5px'},
                n_clicks=0,
            ),
            _go_back_button(parent_page),
        ],
        style={'margin-top': '10px', 'margin-bottom': '100px'},
    )


_NB_CONDITIONS_OPTIONS = [{'label': i, 'value': i} for i in range(10)]
_AND_ID = 'and'
_OR_ID = 'or'
_MERGE_VALUES_OPTIONS = [{'value': _AND_ID, 'label': 'ET'}, {'value': _OR_ID, 'label': 'OU'}]


def _get_condition_tooltip() -> Component:
    return html.Div(
        [
            'Liste de conditions ',
            dbc.Badge('?', id='param-edition-conditions-tooltip', pill=True),
            dbc.Tooltip(
                ['Formats:', html.Br(), 'Régime: A, E, D ou NC.', html.Br(), 'Date: JJ/MM/AAAA'],
                target='param-edition-conditions-tooltip',
            ),
        ]
    )


def _make_mono_conditions(condition: Condition) -> List[MonoCondition]:
    if isinstance(condition, (Equal, Greater, Littler)):
        return [condition]
    if isinstance(condition, Range):
        return [
            Littler(condition.parameter, condition.right, condition.right_strict),
            Greater(condition.parameter, condition.left, condition.left_strict),
        ]
    raise ValueError(f'Unexpected condition type {type(condition)}')


def _change_to_mono_conditions(condition: Condition) -> Tuple[str, List[MonoCondition]]:
    if isinstance(condition, (Equal, Greater, Littler, Range)):
        return _AND_ID, _make_mono_conditions(condition)
    if isinstance(condition, AndCondition):
        children_mono_conditions = [cd for child in condition.conditions for cd in _make_mono_conditions(child)]
        return _AND_ID, children_mono_conditions
    if isinstance(condition, (AndCondition, OrCondition)):
        return _OR_ID, ensure_mono_conditions(condition.conditions)
    raise NotImplementedError(f'Unhandled condition {type(condition)}')


def _get_condition_form(default_condition: Optional[Condition]) -> Component:
    default_conditions: List[MonoCondition] = []
    if default_condition:
        default_merge, default_conditions = _change_to_mono_conditions(default_condition)
    else:
        default_merge = _AND_ID
        default_conditions = [Littler(ParameterEnum.DATE_INSTALLATION.value, None)]
    dropdown_condition_merge = html.Div(
        [
            'Opération',
            dcc.Dropdown(
                options=_MERGE_VALUES_OPTIONS, clearable=False, value=default_merge, id=page_ids.CONDITION_MERGE
            ),
        ]
    )
    dropdown_nb_conditions = html.Div(
        [
            'Nombre de conditions',
            dcc.Dropdown(
                page_ids.NB_CONDITIONS, options=_NB_CONDITIONS_OPTIONS, clearable=False, value=len(default_conditions)
            ),
        ]
    )
    tooltip = _get_condition_tooltip()
    conditions = html.Div(
        id='parametrization-conditions', children=_get_condition_components(len(default_conditions), default_conditions)
    )

    return html.Div([html.H5('Condition'), dropdown_condition_merge, dropdown_nb_conditions, tooltip, conditions])


def _get_source_form(options: _Options, loaded_parameter: Optional[ParameterObject]) -> Component:
    if loaded_parameter:
        default_value = dump_path(loaded_parameter.source.reference.section.path)
    else:
        default_value = ''
    dropdown_source = dcc.Dropdown(
        value=default_value, options=options, id=page_ids.SOURCE, style={'font-size': '0.8em'}
    )
    return html.Div([html.H5('Source'), dropdown_source])


def _get_target_entity(parameter: ParameterObject) -> Ints:
    if isinstance(parameter, NonApplicationCondition):
        return parameter.targeted_entity.section.path
    if isinstance(parameter, AlternativeSection):
        return parameter.targeted_section.path
    raise NotImplementedError(f'{type(parameter)}')


def _get_target_section_form(options: _Options, loaded_parameter: Optional[ParameterObject]) -> Component:
    default_value = dump_path(_get_target_entity(loaded_parameter)) if loaded_parameter else None
    dropdown_target = html.Div(
        [dcc.Dropdown(options=options, id=page_ids.TARGET_SECTION, value=default_value, style={'font-size': '0.8em'})]
    )
    return html.Div([html.H6('Titre'), dropdown_target])


def _ensure_optional_condition(parameter: Optional[ParameterObject]) -> Optional[NonApplicationCondition]:
    if not parameter:
        return None
    if not isinstance(parameter, NonApplicationCondition):
        raise ValueError(f'Expection NonApplicationCondition, not {type(parameter)}')
    return parameter


def _ensure_optional_alternative_section(parameter: Optional[ParameterObject]) -> Optional[AlternativeSection]:
    if not parameter:
        return None
    if not isinstance(parameter, AlternativeSection):
        raise ValueError(f'Expection AlternativeSection, not {type(parameter)}')
    return parameter


def _get_target_alineas_form(
    operation: AMOperation, loaded_parameter: Optional[ParameterObject], text: StructuredText
) -> Component:
    title = html.H6('Alineas visés')
    if not _is_condition(operation):
        return html.Div(
            [
                title,
                dcc.Checklist(options=[], id=page_ids.TARGET_ALINEAS),
                dcc.Store(data=0, id=page_ids.LOADED_NB_ALINEAS),
            ],
            hidden=True,
        )
    condition = _ensure_optional_condition(loaded_parameter)

    if not condition:
        value = []
        options = []
    else:
        path = condition.targeted_entity.section.path
        alineas = condition.targeted_entity.outer_alinea_indices
        target_section_alineas = section.outer_alineas if (section := safe_get_subsection(path, text)) else []
        if target_section_alineas:
            options = [{'label': al.text, 'value': i} for i, al in enumerate(target_section_alineas)]
            value = alineas if alineas else list(range(len(target_section_alineas)))
        else:
            options = []
            value = []
    return html.Div(
        [
            title,
            dcc.Checklist(options=options, value=value, id=page_ids.TARGET_ALINEAS),
            dcc.Store(data=len(options), id=page_ids.LOADED_NB_ALINEAS),
        ]
    )


def _get_target_section_block(
    operation: AMOperation,
    text_title_options: _Options,
    loaded_parameter: Optional[ParameterObject],
    text: StructuredText,
) -> Component:
    return html.Div(
        [
            html.H5('Paragraphe visé'),
            _get_target_section_form(text_title_options, loaded_parameter),
            _get_target_alineas_form(operation, loaded_parameter, text),
        ]
    )


def _get_delete_button(is_edition: bool) -> Component:
    return html.Button(
        'Supprimer',
        id='param-edition-delete-button',
        className='btn btn-danger',
        style={'margin-right': '5px'},
        n_clicks=0,
        hidden=not is_edition,
    )


def _make_form(
    text_title_options: _Options,
    operation: AMOperation,
    parent_page: str,
    loaded_parameter: Optional[ParameterObject],
    destination_rank: int,
    text: StructuredText,
) -> Component:
    return html.Div(
        [
            _get_main_title(operation, is_edition=destination_rank != -1, rank=destination_rank),
            _get_delete_button(is_edition=destination_rank != -1),
            _get_source_form(text_title_options, loaded_parameter),
            _get_target_section_block(operation, text_title_options, loaded_parameter, text),
            _get_new_section_form_from_default(loaded_parameter) if not _is_condition(operation) else html.Div(),
            _get_condition_form(loaded_parameter.condition if loaded_parameter else None),
            html.Div(id='param-edition-upsert-output'),
            html.Div(id='param-edition-delete-output'),
            _buttons(parent_page),
        ]
    )


def _extract_reference_and_values_titles(text: StructuredText, path: Ints, level: int = 0) -> List[Tuple[str, str]]:
    return [(dump_path(path), get_truncated_str('#' * level + ' ' + text.title.text))] + [
        elt
        for rank, sec in enumerate(text.sections)
        for elt in _extract_reference_and_values_titles(sec, path + (rank,), level + 1)
    ]


def _extract_paragraph_reference_dropdown_values(text: StructuredText) -> _Options:
    title_references_and_values = _extract_reference_and_values_titles(text, ())
    return [{'label': title, 'value': reference} for reference, title in title_references_and_values]


def _get_instructions() -> Component:
    return html.Div(
        html.A(
            'Guide de paramétrage',
            href='https://www.notion.so/R-gles-de-param-trisation-47d8e5c4d3434d8691cbd9f59d556f0f',
            target='_blank',
        ),
        className='alert alert-light',
    )


def _structure_edition_component(
    text: StructuredText,
    operation: AMOperation,
    parent_page: str,
    loaded_parameter: Optional[ParameterObject],
    destination_rank: int,
) -> Component:
    dropdown_values = _extract_paragraph_reference_dropdown_values(text)
    return html.Div(
        [
            _get_instructions(),
            _make_form(dropdown_values, operation, parent_page, loaded_parameter, destination_rank, text),
        ]
    )


_EMPHASIZED_WORDS = [
    'déclaration',
    'enregistrement',
    'autorisation',
    'application',
    'alinéa',
    'installations existantes',
    'appliquent',
    'applicables',
    'applicable',
]


def _get_main_component(
    am: ArreteMinisteriel,
    operation: AMOperation,
    am_page: str,
    destination_rank: int,
    loaded_parameter: Optional[ParameterObject],
) -> Component:
    text = am_to_text(am)
    border_style = {'padding': '10px', 'border': '1px solid rgba(0,0,0,.1)', 'border-radius': '5px'}
    am_component_ = am_component(am, emphasized_words=_EMPHASIZED_WORDS, first_level=3)
    cols = [
        html.Div(
            _structure_edition_component(text, operation, am_page, loaded_parameter, destination_rank),
            className='col-4',
        ),
        html.Div(
            am_component_,
            className='col-8',
            style={'overflow-y': 'auto', 'position': 'sticky', 'height': '90vh', **border_style},
        ),
    ]
    return html.Div(cols, className='row')


def _build_page(
    am: ArreteMinisteriel,
    operation: AMOperation,
    am_page: str,
    am_id: str,
    destination_rank: int,
    loaded_parameter: Optional[ParameterObject],
) -> Component:
    hidden_components = [
        html.P(am_id, hidden=True, id=page_ids.AM_ID),
        html.P(operation.value, hidden=True, id=page_ids.AM_OPERATION),
        html.P(destination_rank, hidden=True, id=page_ids.PARAMETER_RANK),
        dcc.Store(id=page_ids.TARGET_SECTION_STORE),
    ]
    page = _get_main_component(am, operation, am_page, destination_rank, loaded_parameter)

    return html.Div([page, *hidden_components], className='parametrization_content')


def _handle_submit(
    n_clicks: int,
    operation_str: str,
    am_id: str,
    parameter_rank: int,
    target_text_dict: Dict[str, Any],
    loaded_nb_alineas: int,
    state: Dict[str, Any],
) -> Component:
    if n_clicks == 0:
        return html.Div()
    try:
        operation = AMOperation(operation_str)
        target_section_nb_alineas = extract_selected_section_nb_alineas(target_text_dict, loaded_nb_alineas)
        extract_and_upsert_new_parameter(state, am_id, operation, parameter_rank, target_section_nb_alineas)
    except FormHandlingError as exc:
        return error_component(f'Erreur dans le formulaire:\n{exc}')
    except ParametrizationError as exc:
        return error_component(
            f'Erreur: la section visée est déjà visée par au moins une autre condition.'
            f' Celle-ci est incompatible avec celle(s) déjà définie(s) :\n{exc}'
        )
    except Exception:  # pylint: disable=broad-except
        return error_component(f'Unexpected error:\n{traceback.format_exc()}')
    return html.Div(
        [
            success_component(f'Enregistrement réussi.'),
            dcc.Location(pathname=build_am_page(am_id), id='param-edition-success-redirect'),
        ]
    )


def _handle_delete(n_clicks: int, operation_str: str, am_id: str, parameter_rank: int) -> Component:
    if n_clicks == 0:
        return html.Div()
    try:
        operation = AMOperation(operation_str)
        remove_parameter(am_id, operation, parameter_rank)
    except Exception:  # pylint: disable=broad-except
        return error_component(f'Unexpected error:\n{traceback.format_exc()}')
    return html.Div(
        [
            success_component(f'Suppression réussie.'),
            dcc.Location(pathname=build_am_page(am_id), id='param-edition-success-redirect'),
        ]
    )


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    return load_structured_am(am_id) or load_initial_am(am_id)


def _build_new_text_component(str_path: Optional[str], am_id: str, operation_str: str) -> Component:
    if operation_str != AMOperation.ADD_ALTERNATIVE_SECTION.value or not str_path:
        return _get_new_section_form('', '')
    am = _load_am(am_id)
    if not am:
        return _get_new_section_form('', '')
    path = load_path(str_path)
    section = safe_get_section(path, am)
    if not section:
        return _get_new_section_form('', '')
    title, content = _extract_title_and_content(section)
    return _get_new_section_form(title, content)


def _build_targeted_alinea_options(section_dict: Dict[str, Any], operation_str: str) -> List[Dict[str, Any]]:
    if operation_str != AMOperation.ADD_CONDITION.value or not section_dict:
        return []
    section = StructuredText.from_dict(section_dict)
    alineas_str = [al.text for al in section.outer_alineas]
    return [{'label': al, 'value': i} for i, al in enumerate(alineas_str)]


def _store_target_section(str_path: Optional[str], am_id: str) -> Dict[str, Any]:
    if not str_path:
        return {}
    am = _load_am(am_id)
    if not am:
        return {}
    path = load_path(str_path)
    section = get_section(path, am)
    return section.to_dict()


def _build_targeted_alinea_value(section_dict: Dict[str, Any], operation_str: str) -> List[int]:
    if operation_str != AMOperation.ADD_CONDITION.value or not section_dict:
        return []
    section = StructuredText.from_dict(section_dict)
    return list(range(len(section.outer_alineas)))


@app.callback(
    Output(page_ids.NEW_TEXT, 'children'),
    Input(page_ids.TARGET_SECTION, 'value'),
    State(page_ids.AM_ID, 'children'),
    State(page_ids.AM_OPERATION, 'children'),
    prevent_initial_call=True,
)
def _(path, am_id, operation):
    return _build_new_text_component(path, am_id, operation)


@app.callback(
    Output(page_ids.TARGET_SECTION_STORE, 'data'),
    Input(page_ids.TARGET_SECTION, 'value'),
    State(page_ids.AM_ID, 'children'),
    prevent_initial_call=True,
)
def __store_target_section(path, am_id):
    return _store_target_section(path, am_id)


@app.callback(
    Output(page_ids.TARGET_ALINEAS, 'options'),
    Input(page_ids.TARGET_SECTION_STORE, 'data'),
    State(page_ids.AM_OPERATION, 'children'),
    prevent_initial_call=True,
)
def __build_targeted_alinea_options(target_section, operation):
    return _build_targeted_alinea_options(target_section, operation)


@app.callback(
    Output(page_ids.TARGET_ALINEAS, 'value'),
    Input(page_ids.TARGET_SECTION_STORE, 'data'),
    State(page_ids.AM_OPERATION, 'children'),
    prevent_initial_call=True,
)
def __build_targeted_alinea_value(target_section, operation):
    return _build_targeted_alinea_value(target_section, operation)


@app.callback(
    Output('param-edition-upsert-output', 'children'),
    Input('submit-val-param-edition', 'n_clicks'),
    State(page_ids.AM_OPERATION, 'children'),
    State(page_ids.AM_ID, 'children'),
    State(page_ids.PARAMETER_RANK, 'children'),
    State(page_ids.TARGET_SECTION_STORE, 'data'),
    State(page_ids.LOADED_NB_ALINEAS, 'data'),
    State('page-content', 'children'),
)
def __(n_clicks, operation, am_id, parameter_rank, target_text_dict, loaded_nb_alineas, state):
    return _handle_submit(n_clicks, operation, am_id, parameter_rank, target_text_dict, loaded_nb_alineas, state)


@app.callback(
    Output('param-edition-delete-output', 'children'),
    Input('param-edition-delete-button', 'n_clicks'),
    State(page_ids.AM_OPERATION, 'children'),
    State(page_ids.AM_ID, 'children'),
    State(page_ids.PARAMETER_RANK, 'children'),
)
def ___(n_clicks, operation, am_id, parameter_rank):
    return _handle_delete(n_clicks, operation, am_id, parameter_rank)


@app.callback(
    Output('parametrization-conditions', 'children'),
    [Input(page_ids.NB_CONDITIONS, 'value')],
    prevent_initial_call=True,
)
def nb_conditions(value):
    return _get_condition_components(value)


def _parse_route(route: str) -> Tuple[str, AMOperation, Optional[int], bool]:
    pieces = route.split('/')[1:]
    if len(pieces) <= 1:
        raise RouteParsingError(f'Error parsing route {route}')
    am_id = pieces[0]
    try:
        operation = AMOperation(pieces[1])
    except ValueError:
        raise RouteParsingError(f'Error parsing route {route}')
    if len(pieces) == 2:
        return am_id, operation, None, False
    try:
        parameter_rank = int(pieces[2])
    except ValueError:
        raise RouteParsingError(f'Error parsing route {route}')
    if len(pieces) == 3:
        return am_id, operation, parameter_rank, False
    if pieces[3] != 'copy':
        raise RouteParsingError(f'Error parsing route {route}')
    return am_id, operation, parameter_rank, True


def _get_parameter(parametrization: Parametrization, operation_id: AMOperation, parameter_rank: int) -> ParameterObject:
    parameters: Union[List[AlternativeSection], List[NonApplicationCondition]]
    if operation_id == operation_id.ADD_ALTERNATIVE_SECTION:
        parameters = parametrization.alternative_sections
    elif operation_id == operation_id.ADD_CONDITION:
        parameters = parametrization.application_conditions
    else:
        raise NotImplementedError(f'{operation_id.value}')
    if parameter_rank >= len(parameters):
        raise RouteParsingError(f'Parameter with rank {parameter_rank} not found.')
    return parameters[parameter_rank]


def router(pathname: str) -> Component:
    try:
        am_id, operation_id, parameter_rank, copy = _parse_route(pathname)
        if am_id not in ID_TO_AM_MD:
            return html.P('404 - Arrêté inconnu')
        am_page = build_am_page(am_id)
        am_metadata = ID_TO_AM_MD.get(am_id)
        am = _load_am(am_id)
        parametrization = load_parametrization(am_id) or Parametrization([], [])
        loaded_parameter = (
            _get_parameter(parametrization, operation_id, parameter_rank) if parameter_rank is not None else None
        )
    except RouteParsingError as exc:
        return html.P(f'404 - Page introuvable - {str(exc)}')
    if not am or not parametrization or not am_metadata:
        return html.P(f'404 - Arrêté {am_id} introuvable.')
    if parameter_rank is not None and not copy:
        destination_parameter_rank = parameter_rank
    else:
        destination_parameter_rank = -1
    return _build_page(am, operation_id, am_page, am_id, destination_parameter_rank, loaded_parameter)
