from copy import copy, deepcopy
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from lib.compute_properties import Regime
from typing import Any, Dict, KeysView, List, Optional, Set, Tuple, Union
from lib.data import Applicability, ArreteMinisteriel, DateCriterion, StructuredText, load_structured_text


class ParameterType(Enum):
    DATE = 'DATE'
    REGIME = 'REGIME'
    BOOLEAN = 'BOOLEAN'


@dataclass(eq=True, frozen=True)
class Parameter:
    id: str
    type: ParameterType

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Parameter':
        return Parameter(dict_['id'], ParameterType(dict_['type']))


class ParameterEnum(Enum):
    DATE_AUTORISATION = Parameter('date-d-autorisation', ParameterType.DATE)
    DATE_INSTALLATION = Parameter('date-d-installation', ParameterType.DATE)
    REGIME = Parameter('regime', ParameterType.REGIME)


class ConditionType(Enum):
    EQUAL = 'EQUAL'
    AND = 'AND'
    OR = 'OR'
    RANGE = 'RANGE'
    GREATER = 'GREATER'
    LITTLER = 'LITTLER'


def load_condition(dict_: Dict[str, Any]) -> 'Condition':
    type_ = ConditionType(dict_['type'])
    if type_ == ConditionType.AND:
        return AndCondition.from_dict(dict_)
    if type_ == ConditionType.OR:
        return OrCondition.from_dict(dict_)
    if type_ == ConditionType.EQUAL:
        return Equal.from_dict(dict_)
    if type_ == ConditionType.GREATER:
        return Greater.from_dict(dict_)
    if type_ == ConditionType.LITTLER:
        return Littler.from_dict(dict_)
    if type_ == ConditionType.RANGE:
        return Range.from_dict(dict_)
    raise ValueError(f'Unknown condition type {type_}')


@dataclass
class AndCondition:
    conditions: List['Condition']
    type: ConditionType = ConditionType.AND

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['conditions'] = [cd.to_dict() for cd in self.conditions]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AndCondition':
        return AndCondition([load_condition(cd) for cd in dict_['conditions']])


@dataclass
class OrCondition:
    conditions: List['Condition']
    type: ConditionType = ConditionType.OR

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['conditions'] = [cd.to_dict() for cd in self.conditions]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'OrCondition':
        return OrCondition([load_condition(cd) for cd in dict_['conditions']])


def parameter_value_to_dict(value: Any, type_: ParameterType) -> Any:
    if type_ == ParameterType.DATE:
        return int(value.timestamp())
    return value


def load_target(json_value: Any, type_: ParameterType) -> Any:
    if type_ == ParameterType.DATE:
        return datetime.fromtimestamp(json_value)
    return json_value


@dataclass
class Littler:
    parameter: Parameter
    target: Any
    strict: bool
    type: ConditionType = ConditionType.LITTLER

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Littler':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Littler(parameter, load_target(dict_['target'], parameter.type), dict_['strict'])


@dataclass
class Greater:
    parameter: Parameter
    target: Any
    strict: bool
    type: ConditionType = ConditionType.GREATER

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Greater':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Greater(parameter, load_target(dict_['target'], parameter.type), dict_['strict'])


@dataclass
class Equal:
    parameter: Parameter
    target: Any
    type: ConditionType = ConditionType.EQUAL

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Equal':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Equal(parameter, load_target(dict_['target'], parameter.type))


@dataclass
class Range:
    parameter: Parameter
    left: Any
    right: Any
    left_strict: bool
    right_strict: bool
    type: ConditionType = ConditionType.RANGE

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['left'] = parameter_value_to_dict(self.left, self.parameter.type)
        res['right'] = parameter_value_to_dict(self.right, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Range':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Range(
            Parameter.from_dict(dict_['parameter']),
            load_target(dict_['left'], parameter.type),
            load_target(dict_['right'], parameter.type),
            dict_['left_strict'],
            dict_['right_strict'],
        )


LeafCondition = Union[Equal, Range, Greater, Littler]

Condition = Union[LeafCondition, AndCondition, OrCondition]

Ints = Tuple[int, ...]


@dataclass
class SectionReference:
    path: Ints

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'SectionReference':
        return SectionReference(tuple(dict_['path']))


@dataclass
class EntityReference:
    section: SectionReference
    outer_alinea_indices: Optional[List[int]]
    whole_arrete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'EntityReference':
        whole_arrete = dict_['whole_arrete'] if 'whole_arrete' in dict_ else False
        return EntityReference(
            SectionReference.from_dict(dict_['section']), dict_['outer_alinea_indices'], whole_arrete
        )


@dataclass
class ConditionSource:
    explanation: str
    reference: EntityReference

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'ConditionSource':
        return ConditionSource(dict_['explanation'], EntityReference.from_dict(dict_['reference']))


