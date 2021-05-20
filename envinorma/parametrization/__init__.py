import math
import sys
import warnings
from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union

from envinorma.data import ArreteMinisteriel, StructuredText
from envinorma.parametrization.conditions import (
    Condition,
    Equal,
    Greater,
    LeafCondition,
    Littler,
    Parameter,
    ParameterEnum,
    ParameterType,
    Range,
    check_condition,
    condition_to_str,
    extract_leaf_conditions,
    extract_parameters_from_condition,
    load_condition,
)

Ints = Tuple[int, ...]


@dataclass
class SectionReference:
    path: Ints
    titles_sequence: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'SectionReference':
        return cls(tuple(dict_['path']), dict_.get('titles_sequence'))


@dataclass
class EntityReference:
    section: SectionReference
    outer_alinea_indices: Optional[List[int]]

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'EntityReference':
        return EntityReference(SectionReference.from_dict(dict_['section']), dict_['outer_alinea_indices'])


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
class NonApplicationCondition:
    targeted_entity: EntityReference
    condition: Condition
    source: ConditionSource
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_entity': self.targeted_entity.to_dict(),
            'condition': self.condition.to_dict(),
            'source': self.source.to_dict(),
            'description': self.description,
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'NonApplicationCondition':
        return NonApplicationCondition(
            EntityReference.from_dict(dict_['targeted_entity']),
            load_condition(dict_['condition']),
            ConditionSource.from_dict(dict_['source']),
            dict_.get('description'),
        )


@dataclass
class AlternativeSection:
    targeted_section: SectionReference
    new_text: StructuredText
    condition: Condition
    source: ConditionSource
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_section': self.targeted_section.to_dict(),
            'new_text': self.new_text.to_dict(),
            'condition': self.condition.to_dict(),
            'source': self.source.to_dict(),
            'description': self.description,
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AlternativeSection':
        return AlternativeSection(
            SectionReference.from_dict(dict_['targeted_section']),
            StructuredText.from_dict(dict_['new_text']),
            load_condition(dict_['condition']),
            ConditionSource.from_dict(dict_['source']),
            dict_.get('description'),
        )


@dataclass
class AMWarning:
    targeted_section: SectionReference
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_section': self.targeted_section.to_dict(),
            'text': self.text,
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AMWarning':
        return AMWarning(SectionReference.from_dict(dict_['targeted_section']), dict_['text'])


def extract_conditions_from_parametrization(
    parameter: Parameter, parametrization: 'Parametrization'
) -> List[LeafCondition]:
    return [
        cd for ap in parametrization.application_conditions for cd in extract_leaf_conditions(ap.condition, parameter)
    ] + [cd for as_ in parametrization.alternative_sections for cd in extract_leaf_conditions(as_.condition, parameter)]


class ParametrizationError(Exception):
    pass


def _check_parametrization(parametrization: 'Parametrization') -> None:
    for app in parametrization.application_conditions:
        check_condition(app.condition)
    for sec in parametrization.alternative_sections:
        check_condition(sec.condition)


def _extract_all_paths(parametrization: 'Parametrization') -> Set[Ints]:
    return set(parametrization.path_to_alternative_sections.keys()).union(
        set(parametrization.path_to_conditions.keys())
    )


_DateRange = Tuple[Optional[datetime], Optional[datetime]]


def _extract_date_range(condition: LeafCondition) -> _DateRange:
    if isinstance(condition, Range):
        return (condition.left, condition.right)
    if isinstance(condition, Equal):
        return (condition.target, condition.target)
    if isinstance(condition, Littler):
        return (None, condition.target)
    if isinstance(condition, Greater):
        return (condition.target, None)
    raise NotImplementedError(type(condition))


def _ranges_strictly_overlap(ranges: List[Tuple[float, float]]) -> bool:
    sorted_ranges = sorted(ranges)
    for ((x, y), (z, t)) in zip(sorted_ranges, sorted_ranges[1:]):
        assert x <= y
        assert z <= t
        if y > z:
            return True
    return False


def _date_ranges_strictly_overlap(ranges: List[_DateRange]) -> bool:
    timestamp_ranges = [
        (dt_left.timestamp() if dt_left else -math.inf, dt_right.timestamp() if dt_right else math.inf)
        for dt_left, dt_right in ranges
    ]
    return _ranges_strictly_overlap(timestamp_ranges)


def _check_date_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    leaf_conditions = [leaf for cd in all_conditions for leaf in extract_leaf_conditions(cd, parameter)]
    ranges: List[_DateRange] = []
    for condition in leaf_conditions:
        ranges.append(_extract_date_range(condition))
    if _date_ranges_strictly_overlap(ranges):
        raise ParametrizationError(
            f'Date ranges overlap, they can be satisfied simultaneously, which can lead to'
            f' ambiguities: {all_conditions}'
        )


