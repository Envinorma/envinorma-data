from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Literal, Union

from .parameter import Parameter, dump_parameter_value, load_parameter_value, parameter_value_to_str


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


@dataclass(eq=True, frozen=True)
class AndCondition:
    conditions: FrozenSet['Condition']
    type: ConditionType = ConditionType.AND

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['conditions'] = [cd.to_dict() for cd in self.conditions]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AndCondition':
        return AndCondition(frozenset([load_condition(cd) for cd in dict_['conditions']]))

    def check(self) -> None:
        if self.type != ConditionType.AND:
            raise ValueError(f'self.type is not as expected: {self.type}')
        for cd in self.conditions:
            cd.check()

    def is_satisfied(self, parameter_values: Dict[Parameter, Any]) -> bool:
        return all([cd.is_satisfied(parameter_values) for cd in self.conditions])

    def parameters(self) -> List[Parameter]:
        return [param for cd in self.conditions for param in cd.parameters()]

    def to_str(self) -> str:
        return '(' + ') and ('.join([cd.to_str() for cd in self.conditions]) + ')'


@dataclass(eq=True, frozen=True)
class OrCondition:
    conditions: FrozenSet['Condition']
    type: ConditionType = ConditionType.OR

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['conditions'] = [cd.to_dict() for cd in self.conditions]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'OrCondition':
        return OrCondition(frozenset([load_condition(cd) for cd in dict_['conditions']]))

    def check(self) -> None:
        if self.type != ConditionType.OR:
            raise ValueError
        for cd in self.conditions:
            cd.check()

    def is_satisfied(self, parameter_values: Dict[Parameter, Any]) -> bool:
        return any([cd.is_satisfied(parameter_values) for cd in self.conditions])

    def parameters(self) -> List[Parameter]:
        return [param for cd in self.conditions for param in cd.parameters()]

    def to_str(self) -> str:
        return '(' + ') or ('.join([cd.to_str() for cd in self.conditions]) + ')'


