import random
from datetime import datetime, timedelta
from string import ascii_letters
from typing import Optional

import pytest
from lib.conditions import Equal, OrCondition, ParameterEnum, Range
from lib.data import EnrichedString, Regime, StructuredText
from lib.parametrization import (
    AlternativeSection,
    ConditionSource,
    EntityReference,
    Greater,
    Littler,
    NonApplicationCondition,
    Parametrization,
    ParametrizationError,
    SectionReference,
    _check_conditions_are_incompatible,
    _check_date_conditions_are_incompatible,
    _check_discrete_conditions_are_incompatible,
    _date_ranges_strictly_overlap,
    _extract_date_range,
    _ranges_strictly_overlap,
    check_parametrization_consistency,
)

_NAC = NonApplicationCondition
_AS = AlternativeSection


def _random_string() -> str:
    return ''.join([random.choice(ascii_letters) for _ in range(9)])


def _random_enriched_string() -> EnrichedString:
    return EnrichedString(_random_string(), [], None)


def _str(text: Optional[str] = None) -> EnrichedString:
    return EnrichedString(text) if text else _random_enriched_string()


def test_check_conditions_are_incompatible():
    for parameter in ParameterEnum:
        _check_conditions_are_incompatible([Equal(parameter.value, '')], parameter.value)


def test_check_discrete_conditions_are_incompatible():
    reg = ParameterEnum.REGIME.value
    _check_discrete_conditions_are_incompatible([Equal(reg, Regime.E)], reg)
    _check_discrete_conditions_are_incompatible([Equal(reg, Regime.E), Equal(reg, Regime.D)], reg)
    _check_discrete_conditions_are_incompatible([Equal(reg, Regime.E), Equal(reg, Regime.D), Equal(reg, Regime.A)], reg)
    _check_discrete_conditions_are_incompatible(
        [OrCondition([Equal(reg, Regime.E), Equal(reg, Regime.D), Equal(reg, Regime.A)])], reg
    )

    with pytest.raises(ParametrizationError):
        _check_discrete_conditions_are_incompatible([Equal(reg, Regime.E), Equal(reg, Regime.E)], reg)
    with pytest.raises(ParametrizationError):
        _check_discrete_conditions_are_incompatible(
            [OrCondition([Equal(reg, Regime.E), Equal(reg, Regime.D)]), Equal(reg, Regime.D)], reg
        )
    with pytest.raises(ParametrizationError):
        _check_discrete_conditions_are_incompatible(
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


def test_check_date_conditions_are_incompatible():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_2 = Equal(date_, dt_1)
    cd_3 = Littler(date_, dt_1)
    cd_4 = Greater(date_, dt_2)

    _check_date_conditions_are_incompatible([cd_1], date_)
    _check_date_conditions_are_incompatible([cd_1, cd_2], date_)
    _check_date_conditions_are_incompatible([cd_1, cd_3, cd_4], date_)
    _check_date_conditions_are_incompatible([cd_2], date_)
    _check_date_conditions_are_incompatible([cd_3], date_)
    _check_date_conditions_are_incompatible([cd_4], date_)

    cd_5 = Littler(date_, dt_2)
    cd_6 = Greater(date_, dt_1)
    with pytest.raises(ParametrizationError):
        _check_date_conditions_are_incompatible([cd_5, cd_6], date_)
    with pytest.raises(ParametrizationError):
        _check_date_conditions_are_incompatible([cd_1, cd_6], date_)
    with pytest.raises(ParametrizationError):
        _check_date_conditions_are_incompatible([cd_5, cd_1], date_)


@pytest.mark.filterwarnings('ignore')  # for inconsistency warnings
def test_check_parametrization_consistency():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_3 = Littler(date_, dt_1)
    cd_4 = Greater(date_, dt_2)
    cd_5 = Littler(date_, dt_2)
    cd_6 = Greater(date_, dt_1)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None, False))
    unique_path = (0,)
    entity = EntityReference(SectionReference(unique_path), None)
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    check_parametrization_consistency(
        Parametrization(
            [_NAC(entity, cd_1, source), _NAC(entity, cd_3, source)], [_AS(entity.section, new_text, cd_4, source)]
        )
    )
    check_parametrization_consistency(Parametrization([_NAC(entity, cd_3, source)], []))
    with pytest.raises(ParametrizationError):
        check_parametrization_consistency(
            Parametrization(
                [_NAC(entity, cd_1, source), _NAC(entity, cd_5, source)], [_AS(entity.section, new_text, cd_6, source)]
            )
        )
    with pytest.raises(ParametrizationError):
        check_parametrization_consistency(Parametrization([_NAC(entity, cd_1, source), _NAC(entity, cd_1, source)], []))
