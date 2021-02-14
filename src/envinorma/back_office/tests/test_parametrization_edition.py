from datetime import date

import pytest
from envinorma.back_office.parametrization_edition import (
    _AND_ID,
    _CONDITION_VARIABLES,
    _OR_ID,
    _assert_strictly_below,
    _build_parameter_value,
    _change_to_mono_conditions,
    _check_compatibility_and_build_range,
    _FormHandlingError,
    _get_str_target,
    _simplify_condition,
    _try_building_range_condition,
)
from envinorma.parametrization.conditions import (
    AndCondition,
    Equal,
    Greater,
    Littler,
    OrCondition,
    ParameterEnum,
    Range,
)


def test_change_to_mono_conditions():
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value
    res = _change_to_mono_conditions(Range(_date, date(2010, 1, 1), date(2020, 1, 1)))
    assert res[0] == _AND_ID
    assert len(res[1]) == 2
    assert res[1][0] == Littler(_date, date(2020, 1, 1), True)
    assert res[1][1] == Greater(_date, date(2010, 1, 1), False)

    res = _change_to_mono_conditions(Range(_date, date(2010, 1, 1), date(2020, 1, 1), True, True))
    assert res[0] == _AND_ID
    assert len(res[1]) == 2
    assert res[1][0] == Littler(_date, date(2020, 1, 1), True)
    assert res[1][1] == Greater(_date, date(2010, 1, 1), True)

    res = _change_to_mono_conditions(Range(_date, date(2010, 1, 1), date(2020, 1, 1), False, False))
    assert res[0] == _AND_ID
    assert len(res[1]) == 2
    assert res[1][0] == Littler(_date, date(2020, 1, 1), False)
    assert res[1][1] == Greater(_date, date(2010, 1, 1), False)

    res = _change_to_mono_conditions(Littler(_date, date(2010, 1, 1), False))
    assert res[0] == _AND_ID
    assert len(res[1]) == 1
    assert res[1][0] == Littler(_date, date(2010, 1, 1), False)

    res = _change_to_mono_conditions(Greater(_date, date(2010, 1, 1), False))
    assert res[0] == _AND_ID
    assert len(res[1]) == 1
    assert res[1][0] == Greater(_date, date(2010, 1, 1), False)

    res = _change_to_mono_conditions(OrCondition([Greater(_date, date(2010, 1, 1), False), Equal(_regime, 'A')]))
    assert res[0] == _OR_ID
    assert len(res[1]) == 2
    assert res[1][0] == Greater(_date, date(2010, 1, 1), False)
    assert res[1][1] == Equal(_regime, 'A')


def test_simplify_condition():
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value

    with pytest.raises(_FormHandlingError):
        _simplify_condition(AndCondition([]))
    with pytest.raises(_FormHandlingError):
        _simplify_condition(OrCondition([]))
    cond = Greater(_date, date(2010, 1, 1), False)
    assert _simplify_condition(OrCondition([cond])) == cond
    assert _simplify_condition(AndCondition([cond])) == cond
    or_cond = OrCondition([cond, cond, cond])
    assert _simplify_condition(or_cond) == or_cond
    or_cond = OrCondition([cond, cond])
    assert _simplify_condition(or_cond) == or_cond
    and_cond = AndCondition([cond, cond, cond])
    assert _simplify_condition(and_cond) == and_cond
    and_cond = AndCondition([cond, cond])
    with pytest.raises(_FormHandlingError):
        _simplify_condition(and_cond)

    cond = Equal(_regime, 'A')
    and_cond = AndCondition([cond, cond])
    with pytest.raises(_FormHandlingError):
        _simplify_condition(and_cond)

    cond = Equal(_regime, 'A')
    or_cond = OrCondition([cond, cond])
    assert _simplify_condition(or_cond) == or_cond

    cond_1 = Greater(_date, date(2010, 1, 1))
    cond_2 = Littler(_date, date(2010, 1, 1))
    and_cond = AndCondition([cond_1, cond_2])
    with pytest.raises(_FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, date(2010, 1, 1))
    cond_2 = Littler(_date, date(2010, 1, 1))
    and_cond = AndCondition([cond_1, cond_2])
    with pytest.raises(_FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, date(2010, 1, 1))
    cond_2 = Equal(_date, date(2010, 1, 1))
    and_cond = AndCondition([cond_1, cond_2])
    with pytest.raises(_FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, date(2020, 1, 1))
    cond_2 = Greater(_date, date(2010, 1, 1))
    and_cond = AndCondition([cond_1, cond_2])
    res = _simplify_condition(and_cond)
    assert isinstance(res, Range)


def test_check_compatibility_and_build_range_try():
    _date = ParameterEnum.DATE_AUTORISATION.value
    cond_1 = Littler(_date, date(2020, 1, 1))
    cond_2 = Greater(_date, date(2010, 1, 1))
    assert isinstance(_check_compatibility_and_build_range(_date, cond_1, cond_2), Range)

    _date = ParameterEnum.DATE_AUTORISATION.value
    cond_1 = Littler(_date, date(2020, 1, 1))
    cond_2 = Greater(_date, date(2020, 1, 1))
    with pytest.raises(_FormHandlingError):
        _check_compatibility_and_build_range(_date, cond_1, cond_2)


def test_building_range_condition():
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value

    assert _try_building_range_condition([]) is None
    assert _try_building_range_condition([AndCondition([])]) is None
    assert _try_building_range_condition([OrCondition([])]) is None
    cond = Greater(_date, date(2010, 1, 1), False)
    assert _try_building_range_condition([cond]) is None
    assert _try_building_range_condition([cond, cond, cond]) is None
    cond_1 = Equal(_regime, 'A')
    cond_2 = Greater(_date, date(2020, 1, 1))
    assert _try_building_range_condition([cond_1, cond_2]) is None

    _date = ParameterEnum.DATE_AUTORISATION.value
    cond_1 = Littler(_date, date(2020, 1, 1))
    cond_2 = Greater(_date, date(2020, 1, 1))
    with pytest.raises(_FormHandlingError):
        _try_building_range_condition([cond_1, cond_2])

    _date = ParameterEnum.DATE_AUTORISATION.value
    cond_1 = Littler(_date, date(2020, 1, 1))
    cond_2 = Greater(_date, date(2010, 1, 1))
    res = _try_building_range_condition([cond_1, cond_2])
    assert isinstance(res, Range)
    assert res.left == date(2010, 1, 1)
    assert res.right == date(2020, 1, 1)


def test_assert_strictly_below():
    with pytest.raises(_FormHandlingError):
        _assert_strictly_below(1, 1)
    with pytest.raises(_FormHandlingError):
        _assert_strictly_below(2, 1)
    assert _assert_strictly_below(1, 2) is None

    with pytest.raises(_FormHandlingError):
        _assert_strictly_below(date(2010, 1, 1), date(2010, 1, 1))
    with pytest.raises(_FormHandlingError):
        _assert_strictly_below(date(2020, 1, 1), date(2010, 1, 1))
    assert _assert_strictly_below(date(2010, 1, 1), date(2020, 1, 1)) is None


def test_build_parameter_value():
    for param in _CONDITION_VARIABLES.values():
        try:
            _build_parameter_value(param.value.type, '')
        except Exception as exc:
            if 'Ce type de paramètre' in str(exc):
                raise exc


def test_get_str_target():
    for param in _CONDITION_VARIABLES.values():
        try:
            _get_str_target('test', param.value.type)
        except Exception as exc:
            if 'Unhandled parameter type' in str(exc):
                raise exc
