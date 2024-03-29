from datetime import date, datetime, timedelta
from typing import Any, List, Tuple, Union

from envinorma.models.classement import Regime
from envinorma.models.condition import (
    Condition,
    ConditionType,
    Equal,
    Greater,
    LeafCondition,
    Littler,
    Range,
    extract_sorted_interval_sides_targets,
)
from envinorma.models.parameter import Parameter, ParameterType

from .models.parametrization import Combinations, Parametrization, extract_conditions_from_parametrization

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
    if not isinstance(condition, Equal):
        raise TypeError
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
        targets = extract_sorted_interval_sides_targets(conditions, True)
        values = _extract_interval_midpoints(targets)
        condition = conditions[0]
        if not isinstance(condition, (Range, Greater, Littler)):
            raise TypeError
        parameter = condition.parameter
        param_names = _compute_parameter_names(targets, parameter)
        return [(param_name, value) for param_name, value in zip(param_names, values)]
    raise NotImplementedError(f'Option dict generation not implemented for conditions with types {types}')


def _generate_options_dicts(parametrization: Parametrization) -> List[_Options]:
    parameters = parametrization.extract_parameters()
    options_dicts: List[_Options] = []
    for parameter in parameters:
        conditions = extract_conditions_from_parametrization(parameter, parametrization)
        options_dicts.append((parameter, _generate_options_dict(conditions)))
    return options_dicts


def generate_exhaustive_combinations(parametrization: Parametrization) -> Combinations:
    options_dicts = _generate_options_dicts(parametrization)
    if not options_dicts:
        return {}
    combinations = _generate_combinations(options_dicts, True)
    return combinations
