from copy import copy, deepcopy
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any, Dict, KeysView, List, Optional, Set, Tuple, Union

from lib.data import Applicability, ArreteMinisteriel, DateCriterion, Regime, StructuredText
from lib.parametrization import (
    Equal,
    Greater,
    Littler,
    AndCondition,
    Range,
    OrCondition,
    ConditionType,
    Parameter,
    ParameterEnum,
    ParameterType,
    Parametrization,
    AlternativeSection,
    NonApplicationCondition,
    Condition,
    Ints,
    LeafCondition,
    Combinations,
    condition_to_str,
)


def _generate_bool_condition(parameter_str: str) -> Equal:
    return Equal(Parameter(parameter_str, ParameterType.BOOLEAN), True)


def _check_application_conditions_are_disjoint(parametrization: Parametrization, raise_errors: bool):
    raise NotImplementedError()


def _check_parametrization_consistency(parametrization: Parametrization, raise_errors: bool) -> None:
    _check_application_conditions_are_disjoint(parametrization, raise_errors)


def _extract_section_titles(am: Union[StructuredText, ArreteMinisteriel], path: List[int]) -> Dict[int, str]:
    sections = am.sections if isinstance(am, ArreteMinisteriel) else am.sections
    if not path:
        titles = {i: section.title.text for i, section in enumerate(sections)}
        return titles
    return _extract_section_titles(sections[path[0]], path[1:])


def _extract_section(am: Union[StructuredText, ArreteMinisteriel], path: List[int]) -> StructuredText:
    if not path:
        if isinstance(am, ArreteMinisteriel):
            raise ValueError()
        return am
    sections = am.sections if isinstance(am, ArreteMinisteriel) else am.sections
    return _extract_section(sections[0], path[1:])


def _check_condition(condition: Condition) -> None:
    if isinstance(condition, Equal):
        assert condition.type == ConditionType.EQUAL
    if isinstance(condition, Greater):
        assert condition.type == ConditionType.GREATER
    if isinstance(condition, Littler):
        assert condition.type == ConditionType.LITTLER
    if isinstance(condition, Range):
        assert condition.type == ConditionType.RANGE
    if isinstance(condition, AndCondition):
        assert condition.type == ConditionType.AND
    if isinstance(condition, OrCondition):
        assert condition.type == ConditionType.OR
    if isinstance(condition, (AndCondition, OrCondition)):
        for subcondition in condition.conditions:
            _check_condition(subcondition)


def _check_parametrization(parametrization: Parametrization) -> None:
    for app in parametrization.application_conditions:
        _check_condition(app.condition)
    for sec in parametrization.alternative_sections:
        _check_condition(sec.condition)


def _extract_parameters_from_condition(condition: Condition) -> List[Parameter]:
    if isinstance(condition, (OrCondition, AndCondition)):
        return [param for cd in condition.conditions for param in _extract_parameters_from_condition(cd)]
    return [condition.parameter]


def _extract_parameters_from_parametrization(parametrization: Parametrization) -> Set[Parameter]:
    application_conditions = {
        cd
        for app_cond in parametrization.application_conditions
        for cd in _extract_parameters_from_condition(app_cond.condition)
    }
    alternative_sections = {
        cd
        for alt_sec in parametrization.alternative_sections
        for cd in _extract_parameters_from_condition(alt_sec.condition)
    }
    return application_conditions.union(alternative_sections)


def _any_parameter_is_undefined(condition: Condition, defined_parameters: KeysView[Parameter]) -> bool:
    parameters = _extract_parameters_from_condition(condition)
    return any([parameter not in defined_parameters for parameter in parameters])


def _is_satisfied_range(condition: Range, parameter_value: Any) -> bool:
    if condition.left_strict and condition.right_strict:
        return condition.left < parameter_value < condition.right
    if condition.left_strict and not condition.right_strict:
        return condition.left < parameter_value <= condition.right
    if not condition.left_strict and condition.right_strict:
        return condition.left <= parameter_value < condition.right
    if not condition.left_strict and not condition.right_strict:
        return condition.left <= parameter_value <= condition.right
    raise NotImplementedError()


