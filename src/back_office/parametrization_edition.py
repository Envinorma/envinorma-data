import json
import os
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Type, Union

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
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
    ParameterType,
    Parametrization,
    SectionReference,
)
from lib.utils import get_parametrization_wip_folder, jsonify

from back_office.utils import AMOperation, div, dump_am_state, load_am_state, load_parametrization, write_file

_Options = List[Dict[str, Any]]

_CONDITION_VARIABLES = {'Régime': ParameterEnum.REGIME, 'Date d\'autorisation': ParameterEnum.DATE_AUTORISATION}
_CONDITION_VARIABLE_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_VARIABLES]
_CONDITION_OPERATIONS = ['<', '<=', '=', '>', '>=']
_CONDITION_OPERATION_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_OPERATIONS]

_CONDITION_PARAMETER = 'param-edition-condition-parameter'
_CONDITION_OPERATION = 'param-edition-condition-operation'
_CONDITION_VALUE = 'param-edition-condition-value'
_DESCRIPTION = 'param-edition-description'
_SOURCE = 'param-edition-source'
_TARGET_SECTION = 'param-edition-target-section'
_TARGET_ALINEAS = 'param-edition-target-alineas'
_CONDITION_MERGE = 'param-edition-condition-merge'
_NB_CONDITIONS = 'param-edition-nb-conditions'
_NEW_TEXT_TITLE = 'param-edition-new-text-title'
_NEW_TEXT_CONTENT = 'param-edition-new-text-content'
_AM_ID = 'param-edition-am-id'
_AM_OPERATION = 'param-edition-am-operation'


def _get_condition_component(rank: int) -> Component:
    dropdown_conditions = [
        dcc.Dropdown(
            id=f'{_CONDITION_PARAMETER}_{rank}',
            options=_CONDITION_VARIABLE_OPTIONS,
            clearable=False,
            value='Date d\'autorisation',
            style={'width': '200px'},
        ),
        dcc.Dropdown(
            id=f'{_CONDITION_OPERATION}_{rank}',
            options=_CONDITION_OPERATION_OPTIONS,
            clearable=False,
            value='=',
            style=dict(width='50px'),
        ),
        dcc.Input(id=f'{_CONDITION_VALUE}_{rank}', value='', type='text', style={'padding': '0', 'height': '36px'}),
    ]
    return div([*dropdown_conditions], style=dict(display='flex'))


def _get_condition_components(nb_components: int) -> Component:
    dropdown_conditions = [_get_condition_component(i) for i in range(nb_components)]
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
            html.Label('Titre', htmlFor=_NEW_TEXT_TITLE, className='form-label'),
            dcc.Input(id=_NEW_TEXT_TITLE, placeholder='Titre', className='form-control'),
            html.Label('Contenu du paragraphe', htmlFor=_NEW_TEXT_CONTENT, className='form-label'),
            div(dcc.Textarea(id=_NEW_TEXT_CONTENT, className='form-control')),
        ]
    )


def _go_back_button(parent_page: str) -> Component:
    return dcc.Link(html.Button('Retour', className='btn btn-primary center'), href=parent_page)


def _make_form(options: _Options, operation: AMOperation, parent_page: str, am_id: str) -> Component:
    dropdown_source = dcc.Dropdown(options=options, id=_SOURCE)
    dropdown_target = dcc.Dropdown(options=options, id=_TARGET_SECTION)
    dropdown_alineas = dcc.Dropdown(options=_ALINEA_OPTIONS, multi=True, value=['TOUS'], id=_TARGET_ALINEAS)
    merge_values = [{'value': 'and', 'label': 'ET'}, {'value': 'or', 'label': 'OU'}]
    dropdown_condition_merge = dcc.Dropdown(options=merge_values, clearable=False, value='and', id=_CONDITION_MERGE)
    dropdown_nb_conditions = dcc.Dropdown(
        _NB_CONDITIONS, options=[{'label': i, 'value': i} for i in range(10)], clearable=False, value=1
    )

    return html.Div(
        [
            _get_main_title(operation),
            html.H4('Description (visible par l\'utilisateur)'),
            _get_description_help(operation),
            dcc.Textarea(value='', className='form-control', id=_DESCRIPTION),
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
            html.Div(id='parametrization-conditions'),
            html.Div(id='form-output-param-edition'),
            html.Button(
                'Enregistrer',
                id='submit-val-param-edition',
                className='btn btn-primary',
                style={'margin-right': '5px'},
                n_clicks=0,
            ),
            _go_back_button(parent_page),
            html.P(am_id, hidden=True, id=_AM_ID),
            html.P(operation.value, hidden=True, id=_AM_OPERATION),
        ]
    )


