from datetime import datetime
from lib.parametric_am import (
    Equal,
    Greater,
    Littler,
    ParameterType,
    Range,
    _mean,
    _extract_interval_midpoints,
    _generate_options_dict,
    _extract_sorted_targets,
    _generate_combinations,
    _change_value,
    Parameter,
)


def test_mean():
    assert _mean(0, 2) == 1
    assert _mean(datetime(2020, 1, 1), datetime(2020, 1, 3)) == datetime(2020, 1, 2)


def test_extract_interval_midpoints():
    assert _extract_interval_midpoints([0, 1, 2, 3]) == [-1, 0.5, 1.5, 2.5, 4]
    res = [datetime(2019, 12, 31), datetime(2020, 1, 2), datetime(2020, 1, 4)]
    assert _extract_interval_midpoints([datetime(2020, 1, 1), datetime(2020, 1, 3)]) == res


def test_generate_options_dict():
    parameter = Parameter('test', ParameterType.BOOLEAN)
    conditions = [Equal(parameter, True), Equal(parameter, True)]
    res = _generate_options_dict(conditions)
    assert len(res) == 2
    assert 'test == True' in res
    assert 'test != True' in res
    assert res['test == True'] == (parameter, True)
    assert res['test != True'] == (parameter, False)


def test_extract_sorted_targets():
    parameter = Parameter('test', ParameterType.DATE)
    conditions = [
        Range(parameter, datetime(2020, 1, 1), datetime(2021, 1, 1), False, True),
        Littler(parameter, datetime(2020, 1, 1), True),
        Greater(parameter, datetime(2021, 1, 1), False),
    ]
    assert _extract_sorted_targets(conditions, True) == [datetime(2020, 1, 1), datetime(2021, 1, 1)]


def test_generate_options_dict_2():
    parameter = Parameter('test', ParameterType.DATE)
    conditions = [
        Range(parameter, datetime(2020, 1, 1), datetime(2021, 1, 1), False, True),
        Littler(parameter, datetime(2020, 1, 1), True),
        Greater(parameter, datetime(2021, 1, 1), False),
    ]
    res = _generate_options_dict(conditions)
    assert len(res) == 3
    str_dt_20 = '2020-01-01 00:00:00'
    str_dt_21 = '2021-01-01 00:00:00'
    assert f'test < {str_dt_20}' in res
    assert f'test < {str_dt_21}' in res
    assert f'test >= {str_dt_21}' in res
    assert res[f'test < {str_dt_20}'] == (parameter, datetime(2019, 12, 31))
    assert res[f'test < {str_dt_21}'] == (parameter, datetime(2020, 7, 2, 1, 0))
    assert res[f'test >= {str_dt_21}'] == (parameter, datetime(2021, 1, 2))


def test_change_value():
    assert not _change_value(True)
    assert _change_value(False)
    assert _change_value(1) == 2
    assert _change_value(2.0) == 3
    assert _change_value(datetime(2020, 1, 1)) == datetime(2020, 1, 2)


def test_generate_combinations():
    parameter_1 = Parameter('test_1', ParameterType.DATE)
    parameter_2 = Parameter('test_2', ParameterType.BOOLEAN)
    option_dict_1 = {
        'test_1 < a': (parameter_1, datetime(2021, 1, 1)),
        'test_1 >= a': (parameter_1, datetime(2022, 1, 1)),
    }
    option_dict_2 = {'test_2 == True': (parameter_2, True), 'test_2 != True': (parameter_2, False)}
    res = _generate_combinations([option_dict_1, option_dict_2])
    assert len(res) == 4
    assert ('test_2 == True', 'test_1 < a') in res
    assert ('test_2 != True', 'test_1 < a') in res
    assert ('test_2 == True', 'test_1 >= a') in res
    assert ('test_2 != True', 'test_1 >= a') in res
