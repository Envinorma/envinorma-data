from copy import copy
from dataclasses import dataclass, replace
from typing import Any, Dict, List, Optional, Tuple, Union

from envinorma.models import ArreteMinisteriel, Regime
from envinorma.models.arrete_ministeriel import AMApplicability
from envinorma.models.condition import AndCondition, Condition, Greater, Littler, OrCondition, Range
from envinorma.models.parameter import Parameter, ParameterEnum
from envinorma.models.structured_text import (
    Applicability,
    PotentialInapplicability,
    PotentialModification,
    SectionParametrization,
    StructuredText,
)

from .models.parametrization import Parametrization
from .natural_language_warnings import (
    generate_inactive_warning,
    generate_modification_warning,
    generate_warning_missing_value,
)
from .tie_parametrization import add_parametrization


def _build_alternative_text(
    text: StructuredText, modification: PotentialModification, parameter_values: Dict[Parameter, Any]
) -> StructuredText:
    new_text = copy(modification.new_version)
    new_text.applicability = Applicability(
        modified=True,
        warnings=[generate_modification_warning(modification.condition, parameter_values)],
        previous_version=text,
    )
    return new_text


def _has_undefined_parameters(condition: Condition, parameter_values: Dict[Parameter, Any]) -> bool:
    for parameter in condition.parameters():
        if parameter not in parameter_values:
            return True
    return False


_SectionParameter = Union[PotentialInapplicability, PotentialModification]


def _compute_warnings(
    parameter: _SectionParameter, parameter_values: Dict[Parameter, Any], whole_text: bool
) -> List[str]:
    if _has_undefined_parameters(parameter.condition, parameter_values):
        modification = isinstance(parameter, PotentialModification)
        alineas = None if isinstance(parameter, PotentialModification) else parameter.alineas
        return [
            generate_warning_missing_value(parameter.condition, parameter_values, alineas, modification, whole_text)
        ]
    return []


def _keep_satisfied_conditions(
    inapplicable_sections: List[PotentialInapplicability], parameter_values: Dict[Parameter, Any], whole_text: bool
) -> Tuple[List[PotentialInapplicability], List[str]]:
    satisfied: List[PotentialInapplicability] = []
    warnings: List[str] = []
    for inapplicable_section in inapplicable_sections:
        if inapplicable_section.condition.is_satisfied(parameter_values):
            satisfied.append(inapplicable_section)
        else:
            warnings = _compute_warnings(inapplicable_section, parameter_values, whole_text)
    return satisfied, warnings


def _keep_satisfied_mofications(
    alternative_sections: List[PotentialModification], parameter_values: Dict[Parameter, Any]
) -> Tuple[List[PotentialModification], List[str]]:
    satisfied: List[PotentialModification] = []
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
    section.outer_alineas = [replace(al, inactive=True) for al in section.outer_alineas]
    return section


def _deactivate_alineas(
    text: StructuredText, inapplicability: PotentialInapplicability, parameter_values: Dict[Parameter, Any]
) -> StructuredText:
    text = copy(text)
    inactive_alineas = inapplicability.alineas
    all_inactive = inactive_alineas is None
    warning = generate_inactive_warning(
        inapplicability.condition, parameter_values, all_alineas=all_inactive, whole_text=False
    )
    if inactive_alineas is not None:
        inactive_alineas_set = set(inactive_alineas)
        new_outer_alineas = [replace(al, inactive=i in inactive_alineas_set) for i, al in enumerate(text.outer_alineas)]
    else:
        new_outer_alineas = [replace(al, inactive=True) for al in text.outer_alineas]
    text.applicability = Applicability(active=not all_inactive, warnings=[warning])
    if inapplicability.subsections_are_inapplicable:
        text.sections = [_deactivate_child_section(section, all_inactive=all_inactive) for section in text.sections]
    text.outer_alineas = new_outer_alineas
    return text


