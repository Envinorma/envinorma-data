from datetime import date, datetime
from typing import List

from envinorma.models import Regime
from envinorma.models.condition import Condition, Equal, Greater, Littler, Range
from envinorma.models.parameter import Parameter, ParameterType
from envinorma.parametrization.combinations import (
    _change_value,
    _extract_interval_midpoints,
    _generate_combinations,
    _generate_equal_option_dicts,
    _generate_options_dict,
    _mean,
)
from envinorma.parametrization.models.parametrization import Combinations


def test_mean():
    assert _mean(0, 2) == 1
    assert _mean(datetime(2020, 1, 1), datetime(2020, 1, 3)) == datetime(2020, 1, 2)


def test_extract_interval_midpoints():
    assert _extract_interval_midpoints([0, 1, 2, 3]) == [-1, 0.5, 1.5, 2.5, 4]
    res = [datetime(2019, 12, 31), datetime(2020, 1, 2), datetime(2020, 1, 4)]
    assert _extract_interval_midpoints([datetime(2020, 1, 1), datetime(2020, 1, 3)]) == res


def test_generate_equal_option_dicts():
    parameter = Parameter('test', ParameterType.BOOLEAN)
    conditions: List[Condition] = [Equal(parameter, True), Equal(parameter, True)]
    res = _generate_equal_option_dicts(conditions)
    assert res == [('test == True', True), ('test != True', False)]


def test_generate_equal_option_dicts_2():
    parameter = Parameter('regime', ParameterType.REGIME)
    conditions: List[Condition] = [Equal(parameter, Regime.A), Equal(parameter, Regime.NC)]
    res = _generate_equal_option_dicts(conditions)
    expected = [
        ('regime == A', Regime.A),
        ('regime == E', Regime.E),
        ('regime == D', Regime.D),
        ('regime == NC', Regime.NC),
    ]
    assert expected == res


def test_generate_options_dict():
    parameter = Parameter('test', ParameterType.BOOLEAN)
    conditions: List[Condition] = [Equal(parameter, True), Equal(parameter, True)]
    res = _generate_options_dict(conditions)
    assert res == [('test == True', True), ('test != True', False)]


def test_generate_options_dict_2():
    parameter = Parameter('test', ParameterType.DATE)
    conditions = [
        Range(parameter, date(2020, 1, 1), date(2021, 1, 1), False, True),
        Littler(parameter, date(2020, 1, 1), True),
        Greater(parameter, date(2021, 1, 1), False),
    ]
    res = _generate_options_dict(conditions)
    str_dt_20 = '2020-01-01'
    str_dt_21 = '2021-01-01'
    expected = [
        (f'test < {str_dt_20}', date(2019, 12, 31)),
        (f'{str_dt_20} <= test < {str_dt_21}', date(2020, 7, 2)),
        (f'test >= {str_dt_21}', date(2021, 1, 2)),
    ]
    assert res == expected


def test_change_value():
    assert not _change_value(True)
    assert _change_value(False)
    assert _change_value(1) == 2
    assert _change_value(2.0) == 3
    assert _change_value(datetime(2020, 1, 1)) == datetime(2020, 1, 2)


def test_generate_combinations():
    parameter_1 = Parameter('test_1', ParameterType.DATE)
    parameter_2 = Parameter('test_2', ParameterType.BOOLEAN)
    options_1 = (parameter_1, [('test_1 < a', datetime(2021, 1, 1)), ('test_1 >= a', datetime(2022, 1, 1))])
    options_2 = (parameter_2, [('test_2 == True', True), ('test_2 != True', False)])
    res = _generate_combinations([options_1, options_2], False)
    expected: Combinations = {
        ('test_1 < a', 'test_2 == True'): {parameter_1: datetime(2021, 1, 1), parameter_2: True},
        ('test_1 < a', 'test_2 != True'): {parameter_1: datetime(2021, 1, 1), parameter_2: False},
        ('test_1 >= a', 'test_2 == True'): {parameter_1: datetime(2022, 1, 1), parameter_2: True},
        ('test_1 >= a', 'test_2 != True'): {parameter_1: datetime(2022, 1, 1), parameter_2: False},
    }
    assert expected == res

    parameter_1 = Parameter('test_1', ParameterType.DATE)
    parameter_2 = Parameter('test_2', ParameterType.BOOLEAN)
    options_1 = (parameter_1, [('test_1 < a', datetime(2021, 1, 1)), ('test_1 >= a', datetime(2022, 1, 1))])
    options_2 = (parameter_2, [('test_2 == True', True), ('test_2 != True', False)])
    res = _generate_combinations([options_1, options_2], True)
    expected: Combinations = {
        (): {},
        ('test_2 == True',): {parameter_2: True},
        ('test_2 != True',): {parameter_2: False},
        ('test_1 < a',): {parameter_1: datetime(2021, 1, 1)},
        ('test_1 < a', 'test_2 == True'): {parameter_1: datetime(2021, 1, 1), parameter_2: True},
        ('test_1 < a', 'test_2 != True'): {parameter_1: datetime(2021, 1, 1), parameter_2: False},
        ('test_1 >= a',): {parameter_1: datetime(2022, 1, 1)},
        ('test_1 >= a', 'test_2 == True'): {parameter_1: datetime(2022, 1, 1), parameter_2: True},
        ('test_1 >= a', 'test_2 != True'): {parameter_1: datetime(2022, 1, 1), parameter_2: False},
    }
    assert expected == res
