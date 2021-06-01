from copy import copy
from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from envinorma.data import (
    Applicability,
    ArreteMinisteriel,
    Classement,
    DateParameterDescriptor,
    Regime,
    StructuredText,
    VersionDescriptor,
)
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
    ParameterObjectWithCondition,
    ParameterType,
    Parametrization,
    Range,
    extract_conditions_from_parametrization,
)
from envinorma.parametrization.conditions import (
    AndCondition,
    ConditionType,
    OrCondition,
    ParameterEnum,
    extract_leaf_conditions,
    extract_parameters_from_condition,
    generate_inactive_warning,
    generate_modification_warning,
    generate_warning_missing_value,
    is_satisfied,
)


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


def _extract_surrounding_dates(target_date: date, limit_dates: List[date]) -> Tuple[Optional[date], Optional[date]]:
    if not limit_dates:
        return None, None
    if target_date < limit_dates[0]:
        return (None, limit_dates[0])
    for date_before, date_after in zip(limit_dates, limit_dates[1:]):
        if target_date < date_after:
            return (date_before, date_after)
    return limit_dates[-1], None


def _is_satisfiable(condition: Condition, regime_target: Regime) -> bool:
    if isinstance(condition, AndCondition):
        return all([_is_satisfiable(cd, regime_target) for cd in condition.conditions])
    if isinstance(condition, OrCondition):
        return any([_is_satisfiable(cd, regime_target) for cd in condition.conditions])
    if condition.parameter != ParameterEnum.REGIME.value:
        return True
    if isinstance(condition, (Range, Littler, Greater)):
        raise ValueError('Cannot have Range, Littler or Greater condition for Regime parameter.')
    return regime_target == condition.target


def _keep_satisfiable(conditions: List[Condition], regime_target: Regime) -> List[Condition]:
    if not isinstance(regime_target, Regime):
        raise ValueError(f'regime_target must be an instance of Regime, not {type(regime_target)}')
    return [condition for condition in conditions if _is_satisfiable(condition, regime_target)]


def _convert_to_date(element: Any) -> date:
    if isinstance(element, datetime):
        return element.date()
    if isinstance(element, date):
        return element
    raise ValueError(f'Expection date or datetime, got {type(element)}')


def _convert_to_dates(elements: List[Any]) -> List[date]:
    return [_convert_to_date(el) for el in elements]