def _apply_satisfied_modificators(
    text: StructuredText,
    inapplicabilities: List[PotentialInapplicability],
    modifications: List[PotentialModification],
    parameter_values: Dict[Parameter, Any],
) -> StructuredText:
    if inapplicabilities and modifications:
        raise NotImplementedError(
            f'Cannot handle inapplicability and modification on one section. (Section title: {text.title.text})\n'
            f'Inapplicability condition: {inapplicabilities[0].condition}\n'
            f'Modification condition: {modifications[0].condition}\n'
        )
    if modifications:
        if len(modifications) > 1:
            raise ValueError(
                f'Cannot handle more than 1 applicable modification on one section. '
                f'Here, {len(modifications)} are applicable.'
            )
        return _build_alternative_text(text, modifications[0], parameter_values)
    if inapplicabilities:
        if len(inapplicabilities) > 1:
            raise ValueError(
                f'Cannot handle more than 1 non-applicability conditions on one section. '
                f'Here, {len(inapplicabilities)} conditions are applicable.'
                f'\n{parameter_values}\n{text}'
            )
        return _deactivate_alineas(text, inapplicabilities[0], parameter_values)
    return text


def _ensure_applicabiliy(candidate: Any) -> Applicability:
    if not isinstance(candidate, Applicability):
        raise ValueError(f'Unexpected type {type(candidate)}')
    return candidate


def _extract_satisfied_objects_and_warnings(
    parametrization: SectionParametrization, parameter_values: Dict[Parameter, Any]
) -> Tuple[List[PotentialInapplicability], List[PotentialModification], List[str]]:
    na_conditions, warnings_1 = _keep_satisfied_conditions(
        parametrization.potential_inapplicabilities, parameter_values, whole_text=False
    )
    alternative_sections, warnings_2 = _keep_satisfied_mofications(
        parametrization.potential_modifications, parameter_values
    )
    all_warnings = warnings_1 + warnings_2 + parametrization.warnings
    return na_conditions, alternative_sections, sorted(all_warnings)


def _apply_parameter_values_in_text(text: StructuredText, parameter_values: Dict[Parameter, Any]) -> StructuredText:
    na_conditions, modifications, warnings = _extract_satisfied_objects_and_warnings(
        text.parametrization, parameter_values
    )
    text = copy(text)
    if not na_conditions and not modifications:
        text.sections = [_apply_parameter_values_in_text(section, parameter_values) for section in text.sections]
        text.applicability = Applicability()
    else:
        text = _apply_satisfied_modificators(text, na_conditions, modifications, parameter_values)

    all_warnings = sorted(set(_ensure_applicabiliy(text.applicability).warnings + warnings))
    text.applicability = replace(_ensure_applicabiliy(text.applicability), warnings=all_warnings)
    return text


def _generate_whole_text_reason_inactive(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    return generate_inactive_warning(condition, parameter_values, True, True)


def _compute_whole_text_applicability(
    applicability: AMApplicability, parameter_values: Dict[Parameter, Any]
) -> Tuple[bool, List[str]]:
    condition = applicability.condition_of_inapplicability
    if not condition:
        return True, applicability.warnings
    if condition.is_satisfied(parameter_values):
        return False, [_generate_whole_text_reason_inactive(condition, parameter_values)]
    warnings = applicability.warnings
    if _has_undefined_parameters(condition, parameter_values):
        warnings.append(generate_warning_missing_value(condition, parameter_values, None, False, True))
    return True, warnings


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


def apply_parameter_values_to_am(
    am: ArreteMinisteriel, parameter_values: Dict[Parameter, Any], parametrization: Optional[Parametrization] = None
) -> ArreteMinisteriel:
    if parametrization:
        add_parametrization(am, parametrization)
    am = copy(am)
    am.sections = [_apply_parameter_values_in_text(section, parameter_values) for section in am.sections]
    return am


@dataclass
class AMWithApplicability:
    arrete: ArreteMinisteriel
    applicable: bool
    warnings: List[str]

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AMWithApplicability':
        return cls(
            arrete=ArreteMinisteriel.from_dict(dict_['am']), applicable=dict_['applicable'], warnings=dict_['warnings']
        )

    def to_dict(self) -> Dict[str, Any]:
        return {'am': self.arrete.to_dict(), 'applicable': self.applicable, 'warnings': self.warnings}


def build_am_with_applicability(
    am: ArreteMinisteriel, parametrization: Optional[Parametrization], parameter_values: Dict[Parameter, Any]
) -> AMWithApplicability:
    if parametrization:
        add_parametrization(am, parametrization)

    applicable, warnings = _compute_whole_text_applicability(am.applicability, parameter_values)
    return AMWithApplicability(
        arrete=apply_parameter_values_to_am(am, parameter_values), applicable=applicable, warnings=warnings
    )