def _extract_reference_and_values_titles(text: StructuredText, path: Ints, level: int = 0) -> List[Tuple[str, str]]:
    return [(json.dumps(path), '#' * level + ' ' + text.title.text[:60])] + [
        elt
        for rank, sec in enumerate(text.sections)
        for elt in _extract_reference_and_values_titles(sec, path + (rank,), level + 1)
    ]


def _extract_paragraph_reference_dropdown_values(text: StructuredText) -> _Options:
    title_references_and_values = _extract_reference_and_values_titles(text, ())
    return [{'label': title, 'value': reference} for reference, title in title_references_and_values]


def _structure_edition_component(
    text: StructuredText, operation: AMOperation, parent_page: str, am_id: str
) -> Component:
    dropdown_values = _extract_paragraph_reference_dropdown_values(text)
    return _make_form(dropdown_values, operation, parent_page, am_id)


def make_am_parametrization_edition_component(
    am: ArreteMinisteriel, operation: AMOperation, parent_page: str, am_id: str
) -> Component:
    text = am_to_text(am)
    return div(_structure_edition_component(text, operation, parent_page, am_id))


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


def _compute_filename() -> str:
    new_version = datetime.now().strftime('%y%m%d_%H%M')
    filename = new_version + '.json'
    return filename


def _add_filename_to_state(am_id: str, filename: str) -> None:
    am_state = load_am_state(am_id)
    am_state.parametrization_draft_filenames.append(filename)
    dump_am_state(am_id, am_state)


_ParameterObject = Union[NonApplicationCondition, AlternativeSection]


