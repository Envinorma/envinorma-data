from datetime import date

import pytest

from envinorma.back_office.pages.parametrization_edition import page_ids
from envinorma.back_office.pages.parametrization_edition.form_handling import (
    FormHandlingError,
    _assert_strictly_below,
    _build_parameter_value,
    _check_compatibility_and_build_range,
    _extract_parameter_to_conditions,
    _NotSimplifiableError,
    _simplify_condition,
    _simplify_mono_conditions,
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


def test_simplify_condition():
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    with pytest.raises(FormHandlingError):
        _simplify_condition(AndCondition([]))
    with pytest.raises(FormHandlingError):
        _simplify_condition(OrCondition([]))
    cond = Greater(_date, d1, False)
    assert _simplify_condition(OrCondition([cond])) == cond
    assert _simplify_condition(AndCondition([cond])) == cond
    or_cond = OrCondition([cond, cond, cond])
    assert _simplify_condition(or_cond) == or_cond
    or_cond = OrCondition([cond, cond])
    assert _simplify_condition(or_cond) == or_cond
    and_cond = AndCondition([cond, cond, cond])
    assert _simplify_condition(and_cond) == and_cond
    and_cond = AndCondition([cond, cond])
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond = Equal(_regime, 'A')
    and_cond = AndCondition([cond, cond])
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond = Equal(_regime, 'A')
    or_cond = OrCondition([cond, cond])
    assert _simplify_condition(or_cond) == or_cond

    cond_1 = Greater(_date, d1)
    cond_2 = Littler(_date, d1)
    and_cond = AndCondition([cond_1, cond_2])
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, d1)
    cond_2 = Littler(_date, d1)
    and_cond = AndCondition([cond_1, cond_2])
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, d1)
    cond_2 = Equal(_date, d1)
    and_cond = AndCondition([cond_1, cond_2])
    with pytest.raises(FormHandlingError):
        _simplify_condition(and_cond)

    cond_1 = Littler(_date, d2)
    cond_2 = Greater(_date, d1)
    and_cond = AndCondition([cond_1, cond_2])
    res = _simplify_condition(and_cond)
    assert res == Range(_date, d1, d2)

    and_cond = AndCondition([Littler(_date, d2), Greater(_date, d1), Equal(_regime, 'A')])
    res = _simplify_condition(and_cond)
    assert res == AndCondition([Range(_date, d1, d2), Equal(_regime, 'A')])


def test_check_compatibility_and_build_range_try():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)

    _date = ParameterEnum.DATE_AUTORISATION.value
    cond_1 = Littler(_date, d2)
    cond_2 = Greater(_date, d1)
    assert isinstance(_check_compatibility_and_build_range(_date, cond_1, cond_2), Range)

    _date = ParameterEnum.DATE_AUTORISATION.value
    cond_1 = Littler(_date, d2)
    cond_2 = Greater(_date, d2)
    with pytest.raises(FormHandlingError):
        _check_compatibility_and_build_range(_date, cond_1, cond_2)


def test_building_range_condition():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    date_ = ParameterEnum.DATE_AUTORISATION.value
    quantity = ParameterEnum.RUBRIQUE_QUANTITY.value
    reg = ParameterEnum.REGIME.value

    assert _try_building_range_condition([]) is None

    with pytest.raises(ValueError):
        _try_building_range_condition([AndCondition([])])

    with pytest.raises(ValueError):
        _try_building_range_condition([OrCondition([])])

    assert _try_building_range_condition([Greater(date_, d1, False)]) == Greater(date_, d1, False)
    assert _try_building_range_condition([Greater(date_, d1, False) for _ in range(3)]) is None

    res = _try_building_range_condition([Equal(reg, 'A'), Greater(date_, d2)])
    assert res == AndCondition([Equal(reg, 'A'), Greater(date_, d2)])

    with pytest.raises(FormHandlingError):
        _try_building_range_condition([Littler(date_, d2), Greater(date_, d2)])

    res = _try_building_range_condition([Littler(date_, d2), Greater(date_, d1)])
    assert res == Range(date_, d1, d2)

    res = _try_building_range_condition([Littler(date_, d2), Greater(date_, d1), Equal(reg, 'E'), Equal(quantity, 10)])
    assert res == AndCondition([Range(date_, d1, d2), Equal(reg, 'E'), Equal(quantity, 10)])

    res = _try_building_range_condition([Littler(quantity, 20), Greater(quantity, 10), Equal(reg, 'D')])
    assert res == AndCondition([Range(quantity, 10, 20), Equal(reg, 'D')])


def test_simplify_mono_conditions():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    d3 = date(2030, 1, 1)
    date_ = ParameterEnum.DATE_AUTORISATION.value
    quantity = ParameterEnum.RUBRIQUE_QUANTITY.value
    reg = ParameterEnum.REGIME.value

    with pytest.raises(_NotSimplifiableError):
        _simplify_mono_conditions(date_, [])

    with pytest.raises(_NotSimplifiableError):
        _simplify_mono_conditions(date_, [Equal(date_, d1), Equal(date_, d2), Equal(date_, d3)])

    res = _simplify_mono_conditions(quantity, [Littler(quantity, 100), Greater(quantity, 10)])
    assert res == Range(quantity, 10, 100)

    with pytest.raises(FormHandlingError):
        _simplify_mono_conditions(reg, [Littler(quantity, 10), Greater(quantity, 100)])

    assert _simplify_mono_conditions(date_, [Littler(date_, d1)]) == Littler(date_, d1)
    assert _simplify_mono_conditions(date_, [Greater(date_, d1)]) == Greater(date_, d1)
    assert _simplify_mono_conditions(date_, [Equal(date_, d1)]) == Equal(date_, d1)


def test_assert_strictly_below():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)

    with pytest.raises(FormHandlingError):
        _assert_strictly_below(1, 1)
    with pytest.raises(FormHandlingError):
        _assert_strictly_below(2, 1)
    assert _assert_strictly_below(1, 2) is None

    with pytest.raises(FormHandlingError):
        _assert_strictly_below(d1, d1)
    with pytest.raises(FormHandlingError):
        _assert_strictly_below(d2, d1)
    assert _assert_strictly_below(d1, d2) is None


def test_build_parameter_value():
    for param in page_ids.CONDITION_VARIABLES.values():
        try:
            _build_parameter_value(param.value.type, '')
        except Exception as exc:
            if 'Ce type de paramètre' in str(exc):
                raise exc


def test_extract_parameter_to_conditions():
    d1 = date(2010, 1, 1)
    d2 = date(2020, 1, 1)
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value

    res = _extract_parameter_to_conditions([Littler(_date, d2), Greater(_date, d1), Equal(_regime, 'A')])
    assert res == {_date: [Littler(_date, d2), Greater(_date, d1)], _regime: [Equal(_regime, 'A')]}
    res = _extract_parameter_to_conditions([Littler(_date, d2), Greater(_date, d1)])
    assert res == {_date: [Littler(_date, d2), Greater(_date, d1)]}
    res = _extract_parameter_to_conditions([Greater(_date, d1), Equal(_regime, 'A')])
    assert res == {_date: [Greater(_date, d1)], _regime: [Equal(_regime, 'A')]}
    res = _extract_parameter_to_conditions([Greater(_date, d1)])
    assert res == {_date: [Greater(_date, d1)]}
    res = _extract_parameter_to_conditions([])
    assert res == {}
