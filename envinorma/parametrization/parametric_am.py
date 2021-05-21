from copy import copy
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from envinorma.data import Applicability, ArreteMinisteriel, DateCriterion, Regime, StructuredText
from envinorma.parametrization import (
    AlternativeSection,
    AMWarning,
    Combinations,
    Condition,
    Equal,
    Greater,
    Ints,
    LeafCondition,
    Littler,
    NonApplicationCondition,
    Parameter,
    ParameterEnum,
    ParameterObjectWithCondition,
    ParameterType,
    Parametrization,
    Range,
    extract_conditions_from_parametrization,
)
from envinorma.parametrization.conditions import (
    ConditionType,
    extract_parameters_from_condition,
    generate_inactive_warning,
    generate_modification_warning,
    generate_warning_missing_value,
    is_satisfied,
)
from envinorma.utils import date_to_str


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


def lower_first_letter(str_: str) -> str:
    return str_[0].lower() + str_[1:]


def _build_alternative_text(
    text: StructuredText, alternative_section: AlternativeSection, parameter_values: Dict[Parameter, Any]
) -> StructuredText:
    new_text = copy(alternative_section.new_text)
    new_text.applicability = Applicability(
        modified=True,
        warnings=[generate_modification_warning(alternative_section.condition, parameter_values)],
        previous_version=text,
    )
    return new_text


def _has_undefined_parameters(condition: Condition, parameter_values: Dict[Parameter, Any]) -> bool:
    parameters = extract_parameters_from_condition(condition)
    for parameter in parameters:
        if parameter not in parameter_values:
            return True
    return False


def _compute_warnings(
    parameter: ParameterObjectWithCondition, parameter_values: Dict[Parameter, Any], whole_text: bool
) -> List[str]:
    if _has_undefined_parameters(parameter.condition, parameter_values):
        modification = isinstance(parameter, AlternativeSection)
        alineas = None if isinstance(parameter, AlternativeSection) else parameter.targeted_entity.outer_alinea_indices
        return [
            generate_warning_missing_value(parameter.condition, parameter_values, alineas, modification, whole_text)
        ]
    return []


def _keep_satisfied_conditions(
    non_application_conditions: List[NonApplicationCondition], parameter_values: Dict[Parameter, Any], whole_text: bool
) -> Tuple[List[NonApplicationCondition], List[str]]:
    satisfied: List[NonApplicationCondition] = []
    warnings: List[str] = []
    for na_condition in non_application_conditions:
        if is_satisfied(na_condition.condition, parameter_values):
            satisfied.append(na_condition)
        else:
            warnings = _compute_warnings(na_condition, parameter_values, whole_text)
    return satisfied, warnings


def _keep_satisfied_mofications(
    alternative_sections: List[AlternativeSection], parameter_values: Dict[Parameter, Any]
) -> Tuple[List[AlternativeSection], List[str]]:
    satisfied: List[AlternativeSection] = []
    warnings: List[str] = []
    for alt in alternative_sections:
        if is_satisfied(alt.condition, parameter_values):
            satisfied.append(alt)
        else:
            warnings = _compute_warnings(alt, parameter_values, False)
    return satisfied, warnings


def _deactivate_child_section(section: StructuredText, all_inactive: bool) -> StructuredText:
    section = copy(section)
    if section.applicability:
        section.applicability.active = not all_inactive
    else:
        section.applicability = Applicability(active=not all_inactive)
    section.sections = [_deactivate_child_section(sec, all_inactive) for sec in section.sections]
    section.outer_alineas = [replace(al, active=False) for al in section.outer_alineas]
    return section


def _deactivate_alineas(
    text: StructuredText, satisfied: NonApplicationCondition, parameter_values: Dict[Parameter, Any]
) -> StructuredText:
    text = copy(text)
    inactive_alineas = satisfied.targeted_entity.outer_alinea_indices
    all_inactive = inactive_alineas is None
    warning = generate_inactive_warning(
        satisfied.condition, parameter_values, all_alineas=all_inactive, whole_text=False
    )
    if inactive_alineas is not None:
        inactive_alineas_set = set(inactive_alineas)
        new_outer_alineas = [
            replace(al, active=i not in inactive_alineas_set) for i, al in enumerate(text.outer_alineas)
        ]
    else:
        new_outer_alineas = [replace(al, active=False) for al in text.outer_alineas]
    text.applicability = Applicability(active=not all_inactive, warnings=[warning])
    text.sections = [_deactivate_child_section(section, all_inactive=all_inactive) for section in text.sections]
    text.outer_alineas = new_outer_alineas
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
                f'\n{parameter_values}\n{text}'
            )
        return _deactivate_alineas(text, non_applicable_conditions[0], parameter_values)
    return text


def _ensure_applicabiliy(candidate: Any) -> Applicability:
    if not isinstance(candidate, Applicability):
        raise ValueError(f'Unexpected type {type(candidate)}')
    return candidate


def _extract_satisfied_objects_and_warnings(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any], path: Ints
) -> Tuple[List[NonApplicationCondition], List[AlternativeSection], List[str]]:
    na_conditions, warnings_1 = _keep_satisfied_conditions(
        parametrization.path_to_conditions.get(path) or [], parameter_values, whole_text=False
    )
    alternative_sections, warnings_2 = _keep_satisfied_mofications(
        parametrization.path_to_alternative_sections.get(path) or [], parameter_values
    )
    warnings_3 = [x.text for x in parametrization.path_to_warnings.get(path) or []]
    all_warnings = warnings_1 + warnings_2 + warnings_3
    return na_conditions, alternative_sections, all_warnings


