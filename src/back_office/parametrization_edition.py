import json
import traceback
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from lib.condition_to_str import extract_parameters_from_condition
from lib.data import ArreteMinisteriel, EnrichedString, Ints, Regime, StructuredText, am_to_text
from lib.parametrization import (
    AlternativeSection,
    AndCondition,
    Condition,
    ConditionSource,
    EntityReference,
    Equal,
    Greater,
    Littler,
    NonApplicationCondition,
    OrCondition,
    Parameter,
    ParameterEnum,
    ParameterObject,
    ParameterType,
    Parametrization,
    Range,
    SectionReference,
)

from back_office.app_init import app
from back_office.components import error_component, success_component
from back_office.components.am_component import am_component
from back_office.fetch_data import (
    load_initial_am,
    load_parametrization,
    load_structured_am,
    remove_parameter,
    upsert_parameter,
)
from back_office.routing import build_am_page
from back_office.utils import (
    ID_TO_AM_MD,
    AMOperation,
    RouteParsingError,
    assert_int,
    assert_list,
    assert_str,
    get_section,
    get_truncated_str,
    safe_get_section,
    safe_get_subsection,
)

_Options = List[Dict[str, Any]]

_AUTORISATION_DATE_FR = 'Date d\'autorisation'
_INSTALLATION_DATE_FR = 'Date de mise en service'
_CONDITION_VARIABLES = {
    'Régime': ParameterEnum.REGIME,
    _AUTORISATION_DATE_FR: ParameterEnum.DATE_AUTORISATION,
    _INSTALLATION_DATE_FR: ParameterEnum.DATE_INSTALLATION,
}
_CONDITION_VARIABLE_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_VARIABLES]
_CONDITION_OPERATIONS = ['<', '=', '>=']
_CONDITION_OPERATION_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_OPERATIONS]

_CONDITION_VARIABLE = 'param-edition-condition-parameter'
_CONDITION_OPERATION = 'param-edition-condition-operation'
_CONDITION_VALUE = 'param-edition-condition-value'
_SOURCE = 'param-edition-source'
_TARGET_SECTION = 'param-edition-target-section'
_TARGET_SECTION_STORE = 'param-edition-target-section-store'
_TARGET_ALINEAS = 'param-edition-target-alineas'
_LOADED_NB_ALINEAS = 'param-edition-loaded-nb-alineas'
_CONDITION_MERGE = 'param-edition-condition-merge'
_NB_CONDITIONS = 'param-edition-nb-conditions'
_NEW_TEXT = 'param-edition-new-text'
_NEW_TEXT_TITLE = 'param-edition-new-text-title'
_NEW_TEXT_CONTENT = 'param-edition-new-text-content'
_AM_ID = 'param-edition-am-id'
_PARAMETER_RANK = 'param-edition-param-rank'
_AM_OPERATION = 'param-edition-am-operation'

_MonoCondition = Union[Equal, Greater, Littler]


def _get_str_operation(condition: _MonoCondition) -> str:
    if isinstance(condition, Equal):
        return '='
    if isinstance(condition, Greater):
        return '>' if condition.strict else '>='
    if isinstance(condition, Littler):
        return '<' if condition.strict else '<='
    raise NotImplementedError(f'Unknown type {type(condition)}')


def _get_str_variable(condition: _MonoCondition) -> str:
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


def _ensure_regime(
    value: Any,
) -> Regime:
    if isinstance(value, Regime):
        return value
    raise ValueError(f'Expected type Regime, received type {type(value)}')


def _get_str_target(value: Any, parameter_type: ParameterType) -> str:
    if value is None:
        return ''
    if parameter_type == parameter_type.DATE:
        return _date_to_dmy(_ensure_date(value))
    if parameter_type == parameter_type.REGIME:
        return _ensure_regime(value).value
    raise ValueError(f'Unhandled parameter type: {parameter_type.value}')


