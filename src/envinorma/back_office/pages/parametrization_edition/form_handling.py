from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from envinorma.back_office.fetch_data import upsert_parameter
from envinorma.back_office.pages.parametrization_edition import page_ids
from envinorma.back_office.utils import AMOperation, assert_int, assert_list, assert_str
from envinorma.data import Regime, StructuredText, ensure_rubrique, load_path
from envinorma.data.text_elements import EnrichedString
from envinorma.parametrization import (
    AlternativeSection,
    ConditionSource,
    EntityReference,
    NonApplicationCondition,
    ParameterObject,
    SectionReference,
)
from envinorma.parametrization.conditions import (
    AndCondition,
    Condition,
    Equal,
    Greater,
    Littler,
    MonoCondition,
    OrCondition,
    Parameter,
    ParameterType,
    Range, ensure_mono_conditions,
)


class FormHandlingError(Exception):
    pass


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
            assert_str(_get_with_error(id_to_value, f'{page_ids.CONDITION_VARIABLE}_{i}')),
            assert_str(_get_with_error(id_to_value, f'{page_ids.CONDITION_OPERATION}_{i}')),
            assert_str(_get_with_error(id_to_value, f'{page_ids.CONDITION_VALUE}_{i}')),
        )
        for i in range(nb_conditions)
    ]


def _build_source(source_str: str) -> ConditionSource:
    return ConditionSource('', EntityReference(SectionReference(load_path(source_str)), None))


def _extract_alinea_indices(target_alineas: Optional[List[int]]) -> Optional[List[int]]:
    if target_alineas is None:
        return None
    assert_list(target_alineas)
    return [assert_int(x) for x in target_alineas]


def _build_non_application_condition(
    source: str,
    target_section: str,
    merge: str,
    conditions: List[Tuple[str, str, str]],
    target_alineas: Optional[List[int]],
) -> NonApplicationCondition:
    return NonApplicationCondition(
        EntityReference(SectionReference(load_path(target_section)), _extract_alinea_indices(target_alineas)),
        _build_condition(conditions, merge),
        _build_source(source),
        description='',
    )


def _get_condition_cls(merge: str) -> Union[Type[AndCondition], Type[OrCondition]]:
    if merge == 'and':
        return AndCondition
    if merge == 'or':
        return OrCondition
    raise FormHandlingError('Mauvaise opération d\'aggrégation dans le formulaire. Attendu: ET ou OU.')


def _extract_parameter(parameter: str) -> Parameter:
    if parameter not in page_ids.CONDITION_VARIABLES:
        raise FormHandlingError(f'Paramètre {parameter} inconnu, attendus: {list(page_ids.CONDITION_VARIABLES.keys())}')
    return page_ids.CONDITION_VARIABLES[parameter].value


def _parse_dmy(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, '%d/%m/%Y')
    except ValueError:
        raise FormHandlingError(f'Date mal formattée. Format attendu JJ/MM/AAAA. Reçu: "{date_str}"')


def _ensure_float(candidate: str) -> float:
    try:
        return float(candidate)
    except ValueError:
        raise FormHandlingError('Valeur incorrecte dans une condition, nombre attendu.')


def _ensure_rubrique(candidate: str) -> str:
    try:
        return ensure_rubrique(candidate)
    except ValueError:
        raise FormHandlingError('Rubrique incorrecte dans une condition, format attendu XXXX')


def _parse_regime(regime_str: str) -> Regime:
    try:
        return Regime(regime_str)
    except ValueError:
        raise FormHandlingError(f'Mauvais régime. Attendu: {[x.value for x in Regime]}. Reçu: "{regime_str}"')


def _build_parameter_value(parameter_type: ParameterType, value_str: str) -> Any:
    if parameter_type == parameter_type.DATE:
        return _parse_dmy(value_str)
    if parameter_type == parameter_type.REGIME:
        return _parse_regime(value_str)
    if parameter_type == parameter_type.REAL_NUMBER:
        return _ensure_float(value_str)
    if parameter_type == parameter_type.RUBRIQUE:
        return _ensure_rubrique(value_str)
    if parameter_type == parameter_type.STRING:
        return value_str
    raise FormHandlingError(f'Ce type de paramètre n\'est pas géré: {parameter_type.value}')


def _extract_condition(rank: int, parameter: str, operator: str, value_str: str) -> Condition:
    try:
        built_parameter = _extract_parameter(parameter)
        value = _build_parameter_value(built_parameter.type, value_str)
    except FormHandlingError as exc:
        raise FormHandlingError(f'Erreur dans la {rank+1}{"ère" if rank == 0 else "ème"} condition: {exc}')
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
    raise FormHandlingError(f'La {rank+1}{"ère" if rank == 0 else "ème"} condition contient un opérateur inattendu.')


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
            raise FormHandlingError('Erreur dans les conditions: les deux conditions sont incompatibles.')