def _is_satisfied_leaf(condition: LeafCondition, parameter_values: Dict[Parameter, Any]) -> bool:
    if condition.parameter not in parameter_values:
        return False
    value = parameter_values[condition.parameter]
    if isinstance(condition, Littler):
        return (value < condition.target) if condition.strict else (value <= condition.target)
    if isinstance(condition, Greater):
        return (value > condition.target) if condition.strict else (value >= condition.target)
    if isinstance(condition, Equal):
        return value == condition.target
    if isinstance(condition, Range):
        return _is_satisfied_range(condition, parameter_values[condition.parameter])
    raise NotImplementedError(f'Condition {type(condition)} not implemented yet.')


def _is_satisfied(condition: Condition, parameter_values: Dict[Parameter, Any]) -> bool:
    if isinstance(condition, AndCondition):
        return all([_is_satisfied(cd, parameter_values) for cd in condition.conditions])
    if isinstance(condition, OrCondition):
        return any([_is_satisfied(cd, parameter_values) for cd in condition.conditions])
    return _is_satisfied_leaf(condition, parameter_values)


def _generate_warning_missing_value(condition: Condition) -> str:
    parameters = _extract_parameters_from_condition(condition)
    if len(parameters) == 1:
        parameter = list(parameters)[0]
        return f'Ce paragraphe pourrait ne pas être applicable selon la valeur du paramètre {parameter.id}.'
    ids = ', '.join([param.id for param in parameters])
    return f'Ce paragraphe pourrait ne pas être applicable selon la valeur des paramètres suivants: {ids}.'


def _generate_reason_active_leaf(condition: LeafCondition) -> str:
    parameter = condition.parameter
    if isinstance(condition, Equal):
        return f'Le paramètre {parameter.id} est égal à {condition.target}'
    if isinstance(condition, Greater):
        return f'Le paramètre {parameter.id} est supérieur à {condition.target}'
    if isinstance(condition, Littler):
        return f'Le paramètre {parameter.id} est inférieur à {condition.target}'
    if isinstance(condition, Range):
        return f'Le paramètre {parameter.id} est entre {condition.left} et {condition.right}'
    raise NotImplementedError(f'stringifying condition {type(condition)} is not implemented yet.')


def _generate_reason_active(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, AndCondition):
        str_ = [condition_to_str(subcondition) for subcondition in condition.conditions]
        return 'Les conditions d\'application suivantes sont respectées: ' + ', '.join(str_)
    if isinstance(condition, OrCondition):
        fulfilled_conditions = [
            condition_to_str(subcondition)
            for subcondition in condition.conditions
            if _is_satisfied(subcondition, parameter_values)
        ]
        if len(fulfilled_conditions) == 1:
            return f'La condition d\'application suivante est respectée: {fulfilled_conditions[0]}'
        return 'Les conditions d\'application suivantes sont respectées: ' + ', '.join(fulfilled_conditions)
    return _generate_reason_active_leaf(condition)


def _generate_reason_inactive_leaf(condition: LeafCondition) -> str:
    parameter = condition.parameter
    if isinstance(condition, Equal):
        return f'Le paramètre {parameter.id} n\'est pas égal à {condition.target}'
    if isinstance(condition, Greater):
        return f'Le paramètre {parameter.id} est inférieur à {condition.target}'
    if isinstance(condition, Littler):
        return f'Le paramètre {parameter.id} est supérieur à {condition.target}'
    if isinstance(condition, Range):
        return f'Le paramètre {parameter.id} n\'est pas entre {condition.left} et {condition.right}'
    raise NotImplementedError(f'stringifying condition {type(condition)} is not implemented yet.')


def _generate_reason_inactive(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, AndCondition):
        unfulfilled_conditions = [
            condition_to_str(subcondition)
            for subcondition in condition.conditions
            if not _is_satisfied(subcondition, parameter_values)
        ]
        if len(unfulfilled_conditions) == 1:
            return f'La condition d\'application suivante n\'est respectée: {unfulfilled_conditions[0]}'
        return 'Les conditions d\'application suivantes ne sont pas respectées: ' + ', '.join(unfulfilled_conditions)
    if isinstance(condition, OrCondition):
        str_ = [condition_to_str(subcondition) for subcondition in condition.conditions]
        if len(str_) == 1:
            return f'La condition d\'application suivante n\'est respectée: {str_[0]}'
        return 'Aucune des conditions d\'application suivantes ne sont pas respectées: ' + ', '.join(str_)
    return _generate_reason_inactive_leaf(condition)


