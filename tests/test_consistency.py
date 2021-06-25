from datetime import datetime, timedelta

import pytest

from envinorma.models.classement import Regime
from envinorma.parametrization.consistency import (
    _check_date_conditions_not_compatible,
    _check_discrete_conditions_not_compatible,
    _date_ranges_strictly_overlap,
    _extract_date_range,
    _ranges_strictly_overlap,
    check_conditions_not_compatible,
)
from envinorma.parametrization.exceptions import ParametrizationError
from envinorma.parametrization.models.condition import Equal, Greater, Littler, OrCondition, Range
from envinorma.parametrization.models.parameter import ParameterEnum


def test_check_conditions_not_compatible():
    for parameter in ParameterEnum:
        check_conditions_not_compatible([Equal(parameter.value, '')], parameter.value)


def test_check_discrete_conditions_not_compatible():
    reg = ParameterEnum.REGIME.value
    _check_discrete_conditions_not_compatible([Equal(reg, Regime.E)], reg)
    _check_discrete_conditions_not_compatible([Equal(reg, Regime.E), Equal(reg, Regime.D)], reg)
    _check_discrete_conditions_not_compatible([Equal(reg, Regime.E), Equal(reg, Regime.D), Equal(reg, Regime.A)], reg)
    _check_discrete_conditions_not_compatible(
        [OrCondition([Equal(reg, Regime.E), Equal(reg, Regime.D), Equal(reg, Regime.A)])], reg
    )

    with pytest.raises(ParametrizationError):
        _check_discrete_conditions_not_compatible([Equal(reg, Regime.E), Equal(reg, Regime.E)], reg)
    with pytest.raises(ParametrizationError):
        _check_discrete_conditions_not_compatible(
            [OrCondition([Equal(reg, Regime.E), Equal(reg, Regime.D)]), Equal(reg, Regime.D)], reg
        )
    with pytest.raises(ParametrizationError):
        _check_discrete_conditions_not_compatible(
            [OrCondition([Littler(reg, Regime.E), Equal(reg, Regime.D)]), Equal(reg, Regime.A)], reg
        )


def test_extract_date_range():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    assert _extract_date_range(Range(date_, dt_1, dt_2)) == (dt_1, dt_2)
    assert _extract_date_range(Equal(date_, dt_1)) == (dt_1, dt_1)
    assert _extract_date_range(Littler(date_, dt_1)) == (None, dt_1)
    assert _extract_date_range(Greater(date_, dt_1)) == (dt_1, None)


def test_ranges_strictly_overlap():
    assert not _ranges_strictly_overlap([])
    assert not _ranges_strictly_overlap([(0, 1)])
    assert not _ranges_strictly_overlap([(0, 0)])
    assert not _ranges_strictly_overlap([(0, 0), (0, 1)])
    assert not _ranges_strictly_overlap([(0, 0), (0, 1), (1, 2)])
    assert not _ranges_strictly_overlap([(0, 0), (0, 1), (1, 2), (3, 4)])
    assert not _ranges_strictly_overlap([(4, 5), (0, 0), (0, 1), (1, 2), (3, 4)])
    assert _ranges_strictly_overlap([(4, 5), (4.5, 4.5)])
    assert _ranges_strictly_overlap([(4, 5), (4.5, 10.5)])
    assert _ranges_strictly_overlap([(4, 5), (0, 10.5)])
    assert _ranges_strictly_overlap([(4, 5), (-10, 4.001)])


def test_date_ranges_strictly_overlap():
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    dt_3 = dt_1 + timedelta(days=3)
    assert not _date_ranges_strictly_overlap([])
    assert not _date_ranges_strictly_overlap([(dt_1, dt_2)])
    assert not _date_ranges_strictly_overlap([(dt_1, dt_2), (dt_2, dt_3)])
    assert not _date_ranges_strictly_overlap([(dt_1, dt_2), (dt_2, dt_3), (None, dt_1)])
    assert not _date_ranges_strictly_overlap([(dt_1, dt_2), (dt_2, dt_3), (None, dt_1), (dt_3, None)])
    assert _date_ranges_strictly_overlap([(dt_1, dt_3), (dt_2, dt_3), (None, dt_1), (dt_3, None)])
    assert _date_ranges_strictly_overlap([(dt_1, dt_2), (dt_2, dt_3), (None, dt_3), (dt_3, None)])
    assert _date_ranges_strictly_overlap([(dt_1, dt_2), (dt_2, dt_3), (None, dt_1), (dt_2, None)])
    assert _date_ranges_strictly_overlap([(dt_1, dt_1), (None, None)])


def test_check_date_conditions_not_compatible():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_2 = Equal(date_, dt_1)
    cd_3 = Littler(date_, dt_1)
    cd_4 = Greater(date_, dt_2)

    _check_date_conditions_not_compatible([cd_1], date_)
    _check_date_conditions_not_compatible([cd_1, cd_2], date_)
    _check_date_conditions_not_compatible([cd_1, cd_3, cd_4], date_)
    _check_date_conditions_not_compatible([cd_2], date_)
    _check_date_conditions_not_compatible([cd_3], date_)
    _check_date_conditions_not_compatible([cd_4], date_)

    cd_5 = Littler(date_, dt_2)
    cd_6 = Greater(date_, dt_1)
    with pytest.raises(ParametrizationError):
        _check_date_conditions_not_compatible([cd_5, cd_6], date_)
    with pytest.raises(ParametrizationError):
        _check_date_conditions_not_compatible([cd_1, cd_6], date_)
    with pytest.raises(ParametrizationError):
        _check_date_conditions_not_compatible([cd_5, cd_1], date_)