_Range = Tuple[float, float]


def _extract_range(condition: LeafCondition) -> _Range:
    if isinstance(condition, Range):
        return (condition.left, condition.right)
    if isinstance(condition, Equal):
        return (condition.target, condition.target)
    if isinstance(condition, Littler):
        return (-math.inf, condition.target)
    if isinstance(condition, Greater):
        return (condition.target, math.inf)
    raise NotImplementedError(type(condition))


def _check_real_number_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    leaf_conditions = [leaf for cd in all_conditions for leaf in extract_leaf_conditions(cd, parameter)]
    ranges = [_extract_range(condition) for condition in leaf_conditions]
    if _ranges_strictly_overlap(ranges):
        raise ParametrizationError(
            f'Ranges overlap, they can be satisfied simultaneously, which can lead to' f' ambiguities: {all_conditions}'
        )


def _check_discrete_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    leaf_conditions = [leaf for cd in all_conditions for leaf in extract_leaf_conditions(cd, parameter)]
    targets: Set = set()
    for condition in leaf_conditions:
        if not isinstance(condition, Equal):
            raise ParametrizationError(f'{parameter.id} conditions must be "=" conditions, got {condition.type}')
        if condition.target in targets:
            raise ParametrizationError(f'Several conditions are simultaneously satisfiable : {all_conditions}')
        targets.add(condition.target)


def _check_bool_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    leaf_conditions = [leaf for cd in all_conditions for leaf in extract_leaf_conditions(cd, parameter)]
    targets: Set[bool] = set()
    for condition in leaf_conditions:
        if not isinstance(condition, Equal):
            raise ParametrizationError(f'bool conditions must be "=" conditions, got {condition.type}')
        if condition.target in targets:
            raise ParametrizationError(f'Several conditions are simultaneously satisfiable : {all_conditions}')
        targets.add(condition.target)


def _check_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    if parameter.type == ParameterType.DATE:
        _check_date_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.REAL_NUMBER:
        _check_real_number_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.REGIME:
        _check_discrete_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.STRING:
        _check_discrete_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.RUBRIQUE:
        _check_discrete_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.BOOLEAN:
        _check_bool_conditions_are_incompatible(all_conditions, parameter)
    else:
        raise NotImplementedError(parameter.type)


def _check_consistency(
    non_application_conditions: List[NonApplicationCondition], alternative_sections: List[AlternativeSection]
) -> None:
    all_conditions = [nac.condition for nac in non_application_conditions] + [
        als.condition for als in alternative_sections
    ]
    if not all_conditions:
        return None
    all_parameters = {param for condition in all_conditions for param in extract_parameters_from_condition(condition)}
    if len(all_parameters) >= 2:
        return  # complicated and infrequent, not checked for now
    if len(all_parameters) == 0:
        raise ParametrizationError('There should be at least one parameter in conditions.')
    _check_conditions_are_incompatible(all_conditions, list(all_parameters)[0])


def check_parametrization_consistency(parametrization: 'Parametrization') -> None:
    all_paths = _extract_all_paths(parametrization)
    for path in all_paths:
        _check_consistency(
            parametrization.path_to_conditions.get(path, []), parametrization.path_to_alternative_sections.get(path, [])
        )


T = TypeVar('T')
K = TypeVar('K')


def _group(elements: List[T], groupper: Callable[[T], K]) -> Dict[K, List[T]]:
    groups: Dict[K, List[T]] = {}
    for element in elements:
        key = groupper(element)
        if key not in groups:
            groups[key] = []
        groups[key].append(element)
    return groups


@dataclass
class Parametrization:
    application_conditions: List[NonApplicationCondition]
    alternative_sections: List[AlternativeSection]
    warnings: List[AMWarning]
    path_to_conditions: Dict[Ints, List[NonApplicationCondition]] = field(init=False)
    path_to_alternative_sections: Dict[Ints, List[AlternativeSection]] = field(init=False)
    path_to_warnings: Dict[Ints, List[AMWarning]] = field(init=False)

    def __post_init__(self):
        self.path_to_conditions = _group(self.application_conditions, lambda x: x.targeted_entity.section.path)
        self.path_to_alternative_sections = _group(self.alternative_sections, lambda x: x.targeted_section.path)
        self.path_to_warnings = _group(self.warnings, lambda x: x.targeted_section.path)
        _check_parametrization(self)
        try:
            check_parametrization_consistency(self)
        except ParametrizationError as exc:
            warnings.warn(f'Parametrization error, will raise an exception in the future : {str(exc)}')

    def to_dict(self) -> Dict[str, Any]:
        res = {}
        res['application_conditions'] = [app.to_dict() for app in self.application_conditions]
        res['alternative_sections'] = [sec.to_dict() for sec in self.alternative_sections]
        res['warnings'] = [warning.to_dict() for warning in self.warnings]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Parametrization':
        return Parametrization(
            [NonApplicationCondition.from_dict(app) for app in dict_['application_conditions']],
            [AlternativeSection.from_dict(sec) for sec in dict_['alternative_sections']],
            [AMWarning.from_dict(sec) for sec in dict_.get('warnings', [])],
        )


