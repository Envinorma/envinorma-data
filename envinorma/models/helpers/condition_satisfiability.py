import math
from datetime import date
from typing import List, Optional, Set, Tuple

from envinorma.models.condition import (
    AndCondition,
    Condition,
    Equal,
    Greater,
    LeafCondition,
    LeafConditions,
    Littler,
    MergeCondition,
    OrCondition,
    Range,
)
from envinorma.models.parameter import ParameterType

_DateRange = Tuple[Optional[date], Optional[date]]


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
        if x > y or z > t:
            raise AssertionError
        if y > z:
            return True
    return False


def _date_ranges_strictly_overlap(ranges: List[_DateRange]) -> bool:
    timestamp_ranges = [
        (float(dt_left.toordinal()) if dt_left else -math.inf, float(dt_right.toordinal()) if dt_right else math.inf)
        for dt_left, dt_right in ranges
    ]
    return _ranges_strictly_overlap(timestamp_ranges)


def _check_date_conditions_are_disjoint(conditions: List[LeafCondition]) -> bool:
    ranges = [_extract_date_range(condition) for condition in conditions]
    return not _date_ranges_strictly_overlap(ranges)


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


def _check_real_number_conditions_are_disjoint(conditions: List[LeafCondition]) -> bool:
    ranges = [_extract_range(condition) for condition in conditions]
    return not _ranges_strictly_overlap(ranges)


def _check_discrete_conditions_are_disjoint(conditions: List[LeafCondition]) -> bool:
    targets: Set = set()
    for condition in conditions:
        if not isinstance(condition, Equal):
            raise ValueError(f'Conditions must be "=" conditions, got {condition.type}')
        if condition.target in targets:
            return False
        targets.add(condition.target)
    return True


_DISCRETE_TYPES = (ParameterType.REGIME, ParameterType.STRING, ParameterType.RUBRIQUE, ParameterType.BOOLEAN)


def _conditions_with_same_parameter_are_disjoint(conditions: List[LeafCondition]) -> bool:
    if len({cd.parameter for cd in conditions}) != 1:
        raise ValueError('All conditions must have the same parameter')
    parameter = conditions[0].parameter
    if parameter.type == ParameterType.DATE:
        return _check_date_conditions_are_disjoint(conditions)
    if parameter.type == ParameterType.REAL_NUMBER:
        return _check_real_number_conditions_are_disjoint(conditions)
    if parameter.type in _DISCRETE_TYPES:
        return _check_discrete_conditions_are_disjoint(conditions)
    raise NotImplementedError(parameter.type)


def _shallow_deep_disjoint(condition_1: LeafCondition, condition_2: MergeCondition) -> bool:
    if isinstance(condition_2, AndCondition):
        conditions_with_same_parameter = [
            c for c in condition_2.conditions if isinstance(c, LeafConditions) and c.parameter == condition_1.parameter
        ]
        return _conditions_with_same_parameter_are_disjoint([condition_1, *conditions_with_same_parameter])
    if isinstance(condition_2, OrCondition):
        for condition in condition_2.conditions:
            if not isinstance(condition, LeafConditions):
                raise ValueError(f'Conditions must be leaf conditions, got {type(condition)}')
            if not _leaf_disjoint(condition_1, condition):
                return False
        return True


def _leaf_disjoint(condition_1: LeafCondition, condition_2: LeafCondition) -> bool:
    if condition_1.parameter != condition_2.parameter:
        return False
    return _conditions_with_same_parameter_are_disjoint([condition_1, condition_2])


def _condition_depth(condition: Condition) -> int:
    if isinstance(condition, LeafConditions):
        return 1
    return 1 + max([_condition_depth(c) for c in condition.conditions])


def _depth_2_disjoint(condition_1: MergeCondition, condition_2: MergeCondition) -> bool:
    if isinstance(condition_2, OrCondition):
        for condition in condition_2.conditions:
            if not isinstance(condition, LeafConditions):
                raise ValueError('Only leaf conditions are supported')
            if not _shallow_deep_disjoint(condition, condition_1):
                return False
        return True
    if isinstance(condition_1, OrCondition):
        return _depth_2_disjoint(condition_2, condition_1)
    # Both are AndConditions
    subconditions = [*condition_1.conditions, *condition_2.conditions]
    for parameter in set(condition_1.parameters()).intersection(set(condition_2.parameters())):
        conditions = [c for c in subconditions if isinstance(c, LeafConditions) and c.parameter == parameter]
        if _conditions_with_same_parameter_are_disjoint(conditions):
            return True
    return False


def could_be_simultaneously_satisfied_with(condition: 'Condition', other_condition: 'Condition') -> bool:
    if isinstance(condition, LeafConditions) and isinstance(other_condition, LeafConditions):
        return not _leaf_disjoint(condition, other_condition)
    if isinstance(condition, LeafConditions) and not isinstance(other_condition, LeafConditions):
        if _condition_depth(other_condition) > 2:
            raise NotImplementedError('Only conditions of depth at most 2 are supported')
        return not _shallow_deep_disjoint(condition, other_condition)
    if isinstance(other_condition, LeafConditions) and not isinstance(condition, LeafConditions):
        return could_be_simultaneously_satisfied_with(other_condition, condition)
    if _condition_depth(condition) > 2 or _condition_depth(other_condition) > 2:
        raise NotImplementedError('Only conditions of depth at most 2 are supported')
    return not _depth_2_disjoint(condition, other_condition)  # type: ignore
