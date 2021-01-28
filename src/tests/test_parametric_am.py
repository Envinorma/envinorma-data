import random
from copy import copy
from dataclasses import replace
from datetime import datetime, timedelta
from string import ascii_letters
from typing import List, Optional

from lib.data import ArreteMinisteriel, EnrichedString, Regime, StructuredText, StructuredTextSignature
from lib.parametric_am import (
    _apply_parameter_values_to_am,
    _change_value,
    _date_not_in_parametrization,
    _extract_installation_date_criterion,
    _extract_interval_midpoints,
    _extract_parameters_from_parametrization,
    _extract_sorted_targets,
    _extract_warning,
    _extract_warnings,
    _generate_combinations,
    _generate_equal_option_dicts,
    _generate_options_dict,
    is_satisfied,
    _mean,
    generate_all_am_versions,
)
from lib.parametrization import (
    AlternativeSection,
    AndCondition,
    Condition,
    ConditionSource,
    EntityReference,
    Equal,
    Greater,
    Littler,
    NonApplicationCondition,
    OrCondition,
    Parameter,
    ParameterEnum,
    ParameterType,
    Parametrization,
    Range,
    SectionReference,
)


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
    assert len(res) == 2
    assert 'test == True' in res
    assert 'test != True' in res
    assert res['test == True'] == (parameter, True)
    assert res['test != True'] == (parameter, False)


def test_generate_equal_option_dicts_2():
    parameter = Parameter('regime', ParameterType.REGIME)
    conditions: List[Condition] = [Equal(parameter, Regime.A), Equal(parameter, Regime.NC)]
    res = _generate_equal_option_dicts(conditions)
    assert len(res) == 4
    assert 'regime == A' in res
    assert 'regime == E' in res
    assert 'regime == D' in res
    assert 'regime == NC' in res
    assert res['regime == A'] == (parameter, Regime.A)
    assert res['regime == E'] == (parameter, Regime.E)
    assert res['regime == D'] == (parameter, Regime.D)
    assert res['regime == NC'] == (parameter, Regime.NC)


def test_generate_options_dict():
    parameter = Parameter('test', ParameterType.BOOLEAN)
    conditions: List[Condition] = [Equal(parameter, True), Equal(parameter, True)]
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
    str_dt_20 = '2020-01-01'
    str_dt_21 = '2021-01-01'
    assert f'test < {str_dt_20}' in res
    assert f'{str_dt_20} <= test < {str_dt_21}' in res
    assert f'test >= {str_dt_21}' in res
    assert res[f'test < {str_dt_20}'] == (parameter, datetime(2019, 12, 31))
    assert res[f'{str_dt_20} <= test < {str_dt_21}'] == (parameter, datetime(2020, 7, 2, 1, 0))
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


def _random_string() -> str:
    return ''.join([random.choice(ascii_letters) for _ in range(9)])


def _random_enriched_string() -> EnrichedString:
    return EnrichedString(_random_string(), [], None)


def _str(text: Optional[str] = None) -> EnrichedString:
    return EnrichedString(text) if text else _random_enriched_string()


def test_apply_parameter_values_to_am_whole_arrete():
    sections = [
        StructuredText(_str(), [_str('Initial version 1')], [], None),
        StructuredText(_str(), [_str('Initial version 2')], [], None),
        StructuredText(
            _str('Conditions d\'application'),
            [_str('Cet arrete ne s\'applique qu\'aux nouvelles installations.')],
            [],
            None,
        ),
    ]
    am = ArreteMinisteriel(_str(), sections, [], '')

    parameter = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    is_installation_old = Equal(parameter, False)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None, False))
    parametrization = Parametrization(
        [NonApplicationCondition(EntityReference(SectionReference(tuple()), None, True), is_installation_old, source)],
        [],
    )

    new_am_1 = _apply_parameter_values_to_am(am, parametrization, {parameter: False})
    assert not new_am_1.active
    assert new_am_1.warning_inactive is not None

    new_am_2 = _apply_parameter_values_to_am(am, parametrization, {parameter: True})
    assert new_am_2.active
    assert new_am_2.warning_inactive is None

    new_am_3 = _apply_parameter_values_to_am(am, parametrization, {})
    assert new_am_3.active
    assert new_am_3.warning_inactive is not None


def _all_alineas_inactive(text: StructuredText) -> bool:
    return all([not al.active for al in text.outer_alineas]) and all(
        [_all_alineas_inactive(sec) for sec in text.sections]
    )


def _all_alineas_active(text: StructuredText) -> bool:
    return all([al.active for al in text.outer_alineas]) and all([_all_alineas_active(sec) for sec in text.sections])


