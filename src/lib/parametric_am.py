from copy import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, KeysView, List, Optional, Set, Tuple, Union
from lib.am_structure_extraction import ArreteMinisteriel, StructuredText


class ParameterType(Enum):
    DATE = 'DATE'
    BOOLEAN = 'BOOLEAN'


@dataclass
class Parameter:
    id: str
    type: ParameterType


class ParameterEnum(Enum):
    DATE_D_AUTORISATION = Parameter('date-d-autorisation', ParameterType.DATE)


class ConditionType(Enum):
    EQUAL = 'EQUAL'
    AND = 'AND'
    OR = 'OR'
    RANGE = 'RANGE'
    GREATER = 'GREATER'
    LITTLER = 'LITTLER'


@dataclass
class AndCondition:
    conditions: List['Condition']
    type: ConditionType = ConditionType.AND


@dataclass
class OrCondition:
    conditions: List['Condition']
    type: ConditionType = ConditionType.OR


@dataclass
class Littler:
    parameter: Parameter
    target: Any
    strict: bool
    type: ConditionType = ConditionType.LITTLER


@dataclass
class Greater:
    parameter: Parameter
    target: Any
    strict: bool
    type: ConditionType = ConditionType.GREATER


@dataclass
class Equal:
    parameter: Parameter
    target: Any
    type: ConditionType = ConditionType.EQUAL


@dataclass
class Range:
    parameter: Parameter
    left: Any
    right: Any
    left_strict: bool
    right_strict: bool
    type: ConditionType = ConditionType.RANGE


Condition = Union[Equal, Range, Greater, Littler, AndCondition, OrCondition]

Ints = Tuple[int, ...]


@dataclass
class SectionReference:
    path: Ints


@dataclass
class EntityReference:
    section: SectionReference
    outer_alinea_indices: Optional[List[int]]


@dataclass
class ConditionSource:
    explanation: str
    reference: EntityReference


@dataclass
class ApplicationCondition:
    targeted_entity: EntityReference
    condition: Condition
    source: ConditionSource


@dataclass
class AlternativeSection:
    targeted_section: SectionReference
    new_text: StructuredText
    condition: Condition
    source: ConditionSource


@dataclass
class Parametrization:
    application_conditions: List[ApplicationCondition]
    alternative_sections: List[AlternativeSection]
    path_to_conditions: Dict[Ints, List[ApplicationCondition]] = field(init=False)
    path_to_alternative_sections: Dict[Ints, List[AlternativeSection]] = field(init=False)

    def __post_init__(self):
        self.path_to_conditions = {}
        for cd in self.application_conditions:
            path = cd.targeted_entity.section.path
            if path not in self.path_to_conditions:
                self.path_to_conditions[path] = []
            self.path_to_conditions[path].append(cd)

        self.path_to_alternative_sections = {}
        for sec in self.alternative_sections:
            path = sec.targeted_section.path
            if path not in self.path_to_alternative_sections:
                self.path_to_alternative_sections[path] = []
            self.path_to_alternative_sections[path].append(sec)


def _generate_bool_condition(parameter_str: str) -> Equal:
    return Equal(Parameter(parameter_str, ParameterType.BOOLEAN), True)


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


def condition_to_str(condition: Condition) -> str:
    if isinstance(condition, Equal):
        return f'Si {condition.parameter.id} == {condition.target}:'
    if isinstance(condition, Littler):
        comp = '<' if condition.strict else '<='
        return f'Si {condition.parameter.id} {comp} {condition.target}:'
    if isinstance(condition, Greater):
        comp = '>' if condition.strict else '>='
        return f'Si {condition.parameter.id} {comp} {condition.target}:'
    raise NotImplementedError(f'stringifying condition {condition.type} is not implemented yet.')


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


def _any_parameter_is_undefined(parametrization: Parametrization, defined_parameters: KeysView[Parameter]) -> bool:
    parameters = _extract_parameters_from_parametrization(parametrization)
    return any([parameter not in defined_parameters for parameter in parameters])


def _condition_is_fulfilled(condition: Condition, parameter_values: Dict[Parameter, Any]) -> bool:
    if isinstance(condition, AndCondition):
        return all([_condition_is_fulfilled(cd, parameter_values) for cd in condition.conditions])
    if isinstance(condition, OrCondition):
        return any([_condition_is_fulfilled(cd, parameter_values) for cd in condition.conditions])
    value = parameter_values[condition.parameter]
    if isinstance(condition, Littler):
        if condition.strict:
            return value < condition.target
        return value <= condition.target
    if isinstance(condition, Greater):
        if condition.strict:
            return value > condition.target
        return value >= condition.target
    raise NotImplementedError('Condition {condition.type} not implemented yet.')


def _generate_warning_missing_value(condition: ApplicationCondition) -> str:
    parameters = _extract_parameters_from_condition(condition.condition)
    if len(parameters) == 1:
        parameter = list(parameters)[0]
        return f'Ce paragraphe pourrait ne pas être applicable selon la valeur du paramètre {parameter.id}.'
    ids = ', '.join([param.id for param in parameters])
    return f'Ce paragraphe pourrait ne pas être applicable selon la valeur des paramètres suivants: {ids}.'


def _generate_reason_inactive(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, AndCondition):
        unfulfilled_conditions = [
            condition_to_str(subcondition)
            for subcondition in condition.conditions
            if not _condition_is_fulfilled(subcondition, parameter_values)
        ]
        if len(unfulfilled_conditions) == 1:
            return f'La condition d\'application suivante n\'est respectée: {unfulfilled_conditions[0]}'
        return 'Les conditions d\'application suivantes ne sont pas respectées: ' + ', '.join(unfulfilled_conditions)
    if isinstance(condition, OrCondition):
        str_ = [condition_to_str(subcondition) for subcondition in condition.conditions]
        if len(str_) == 1:
            return f'La condition d\'application suivante n\'est respectée: {str_[0]}'
        return 'Aucune des conditions d\'application suivantes ne sont pas respectées: ' + ', '.join(str_)
    parameter = condition.parameter
    if isinstance(condition, Equal):
        value = parameter_values[parameter]
        return f'Le paramètre {parameter.id} n\'est pas égal à {value}'
    raise NotImplementedError(f'stringifying condition {condition.type} is not implemented yet.')


def _apply_parameter_values_in_text(
    text: StructuredText, parametrization: Parametrization, parameter_values: Dict[Parameter, Any], path: Ints
) -> StructuredText:
    new_text = copy(text)
    new_text.sections = [
        _apply_parameter_values_in_text(section, parametrization, parameter_values, path + (i,))
        for i, section in enumerate(text.sections)
    ]
    for condition in parametrization.path_to_conditions.get(path) or []:
        if _any_parameter_is_undefined(parametrization, parameter_values.keys()):
            new_text.warnings.append(_generate_warning_missing_value(condition))
        else:
            if not _condition_is_fulfilled(condition.condition, parameter_values):
                new_text.active = False
                new_text.reason_inactive = _generate_reason_inactive(condition.condition, parameter_values)
    return new_text


def _apply_parameter_values_to_am(
    am: ArreteMinisteriel, parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> ArreteMinisteriel:
    new_am = copy(am)
    new_am.sections = [
        _apply_parameter_values_in_text(section, parametrization, parameter_values, (i,))
        for i, section in enumerate(am.sections)
    ]
    return new_am