def _extract_non_str_children(page_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    child_or_children = page_state.get('props', {}).get('children')
    if not child_or_children:
        return []
    if isinstance(child_or_children, dict):
        return [child_or_children]
    if isinstance(child_or_children, list):
        return child_or_children
    return []


def _extract_components_with_id(page_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    children = _extract_non_str_children(page_state)
    return [child for child in children if child.get('props', {}).get('id')] + [
        dc for child in children for dc in _extract_components_with_id(child)
    ]


def _extract_id_to_value(page_state: Dict[str, Any]) -> Dict[str, Any]:
    children = _extract_components_with_id(page_state)
    return {child['props']['id']: child['props'].get('value') for child in children}


def _get_with_error(dict_: Dict[str, Any], key: str) -> Any:
    if key not in dict_:
        raise ValueError(f'Expecting key {key} in dict_. Existing keys: {list(dict_.keys())}')
    return dict_[key]


def _assert_int(value: Any) -> int:
    if not isinstance(value, int):
        raise ValueError(f'Expecting type int, received type {type(value)}')
    return value


def _assert_str(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f'Expecting type str, received type {type(value)}')
    return value


def _assert_list(value: Any) -> List:
    if not isinstance(value, list):
        raise ValueError(f'Expecting type list, received type {type(value)}')
    return value


def _extract_conditions(nb_conditions: int, id_to_value: Dict[str, Any]) -> List[Tuple[str, str, str]]:
    return [
        (
            _assert_str(_get_with_error(id_to_value, f'{_CONDITION_PARAMETER}_{i}')),
            _assert_str(_get_with_error(id_to_value, f'{_CONDITION_OPERATION}_{i}')),
            _assert_str(_get_with_error(id_to_value, f'{_CONDITION_VALUE}_{i}')),
        )
        for i in range(nb_conditions)
    ]


class _ErrorInForm(Exception):
    pass


def _build_source(source_str: str) -> ConditionSource:
    return ConditionSource('', EntityReference(SectionReference(_get_path(source_str)), None))


def _extract_alinea_indices(target_alineas: List[Union[str, int]]) -> Optional[List[int]]:
    _assert_list(target_alineas)
    if target_alineas == ['TOUS']:
        return None
    if 'TOUS' in target_alineas and len(target_alineas) >= 2:
        raise _ErrorInForm(
            'Le champ "Alineas visés" ne peut contenir la valeur "TOUS" que ' 'si c\'est la seule valeur renseignée.'
        )
    return [_assert_int(x) for x in target_alineas]


def _get_path(path_str: str) -> Ints:
    return tuple(json.loads(path_str))


def _build_non_application_condition(
    description: str,
    source: str,
    target_section: str,
    merge: str,
    conditions: List[Tuple[str, str, str]],
    target_alineas: List[Union[str, int]],
) -> NonApplicationCondition:
    return NonApplicationCondition(
        EntityReference(SectionReference(_get_path(target_section)), _extract_alinea_indices(target_alineas)),
        _build_condition(conditions, merge),
        _build_source(source),
        description,
    )


def _get_condition_cls(merge: str) -> Union[Type[AndCondition], Type[OrCondition]]:
    if merge == 'and':
        return AndCondition
    if merge == 'or':
        return OrCondition
    raise _ErrorInForm('Mauvaise opération d\'aggrégation dans le formulaire. Attendu: ET ou OU.')


def _extract_parameter(parameter: str) -> Parameter:
    if parameter not in _CONDITION_VARIABLES:
        raise _ErrorInForm(f'Paramètre {parameter} inconnu, attendus: {list(_CONDITION_VARIABLES.keys())}')
    return _CONDITION_VARIABLES[parameter].value


def _parse_dmy(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        raise _ErrorInForm(f'Date mal formattée. Format attendu JJ/MM/AAAA. Reçu: "{date_str}"')


def _parse_regime(regime_str: str) -> Regime:
    try:
        return Regime(regime_str)
    except ValueError:
        raise _ErrorInForm(f'Mauvais régime. Attendu: {[x.value for x in Regime]}. Reçu: "{regime_str}"')


def _build_parameter_value(parameter_type: ParameterType, value_str: str) -> Any:
    if parameter_type == parameter_type.DATE:
        return _parse_dmy(value_str)
    if parameter_type == parameter_type.REGIME:
        return _parse_regime(value_str)
    raise _ErrorInForm(f'Ce type de paramètre n\'est pas géré: {parameter_type.value}')


def _extract_condition(rank: int, parameter: str, operator: str, value_str: str) -> Condition:
    try:
        built_parameter = _extract_parameter(parameter)
        value = _build_parameter_value(built_parameter.type, value_str)
    except _ErrorInForm as exc:
        raise _ErrorInForm(f'Erreur dans la {rank+1}{"ère" if rank == 0 else "ème"} condition: {exc}')
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
    raise _ErrorInForm(f'La {rank+1}{"ère" if rank == 0 else "ème"} condition contient un opérateur inattendu.')


def _build_condition(conditions_raw: List[Tuple[str, str, str]], merge: str) -> Condition:
    condition_cls = _get_condition_cls(merge)
    conditions = [_extract_condition(i, *condition_raw) for i, condition_raw in enumerate(conditions_raw)]
    return condition_cls(conditions)


def _extract_alineas(text: str) -> List[EnrichedString]:
    return [EnrichedString(line) for line in text.split('\n')]


def _build_alternative_section(
    description: str,
    source: str,
    target_section: str,
    merge: str,
    conditions: List[Tuple[str, str, str]],
    new_text_title: str,
    new_text_content: str,
) -> AlternativeSection:
    new_text = StructuredText(EnrichedString(new_text_title), _extract_alineas(new_text_content), [], None)
    return AlternativeSection(
        SectionReference(_get_path(target_section)),
        new_text,
        _build_condition(conditions, merge),
        _build_source(source),
        description,
    )


_MIN_NB_CHARS = 5


def _extract_new_text_parameters(id_to_value: Dict[str, str]) -> Tuple[str, str]:
    new_text_title = _get_with_error(id_to_value, _NEW_TEXT_TITLE)
    if len(new_text_title or '') < _MIN_NB_CHARS:
        raise _ErrorInForm(f'Le champ "Titre" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    new_text_content = _get_with_error(id_to_value, _NEW_TEXT_CONTENT)
    if len(new_text_content or '') < _MIN_NB_CHARS:
        raise _ErrorInForm(f'Le champ "Contenu du paragraphe" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    return new_text_title, new_text_content


def _extract_new_parameter_object(page_state: Dict[str, Any], operation: AMOperation) -> _ParameterObject:
    id_to_value = _extract_id_to_value(page_state)
    description = _assert_str(_get_with_error(id_to_value, _DESCRIPTION))
    if len(description) < _MIN_NB_CHARS:
        raise _ErrorInForm(f'Le champ "Description" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    source = _get_with_error(id_to_value, _SOURCE)
    if not source:
        raise _ErrorInForm('Le champ "Source" est obligatoire.')
    target_section = _get_with_error(id_to_value, _TARGET_SECTION)
    if not target_section:
        raise _ErrorInForm('Le champ "Paragraphe visé" est obligatoire.')
    merge = _get_with_error(id_to_value, _CONDITION_MERGE)
    nb_conditions = int(_get_with_error(id_to_value, _NB_CONDITIONS))
    conditions = _extract_conditions(nb_conditions, id_to_value)
    if operation == operation.ADD_CONDITION:
        target_alineas = _get_with_error(id_to_value, _TARGET_ALINEAS)
        return _build_non_application_condition(description, source, target_section, merge, conditions, target_alineas)
    if operation == operation.ADD_ALTERNATIVE_SECTION:
        new_text_title, new_text_content = _extract_new_text_parameters(id_to_value)
        return _build_alternative_section(
            description, source, target_section, merge, conditions, new_text_title, new_text_content
        )
    raise NotImplementedError(f'Expecting operation not to be {operation.value}')


def _build_new_parametrization(am_id: str, new_parameter: _ParameterObject) -> Parametrization:
    old_parametrization = load_parametrization(am_id, load_am_state(am_id))
    if not old_parametrization:
        raise ValueError('Parametrization not found, which should not happen.')
    if isinstance(new_parameter, NonApplicationCondition):
        new_conditions = old_parametrization.application_conditions + [new_parameter]
        new_sections = old_parametrization.alternative_sections
    else:
        new_conditions = old_parametrization.application_conditions
        new_sections = old_parametrization.alternative_sections + [new_parameter]
    return Parametrization(new_conditions, new_sections)


def _extract_and_dump_new_object(page_state: Dict[str, Any], am_id: str, operation: AMOperation) -> None:
    new_parameter = _extract_new_parameter_object(page_state, operation)
    parametrization = _build_new_parametrization(am_id, new_parameter)
    filename = _compute_filename()
    full_filename = os.path.join(get_parametrization_wip_folder(am_id), filename)
    json_ = jsonify(parametrization.to_dict())
    write_file(json_, full_filename)
    _add_filename_to_state(am_id, filename)


def _replace_line_breaks(message: str) -> List[Component]:
    return [html.P(piece) for piece in message.split('\n')]


def _error_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-danger', style={'margin-top': '15px'})


def _success_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-success', style={'margin-top': '15px'})


def _handle_submit(n_clicks: int, operation_str: str, am_id: str, state: Dict[str, Any]) -> Component:
    if n_clicks == 0:
        return html.Div()
    try:
        operation = AMOperation(operation_str)
        _extract_and_dump_new_object(state, am_id, operation)
    except _ErrorInForm as exc:
        return _error_component(f'Erreur dans le formulaire:\n{exc}')
    except Exception:  # pylint: disable=broad-except
        return _error_component(f'Unexpected error:\n{traceback.format_exc()}')
    return _success_component(f'Enregistrement réussi.')


def add_parametrization_edition_callbacks(app: dash.Dash):
    def handle_submit(n_clicks, operation, am_id, state):
        return _handle_submit(n_clicks, operation, am_id, state)

    app.callback(
        Output('form-output-param-edition', 'children'),
        [
            Input('submit-val-param-edition', 'n_clicks'),
            Input(_AM_OPERATION, 'children'),
            Input(_AM_ID, 'children'),
        ],
        [State('page-content', 'children')],
    )(handle_submit)

    def nb_conditions(value):
        return _get_condition_components(value)

    app.callback(
        Output('parametrization-conditions', 'children'),
        [Input(_NB_CONDITIONS, 'value')],
    )(nb_conditions)
