import random
from datetime import datetime, timedelta
from string import ascii_letters
from typing import Optional

import pytest

from envinorma.models import ArreteMinisteriel, EnrichedString, Regime, StructuredText
from envinorma.models.text_elements import estr
from envinorma.parametrization import (
    AlternativeSection,
    ConditionSource,
    EntityReference,
    Greater,
    Littler,
    NonApplicationCondition,
    Parametrization,
    ParametrizationError,
    SectionNotFoundWarning,
    SectionReference,
    _check_conditions_are_incompatible,
    _check_date_conditions_are_incompatible,
    _check_discrete_conditions_are_incompatible,
    _date_ranges_strictly_overlap,
    _extract_date_range,
    _extract_paths,
    _group,
    _ranges_strictly_overlap,
    add_titles_sequences,
    add_titles_sequences_section,
    check_parametrization_consistency,
    extract_titles_sequence,
    regenerate_paths,
)
from envinorma.parametrization.conditions import Condition, Equal, OrCondition, ParameterEnum, Range

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
    source = ConditionSource('', EntityReference(SectionReference((2,)), None))
    unique_path = (0,)
    entity = EntityReference(SectionReference(unique_path), None)
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    check_parametrization_consistency(
        Parametrization(
            [_NAC(entity, cd_1, source), _NAC(entity, cd_3, source)], [_AS(entity.section, new_text, cd_4, source)], []
        )
    )
    check_parametrization_consistency(Parametrization([_NAC(entity, cd_3, source)], [], []))
    with pytest.raises(ParametrizationError):
        check_parametrization_consistency(
            Parametrization(
                [_NAC(entity, cd_1, source), _NAC(entity, cd_5, source)],
                [_AS(entity.section, new_text, cd_6, source)],
                [],
            )
        )
    with pytest.raises(ParametrizationError):
        check_parametrization_consistency(
            Parametrization([_NAC(entity, cd_1, source), _NAC(entity, cd_1, source)], [], [])
        )