def test_apply_parameter_values_to_am():
    cd_alineas = [
        _str('L\'article 1 ne s\'applique qu\'aux nouvelles installations'),
        _str('Pour les installations nouvelles, l\'article 2 est remplacé par "version modifiée"'),
    ]
    sections = [
        StructuredText(_str('Art. 1'), [_str('Initial version 1')], [], None),
        StructuredText(_str('Art. 2'), [_str('Initial version 2')], [], None),
        StructuredText(_str('Conditions d\'application'), cd_alineas, [], None),
        StructuredText(_str('Art. 3'), [_str(), _str()], [], None),
    ]
    am = ArreteMinisteriel(_str(), sections, [], '')

    parameter = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    is_installation_old = Equal(parameter, False)
    is_installation_new = Equal(parameter, True)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None, False))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [
            NonApplicationCondition(EntityReference(SectionReference((0,)), None), is_installation_old, source),
            NonApplicationCondition(EntityReference(SectionReference((3,)), [0]), is_installation_old, source),
        ],
        [AlternativeSection(SectionReference((1,)), new_text, is_installation_new, source)],
    )

    new_am_1 = _apply_parameter_values_to_am(am, parametrization, {parameter: False})

    assert _all_alineas_inactive(new_am_1.sections[0])
    assert len(new_am_1.sections[0].applicability.warnings) == 1

    assert not new_am_1.sections[1].applicability.modified
    assert len(new_am_1.sections[1].applicability.warnings) == 0

    assert not new_am_1.sections[3].outer_alineas[0].active
    assert new_am_1.sections[3].outer_alineas[1].active
    assert len(new_am_1.sections[3].applicability.warnings) == 1

    new_am_2 = _apply_parameter_values_to_am(am, parametrization, {parameter: True})

    assert _all_alineas_active(new_am_2.sections[0])
    assert len(new_am_2.sections[0].applicability.warnings) == 0

    assert new_am_2.sections[1].applicability.modified
    assert len(new_am_2.sections[1].applicability.warnings) == 1
    assert new_am_2.sections[1].applicability.new_version.outer_alineas[0].text == 'version modifiée'

    assert new_am_2.sections[3].outer_alineas[0].active
    assert new_am_2.sections[3].outer_alineas[1].active
    assert len(new_am_2.sections[3].applicability.warnings) == 0

    new_am_3 = _apply_parameter_values_to_am(am, parametrization, {})
    assert _all_alineas_active(new_am_3.sections[0])
    assert len(new_am_3.sections[0].applicability.warnings) == 1

    assert not new_am_3.sections[1].applicability.modified
    assert len(new_am_3.sections[1].applicability.warnings) == 1

    assert new_am_3.sections[3].outer_alineas[0].active
    assert new_am_3.sections[3].outer_alineas[1].active
    assert len(new_am_3.sections[3].applicability.warnings) == 1


def test_extract_parameters_from_parametrization():
    parameter_1 = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    condition_1 = Equal(parameter_1, True)
    parameter_2 = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    condition_2 = Equal(parameter_2, True)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None, False))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [NonApplicationCondition(EntityReference(SectionReference((0,)), None), condition_1, source)],
        [AlternativeSection(SectionReference((1,)), new_text, condition_2, source)],
    )

    parameters = _extract_parameters_from_parametrization(parametrization)
    assert len(parameters) == 1
    assert list(parameters)[0].id == 'nouvelle-installation'


def test_extract_parameters_from_parametrization_2():
    parameter_1 = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    condition_1 = Equal(parameter_1, True)
    parameter_2 = Parameter('nouvelle-installation-2', ParameterType.BOOLEAN)
    condition_2 = Equal(parameter_2, True)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None, False))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [NonApplicationCondition(EntityReference(SectionReference((0,)), None), condition_1, source)],
        [AlternativeSection(SectionReference((1,)), new_text, condition_2, source)],
    )

    parameters = _extract_parameters_from_parametrization(parametrization)
    assert len(parameters) == 2
    assert copy(parameter_1) in parameters
    assert copy(parameter_2) in parameters


def test_generate_all_am_versions():
    sections = [
        StructuredText(_str('Art. 1'), [_str('Initial version 1')], [], None),
        StructuredText(_str('Art. 2'), [_str('Initial version 2')], [], None),
        StructuredText(_str('Art. 3'), [_str('condition source')], [], None),
    ]
    am = ArreteMinisteriel(_str(), sections, [], '')

    parameter = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    condition = Equal(parameter, False)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None, False))
    parametrization = Parametrization(
        [NonApplicationCondition(EntityReference(SectionReference((0,)), None), condition, source)], []
    )

    res = generate_all_am_versions(am, parametrization)
    assert len(res) == 3
    assert ('nouvelle-installation != False',) in res
    assert ('nouvelle-installation == False',) in res
    assert () in res
    assert _all_alineas_inactive(res[('nouvelle-installation == False',)].sections[0])
    assert _all_alineas_active(res[('nouvelle-installation != False',)].sections[0])
    assert _all_alineas_active(res[()].sections[0])
    assert len(res[()].sections[0].applicability.warnings) == 1

    res_2 = generate_all_am_versions(am, Parametrization([], []))
    assert len(res_2) == 1
    assert tuple() in res_2
    assert res_2[()].sections[0].applicability is None