def _apply_parameter_values_in_text(
    text: StructuredText, parametrization: Parametrization, parameter_values: Dict[Parameter, Any], path: Ints
) -> StructuredText:
    na_conditions, alternative_sections, warnings = _extract_satisfied_objects_and_warnings(
        parametrization, parameter_values, path
    )
    text = copy(text)
    if not na_conditions and not alternative_sections:
        text.sections = [
            _apply_parameter_values_in_text(section, parametrization, parameter_values, path + (i,))
            for i, section in enumerate(text.sections)
        ]
        text.applicability = Applicability()
    else:
        text = _apply_satisfied_modificators(text, na_conditions, alternative_sections, parameter_values)

    all_warnings = list(set(_ensure_applicabiliy(text.applicability).warnings + warnings))
    text.applicability = replace(_ensure_applicabiliy(text.applicability), warnings=all_warnings)
    return text


def _generate_whole_text_reason_inactive(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    return generate_inactive_warning(condition, parameter_values, True, True)


def _compute_whole_text_applicability(
    application_conditions: List[NonApplicationCondition],
    parameter_values: Dict[Parameter, Any],
    simple_warnings: List[AMWarning],
) -> Tuple[bool, List[str]]:
    na_conditions, warnings = _keep_satisfied_conditions(application_conditions, parameter_values, whole_text=True)
    if len(na_conditions) > 1:
        raise ValueError(
            f'Cannot handle more than one inapplicability on the whole text. '
            f'Here, {len(na_conditions)} inapplicability conditions are fulfilled.'
        )
    if not na_conditions:
        return True, warnings + [x.text for x in simple_warnings]
    if application_conditions[0].targeted_entity.outer_alinea_indices:
        raise ValueError('Can only deactivate the whole AM, not particular alineas.')
    description = _generate_whole_text_reason_inactive(na_conditions[0].condition, parameter_values)
    return False, [description]


def _extract_installation_date_criterion(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> Optional[DateCriterion]:
    targets = _extract_sorted_targets(
        extract_conditions_from_parametrization(ParameterEnum.DATE_INSTALLATION.value, parametrization), True
    )
    if not targets or ParameterEnum.DATE_INSTALLATION.value not in parameter_values:
        return None
    value = parameter_values[ParameterEnum.DATE_INSTALLATION.value]
    if value < targets[0]:
        return DateCriterion(None, date_to_str(targets[0]))
    for date_before, date_after in zip(targets, targets[1:]):
        if value < date_after:
            return DateCriterion(date_to_str(date_before), date_to_str(date_after))
    return DateCriterion(date_to_str(targets[-1]), None)


def _date_not_in_parametrization(parametrization: Parametrization) -> bool:
    return len(extract_conditions_from_parametrization(ParameterEnum.DATE_INSTALLATION.value, parametrization)) == 0


def apply_parameter_values_to_am(
    am: ArreteMinisteriel, parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> ArreteMinisteriel:
    am = copy(am)
    am.unique_version = _date_not_in_parametrization(parametrization)
    am.installation_date_criterion = _extract_installation_date_criterion(parametrization, parameter_values)
    am.sections = [
        _apply_parameter_values_in_text(section, parametrization, parameter_values, (i,))
        for i, section in enumerate(am.sections)
    ]
    am.active, am.applicability_warnings = _compute_whole_text_applicability(
        parametrization.path_to_conditions.get(tuple()) or [],
        parameter_values,
        parametrization.path_to_warnings.get(tuple()) or [],
    )
    return am


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


def _extract_sorted_targets(conditions: Union[List[Condition], List[LeafCondition]], right_strict: bool) -> List[Any]:
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


def _generate_equal_option_dicts(
    conditions: Union[List[Condition], List[LeafCondition]]
) -> Dict[str, Tuple[Parameter, Any]]:
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


def _generate_options_dict(conditions: Union[List[Condition], List[LeafCondition]]) -> Dict[str, Tuple[Parameter, Any]]:
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


def extract_parameters_from_parametrization(parametrization: Parametrization) -> Set[Parameter]:
    application_conditions = {
        cd
        for app_cond in parametrization.application_conditions
        for cd in extract_parameters_from_condition(app_cond.condition)
    }
    alternative_sections = {
        cd
        for alt_sec in parametrization.alternative_sections
        for cd in extract_parameters_from_condition(alt_sec.condition)
    }
    return application_conditions.union(alternative_sections)


def _generate_options_dicts(parametrization: Parametrization, date_only: bool) -> List[OptionsDict]:
    parameters = extract_parameters_from_parametrization(parametrization)
    if date_only:
        parameters = {param for param in parameters if param == ParameterEnum.DATE_INSTALLATION.value}
    options_dicts = []
    for parameter in parameters:
        conditions = extract_conditions_from_parametrization(parameter, parametrization)
        options_dicts.append(_generate_options_dict(conditions))
    return options_dicts


def _generate_exhaustive_combinations(parametrization: Parametrization, date_only: bool) -> Combinations:
    options_dicts = _generate_options_dicts(parametrization, date_only)
    if not options_dicts:
        return {}
    combinations = _generate_combinations(options_dicts)
    if () not in combinations:  # for undefined parameters warnings
        combinations[()] = {}
    return combinations


def generate_all_am_versions(
    am: ArreteMinisteriel,
    parametrization: Parametrization,
    date_only: bool,
    combinations: Optional[Combinations] = None,
) -> Dict[Tuple[str, ...], ArreteMinisteriel]:
    if combinations is None:
        combinations = _generate_exhaustive_combinations(parametrization, date_only)
    if not combinations:
        return {tuple(): replace(apply_parameter_values_to_am(am, parametrization, {}), unique_version=True)}
    return {
        combination_name: apply_parameter_values_to_am(am, parametrization, parameter_values)
        for combination_name, parameter_values in combinations.items()
    }