def _get_condition_component(rank: int, default_condition: Optional[_MonoCondition] = None) -> Component:
    default_variable = _INSTALLATION_DATE_FR if not default_condition else _get_str_variable(default_condition)
    default_operation = '=' if not default_condition else _get_str_operation(default_condition)
    default_target = (
        '' if not default_condition else _get_str_target(default_condition.target, default_condition.parameter.type)
    )
    dropdown_conditions = [
        dcc.Dropdown(
            id=f'{_CONDITION_VARIABLE}_{rank}',
            options=_CONDITION_VARIABLE_OPTIONS,
            clearable=False,
            value=default_variable,
            style={'width': '200px'},
        ),
        dcc.Dropdown(
            id=f'{_CONDITION_OPERATION}_{rank}',
            options=_CONDITION_OPERATION_OPTIONS,
            clearable=False,
            value=default_operation,
            style=dict(width='50px'),
        ),
        dcc.Input(
            id=f'{_CONDITION_VALUE}_{rank}',
            value=default_target,
            type='text',
            style={'height': '36px'},
            className='form-control',
        ),
    ]
    return html.Div(dropdown_conditions, style=dict(display='flex'))


def _get_condition_components(
    nb_components: int, default_conditions: Optional[List[_MonoCondition]] = None
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
            html.Div(dcc.Input(id=_NEW_TEXT_TITLE, value=default_title), hidden=True),
            html.Label('Contenu du paragraphe', htmlFor=_NEW_TEXT_CONTENT, className='form-label'),
            html.Div(
                dcc.Textarea(
                    id=_NEW_TEXT_CONTENT, className='form-control', value=default_content, style={'min-height': '300px'}
                )
            ),
        ],
        id=_NEW_TEXT,
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


def _ensure_mono_condition(condition: Condition) -> _MonoCondition:
    if isinstance(condition, (Equal, Greater, Littler)):
        return condition
    raise ValueError(f'Unexpected condition type {type(condition)}')


def _ensure_mono_conditions(conditions: List[Condition]) -> List[_MonoCondition]:
    return [_ensure_mono_condition(x) for x in conditions]


def _change_to_mono_conditions(condition: Condition) -> Tuple[str, List[_MonoCondition]]:
    if isinstance(condition, (Equal, Greater, Littler)):
        return _AND_ID, [condition]
    if isinstance(condition, Range):
        conditions = [
            Littler(condition.parameter, condition.right, condition.right_strict),
            Greater(condition.parameter, condition.left, condition.left_strict),
        ]
        return _AND_ID, conditions
    if isinstance(condition, (AndCondition, OrCondition)):
        mono_conditions = _ensure_mono_conditions(condition.conditions)
        merge = _AND_ID if isinstance(condition, AndCondition) else _OR_ID
        return merge, mono_conditions
    raise NotImplementedError(f'Unhandled condition {type(condition)}')