def _check_compatibility_and_build_range(
    parameter: Parameter, condition_1: MonoCondition, condition_2: MonoCondition
) -> Range:
    if isinstance(condition_1, Equal) or isinstance(condition_2, Equal):
        raise FormHandlingError('Erreur dans les conditions. Elles sont soit redondantes, soit incompatibles.')
    if isinstance(condition_1, Littler) and isinstance(condition_2, Littler):
        raise FormHandlingError('Erreur dans les conditions. Elles sont redondantes.')
    if isinstance(condition_1, Greater) and isinstance(condition_2, Greater):
        raise FormHandlingError('Erreur dans les conditions. Elles sont redondantes.')
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


def _extract_parameter_to_conditions(conditions: List[MonoCondition]) -> Dict[Parameter, List[MonoCondition]]:
    res: Dict[Parameter, List[MonoCondition]] = {}
    for condition in conditions:
        if condition.parameter not in res:
            res[condition.parameter] = []
        res[condition.parameter].append(condition)
    return res


class _NotSimplifiableError(Exception):
    pass


def _simplify_mono_conditions(parameter: Parameter, conditions: List[MonoCondition]) -> Union[MonoCondition, Range]:
    if len(conditions) >= 3 or len(conditions) == 0:
        raise _NotSimplifiableError()
    if len(conditions) == 1:
        return conditions[0]
    if parameter.type not in (ParameterType.DATE, ParameterType.REAL_NUMBER):
        raise FormHandlingError('Erreur dans les conditions: elles sont soit incompatibles, soit redondantes.')
    return _check_compatibility_and_build_range(parameter, conditions[0], conditions[1])


def _try_building_range_condition(conditions: List[Condition]) -> Optional[Condition]:
    if not conditions:
        return None
    mono_conditions = ensure_mono_conditions(conditions)
    parameter_to_conditions = _extract_parameter_to_conditions(mono_conditions)
    try:
        new_conditions = [_simplify_mono_conditions(param, cds) for param, cds in parameter_to_conditions.items()]
    except _NotSimplifiableError:
        return None
    return AndCondition([*new_conditions]) if len(new_conditions) != 1 else new_conditions[0]


def _simplify_condition(condition: Condition) -> Condition:
    if isinstance(condition, (AndCondition, OrCondition)):
        if len(condition.conditions) == 1:
            return condition.conditions[0]
        if len(condition.conditions) == 0:
            raise FormHandlingError('Au moins une condition est nécessaire !')
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
        SectionReference(load_path(target_section)),
        new_text,
        _build_condition(conditions, merge),
        _build_source(source),
        description='',
    )


_MIN_NB_CHARS = 1


def _extract_new_text_parameters(id_to_value: Dict[str, str]) -> Tuple[str, str]:
    new_text_title = _get_with_error(id_to_value, page_ids.NEW_TEXT_TITLE)
    if len(new_text_title or '') < _MIN_NB_CHARS:
        raise FormHandlingError(f'Le champ "Titre" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    new_text_content = _get_with_error(id_to_value, page_ids.NEW_TEXT_CONTENT)
    if len(new_text_content or '') < _MIN_NB_CHARS:
        raise FormHandlingError(f'Le champ "Contenu du paragraphe" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    return new_text_title, new_text_content


def _count_alineas_in_section(text_dict: Dict[str, Any]) -> int:
    if not text_dict:
        return 0
    return len(StructuredText.from_dict(text_dict).outer_alineas)


def _extract_new_parameter_object(
    page_state: Dict[str, Any], operation: AMOperation, nb_alinea_options: int
) -> ParameterObject:
    id_to_value = _extract_id_to_value(page_state)
    source = _get_with_error(id_to_value, page_ids.SOURCE)
    if not source:
        raise FormHandlingError('Le champ "Source" est obligatoire.')
    target_section = _get_with_error(id_to_value, page_ids.TARGET_SECTION)
    if not target_section:
        raise FormHandlingError('Le champ "Paragraphe visé" est obligatoire.')
    merge = _get_with_error(id_to_value, page_ids.CONDITION_MERGE)
    nb_conditions = int(_get_with_error(id_to_value, page_ids.NB_CONDITIONS))
    if nb_conditions == 0:
        raise FormHandlingError('Il doit y avoir au moins une condition.')
    conditions = _extract_conditions(nb_conditions, id_to_value)
    if operation == operation.ADD_CONDITION:
        target_alineas = _get_with_error(id_to_value, page_ids.TARGET_ALINEAS)
        if len(set(target_alineas)) == nb_alinea_options:
            target_alineas = None
        return _build_non_application_condition(source, target_section, merge, conditions, target_alineas)
    if operation == operation.ADD_ALTERNATIVE_SECTION:
        new_text_title, new_text_content = _extract_new_text_parameters(id_to_value)
        return _build_alternative_section(source, target_section, merge, conditions, new_text_title, new_text_content)
    raise NotImplementedError(f'Expecting operation not to be {operation.value}')


def extract_and_upsert_new_parameter(
    page_state: Dict[str, Any], am_id: str, operation: AMOperation, parameter_rank: int, nb_alinea_options: int
) -> None:
    new_parameter = _extract_new_parameter_object(page_state, operation, nb_alinea_options)
    upsert_parameter(am_id, new_parameter, parameter_rank)


def extract_selected_section_nb_alineas(target_text_dict: Dict[str, Any], loaded_nb_alineas: int) -> int:
    return _count_alineas_in_section(target_text_dict) or loaded_nb_alineas
