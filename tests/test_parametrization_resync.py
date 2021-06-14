from datetime import datetime, timedelta

import pytest

from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import estr
from envinorma.parametrization.models.condition import Greater, Range
from envinorma.parametrization.models.parameter import ParameterEnum
from envinorma.parametrization.models.parametrization import (
    AlternativeSection,
    ConditionSource,
    EntityReference,
    InapplicableSection,
    Parametrization,
    SectionReference,
)
from envinorma.parametrization.resync import (
    SectionNotFoundWarning,
    _add_titles_sequences_section,
    _extract_paths,
    _extract_titles_sequence,
    add_titles_sequences,
    regenerate_paths,
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
        _extract_titles_sequence(_get_simple_text(), (1, 3))

    with pytest.raises(ValueError):
        _extract_titles_sequence(_get_simple_text(), (0, 0, 0))
    assert _extract_titles_sequence(_get_simple_text(), ()) == []
    assert _extract_titles_sequence(_get_simple_text(), (0,)) == ['Section 1']
    assert _extract_titles_sequence(_get_simple_text(), (0, 0)) == ['Section 1', 'Section 1.1']
    assert _extract_titles_sequence(_get_simple_text(), (1,)) == ['Section 2']


def test_add_titles_sequences_section():
    with pytest.raises(ValueError):
        _add_titles_sequences_section(SectionReference((1, 3)), _get_simple_am())
    with pytest.raises(ValueError):
        _add_titles_sequences_section(SectionReference((1, 0)), _get_simple_am())
    with pytest.raises(ValueError):
        _add_titles_sequences_section(SectionReference((0, 0, 0, 0)), _get_simple_am())
    res = _add_titles_sequences_section(SectionReference((0,)), _get_simple_am())
    assert res == SectionReference((0,), ['Chapter I'])
    res = _add_titles_sequences_section(SectionReference((0, 0)), _get_simple_am())
    assert res == SectionReference((0, 0), ['Chapter I', 'Section 1'])
    res = _add_titles_sequences_section(SectionReference((0, 1)), _get_simple_am())
    assert res == SectionReference((0, 1), ['Chapter I', 'Section 2'])
    res = _add_titles_sequences_section(SectionReference((0, 0, 0)), _get_simple_am())
    assert res == SectionReference((0, 0, 0), ['Chapter I', 'Section 1', 'Section 1.1'])


def test_add_titles_sequences():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_4 = Greater(date_, dt_2)
    source = ConditionSource(EntityReference(SectionReference((0, 1)), None))
    entity = EntityReference(SectionReference((0,)), None)
    section = SectionReference((0, 0, 0))
    new_text = StructuredText(estr('Art. 2'), [estr('version modifiée')], [], None)
    res = add_titles_sequences(
        Parametrization(
            [InapplicableSection(entity, cd_1, source)], [AlternativeSection(section, new_text, cd_4, source)], []
        ),
        _get_simple_am(),
    )
    new_source = ConditionSource(EntityReference(SectionReference((0, 1), ['Chapter I', 'Section 2']), None))
    new_entity_0 = EntityReference(SectionReference((0,), ['Chapter I']), None)
    new_section = SectionReference((0, 0, 0), ['Chapter I', 'Section 1', 'Section 1.1'])
    assert res == Parametrization(
        [InapplicableSection(new_entity_0, cd_1, new_source)],
        [AlternativeSection(new_section, new_text, cd_4, new_source)],
        [],
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
    source = ConditionSource(EntityReference(SectionReference((19,), ['Chapter I', 'Section 2']), None))
    entity = EntityReference(SectionReference((19,), ['Chapter I']), None)
    section = SectionReference((19,), ['Chapter I', 'Section 1', 'Section 1.1'])
    new_text = StructuredText(estr('Art. 2'), [estr('version modifiée')], [], None)
    res = regenerate_paths(
        Parametrization(
            [InapplicableSection(entity, cd_1, source)], [AlternativeSection(section, new_text, cd_4, source)], []
        ),
        _get_simple_am(),
    )
    new_source = ConditionSource(EntityReference(SectionReference((0, 1), ['Chapter I', 'Section 2']), None))
    new_entity_0 = EntityReference(SectionReference((0,), ['Chapter I']), None)
    new_section = SectionReference((0, 0, 0), ['Chapter I', 'Section 1', 'Section 1.1'])
    assert res.alternative_sections[0] == AlternativeSection(new_section, new_text, cd_4, new_source)
    assert res == Parametrization(
        [InapplicableSection(new_entity_0, cd_1, new_source)],
        [AlternativeSection(new_section, new_text, cd_4, new_source)],
        [],
    )
