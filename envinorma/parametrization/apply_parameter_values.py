from copy import copy
from dataclasses import replace
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from envinorma.models import Ints
from envinorma.models.arrete_ministeriel import ArreteMinisteriel, DateParameterDescriptor, VersionDescriptor
from envinorma.models.classement import Regime
from envinorma.models.structured_text import Applicability, StructuredText

from .models.condition import (
    AndCondition,
    Condition,
    Greater,
    Littler,
    OrCondition,
    Range,
    extract_leaf_conditions,
    extract_sorted_interval_sides_targets,
)
from .models.parameter import AED_PARAMETERS, Parameter, ParameterEnum
from .models.parametrization import (
    AlternativeSection,
    AMWarning,
    InapplicableSection,
    ParameterObjectWithCondition,
    Parametrization,
)
from .natural_language_warnings import (
    generate_inactive_warning,
    generate_modification_warning,
    generate_warning_missing_value,
)


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
    for parameter in condition.parameters():
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
    inapplicable_sections: List[InapplicableSection], parameter_values: Dict[Parameter, Any], whole_text: bool
) -> Tuple[List[InapplicableSection], List[str]]:
    satisfied: List[InapplicableSection] = []
    warnings: List[str] = []
    for inapplicable_section in inapplicable_sections:
        if inapplicable_section.condition.is_satisfied(parameter_values):
            satisfied.append(inapplicable_section)
        else:
            warnings = _compute_warnings(inapplicable_section, parameter_values, whole_text)
    return satisfied, warnings


def _keep_satisfied_mofications(
    alternative_sections: List[AlternativeSection], parameter_values: Dict[Parameter, Any]
) -> Tuple[List[AlternativeSection], List[str]]:
    satisfied: List[AlternativeSection] = []
    warnings: List[str] = []
    for alt in alternative_sections:
        if alt.condition.is_satisfied(parameter_values):
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
    text: StructuredText, satisfied: InapplicableSection, parameter_values: Dict[Parameter, Any]
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
    inapplicable_sections: List[InapplicableSection],
    alternative_sections: List[AlternativeSection],
    parameter_values: Dict[Parameter, Any],
) -> StructuredText:
    if inapplicable_sections and alternative_sections:
        raise NotImplementedError(
            f'Cannot apply conditions and alternative sections on one section. (Section title: {text.title.text})\n'
            f'Non applicable condition: {inapplicable_sections[0].condition}\n'
            f'Modification condition: {alternative_sections[0].condition}\n'
        )
    if alternative_sections:
        if len(alternative_sections) > 1:
            raise ValueError(
                f'Cannot handle more than 1 applicable modification on one section. '
                f'Here, {len(alternative_sections)} are applicable.'
            )
        return _build_alternative_text(text, alternative_sections[0], parameter_values)
    if inapplicable_sections:
        if len(inapplicable_sections) > 1:
            raise ValueError(
                f'Cannot handle more than 1 non-applicability conditions on one section. '
                f'Here, {len(inapplicable_sections)} conditions are applicable.'
                f'\n{parameter_values}\n{text}'
            )
        return _deactivate_alineas(text, inapplicable_sections[0], parameter_values)
    return text


def _ensure_applicabiliy(candidate: Any) -> Applicability:
    if not isinstance(candidate, Applicability):
        raise ValueError(f'Unexpected type {type(candidate)}')
    return candidate


def _extract_satisfied_objects_and_warnings(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any], path: Ints
) -> Tuple[List[InapplicableSection], List[AlternativeSection], List[str]]:
    na_conditions, warnings_1 = _keep_satisfied_conditions(
        parametrization.path_to_conditions.get(path) or [], parameter_values, whole_text=False
    )
    alternative_sections, warnings_2 = _keep_satisfied_mofications(
        parametrization.path_to_alternative_sections.get(path) or [], parameter_values
    )
    warnings_3 = [x.text for x in parametrization.path_to_warnings.get(path) or []]
    all_warnings = warnings_1 + warnings_2 + warnings_3
    return na_conditions, alternative_sections, sorted(all_warnings)


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

    all_warnings = sorted(list(set(_ensure_applicabiliy(text.applicability).warnings + warnings)))
    text.applicability = replace(_ensure_applicabiliy(text.applicability), warnings=all_warnings)
    return text


def _generate_whole_text_reason_inactive(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    return generate_inactive_warning(condition, parameter_values, True, True)


def _compute_whole_text_applicability(
    inapplicable_sections: List[InapplicableSection],
    parameter_values: Dict[Parameter, Any],
    simple_warnings: List[AMWarning],
) -> Tuple[bool, List[str]]:
    na_conditions, warnings = _keep_satisfied_conditions(inapplicable_sections, parameter_values, whole_text=True)
    if len(na_conditions) > 1:
        raise ValueError(
            f'Cannot handle more than one inapplicability on the whole text. '
            f'Here, {len(na_conditions)} inapplicability conditions are fulfilled.'
        )
    if not na_conditions:
        return True, warnings + [x.text for x in simple_warnings]
    if inapplicable_sections[0].targeted_entity.outer_alinea_indices:
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
        return DateParameterDescriptor(True, True)
    value = _convert_to_date(parameter_values[searched_date_parameter])
    limit_dates = _convert_to_dates(extract_sorted_interval_sides_targets(leaf_conditions, True))
    date_left, date_right = _extract_surrounding_dates(value, limit_dates)
    return DateParameterDescriptor(True, False, date_left, date_right)


def _date_de_mise_en_service_parameter(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> DateParameterDescriptor:
    return _used_date_parameter(ParameterEnum.DATE_INSTALLATION.value, parametrization, parameter_values)


def _find_used_date(parametrization: Parametrization) -> Parameter:
    used_date_parameters = parametrization.extract_parameters().intersection(AED_PARAMETERS)
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
        _date_de_mise_en_service_parameter(parametrization, parameter_values),
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