def test_extract_installation_date_criterion():
    parameter = ParameterEnum.DATE_INSTALLATION.value
    date_1 = datetime(2018, 1, 1)
    date_2 = datetime(2019, 1, 1)
    condition_1 = Greater(parameter, date_1, False)
    condition_2 = Range(parameter, date_1, date_2, left_strict=False, right_strict=True)
    condition_3 = Littler(parameter, date_2, True)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None, False))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None, None)
    parametrization = Parametrization(
        [
            NonApplicationCondition(EntityReference(SectionReference((0,)), None), condition_1, source),
            NonApplicationCondition(EntityReference(SectionReference((0,)), None), condition_3, source),
        ],
        [AlternativeSection(SectionReference((1,)), new_text, condition_2, source)],
    )

    oldest = _extract_installation_date_criterion(parametrization, {parameter: date_1 - timedelta(1)})
    assert oldest
    assert oldest.left_date is None
    assert oldest.right_date == '2018-01-01'
    mid = _extract_installation_date_criterion(parametrization, {parameter: date_1 + timedelta(1)})
    assert mid
    assert mid.left_date == '2018-01-01'
    assert mid.right_date == '2019-01-01'
    youngest = _extract_installation_date_criterion(parametrization, {parameter: date_2 + timedelta(1)})
    assert youngest
    assert youngest.left_date == '2019-01-01'
    assert youngest.right_date is None

    assert _extract_installation_date_criterion(parametrization, {}) is None
    assert _extract_installation_date_criterion(Parametrization([], []), {}) is None


def test_is_satisfied():
    param_1 = Parameter('regime', ParameterType.REGIME)
    param_2 = Parameter('date', ParameterType.DATE)
    condition_1 = Equal(param_1, Regime.A)
    condition_2 = Equal(param_1, Regime.E)
    condition_3 = Littler(param_2, 1, True)
    assert not is_satisfied(AndCondition([condition_1]), {})
    assert is_satisfied(AndCondition([condition_1]), {param_1: Regime.A})
    assert is_satisfied(OrCondition([condition_1, condition_2]), {param_1: Regime.A})
    assert is_satisfied(OrCondition([condition_1, condition_3]), {param_1: Regime.A})
    assert not is_satisfied(AndCondition([condition_1, condition_2]), {param_1: Regime.A})
    assert is_satisfied(AndCondition([condition_1, condition_3]), {param_1: Regime.A, param_2: 0.5})
    assert is_satisfied(OrCondition([condition_2, condition_3]), {param_1: Regime.E, param_2: 0.5})
    assert not is_satisfied(OrCondition([condition_1, condition_3]), {param_1: Regime.E, param_2: 5})


def test_date_not_in_parametrization():
    assert _date_not_in_parametrization(Parametrization([], []))
    nac = NonApplicationCondition(
        EntityReference(SectionReference((1,)), None),
        Equal(ParameterEnum.DATE_INSTALLATION.value, True),
        ConditionSource('', EntityReference(SectionReference((1,)), None)),
    )
    assert not _date_not_in_parametrization(Parametrization([nac], []))


def test_extract_warning():
    ref = (0,)
    base_text = StructuredTextSignature(ref, 'title', ['al1', 'al2'], 2, 2, 4)
    assert _extract_warning(ref, base_text, base_text) is None
    assert _extract_warning(ref, base_text, None) is not None
    assert _extract_warning(ref, base_text, replace(base_text, title='title2')) is not None
    assert _extract_warning(ref, base_text, replace(base_text, outer_alineas_text=['al3', 'al4', 'al5'])) is not None
    assert _extract_warning(ref, base_text, replace(base_text, depth_in_am=10)) is not None
    assert _extract_warning(ref, base_text, replace(base_text, rank_in_section_list=10)) is not None
    assert _extract_warning(ref, base_text, replace(base_text, section_list_size=10)) is not None


def test_extract_warnings():
    ref = (0,)
    base_text = StructuredTextSignature(ref, 'title', ['al1', 'al2'], 2, 2, 4)
    assert len(_extract_warnings([ref], {ref: base_text}, {ref: base_text})) == 0
    assert len(_extract_warnings([ref], {ref: base_text}, {})) == 1
    assert len(_extract_warnings([ref], {ref: base_text}, {ref: replace(base_text, title='title2')})) == 1
    assert len(_extract_warnings([ref], {ref: base_text}, {ref: replace(base_text, outer_alineas_text=['al3'])})) == 1
    assert len(_extract_warnings([ref], {ref: base_text}, {ref: replace(base_text, depth_in_am=10)})) == 1
    assert len(_extract_warnings([ref], {ref: base_text}, {ref: replace(base_text, rank_in_section_list=10)})) == 1
    assert len(_extract_warnings([ref], {ref: base_text}, {ref: replace(base_text, section_list_size=10)})) == 1


def _get_simple_text() -> StructuredText:
    return StructuredText(_str('Conditions d\'application'), [_str('al 1'), _str('al 2')], [], None)