@dataclass(eq=True, frozen=True)
class Littler:
    parameter: Parameter
    target: Any
    strict: bool = True
    type: ConditionType = ConditionType.LITTLER

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = dump_parameter_value(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Littler':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Littler(parameter, load_parameter_value(dict_['target'], parameter.type), dict_['strict'])

    def check(self) -> None:
        if self.type != ConditionType.LITTLER:
            raise ValueError(f'self.type is not as expected: {self.type}')

    def is_satisfied(self, parameter_values: Dict[Parameter, Any]) -> bool:
        if self.parameter not in parameter_values:
            return False
        value = parameter_values[self.parameter]
        return (value < self.target) if self.strict else (value <= self.target)

    def parameters(self) -> List[Parameter]:
        return [self.parameter]

    def to_str(self) -> str:
        comp = '<' if self.strict else '<='
        return f'{self.parameter.id} {comp} {parameter_value_to_str(self.target)}'


@dataclass(eq=True, frozen=True)
class Greater:
    parameter: Parameter
    target: Any
    strict: bool = False
    type: ConditionType = ConditionType.GREATER

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = dump_parameter_value(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Greater':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Greater(parameter, load_parameter_value(dict_['target'], parameter.type), dict_['strict'])

    def check(self) -> None:
        if self.type != ConditionType.GREATER:
            raise ValueError(f'self.type is not as expected: {self.type}')

    def is_satisfied(self, parameter_values: Dict[Parameter, Any]) -> bool:
        if self.parameter not in parameter_values:
            return False
        value = parameter_values[self.parameter]
        return (value > self.target) if self.strict else (value >= self.target)

    def parameters(self) -> List[Parameter]:
        return [self.parameter]

    def to_str(self) -> str:
        comp = '>' if self.strict else '>='
        return f'{self.parameter.id} {comp} {parameter_value_to_str(self.target)}'


@dataclass(eq=True, frozen=True)
class Equal:
    parameter: Parameter
    target: Any
    type: ConditionType = ConditionType.EQUAL

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = dump_parameter_value(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Equal':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Equal(parameter, load_parameter_value(dict_['target'], parameter.type))

    def check(self) -> None:
        if self.type != ConditionType.EQUAL:
            raise ValueError(f'self.type is not as expected: {self.type}')

    def is_satisfied(self, parameter_values: Dict[Parameter, Any]) -> bool:
        if self.parameter not in parameter_values:
            return False
        return parameter_values[self.parameter] == self.target

    def parameters(self) -> List[Parameter]:
        return [self.parameter]

    def to_str(self) -> str:
        return f'{self.parameter.id} == {parameter_value_to_str(self.target)}'


@dataclass(eq=True, frozen=True)
class Range:
    parameter: Parameter
    left: Any
    right: Any
    left_strict: bool = False
    right_strict: bool = True
    type: ConditionType = ConditionType.RANGE

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['left'] = dump_parameter_value(self.left, self.parameter.type)
        res['right'] = dump_parameter_value(self.right, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Range':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Range(
            Parameter.from_dict(dict_['parameter']),
            load_parameter_value(dict_['left'], parameter.type),
            load_parameter_value(dict_['right'], parameter.type),
            dict_['left_strict'],
            dict_['right_strict'],
        )

    def check(self) -> None:
        if self.type != ConditionType.RANGE:
            raise ValueError(f'self.type is not as expected: {self.type}')

    def is_satisfied(self, parameter_values: Dict[Parameter, Any]) -> bool:
        if self.parameter not in parameter_values:
            return False
        parameter_value = parameter_values[self.parameter]
        if self.left_strict and self.right_strict:
            return self.left < parameter_value < self.right
        if self.left_strict and not self.right_strict:
            return self.left < parameter_value <= self.right
        if not self.left_strict and self.right_strict:
            return self.left <= parameter_value < self.right
        if not self.left_strict and not self.right_strict:
            return self.left <= parameter_value <= self.right
        raise NotImplementedError()

    def parameters(self) -> List[Parameter]:
        return [self.parameter]

    def to_str(self) -> str:
        left_comp = '<' if self.left_strict else '<='
        right_comp = '<' if self.right_strict else '<='
        return (
            f'{parameter_value_to_str(self.left)} {left_comp} {self.parameter.id} '
            f'{right_comp} {parameter_value_to_str(self.right)}'
        )


LeafConditions = (Equal, Range, Greater, Littler)  # for runtime type checking
LeafCondition = Union[Equal, Range, Greater, Littler]  # for typing

Conditions = (LeafCondition, AndCondition, OrCondition)
Condition = Union[LeafCondition, AndCondition, OrCondition]

MergeConditions = (AndCondition, OrCondition)
MergeCondition = Union[AndCondition, OrCondition]

MonoConditions = (Equal, Greater, Littler)
MonoCondition = Union[Equal, Greater, Littler]

MergeType = Literal['AND', 'OR']


def ensure_mono_condition(condition: Condition) -> MonoCondition:
    if isinstance(condition, MonoConditions):
        return condition
    raise ValueError(f'Unexpected condition type : expecting type MonoCondition, got {type(condition)}')


def ensure_mono_conditions(conditions: List[Condition]) -> List[MonoCondition]:
    return [ensure_mono_condition(x) for x in conditions]


def extract_leaf_conditions(condition: Condition, parameter: Parameter) -> List[LeafCondition]:
    if isinstance(condition, MergeConditions):
        return [
            cond for search_cond in condition.conditions for cond in extract_leaf_conditions(search_cond, parameter)
        ]
    if condition.parameter.id == parameter.id:
        return [condition]
    return []


def _check_range_is_right_strict(range_: Range) -> None:
    if range_.left_strict:
        raise AssertionError
    if not range_.right_strict:
        raise AssertionError


def _check_condition_is_right_strict(condition: Condition) -> None:
    if isinstance(condition, Range):
        _check_range_is_right_strict(condition)
    elif isinstance(condition, Littler):
        if not condition.strict:
            raise AssertionError
    elif isinstance(condition, Greater):
        if condition.strict:
            raise AssertionError
    else:
        raise ValueError(f'Unexpected type {type(condition)}')


def extract_sorted_interval_sides_targets(
    conditions: Union[List[Condition], List[LeafCondition]], right_strict: bool
) -> List[Any]:
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
    return sorted(set(targets))