def _get_simple_text() -> StructuredText:
    sub_section_1 = StructuredText(estr('Section 1.1'), [], [], None)
    section_1 = StructuredText(estr('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(estr('Section 2'), [estr('bar')], [], None)
    return StructuredText(estr('Chapter I'), [estr('alinea'), estr('foo')], [section_1, section_2], None)


def _get_simple_am() -> ArreteMinisteriel:
    return ArreteMinisteriel(estr('arrete du 10/10/10'), [_get_simple_text()], [], None, id='FAKE_CID')


def test_extract_titles_sequence():
    with pytest.raises(ValueError):
        extract_titles_sequence(_get_simple_text(), (1, 3))

    with pytest.raises(ValueError):
        extract_titles_sequence(_get_simple_text(), (0, 0, 0))
    assert extract_titles_sequence(_get_simple_text(), ()) == []
    assert extract_titles_sequence(_get_simple_text(), (0,)) == ['Section 1']
    assert extract_titles_sequence(_get_simple_text(), (0, 0)) == ['Section 1', 'Section 1.1']
    assert extract_titles_sequence(_get_simple_text(), (1,)) == ['Section 2']


def test_add_titles_sequences_section():
    with pytest.raises(ValueError):
        add_titles_sequences_section(SectionReference((1, 3)), _get_simple_am())
    with pytest.raises(ValueError):
        add_titles_sequences_section(SectionReference((1, 0)), _get_simple_am())
    with pytest.raises(ValueError):
        add_titles_sequences_section(SectionReference((0, 0, 0, 0)), _get_simple_am())
    res = add_titles_sequences_section(SectionReference((0,)), _get_simple_am())
    assert res == SectionReference((0,), ['Chapter I'])
    res = add_titles_sequences_section(SectionReference((0, 0)), _get_simple_am())
    assert res == SectionReference((0, 0), ['Chapter I', 'Section 1'])
    res = add_titles_sequences_section(SectionReference((0, 1)), _get_simple_am())
    assert res == SectionReference((0, 1), ['Chapter I', 'Section 2'])
    res = add_titles_sequences_section(SectionReference((0, 0, 0)), _get_simple_am())
    assert res == SectionReference((0, 0, 0), ['Chapter I', 'Section 1', 'Section 1.1'])


def test_add_titles_sequences():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_4 = Greater(date_, dt_2)
    source = ConditionSource('', EntityReference(SectionReference((0, 1)), None))
    entity = EntityReference(SectionReference((0,)), None)
    section = SectionReference((0, 0, 0))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    res = add_titles_sequences(
        Parametrization([_NAC(entity, cd_1, source)], [_AS(section, new_text, cd_4, source)], []),
        _get_simple_am(),
    )
    new_source = ConditionSource('', EntityReference(SectionReference((0, 1), ['Chapter I', 'Section 2']), None))
    new_entity_0 = EntityReference(SectionReference((0,), ['Chapter I']), None)
    new_section = SectionReference((0, 0, 0), ['Chapter I', 'Section 1', 'Section 1.1'])
    assert res == Parametrization(
        [_NAC(new_entity_0, cd_1, new_source)], [_AS(new_section, new_text, cd_4, new_source)], []
    )


def test_extract_paths():
    with pytest.warns(SectionNotFoundWarning):
        _extract_paths(_get_simple_text(), ['Seerzection 1', 'Section 1.1'])

    with pytest.warns(SectionNotFoundWarning):
        _extract_paths(_get_simple_text(), ['Section 1', 'Section 1.1', 'Section 1.1.1'])
    assert _extract_paths(_get_simple_text(), []) == ()
    assert _extract_paths(_get_simple_text(), ['Section 1']) == (0,)
    assert _extract_paths(_get_simple_text(), ['Section 1', 'Section 1.1']) == (0, 0)
    assert _extract_paths(_get_simple_text(), ['Section 2']) == (1,)


def test_regenerate_paths():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_4 = Greater(date_, dt_2)
    source = ConditionSource('', EntityReference(SectionReference((19,), ['Chapter I', 'Section 2']), None))
    entity = EntityReference(SectionReference((19,), ['Chapter I']), None)
    section = SectionReference((19,), ['Chapter I', 'Section 1', 'Section 1.1'])
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    res = regenerate_paths(
        Parametrization([_NAC(entity, cd_1, source)], [_AS(section, new_text, cd_4, source)], []),
        _get_simple_am(),
    )
    new_source = ConditionSource('', EntityReference(SectionReference((0, 1), ['Chapter I', 'Section 2']), None))
    new_entity_0 = EntityReference(SectionReference((0,), ['Chapter I']), None)
    new_section = SectionReference((0, 0, 0), ['Chapter I', 'Section 1', 'Section 1.1'])
    assert res.alternative_sections[0] == _AS(new_section, new_text, cd_4, new_source)
    assert res == Parametrization(
        [_NAC(new_entity_0, cd_1, new_source)], [_AS(new_section, new_text, cd_4, new_source)], []
    )


def test_group():
    assert _group([], lambda x: x) == {}
    assert _group([1, 2, 3, 4, 1], lambda x: x) == {1: [1, 1], 2: [2], 3: [3], 4: [4]}
    assert _group([1, 2, -1], lambda x: abs(x)) == {1: [1, -1], 2: [2]}
    assert _group([{'key': 'value'}, {}], lambda x: x.get('key', '')) == {'value': [{'key': 'value'}], '': [{}]}


def _simple_nac(condition: Condition) -> NonApplicationCondition:
    source = ConditionSource('', EntityReference(SectionReference((0, 1)), None))
    target = EntityReference(SectionReference((0,)), None)
    return _NAC(target, condition, source)


def test_extract_conditions():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_2 = Greater(date_, dt_2)

    parametrization = Parametrization([], [], [])
    assert parametrization.extract_conditions() == []

    parametrization = Parametrization([_simple_nac(cd_1)], [], [])
    assert parametrization.extract_conditions() == [cd_1]

    parametrization = Parametrization([_simple_nac(cd_1), _simple_nac(cd_2)], [], [])
    assert parametrization.extract_conditions() == [cd_1, cd_2]