def lower_first_letter(str_: str) -> str:
    return str_[0].lower() + str_[1:]


def _merge_applicabilities(applicabilities: List[Applicability]) -> Applicability:
    for applicability in applicabilities:
        if not applicability.active:
            if applicability.reason_inactive is None:
                raise ValueError('reason_inactive must be defined when inactive.')
            return Applicability(False, reason_inactive=applicability.reason_inactive)
    warnings = [warn for app in applicabilities for warn in app.warnings]
    return Applicability(True, None, False, warnings=warnings)


def _build_alternative_text(
    text: StructuredText, alternative_section: AlternativeSection, parameter_values: Dict[Parameter, Any]
) -> StructuredText:
    new_text = deepcopy(text)
    new_text.title = alternative_section.new_text.title
    new_text.sections = alternative_section.new_text.sections
    new_text.outer_alineas = alternative_section.new_text.outer_alineas
    new_text.applicability = Applicability(
        True,
        None,
        True,
        alternative_section.description or _generate_reason_active(alternative_section.condition, parameter_values),
    )
    return new_text


def _compute_undefined_parameters_default_warnings(
    condition: Condition, parameter_values: Dict[Parameter, Any]
) -> List[str]:
    all_parameters = _extract_parameters_from_condition(condition)
    undefined_parameters = {parameter for parameter in all_parameters if parameter not in parameter_values}
    return [f'Le paramètre {parameter} n\'est pas défini' for parameter in undefined_parameters]


def _compute_sentence_end(parameter: Parameter) -> str:
    if parameter == ParameterEnum.DATE_INSTALLATION.value:
        return 'à la valeur de la date d\'installation'
    if parameter == ParameterEnum.REGIME.value:
        return 'au régime auquel est soumis l\'installation'
    return f'à la valeur du paramètre {parameter.id}'


def _compute_undefined_parameters_warnings_leaf(
    condition: LeafCondition, parameter_values: Dict[Parameter, Any], for_applicability: bool
) -> List[str]:
    if condition.parameter not in parameter_values:
        if for_applicability:
            return [f'L\'applicabilité de ce paragraphe est conditionnée {_compute_sentence_end(condition.parameter)}.']

        return [
            f'Ce paragraphe peut être modifié. Cette modification est '
            f'conditionnée {_compute_sentence_end(condition.parameter)}.'
        ]
    return []


def _compute_undefined_parameters_warnings(
    condition: Condition, parameter_values: Dict[Parameter, Any], for_applicability: bool
) -> List[str]:
    if isinstance(condition, (Range, Equal, Greater, Littler)):
        return _compute_undefined_parameters_warnings_leaf(condition, parameter_values, for_applicability)
    return _compute_undefined_parameters_default_warnings(condition, parameter_values)


def _has_undefined_parameters(condition: Condition, parameter_values: Dict[Parameter, Any]) -> bool:
    parameters = _extract_parameters_from_condition(condition)
    for parameter in parameters:
        if parameter not in parameter_values:
            return True
    return False


def _compute_warnings(
    conditionned_element: Union[AlternativeSection, NonApplicationCondition], parameter_values: Dict[Parameter, Any]
) -> List[str]:
    warnings: List[str] = []
    if _has_undefined_parameters(conditionned_element.condition, parameter_values):
        if conditionned_element.description:
            warnings.append(conditionned_element.description)
        else:
            warnings.extend(
                _compute_undefined_parameters_warnings(conditionned_element.condition, parameter_values, False)
            )
    return warnings


def _keep_satisfied_conditions(
    non_application_conditions: List[NonApplicationCondition], parameter_values: Dict[Parameter, Any]
) -> Tuple[List[NonApplicationCondition], List[str]]:
    satisfied: List[NonApplicationCondition] = []
    warnings: List[str] = []
    for na_condition in non_application_conditions:
        if _is_satisfied(na_condition.condition, parameter_values):
            satisfied.append(na_condition)
        else:
            warnings = _compute_warnings(na_condition, parameter_values)
    return satisfied, warnings


