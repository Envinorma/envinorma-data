from datetime import date, datetime

import pytest

from envinorma.back_office.pages.parametrization_edition import page_ids
from envinorma.back_office.pages.parametrization_edition.condition_form import _AND_ID, ConditionFormValues
from envinorma.back_office.pages.parametrization_edition.form_handling import (
    FormHandlingError,
    _assert_strictly_below,
    _build_condition,
    _build_new_text,
    _build_parameter_value,
    _build_section_reference,
    _build_source,
    _build_target_versions,
    _check_compatibility_and_build_range,
    _extract_parameter_to_conditions,
    _Modification,
    _NotSimplifiableError,
    _simplify_alineas,
    _simplify_condition,
    _simplify_mono_conditions,
    _try_building_range_condition,
)
from envinorma.back_office.pages.parametrization_edition.target_sections_form import TargetSectionFormValues
from envinorma.data import ArreteMinisteriel, Regime, StructuredText, dump_path
from envinorma.data.text_elements import EnrichedString, estr
from envinorma.parametrization import ConditionSource, EntityReference, SectionReference
from envinorma.parametrization.conditions import (
    AndCondition,
    Condition,
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


def _get_am() -> ArreteMinisteriel:
    subsections = [StructuredText(estr(''), [estr('al1.1.1'), estr('al1.1.2')], [], None)]
    sections = [StructuredText(estr(''), [estr('al1.1'), estr('al1.2')], subsections, None)]
    return ArreteMinisteriel(estr('Arrêté du 10/10/10'), sections, [], None, id='JORFTEXT')


def test_simplify_alineas():
    am = _get_am()
    assert _simplify_alineas(am, SectionReference((0,)), None) is None
    assert _simplify_alineas(am, SectionReference((0,)), [0, 1]) is None
    assert _simplify_alineas(am, SectionReference((0,)), [0]) == [0]
    assert _simplify_alineas(am, SectionReference((0, 0)), [0]) == [0]
    assert _simplify_alineas(am, SectionReference((0, 0)), [0, 1]) is None


def test_build_target_versions():
    am = _get_am()
    form_values = TargetSectionFormValues([], [], [], [])
    assert _build_target_versions(am, form_values) == []

    form_values = TargetSectionFormValues(['title'], ['content'], [dump_path((0, 0))], [])
    text = StructuredText(estr('title'), [estr('content')], [], None)
    modif = _Modification(SectionReference((0, 0)), None, text)
    res = _build_target_versions(am, form_values)
    modif.new_text.id = res[0].new_text.id
    assert _remove_ids(res) == _remove_ids([modif])

    form_values = TargetSectionFormValues([], [], [dump_path((0, 0))], [[0, 1]])
    modif = _Modification(SectionReference((0, 0)), None, None)
    assert _remove_ids(_build_target_versions(am, form_values)) == _remove_ids([modif])

    form_values = TargetSectionFormValues([], [], [dump_path((0, 0))], [[0]])
    modif = _Modification(SectionReference((0, 0)), [0], None)
    assert _build_target_versions(am, form_values) == [modif]

    form_values = TargetSectionFormValues([], [], [dump_path((0,))], [[0]])
    modif = _Modification(SectionReference((0,)), [0], None)
    assert _build_target_versions(am, form_values) == [modif]


def _remove_ids(obj):
    if isinstance(obj, list):
        for el in obj:
            _remove_ids(el)
    if isinstance(obj, StructuredText):
        _remove_ids(obj.outer_alineas)
        _remove_ids(obj.sections)
        _remove_ids(obj.title)
    if isinstance(obj, EnrichedString):
        obj.id = ''
    if isinstance(obj, _Modification):
        _remove_ids(obj.new_text)
    return obj


def test_build_new_text():
    assert _build_new_text(None, None) is None
    assert _build_new_text('', '') is None
    with pytest.raises(FormHandlingError):
        _build_new_text('aa', '')
    with pytest.raises(FormHandlingError):
        _build_new_text('', 'bb')
    with pytest.raises(FormHandlingError):
        _build_new_text('aa', None)
    with pytest.raises(FormHandlingError):
        _build_new_text(None, 'bb')
    assert _build_new_text('aa', 'bb').title.text == 'aa'
    assert _remove_ids(_build_new_text('aa', 'bb').outer_alineas) == _remove_ids([estr('bb')])


def test_build_condition():
    with pytest.raises(FormHandlingError):
        assert _build_condition(ConditionFormValues([], [], [], _AND_ID))

    res = Equal(ParameterEnum.DATE_DECLARATION.value, datetime(2020, 1, 1))
    assert _build_condition(ConditionFormValues(['Date de déclaration'], ['='], ['01/01/2020'], _AND_ID)) == res

    res = Range(ParameterEnum.DATE_DECLARATION.value, datetime(2020, 1, 1), datetime(2020, 1, 31))
    form_values = ConditionFormValues(['Date de déclaration'] * 2, ['>=', '<'], ['01/01/2020', '31/01/2020'], _AND_ID)
    assert _build_condition(form_values) == res

    cd_1 = Equal(ParameterEnum.DATE_DECLARATION.value, datetime(2020, 1, 1))
    cd_2 = Equal(ParameterEnum.REGIME.value, Regime.A)
    res = AndCondition([cd_1, cd_2])
    form_values = ConditionFormValues(['Date de déclaration', 'Régime'], ['=', '='], ['01/01/2020', 'A'], _AND_ID)
    assert _build_condition(form_values) == res


def test_build_source():
    with pytest.raises(FormHandlingError):
        _build_source('')
    assert _build_source('[1, 2]') == ConditionSource('', EntityReference(SectionReference((1, 2)), None))


def test_build_section_reference():
    with pytest.raises(FormHandlingError):
        _build_section_reference('')
    assert _build_section_reference('[1, 2, 3]') == SectionReference((1, 2, 3))