def _get_condition_form(default_condition: Optional[Condition]) -> Component:
    default_conditions: List[_MonoCondition] = []
    if default_condition:
        default_merge, default_conditions = _change_to_mono_conditions(default_condition)
    else:
        default_merge = _AND_ID
        default_conditions = [Littler(ParameterEnum.DATE_INSTALLATION.value, None)]
    dropdown_condition_merge = html.Div(
        [
            'Opération',
            dcc.Dropdown(options=_MERGE_VALUES_OPTIONS, clearable=False, value=default_merge, id=_CONDITION_MERGE),
        ]
    )
    dropdown_nb_conditions = html.Div(
        [
            'Nombre de conditions',
            dcc.Dropdown(
                _NB_CONDITIONS, options=_NB_CONDITIONS_OPTIONS, clearable=False, value=len(default_conditions)
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
        default_value = _dump_path(loaded_parameter.source.reference.section.path)
    else:
        default_value = ''
    dropdown_source = dcc.Dropdown(value=default_value, options=options, id=_SOURCE, style={'font-size': '0.8em'})
    return html.Div([html.H5('Source'), dropdown_source])


def _get_target_entity(parameter: ParameterObject) -> Ints:
    if isinstance(parameter, NonApplicationCondition):
        return parameter.targeted_entity.section.path
    if isinstance(parameter, AlternativeSection):
        return parameter.targeted_section.path
    raise NotImplementedError(f'{type(parameter)}')


def _get_target_section_form(options: _Options, loaded_parameter: Optional[ParameterObject]) -> Component:
    default_value = _dump_path(_get_target_entity(loaded_parameter)) if loaded_parameter else None
    dropdown_target = html.Div(
        [dcc.Dropdown(options=options, id=_TARGET_SECTION, value=default_value, style={'font-size': '0.8em'})]
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
            [title, dcc.Checklist(options=[], id=_TARGET_ALINEAS), dcc.Store(data=0, id=_LOADED_NB_ALINEAS)],
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
            dcc.Checklist(options=options, value=value, id=_TARGET_ALINEAS),
            dcc.Store(data=len(options), id=_LOADED_NB_ALINEAS),
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
    return [(_dump_path(path), get_truncated_str('#' * level + ' ' + text.title.text))] + [
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
        html.P(am_id, hidden=True, id=_AM_ID),
        html.P(operation.value, hidden=True, id=_AM_OPERATION),
        html.P(destination_rank, hidden=True, id=_PARAMETER_RANK),
        dcc.Store(id=_TARGET_SECTION_STORE),
    ]
    page = _get_main_component(am, operation, am_page, destination_rank, loaded_parameter)

    return html.Div([page, *hidden_components], className='parametrization_content')


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


def _remove_str(elements: List[Union[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    return [el for el in elements if not isinstance(el, str)]


def _extract_non_str_children(page_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    child_or_children = page_state.get('props', {}).get('children')
    if not child_or_children:
        return []
    if isinstance(child_or_children, dict):
        return [child_or_children]
    if isinstance(child_or_children, list):
        return _remove_str(child_or_children)
    return []


def _extract_components_with_id(page_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    children = _extract_non_str_children(page_state)
    shallow = [child for child in children if child.get('props', {}).get('id')]
    return shallow + [dc for child in children for dc in _extract_components_with_id(child)]


def _extract_id_to_value(page_state: Dict[str, Any]) -> Dict[str, Any]:
    children = _extract_components_with_id(page_state)
    return {child['props']['id']: child['props'].get('value') for child in children}


def _get_with_error(dict_: Dict[str, Any], key: str) -> Any:
    if key not in dict_:
        raise ValueError(f'Expecting key {key} in dict_. Existing keys: {list(dict_.keys())}')
    return dict_[key]


def _extract_conditions(nb_conditions: int, id_to_value: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    return [
        (
            assert_str(_get_with_error(id_to_value, f'{_CONDITION_VARIABLE}_{i}')),
            assert_str(_get_with_error(id_to_value, f'{_CONDITION_OPERATION}_{i}')),
            assert_str(_get_with_error(id_to_value, f'{_CONDITION_VALUE}_{i}')),
        )
        for i in range(nb_conditions)
    ]


class _FormHandlingError(Exception):
    pass


def _build_source(source_str: str) -> ConditionSource:
    return ConditionSource('', EntityReference(SectionReference(_load_path(source_str)), None))


def _extract_alinea_indices(target_alineas: Optional[List[int]]) -> Optional[List[int]]:
    if target_alineas is None:
        return None
    assert_list(target_alineas)
    return [assert_int(x) for x in target_alineas]


def _load_path(path_str: str) -> Ints:
    return tuple(json.loads(path_str))


def _dump_path(path: Ints) -> str:
    return json.dumps(path)


def _build_non_application_condition(
    source: str,
    target_section: str,
    merge: str,
    conditions: List[Tuple[str, str, str]],
    target_alineas: Optional[List[int]],
) -> NonApplicationCondition:
    return NonApplicationCondition(
        EntityReference(SectionReference(_load_path(target_section)), _extract_alinea_indices(target_alineas)),
        _build_condition(conditions, merge),
        _build_source(source),
        description='',
    )


def _get_condition_cls(merge: str) -> Union[Type[AndCondition], Type[OrCondition]]:
    if merge == 'and':
        return AndCondition
    if merge == 'or':
        return OrCondition
    raise _FormHandlingError('Mauvaise opération d\'aggrégation dans le formulaire. Attendu: ET ou OU.')


def _extract_parameter(parameter: str) -> Parameter:
    if parameter not in _CONDITION_VARIABLES:
        raise _FormHandlingError(f'Paramètre {parameter} inconnu, attendus: {list(_CONDITION_VARIABLES.keys())}')
    return _CONDITION_VARIABLES[parameter].value


def _parse_dmy(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        raise _FormHandlingError(f'Date mal formattée. Format attendu JJ/MM/AAAA. Reçu: "{date_str}"')


def _parse_regime(regime_str: str) -> Regime:
    try:
        return Regime(regime_str)
    except ValueError:
        raise _FormHandlingError(f'Mauvais régime. Attendu: {[x.value for x in Regime]}. Reçu: "{regime_str}"')


def _build_parameter_value(parameter_type: ParameterType, value_str: str) -> Any:
    if parameter_type == parameter_type.DATE:
        return _parse_dmy(value_str)
    if parameter_type == parameter_type.REGIME:
        return _parse_regime(value_str)
    raise _FormHandlingError(f'Ce type de paramètre n\'est pas géré: {parameter_type.value}')


def _extract_condition(rank: int, parameter: str, operator: str, value_str: str) -> Condition:
    try:
        built_parameter = _extract_parameter(parameter)
        value = _build_parameter_value(built_parameter.type, value_str)
    except _FormHandlingError as exc:
        raise _FormHandlingError(f'Erreur dans la {rank+1}{"ère" if rank == 0 else "ème"} condition: {exc}')
    if operator == '<':
        return Littler(built_parameter, value, True)
    if operator == '<=':
        return Littler(built_parameter, value, False)
    if operator == '>':
        return Greater(built_parameter, value, True)
    if operator == '>=':
        return Greater(built_parameter, value, False)
    if operator == '=':
        return Equal(built_parameter, value)
    raise _FormHandlingError(f'La {rank+1}{"ère" if rank == 0 else "ème"} condition contient un opérateur inattendu.')


def _assert_mono_condition(condition: Condition) -> _MonoCondition:
    if not isinstance(condition, (Equal, Greater, Littler)):
        raise ValueError(f'Expecting type _MonoCondition, got {type(condition)}')
    return condition


def _assert_greater_condition(condition: Condition) -> Greater:
    if not isinstance(condition, Greater):
        raise ValueError(f'Expecting type Greater, got {type(condition)}')
    return condition


def _assert_littler_condition(condition: Condition) -> Littler:
    if not isinstance(condition, Littler):
        raise ValueError(f'Expecting type Greater, got {type(condition)}')
    return condition


def _assert_strictly_below(small_candidate: Any, great_candidate: Any) -> None:
    if isinstance(small_candidate, (datetime, date, float, int)):
        if small_candidate >= great_candidate:
            raise _FormHandlingError('Erreur dans les conditions: les deux conditions sont incompatibles.')


def _check_compatibility_and_build_range(
    parameter: Parameter, condition_1: _MonoCondition, condition_2: _MonoCondition
) -> Condition:
    if isinstance(condition_1, Equal) or isinstance(condition_2, Equal):
        raise _FormHandlingError('Erreur dans les conditions. Elles sont soit redondantes, soit incompatibles.')
    if isinstance(condition_1, Littler) and isinstance(condition_2, Littler):
        raise _FormHandlingError('Erreur dans les conditions. Elles sont redondantes.')
    if isinstance(condition_1, Greater) and isinstance(condition_2, Greater):
        raise _FormHandlingError('Erreur dans les conditions. Elles sont redondantes.')
    if isinstance(condition_1, Littler):
        littler_condition = condition_1
        greater_condition = _assert_greater_condition(condition_2)
    else:
        littler_condition = _assert_littler_condition(condition_2)
        greater_condition = _assert_greater_condition(condition_1)
    littler_target = littler_condition.target
    greater_target = greater_condition.target
    _assert_strictly_below(greater_target, littler_target)
    return Range(parameter, greater_target, littler_target)


def _try_building_range_condition(conditions: List[Condition]) -> Optional[Condition]:
    _parameters = {param for cond in conditions for param in extract_parameters_from_condition(cond)}
    if len(_parameters) != 1:
        return None
    if len(conditions) != 2:
        return None
    _parameter = list(_parameters)[0]
    if _parameter == ParameterEnum.REGIME.value:
        raise _FormHandlingError('Erreur dans les conditions: elles sont soit incompatibles, soit redondantes.')
    condition_1 = _assert_mono_condition(conditions[0])
    condition_2 = _assert_mono_condition(conditions[1])
    return _check_compatibility_and_build_range(_parameter, condition_1, condition_2)


def _simplify_condition(condition: Condition) -> Condition:
    if isinstance(condition, (AndCondition, OrCondition)):
        if len(condition.conditions) == 1:
            return condition.conditions[0]
        if len(condition.conditions) == 0:
            raise _FormHandlingError('Au moins une condition est nécessaire !')
    if isinstance(condition, AndCondition):
        potential_range_condition = _try_building_range_condition(condition.conditions)
        if potential_range_condition:
            return potential_range_condition
    return condition


def _build_condition(conditions_raw: List[Tuple[str, str, str]], merge: str) -> Condition:
    condition_cls = _get_condition_cls(merge)
    conditions = [_extract_condition(i, *condition_raw) for i, condition_raw in enumerate(conditions_raw)]
    return _simplify_condition(condition_cls(conditions))


def _extract_alineas(text: str) -> List[EnrichedString]:
    return [EnrichedString(line) for line in text.split('\n')]


def _build_alternative_section(
    source: str,
    target_section: str,
    merge: str,
    conditions: List[Tuple[str, str, str]],
    new_text_title: str,
    new_text_content: str,
) -> AlternativeSection:
    new_text = StructuredText(EnrichedString(new_text_title), _extract_alineas(new_text_content), [], None)
    return AlternativeSection(
        SectionReference(_load_path(target_section)),
        new_text,
        _build_condition(conditions, merge),
        _build_source(source),
        description='',
    )


_MIN_NB_CHARS = 1


def _extract_new_text_parameters(id_to_value: Dict[str, str]) -> Tuple[str, str]:
    new_text_title = _get_with_error(id_to_value, _NEW_TEXT_TITLE)
    if len(new_text_title or '') < _MIN_NB_CHARS:
        raise _FormHandlingError(f'Le champ "Titre" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    new_text_content = _get_with_error(id_to_value, _NEW_TEXT_CONTENT)
    if len(new_text_content or '') < _MIN_NB_CHARS:
        raise _FormHandlingError(f'Le champ "Contenu du paragraphe" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    return new_text_title, new_text_content


def _count_alineas_in_section(text_dict: Dict[str, Any]) -> int:
    if not text_dict:
        return 0
    return len(StructuredText.from_dict(text_dict).outer_alineas)


def _extract_new_parameter_object(
    page_state: Dict[str, Any], operation: AMOperation, nb_alinea_options: int
) -> ParameterObject:
    id_to_value = _extract_id_to_value(page_state)
    source = _get_with_error(id_to_value, _SOURCE)
    if not source:
        raise _FormHandlingError('Le champ "Source" est obligatoire.')
    target_section = _get_with_error(id_to_value, _TARGET_SECTION)
    if not target_section:
        raise _FormHandlingError('Le champ "Paragraphe visé" est obligatoire.')
    merge = _get_with_error(id_to_value, _CONDITION_MERGE)
    nb_conditions = int(_get_with_error(id_to_value, _NB_CONDITIONS))
    if nb_conditions == 0:
        raise _FormHandlingError('Il doit y avoir au moins une condition.')
    conditions = _extract_conditions(nb_conditions, id_to_value)
    if operation == operation.ADD_CONDITION:
        target_alineas = _get_with_error(id_to_value, _TARGET_ALINEAS)
        if len(set(target_alineas)) == nb_alinea_options:
            target_alineas = None
        return _build_non_application_condition(source, target_section, merge, conditions, target_alineas)
    if operation == operation.ADD_ALTERNATIVE_SECTION:
        new_text_title, new_text_content = _extract_new_text_parameters(id_to_value)
        return _build_alternative_section(source, target_section, merge, conditions, new_text_title, new_text_content)
    raise NotImplementedError(f'Expecting operation not to be {operation.value}')


def _extract_and_upsert_new_parameter(
    page_state: Dict[str, Any], am_id: str, operation: AMOperation, parameter_rank: int, nb_alinea_options: int
) -> None:
    new_parameter = _extract_new_parameter_object(page_state, operation, nb_alinea_options)
    upsert_parameter(am_id, new_parameter, parameter_rank)


def _extract_selected_section_nb_alineas(target_text_dict: Dict[str, Any], loaded_nb_alineas: int) -> int:
    return _count_alineas_in_section(target_text_dict) or loaded_nb_alineas


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
        target_section_nb_alineas = _extract_selected_section_nb_alineas(target_text_dict, loaded_nb_alineas)
        _extract_and_upsert_new_parameter(state, am_id, operation, parameter_rank, target_section_nb_alineas)
    except _FormHandlingError as exc:
        return error_component(f'Erreur dans le formulaire:\n{exc}')
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
    path = _load_path(str_path)
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
    path = _load_path(str_path)
    section = get_section(path, am)
    return section.to_dict()


def _build_targeted_alinea_value(section_dict: Dict[str, Any], operation_str: str) -> List[int]:
    if operation_str != AMOperation.ADD_CONDITION.value or not section_dict:
        return []
    section = StructuredText.from_dict(section_dict)
    return list(range(len(section.outer_alineas)))


@app.callback(
    Output(_NEW_TEXT, 'children'),
    Input(_TARGET_SECTION, 'value'),
    State(_AM_ID, 'children'),
    State(_AM_OPERATION, 'children'),
    prevent_initial_call=True,
)
def _(path, am_id, operation):
    return _build_new_text_component(path, am_id, operation)


@app.callback(
    Output(_TARGET_SECTION_STORE, 'data'),
    Input(_TARGET_SECTION, 'value'),
    State(_AM_ID, 'children'),
    prevent_initial_call=True,
)
def __store_target_section(path, am_id):
    return _store_target_section(path, am_id)


@app.callback(
    Output(_TARGET_ALINEAS, 'options'),
    Input(_TARGET_SECTION_STORE, 'data'),
    State(_AM_OPERATION, 'children'),
    prevent_initial_call=True,
)
def __build_targeted_alinea_options(target_section, operation):
    return _build_targeted_alinea_options(target_section, operation)


@app.callback(
    Output(_TARGET_ALINEAS, 'value'),
    Input(_TARGET_SECTION_STORE, 'data'),
    State(_AM_OPERATION, 'children'),
    prevent_initial_call=True,
)
def __build_targeted_alinea_value(target_section, operation):
    return _build_targeted_alinea_value(target_section, operation)


@app.callback(
    Output('param-edition-upsert-output', 'children'),
    Input('submit-val-param-edition', 'n_clicks'),
    State(_AM_OPERATION, 'children'),
    State(_AM_ID, 'children'),
    State(_PARAMETER_RANK, 'children'),
    State(_TARGET_SECTION_STORE, 'data'),
    State(_LOADED_NB_ALINEAS, 'data'),
    State('page-content', 'children'),
)
def __(n_clicks, operation, am_id, parameter_rank, target_text_dict, loaded_nb_alineas, state):
    return _handle_submit(n_clicks, operation, am_id, parameter_rank, target_text_dict, loaded_nb_alineas, state)


@app.callback(
    Output('param-edition-delete-output', 'children'),
    Input('param-edition-delete-button', 'n_clicks'),
    State(_AM_OPERATION, 'children'),
    State(_AM_ID, 'children'),
    State(_PARAMETER_RANK, 'children'),
)
def ___(n_clicks, operation, am_id, parameter_rank):
    return _handle_delete(n_clicks, operation, am_id, parameter_rank)


@app.callback(
    Output('parametrization-conditions', 'children'), [Input(_NB_CONDITIONS, 'value')], prevent_initial_call=True
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