def _keep_satisfied_mofications(
    alternative_sections: List[AlternativeSection], parameter_values: Dict[Parameter, Any]
) -> Tuple[List[AlternativeSection], List[str]]:
    satisfied: List[AlternativeSection] = []
    warnings: List[str] = []
    for alt in alternative_sections:
        if _is_satisfied(alt.condition, parameter_values):
            satisfied.append(alt)
        else:
            warnings = _compute_warnings(alt, parameter_values)
    return satisfied, warnings


def _deactivate_child_section(section: StructuredText) -> StructuredText:
    section = copy(section)
    section.sections = [_deactivate_child_section(sec) for sec in section.sections]
    section.applicability = Applicability(False, None)
    return section


def _build_filtered_text(
    text: StructuredText, non_applicability_condition: NonApplicationCondition, parameter_values: Dict[Parameter, Any]
) -> StructuredText:
    text = copy(text)
    description = non_applicability_condition.description or _generate_reason_inactive(
        non_applicability_condition.condition, parameter_values
    )
    if non_applicability_condition.targeted_entity.outer_alinea_indices:
        alineas_to_delete = set(non_applicability_condition.targeted_entity.outer_alinea_indices)
        text.outer_alineas = [al for i, al in enumerate(text.outer_alineas) if i not in alineas_to_delete]
        modification_description = f'{description} ({len(alineas_to_delete)} alineas ne s\'appliquent pas.)'
        text.applicability = Applicability(True, None, True, modification_description)
        return text

    text.applicability = Applicability(False, description)
    text.sections = [_deactivate_child_section(section) for section in text.sections]
    return text


def _apply_satisfied_modificators(
    text: StructuredText,
    non_applicable_conditions: List[NonApplicationCondition],
    alternative_sections: List[AlternativeSection],
    parameter_values: Dict[Parameter, Any],
) -> StructuredText:
    if non_applicable_conditions and alternative_sections:
        raise NotImplementedError(
            f'Cannot apply conditions and alternative sections on one section. (Section title: {text.title.text})\n'
            f'Non applicable condition: {non_applicable_conditions[0].condition}\n'
            f'Modification condition: {alternative_sections[0].condition}\n'
        )
    if alternative_sections:
        if len(alternative_sections) > 1:
            raise ValueError(
                f'Cannot handle more than 1 applicable modification on one section. '
                f'Here, {len(alternative_sections)} are applicable.'
            )
        return _build_alternative_text(text, alternative_sections[0], parameter_values)
    if non_applicable_conditions:
        if len(non_applicable_conditions) > 1:
            raise ValueError(
                f'Cannot handle more than 1 non-applicability conditions on one section. '
                f'Here, {len(non_applicable_conditions)} conditions are applicable.'
            )
        return _build_filtered_text(text, non_applicable_conditions[0], parameter_values)
    return text


def _apply_parameter_values_in_text(
    text: StructuredText, parametrization: Parametrization, parameter_values: Dict[Parameter, Any], path: Ints
) -> StructuredText:
    na_conditions, warnings_1 = _keep_satisfied_conditions(
        parametrization.path_to_conditions.get(path) or [], parameter_values
    )
    alternative_sections, warnings_2 = _keep_satisfied_mofications(
        parametrization.path_to_alternative_sections.get(path) or [], parameter_values
    )
    text = copy(text)
    if not na_conditions and not alternative_sections:
        text.sections = [
            _apply_parameter_values_in_text(section, parametrization, parameter_values, path + (i,))
            for i, section in enumerate(text.sections)
        ]
        text.applicability = Applicability(True)
    else:
        text = _apply_satisfied_modificators(text, na_conditions, alternative_sections, parameter_values)

    text.applicability.warnings.extend(warnings_1 + warnings_2)
    return text


def _compute_whole_text_applicability(
    application_conditions: List[NonApplicationCondition], parameter_values: Dict[Parameter, Any]
) -> Applicability:
    na_conditions, warnings = _keep_satisfied_conditions(application_conditions, parameter_values)
    if len(na_conditions) > 1:
        raise ValueError(
            f'Cannot handle more than 1 non-applicability conditions on one section. '
            f'Here, {len(na_conditions)} conditions are applicable.'
        )
    if not na_conditions:
        return Applicability(True, warnings=warnings)
    if application_conditions[0].targeted_entity.outer_alinea_indices:
        raise ValueError('Can only deactivate the whole AM, not particular alineas.')
    description = na_conditions[0].description or _generate_reason_inactive(
        na_conditions[0].condition, parameter_values
    )
    return Applicability(False, description)