@dataclass
class ApplicationCondition:
    targeted_entity: EntityReference
    condition: Condition
    source: ConditionSource

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_entity': self.targeted_entity.to_dict(),
            'condition': self.condition.to_dict(),
            'source': self.source.to_dict(),
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'ApplicationCondition':
        return ApplicationCondition(
            EntityReference.from_dict(dict_['targeted_entity']),
            load_condition(dict_['condition']),
            ConditionSource.from_dict(dict_['source']),
        )


@dataclass
class AlternativeSection:
    targeted_section: SectionReference
    new_text: StructuredText
    condition: Condition
    source: ConditionSource

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_section': self.targeted_section.to_dict(),
            'new_text': self.new_text.as_dict(),
            'condition': self.condition.to_dict(),
            'source': self.source.to_dict(),
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AlternativeSection':
        return AlternativeSection(
            SectionReference.from_dict(dict_['targeted_section']),
            load_structured_text(dict_['new_text']),
            load_condition(dict_['condition']),
            ConditionSource.from_dict(dict_['source']),
        )


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

    def to_dict(self) -> Dict[str, Any]:
        return {
            'application_conditions': [app.to_dict() for app in self.application_conditions],
            'alternative_sections': [sec.to_dict() for sec in self.alternative_sections],
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Parametrization':
        return Parametrization(
            [ApplicationCondition.from_dict(app) for app in dict_['application_conditions']],
            [AlternativeSection.from_dict(sec) for sec in dict_['alternative_sections']],
        )


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
    if isinstance(condition, Range):
        left_comp = '<' if condition.left_strict else '<='
        right_comp = '<' if condition.right_strict else '<='
        return f'Si {condition.left} {left_comp} {condition.parameter.id} {right_comp} {condition.right_strict}:'
    raise NotImplementedError(f'stringifying condition {condition.type} is not implemented yet.')


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


def _compute_applicability(condition: ApplicationCondition, parameter_values: Dict[Parameter, Any]) -> Applicability:
    result = Applicability(True, '', False)
    if _any_parameter_is_undefined(condition.condition, parameter_values.keys()):
        result.warnings.append(_generate_warning_missing_value(condition.condition))
    else:
        if not _is_satisfied(condition.condition, parameter_values):
            result.active = False
            result.reason_inactive = _generate_reason_inactive(condition.condition, parameter_values)
    return result


def _merge_applicabilities(applicabilities: List[Applicability]) -> Applicability:
    all_active = all([app.active for app in applicabilities])
    reason_inactive = '\n'.join([app.reason_inactive for app in applicabilities if app.reason_inactive])
    warnings = [warn for app in applicabilities for warn in app.warnings]
    return Applicability(all_active, reason_inactive, False, warnings=warnings)


def _build_alternative_text(
    text: StructuredText, alternative_section: AlternativeSection, parameter_values: Dict[Parameter, Any]
) -> StructuredText:
    new_text = deepcopy(text)
    new_text.title = alternative_section.new_text.title
    new_text.sections = alternative_section.new_text.sections
    new_text.outer_alineas = alternative_section.new_text.outer_alineas
    new_text.applicability = Applicability(
        True, None, True, _generate_reason_active(alternative_section.condition, parameter_values)
    )
    return new_text


def _compute_undefined_parameters_warnings(condition: Condition, parameter_values: Dict[Parameter, Any]) -> List[str]:
    all_parameters = _extract_parameters_from_condition(condition)
    undefined_parameters = {parameter for parameter in all_parameters if parameter not in parameter_values}
    return [f'Le paramètre {parameter} n\'est pas défini' for parameter in undefined_parameters]


def _keep_unsatisfied_conditions(
    application_conditions: List[ApplicationCondition], parameter_values: Dict[Parameter, Any]
) -> Tuple[List[ApplicationCondition], List[str]]:
    unsatisfied: List[ApplicationCondition] = []
    warnings: List[str] = []
    for application_condition in application_conditions:
        if not _is_satisfied(application_condition.condition, parameter_values):
            unsatisfied.append(application_condition)
        else:
            warnings.extend(_compute_undefined_parameters_warnings(application_condition.condition, parameter_values))
    return unsatisfied, warnings


def _keep_satisfied_mofications(
    alternative_sections: List[AlternativeSection], parameter_values: Dict[Parameter, Any]
) -> Tuple[List[AlternativeSection], List[str]]:
    satisfied: List[AlternativeSection] = []
    warnings: List[str] = []
    for alt in alternative_sections:
        if _is_satisfied(alt.condition, parameter_values):
            satisfied.append(alt)
        else:
            warnings.extend(_compute_undefined_parameters_warnings(alt.condition, parameter_values))
    return satisfied, warnings


def _apply_parameter_values_in_text(
    text: StructuredText, parametrization: Parametrization, parameter_values: Dict[Parameter, Any], path: Ints
) -> StructuredText:

    application_conditions, warnings_1 = _keep_unsatisfied_conditions(
        parametrization.path_to_conditions.get(path) or [], parameter_values
    )
    alternative_sections, warnings_2 = _keep_satisfied_mofications(
        parametrization.path_to_alternative_sections.get(path) or [], parameter_values
    )
    if application_conditions and alternative_sections:
        raise NotImplementedError(
            f'Cannot apply conditions and alternative sections on one section. (Section title: {text.title.text})'
        )

    if alternative_sections:
        if len(alternative_sections) > 1:
            raise ValueError(
                f'Cannot handle more than 1 applicable modification on one section. '
                'Here, {len(alternative_sections)} are applicable.'
            )
        return _build_alternative_text(text, alternative_sections[0], parameter_values)

    new_text = copy(text)
    new_text.sections = [
        _apply_parameter_values_in_text(section, parametrization, parameter_values, path + (i,))
        for i, section in enumerate(text.sections)
    ]
    if application_conditions:
        applicabilities = [_compute_applicability(condition, parameter_values) for condition in application_conditions]
        new_text.applicability = _merge_applicabilities(applicabilities)
    else:
        new_text.applicability = Applicability(True)
    new_text.applicability.warnings.extend(warnings_1 + warnings_2)
    return new_text


def _compute_whole_text_applicability(
    application_conditions: List[ApplicationCondition], parameter_values: Dict[Parameter, Any]
) -> Applicability:
    applicabilities = [_compute_applicability(condition, parameter_values) for condition in application_conditions]
    return _merge_applicabilities(applicabilities)


def _date_to_str(date: datetime) -> str:
    return date.strftime('%Y-%m-%d')


def _extract_installation_date_criterion(
    parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> Optional[DateCriterion]:
    targets = _extract_sorted_targets(
        _extract_conditions_from_parametrization(ParameterEnum.DATE_INSTALLATION.value, parametrization), True
    )
    if not targets:
        return None
    value = parameter_values[ParameterEnum.DATE_INSTALLATION.value]
    if value < targets[0]:
        return DateCriterion(None, _date_to_str(targets[0]))
    for date_before, date_after in zip(targets, targets[1:]):
        if value < date_after:
            return DateCriterion(_date_to_str(date_before), _date_to_str(date_after))
    return DateCriterion(_date_to_str(targets[-1]), None)


def _apply_parameter_values_to_am(
    am: ArreteMinisteriel, parametrization: Parametrization, parameter_values: Dict[Parameter, Any]
) -> ArreteMinisteriel:
    new_am = copy(am)
    new_am.installation_date_criterion = _extract_installation_date_criterion(parametrization, parameter_values)
    new_am.sections = [
        _apply_parameter_values_in_text(section, parametrization, parameter_values, (i,))
        for i, section in enumerate(am.sections)
    ]
    new_am.applicability = _compute_whole_text_applicability(
        parametrization.path_to_conditions.get(tuple()) or [], parameter_values
    )
    return new_am


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


Combinations = Dict[Tuple[str, ...], Dict[Parameter, Any]]


def _generate_exhaustive_combinations(parametrization: Parametrization) -> Combinations:
    options_dicts = _generate_options_dicts(parametrization)
    if not options_dicts:
        return {}
    combinations = _generate_combinations(options_dicts)
    return combinations


def generate_all_am_versions(
    am: ArreteMinisteriel, parametrization: Parametrization, combinations: Optional[Combinations] = None
) -> Dict[Tuple[str, ...], ArreteMinisteriel]:
    if combinations is None:
        combinations = _generate_exhaustive_combinations(parametrization)
    if not combinations:
        return {tuple(): am}
    return {
        combination_name: _apply_parameter_values_to_am(am, parametrization, parameter_values)
        for combination_name, parameter_values in combinations.items()
    }


def build_simple_parametrization(
    non_applicable_section_references: List[Ints],
    modified_articles: Dict[Ints, StructuredText],
    source_section: Ints,
    date: datetime,
) -> Parametrization:
    source = ConditionSource.from_dict(
        {
            'explanation': 'Paragraphe décrivant ce qui s\'applique aux installations existantes',
            'reference': {'section': {'path': source_section}, 'outer_alinea_indices': None},
        }
    )
    condition = Greater(Parameter('date-d-installation', ParameterType.DATE), date, False)
    application_conditions = [
        ApplicationCondition(EntityReference(SectionReference(tuple(ref)), None), condition, source)
        for ref in non_applicable_section_references
    ]
    alternative_sections = [
        AlternativeSection(SectionReference(ref), value, condition, source) for ref, value in modified_articles.items()
    ]
    return Parametrization(application_conditions, alternative_sections)
