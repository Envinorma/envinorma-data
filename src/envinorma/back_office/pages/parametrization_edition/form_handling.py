from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Type, Union, cast

from envinorma.back_office.fetch_data import load_most_advanced_am, upsert_parameter
from envinorma.back_office.pages.parametrization_edition import page_ids
from envinorma.back_office.pages.parametrization_edition.condition_form import ConditionFormValues
from envinorma.back_office.pages.parametrization_edition.target_sections_form import TargetSectionFormValues
from envinorma.back_office.utils import AMOperation, safe_get_section
from envinorma.data import ArreteMinisteriel, Regime, StructuredText, ensure_rubrique, load_path
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
    Range,
    ensure_mono_conditions,
)


class FormHandlingError(Exception):
    pass


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


def _build_sourceVNEWW(source_str: str) -> ConditionSource:
    return ConditionSource('', EntityReference(SectionReference(load_path(source_str)), None))


def _build_conditionVNEWWW(condition_form_values: ConditionFormValues) -> Condition:
    condition_cls = _get_condition_cls(condition_form_values.merge)
    conditions_raw = zip(
        condition_form_values.parameters, condition_form_values.operations, condition_form_values.values
    )
    conditions = [_extract_condition(i, *condition_raw) for i, condition_raw in enumerate(conditions_raw)]
    return _simplify_condition(condition_cls(conditions))


@dataclass
class _Modification:
    target_section: SectionReference
    target_alineas: Optional[List[int]]
    new_text: Optional[StructuredText]


def _extract_alineas(text: str) -> List[EnrichedString]:
    return [EnrichedString(line) for line in text.split('\n')]


_MIN_NB_CHARS = 1


def _check_and_build_new_text(title: str, content: str) -> StructuredText:
    if len(title or '') < _MIN_NB_CHARS:
        raise FormHandlingError(f'Le champ "Titre" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    if len(content or '') < _MIN_NB_CHARS:
        raise FormHandlingError(f'Le champ "Contenu du paragraphe" doit contenir au moins {_MIN_NB_CHARS} caractères.')
    return StructuredText(EnrichedString(title), _extract_alineas(content), [], None)


def _build_new_text(new_text_title: Optional[str], new_text_content: Optional[str]) -> Optional[StructuredText]:
    if not new_text_title:
        assert new_text_content is None, f'{new_text_title} and {new_text_content} must be simultaneously None'
        return None
    assert new_text_content is not None, f'new_text_content must not be None'
    return _check_and_build_new_text(new_text_title, new_text_content)


def _simplify_alineas(
    am: ArreteMinisteriel, section: SectionReference, target_alineas: Optional[List[int]]
) -> Optional[List[int]]:
    if not target_alineas:
        return None
    target_section = safe_get_section(section.path, am)
    if target_section is None:
        raise FormHandlingError('La section visée est introuvable dans l\'arrêté')
    if len(set(target_alineas)) == len(target_section.outer_alineas):
        return None
    return target_alineas


def _build_target_versionVNEWW(
    am: ArreteMinisteriel,
    new_text_title: Optional[str],
    new_text_content: Optional[str],
    target_section: str,
    target_alineas: Optional[List[int]],
) -> _Modification:
    section = SectionReference(load_path(target_section))
    simplified_target_alineas = _simplify_alineas(am, section, target_alineas)
    new_text = _build_new_text(new_text_title, new_text_content)
    return _Modification(section, simplified_target_alineas, new_text)


def _build_target_versionsVNEWW(am: ArreteMinisteriel, form_values: TargetSectionFormValues) -> List[_Modification]:
    new_texts_titles = form_values.new_texts_titles or len(form_values.target_sections) * [None]
    new_texts_contents = form_values.new_texts_contents or len(form_values.target_sections) * [None]
    target_sections = form_values.target_sections
    target_alineas = form_values.target_alineas or len(form_values.target_sections) * [None]
    return [
        _build_target_versionVNEWW(am, title, content, section, alineas)
        for title, content, section, alineas in zip(
            new_texts_titles, new_texts_contents, target_sections, target_alineas
        )
    ]


def _build_non_application_conditionVNEWWW(
    condition: Condition, source: ConditionSource, modification: _Modification
) -> NonApplicationCondition:
    targeted_entity = EntityReference(modification.target_section, outer_alinea_indices=modification.target_alineas)
    return NonApplicationCondition(targeted_entity=targeted_entity, condition=condition, source=source)


def _build_parameter_object(
    condition: Condition, source: ConditionSource, modification: _Modification
) -> ParameterObject:
    if modification.new_text:
        return AlternativeSection(
            targeted_section=modification.target_section,
            new_text=modification.new_text,
            condition=condition,
            source=source,
        )
    return _build_non_application_conditionVNEWWW(condition, source, modification)


def _extract_new_parameter_objectsVNEWWWW(
    am: ArreteMinisteriel,
    source_str: str,
    target_section_form_values: TargetSectionFormValues,
    condition_form_values: ConditionFormValues,
) -> List[ParameterObject]:
    condition = _build_conditionVNEWWW(condition_form_values)
    target_versions = _build_target_versionsVNEWW(am, target_section_form_values)
    source = _build_sourceVNEWW(source_str)
    return [_build_parameter_object(condition, source, target_version) for target_version in target_versions]


def _check_consistency(operation: AMOperation, parameters: List[ParameterObject]) -> None:
    for parameter in parameters:
        if operation == AMOperation.ADD_CONDITION:
            assert isinstance(
                parameter, NonApplicationCondition
            ), f'Expect NonApplicationCondition, got {type(parameter)}'
        elif operation == AMOperation.ADD_ALTERNATIVE_SECTION:
            assert isinstance(parameter, AlternativeSection), f'Expect AlternativeSection, got {type(parameter)}'
        else:
            raise ValueError(f'Unexpected operation {operation}')


def extract_and_upsert_new_parameter(
    operation: AMOperation,
    am_id: str,
    parameter_rank: int,
    source_str: str,
    target_section_form_values: TargetSectionFormValues,
    condition_form_values: ConditionFormValues,
) -> None:
    am = load_most_advanced_am(am_id)
    if not am:
        raise ValueError(f'AM with id {am_id} not found!')
    new_parameters = _extract_new_parameter_objectsVNEWWWW(
        am, source_str, target_section_form_values, condition_form_values
    )
    _check_consistency(operation, new_parameters)
    _upsert_parameters(am_id, new_parameters, parameter_rank)


def _upsert_parameters(am_id: str, new_parameters: List[ParameterObject], parameter_rank: int):
    if parameter_rank != -1 and len(new_parameters) != 1:
        raise ValueError('Must have only one parameter when updating a specific parameter..')
    for parameter in new_parameters:
        upsert_parameter(am_id, parameter, parameter_rank)