def _date_to_str(date: datetime) -> str:
    return date.strftime('%Y-%m-%d')


def _extract_installation_date_criterion(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> Optional[DateCriterion]:
    targets = _extract_sorted_targets(
        _extract_conditions_from_parametrization(ParameterEnum.DATE_INSTALLATION.value, parametrization), True
    )
    if not targets or ParameterEnum.DATE_INSTALLATION.value not in parameter_values:
        return None
    value = parameter_values[ParameterEnum.DATE_INSTALLATION.value]
    if value < targets[0]:
        return DateCriterion(None, _date_to_str(targets[0]))
    for date_before, date_after in zip(targets, targets[1:]):
        if value < date_after:
            return DateCriterion(_date_to_str(date_before), _date_to_str(date_after))
    return DateCriterion(_date_to_str(targets[-1]), None)


def _date_not_in_parametrization(parametrization: Parametrization) -> bool:
    return len(_extract_conditions_from_parametrization(ParameterEnum.DATE_INSTALLATION.value, parametrization)) == 0


def _apply_parameter_values_to_am(
    am: ArreteMinisteriel, parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> ArreteMinisteriel:
    am = copy(am)
    am.unique_version = _date_not_in_parametrization(parametrization)
    am.installation_date_criterion = _extract_installation_date_criterion(parametrization, parameter_values)
    am.sections = [
        _apply_parameter_values_in_text(section, parametrization, parameter_values, (i,))
        for i, section in enumerate(am.sections)
    ]
    am.applicability = _compute_whole_text_applicability(
        parametrization.path_to_conditions.get(tuple()) or [], parameter_values
    )
    return am


def _extract_leaf_conditions(condition: Condition, parameter: Parameter) -> List[Condition]:
    if isinstance(condition, (OrCondition, AndCondition)):
        return [
            cond for search_cond in condition.conditions for cond in _extract_leaf_conditions(search_cond, parameter)
        ]
    if condition.parameter.id == parameter.id:
        return [condition]
    return []


def _extract_conditions_from_parametrization(parameter: Parameter, parametrization: Parametrization) -> List[Condition]:
    return [
        cond
        for app in parametrization.application_conditions
        for cond in _extract_leaf_conditions(app.condition, parameter)
    ]


def _generate_combinations(
    options_dicts: List[Dict[str, Tuple[Parameter, Any]]]
) -> Dict[Tuple[str, ...], Dict[Parameter, Any]]:
    if len(options_dicts) == 0:
        raise ValueError('Cannot combine zero options dicts')
    if len(options_dicts) == 1:
        return {(str_,): {param: target} for str_, (param, target) in options_dicts[0].items()}
    rec_combinations = _generate_combinations(options_dicts[1:])
    return {
        name + (new_name,): {**combination, new_combination[0]: new_combination[1]}
        for new_name, new_combination in options_dicts[0].items()
        for name, combination in rec_combinations.items()
    }


def _change_value(value: Any) -> Any:
    if isinstance(value, bool):
        return not value
    if isinstance(value, (float, int)):
        return value + 1
    if isinstance(value, datetime):
        return value + timedelta(days=1)
    raise NotImplementedError(f'Cannot generate changed value for type {type(value)}')


def _check_condition_is_right_strict(condition: Condition) -> None:
    if isinstance(condition, Range):
        assert not condition.left_strict
        assert condition.right_strict
    elif isinstance(condition, Littler):
        assert condition.strict
    elif isinstance(condition, Greater):
        assert not condition.strict
    else:
        raise ValueError(f'Unexpected type {type(condition)}')


def _extract_sorted_targets(conditions: List[Condition], right_strict: bool) -> List[Any]:
    targets: List[Any] = []
    for condition in conditions:
        if not isinstance(condition, (Littler, Greater, Range)):
            raise ValueError(f'Excepting types (Littler, Greater, Range), received {type(condition)}')
        if right_strict:
            _check_condition_is_right_strict(condition)
        if isinstance(condition, (Littler, Greater)):
            targets.append(condition.target)
        else:
            targets.extend([condition.left, condition.right])
    return list(sorted(list(set(targets))))


def _mean(a: Any, b: Any):
    if isinstance(a, datetime) and isinstance(b, datetime):
        return datetime.fromtimestamp((a.timestamp() + b.timestamp()) / 2)
    return (a + b) / 2


def _extract_interval_midpoints(interval_sides: List[Any]) -> List[Any]:
    left = (interval_sides[0] - timedelta(1)) if isinstance(interval_sides[0], datetime) else (interval_sides[0] - 1)
    right = (
        (interval_sides[-1] + timedelta(1)) if isinstance(interval_sides[-1], datetime) else (interval_sides[-1] + 1)
    )
    midpoints = [_mean(a, b) for a, b in zip(interval_sides[1:], interval_sides[:-1])]
    return [left] + midpoints + [right]


def _generate_equal_option_dicts(conditions: List[Condition]) -> Dict[str, Tuple[Parameter, Any]]:
    condition = conditions[0]
    assert isinstance(condition, Equal)
    targets = list({cd.target for cd in conditions if isinstance(cd, Equal)})
    if len(targets) == 1:
        return {
            f'{condition.parameter.id} == {condition.target}': (condition.parameter, condition.target),
            f'{condition.parameter.id} != {condition.target}': (condition.parameter, _change_value(condition.target)),
        }
    if condition.parameter.type == ParameterType.REGIME:
        return {
            f'{condition.parameter.id} == {regime.value}': (condition.parameter, regime)
            for regime in (Regime.A, Regime.E, Regime.D, Regime.NC)
        }

    raise NotImplementedError(
        f'Can only generate options dict for type Equal with one target. Received {len(targets)} targets: {targets}'
    )


def _compute_parameter_names(targets: List[Any], parameter: Parameter) -> List[str]:
    if parameter.type == ParameterType.DATE:
        strs = [str(target.strftime('%Y-%m-%d')) for target in targets]
    else:
        strs = [str(target) for target in targets]
    left_name = f'{parameter.id} < {strs[0]}'
    mid_names = [f'{l_str} <= {parameter.id} < {r_str}' for l_str, r_str in zip(strs, strs[1:])]
    right_name = f'{parameter.id} >= {strs[-1]}'
    return [left_name] + mid_names + [right_name]


def _generate_options_dict(conditions: List[Condition]) -> Dict[str, Tuple[Parameter, Any]]:
    types = {condition.type for condition in conditions}
    if types == {ConditionType.EQUAL}:
        return _generate_equal_option_dicts(conditions)
    if ConditionType.EQUAL not in types:
        targets = _extract_sorted_targets(conditions, True)
        values = _extract_interval_midpoints(targets)
        condition = conditions[0]
        assert isinstance(condition, (Range, Greater, Littler))
        parameter = condition.parameter
        param_names = _compute_parameter_names(targets, parameter)
        return {param_name: (parameter, value) for param_name, value in zip(param_names, values)}
    raise NotImplementedError(f'Option dict generation not implemented for conditions with types {types}')


OptionsDict = Dict[str, Tuple[Parameter, Any]]


def _generate_options_dicts(parametrization: Parametrization) -> List[OptionsDict]:
    parameters = _extract_parameters_from_parametrization(parametrization)
    options_dicts = []
    for parameter in parameters:
        conditions = _extract_conditions_from_parametrization(parameter, parametrization)
        options_dicts.append(_generate_options_dict(conditions))
    return options_dicts


def _generate_exhaustive_combinations(parametrization: Parametrization) -> Combinations:
    options_dicts = _generate_options_dicts(parametrization)
    if not options_dicts:
        return {}
    combinations = _generate_combinations(options_dicts)
    if () not in combinations:  # for undefined parameters warnings
        combinations[()] = {}
    return combinations


def generate_all_am_versions(
    am: ArreteMinisteriel, parametrization: Parametrization, combinations: Optional[Combinations] = None
) -> Dict[Tuple[str, ...], ArreteMinisteriel]:
    if combinations is None:
        combinations = _generate_exhaustive_combinations(parametrization)
    if not combinations:
        return {tuple(): replace(am, unique_version=True)}
    return {
        combination_name: _apply_parameter_values_to_am(am, parametrization, parameter_values)
        for combination_name, parameter_values in combinations.items()
    }