ParameterObjectWithCondition = Union[NonApplicationCondition, AlternativeSection]
ParameterObject = Union[ParameterObjectWithCondition, AMWarning]
Combinations = Dict[Tuple[str, ...], Dict[Parameter, Any]]


def extract_titles_sequence(text: Union[ArreteMinisteriel, StructuredText], path: Ints) -> List[str]:
    if not path:
        return []
    if path[0] >= len(text.sections):
        raise ValueError(f'Path is not compatible with this text.')
    return [text.sections[path[0]].title.text] + extract_titles_sequence(text.sections[path[0]], path[1:])


def add_titles_sequences_section(obj: SectionReference, am: ArreteMinisteriel) -> SectionReference:
    return replace(obj, titles_sequence=extract_titles_sequence(am, obj.path))


def add_titles_sequences_non_application_condition(
    obj: NonApplicationCondition, am: ArreteMinisteriel
) -> NonApplicationCondition:
    new_source = deepcopy(obj)
    new_source.source.reference.section = add_titles_sequences_section(new_source.source.reference.section, am)
    new_source.targeted_entity.section = add_titles_sequences_section(new_source.targeted_entity.section, am)
    return new_source


def add_titles_sequences_alternative_section(obj: AlternativeSection, am: ArreteMinisteriel) -> AlternativeSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = add_titles_sequences_section(new_source.source.reference.section, am)
    new_source.targeted_section = add_titles_sequences_section(new_source.targeted_section, am)
    return new_source


def add_titles_sequences(parametrization: Parametrization, am: ArreteMinisteriel) -> Parametrization:
    return replace(
        parametrization,
        application_conditions=[
            add_titles_sequences_non_application_condition(x, am) for x in parametrization.application_conditions
        ],
        alternative_sections=[
            add_titles_sequences_alternative_section(x, am) for x in parametrization.alternative_sections
        ],
    )


class SectionNotFoundWarning(Warning):
    pass


def _extract_paths(text: Union[ArreteMinisteriel, StructuredText], titles_sequence: List[str]) -> Ints:
    if not titles_sequence:
        return ()
    for i, section in enumerate(text.sections):
        if section.title.text == titles_sequence[0]:
            return (i,) + _extract_paths(section, titles_sequence[1:])
    warnings.warn(
        SectionNotFoundWarning(f'Title {titles_sequence[0]} not found among sections, replacing path with (inf,).')
    )
    return (sys.maxsize,)


class UndefinedTitlesSequencesError(Exception):
    pass


def regenerate_paths_section(obj: SectionReference, am: ArreteMinisteriel) -> SectionReference:
    if obj.titles_sequence is None:
        raise UndefinedTitlesSequencesError('Titles sequences need to be defined')
    return replace(obj, path=_extract_paths(am, obj.titles_sequence))


def regenerate_paths_non_application_condition(
    obj: NonApplicationCondition, am: ArreteMinisteriel
) -> NonApplicationCondition:
    new_source = deepcopy(obj)
    new_source.source.reference.section = regenerate_paths_section(new_source.source.reference.section, am)
    new_source.targeted_entity.section = regenerate_paths_section(new_source.targeted_entity.section, am)
    return new_source


def regenerate_paths_alternative_section(obj: AlternativeSection, am: ArreteMinisteriel) -> AlternativeSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = regenerate_paths_section(new_source.source.reference.section, am)
    new_source.targeted_section = regenerate_paths_section(new_source.targeted_section, am)
    return new_source


def regenerate_paths(parametrization: Parametrization, am: ArreteMinisteriel) -> Parametrization:
    return replace(
        parametrization,
        application_conditions=[
            regenerate_paths_non_application_condition(x, am) for x in parametrization.application_conditions
        ],
        alternative_sections=[
            regenerate_paths_alternative_section(x, am) for x in parametrization.alternative_sections
        ],
    )