def _used_date_parameter(
    searched_date_parameter: Parameter, parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> DateParameterDescriptor:
    conditions = parametrization.extract_conditions()
    if ParameterEnum.REGIME.value in parameter_values:
        conditions = _keep_satisfiable(conditions, parameter_values[ParameterEnum.REGIME.value])
    leaf_conditions = [leaf for cd in conditions for leaf in extract_leaf_conditions(cd, searched_date_parameter)]
    if not leaf_conditions:
        return DateParameterDescriptor(False)
    if searched_date_parameter not in parameter_values:
        return DateParameterDescriptor(True, False)
    value = _convert_to_date(parameter_values[searched_date_parameter])
    limit_dates = _convert_to_dates(_extract_sorted_targets(leaf_conditions, True))
    date_left, date_right = _extract_surrounding_dates(value, limit_dates)
    return DateParameterDescriptor(True, True, date_left, date_right)


def _installation_date_parameter(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> DateParameterDescriptor:
    return _used_date_parameter(ParameterEnum.DATE_INSTALLATION.value, parametrization, parameter_values)


_AED_PARAMETERS = {
    ParameterEnum.DATE_AUTORISATION.value,
    ParameterEnum.DATE_ENREGISTREMENT.value,
    ParameterEnum.DATE_DECLARATION.value,
}


def _find_used_date(parametrization: Parametrization) -> Parameter:
    used_date_parameters = extract_parameters_from_parametrization(parametrization).intersection(_AED_PARAMETERS)
    if not used_date_parameters:
        return ParameterEnum.DATE_DECLARATION.value
    if len(used_date_parameters) == 1:
        return used_date_parameters.pop()
    raise ValueError(f'Cannot handle several AED dates in the same parametrization, got {used_date_parameters}.')


def _aed_date_parameter(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> DateParameterDescriptor:
    used_date = _find_used_date(parametrization)
    return _used_date_parameter(used_date, parametrization, parameter_values)


def _date_parameters(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> Tuple[DateParameterDescriptor, DateParameterDescriptor]:
    return (
        _aed_date_parameter(parametrization, parameter_values),
        _installation_date_parameter(parametrization, parameter_values),
    )


def _compute_am_version_descriptor(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> VersionDescriptor:
    am_applicable, am_applicability_warnings = _compute_whole_text_applicability(
        parametrization.path_to_conditions.get(tuple()) or [],
        parameter_values,
        parametrization.path_to_warnings.get(tuple()) or [],
    )
    date_parameters = _date_parameters(parametrization, parameter_values)
    return VersionDescriptor(am_applicable, am_applicability_warnings, *date_parameters)


def apply_parameter_values_to_am(
    am: ArreteMinisteriel, parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> ArreteMinisteriel:
    am = copy(am)
    am.sections = [
        _apply_parameter_values_in_text(section, parametrization, parameter_values, (i,))
        for i, section in enumerate(am.sections)
    ]
    am.version_descriptor = _compute_am_version_descriptor(parametrization, parameter_values)
    return am


_Options = Tuple[Parameter, List[Tuple[str, Any]]]


def _generate_combinations(all_options: List[_Options], add_unknown_target: bool) -> Combinations:
    if len(all_options) == 0:
        return {(): {}}
    rec_combinations = _generate_combinations(all_options[1:], add_unknown_target)
    parameter, options = all_options[0]
    result = {
        (name,) + name_rec: {parameter: target, **combination_rec}
        for name, target in options
        for name_rec, combination_rec in rec_combinations.items()
    }
    if add_unknown_target:
        result = {**result, **rec_combinations}
    return result


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
    if isinstance(a, date) and isinstance(b, date):
        return date.fromordinal((a.toordinal() + b.toordinal()) // 2)
    return (a + b) / 2


def _is_date(candidate: Any) -> bool:
    return isinstance(candidate, (date, datetime))


def _extract_interval_midpoints(interval_sides: List[Any]) -> List[Any]:
    left = (interval_sides[0] - timedelta(1)) if _is_date(interval_sides[0]) else (interval_sides[0] - 1)
    right = (interval_sides[-1] + timedelta(1)) if _is_date(interval_sides[-1]) else (interval_sides[-1] + 1)
    midpoints = [_mean(a, b) for a, b in zip(interval_sides[1:], interval_sides[:-1])]
    return [left] + midpoints + [right]


def _generate_equal_option_dicts(conditions: Union[List[Condition], List[LeafCondition]]) -> List[Tuple[str, Any]]:
    condition = conditions[0]
    assert isinstance(condition, Equal)
    targets = list({cd.target for cd in conditions if isinstance(cd, Equal)})
    parameter = condition.parameter
    if len(targets) == 1:
        return [
            (f'{parameter.id} == {condition.target}', condition.target),
            (f'{parameter.id} != {condition.target}', _change_value(condition.target)),
        ]
    if parameter.type == ParameterType.REGIME:
        return [(f'{parameter.id} == {regime.value}', regime) for regime in (Regime.A, Regime.E, Regime.D, Regime.NC)]
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


def _generate_options_dict(conditions: Union[List[Condition], List[LeafCondition]]) -> List[Tuple[str, Any]]:
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
        return [(param_name, value) for param_name, value in zip(param_names, values)]
    raise NotImplementedError(f'Option dict generation not implemented for conditions with types {types}')


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


def _keep_aed_parameter(parameters: Set[Parameter], am_regime: Optional[Regime]) -> Optional[Parameter]:
    aed_parameters = _AED_PARAMETERS.intersection(parameters)
    if len(aed_parameters) == 0:
        return None
    if len(aed_parameters) == 1:
        return list(aed_parameters)[0]
    if not am_regime:
        raise ValueError('Cannot extract AED date parameter without a known regime')
    if am_regime == Regime.A:
        candidate = ParameterEnum.DATE_AUTORISATION.value
    elif am_regime == Regime.E:
        candidate = ParameterEnum.DATE_ENREGISTREMENT.value
    elif am_regime in {Regime.D, Regime.DC}:
        candidate = ParameterEnum.DATE_DECLARATION.value
    else:
        return None
    return candidate if candidate in parameters else None


def _keep_relevant_date_parameters(parameters: Set[Parameter], am_regime: Optional[Regime]) -> Set[Parameter]:
    result = {ParameterEnum.DATE_INSTALLATION.value}.intersection(parameters)
    aed_parameter = _keep_aed_parameter(parameters, am_regime)
    if aed_parameter:
        result.add(aed_parameter)
    return result


def _generate_options_dicts(
    parametrization: Parametrization, date_only: bool, am_regime: Optional[Regime]
) -> List[_Options]:
    parameters = extract_parameters_from_parametrization(parametrization)
    if date_only:
        parameters = _keep_relevant_date_parameters(parameters, am_regime)
    options_dicts: List[_Options] = []
    for parameter in parameters:
        conditions = extract_conditions_from_parametrization(parameter, parametrization)
        options_dicts.append((parameter, _generate_options_dict(conditions)))
    return options_dicts


def _generate_exhaustive_combinations(
    parametrization: Parametrization, date_only: bool, am_regime: Optional[Regime]
) -> Combinations:
    options_dicts = _generate_options_dicts(parametrization, date_only, am_regime)
    if not options_dicts:
        return {}
    combinations = _generate_combinations(options_dicts, True)
    return combinations


def _extract_am_regime(classements: List[Classement]) -> Optional[Regime]:
    regimes: Set[Regime] = {classement.regime for classement in classements}
    if len(regimes) != 1:
        return None
    return list(regimes)[0]


def generate_all_am_versions(
    am: ArreteMinisteriel,
    parametrization: Parametrization,
    date_only: bool,
    combinations: Optional[Combinations] = None,
) -> Dict[Tuple[str, ...], ArreteMinisteriel]:
    if combinations is None:
        combinations = _generate_exhaustive_combinations(parametrization, date_only, _extract_am_regime(am.classements))
    if not combinations:
        combinations = {(): {}}
    return {
        combination_name: apply_parameter_values_to_am(am, parametrization, parameter_values)
        for combination_name, parameter_values in combinations.items()
    }
