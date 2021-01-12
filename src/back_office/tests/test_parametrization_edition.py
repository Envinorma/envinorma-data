from datetime import date
from lib.parametrization import Equal, Greater, Littler, OrCondition, ParameterEnum, Range
from back_office.parametrization_edition import _simplify_condition, _AND_ID, _OR_ID


def test_simplify_condition():
    _date = ParameterEnum.DATE_AUTORISATION.value
    _regime = ParameterEnum.REGIME.value
    res = _simplify_condition(Range(_date, date(2010, 1, 1), date(2020, 1, 1)))
    assert res[0] == _AND_ID
    assert len(res[1]) == 2
    assert res[1][0] == Littler(_date, date(2020, 1, 1), True)
    assert res[1][1] == Greater(_date, date(2010, 1, 1), False)

    res = _simplify_condition(Range(_date, date(2010, 1, 1), date(2020, 1, 1), True, True))
    assert res[0] == _AND_ID
    assert len(res[1]) == 2
    assert res[1][0] == Littler(_date, date(2020, 1, 1), True)
    assert res[1][1] == Greater(_date, date(2010, 1, 1), True)

    res = _simplify_condition(Range(_date, date(2010, 1, 1), date(2020, 1, 1), False, False))
    assert res[0] == _AND_ID
    assert len(res[1]) == 2
    assert res[1][0] == Littler(_date, date(2020, 1, 1), False)
    assert res[1][1] == Greater(_date, date(2010, 1, 1), False)

    res = _simplify_condition(Littler(_date, date(2010, 1, 1), False))
    assert res[0] == _AND_ID
    assert len(res[1]) == 1
    assert res[1][0] == Littler(_date, date(2010, 1, 1), False)

    res = _simplify_condition(Greater(_date, date(2010, 1, 1), False))
    assert res[0] == _AND_ID
    assert len(res[1]) == 1
    assert res[1][0] == Greater(_date, date(2010, 1, 1), False)

    res = _simplify_condition(OrCondition([Greater(_date, date(2010, 1, 1), False), Equal(_regime, 'A')]))
    assert res[0] == _OR_ID
    assert len(res[1]) == 2
    assert res[1][0] == Greater(_date, date(2010, 1, 1), False)
    assert res[1][1] == Equal(_regime, 'A')
