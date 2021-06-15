import math
from datetime import date
from typing import List, Optional, Set, Tuple

from .exceptions import ParametrizationError
from .models.condition import Condition, Equal, Greater, LeafCondition, Littler, Range, extract_leaf_conditions
from .models.parameter import Parameter, ParameterType

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
        assert x <= y
        assert z <= t
        if y > z:
            return True
    return False


def _date_ranges_strictly_overlap(ranges: List[_DateRange]) -> bool:
    timestamp_ranges = [
        (float(dt_left.toordinal()) if dt_left else -math.inf, float(dt_right.toordinal()) if dt_right else math.inf)
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


def check_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
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
