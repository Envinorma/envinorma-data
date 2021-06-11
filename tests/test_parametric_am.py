import random
from copy import copy
from datetime import date, datetime, timedelta
from operator import itemgetter
from string import ascii_letters
from typing import List, Optional

import pytest

from envinorma.models import (
    Applicability,
    ArreteMinisteriel,
    Classement,
    DateParameterDescriptor,
    EnrichedString,
    Regime,
    StructuredText,
)
from envinorma.parametrization import (
    AlternativeSection,
    AMWarning,
    Combinations,
    ConditionSource,
    EntityReference,
    NonApplicationCondition,
    Parametrization,
    SectionReference,
)
from envinorma.parametrization.conditions import (
    AndCondition,
    Condition,
    Equal,
    Greater,
    Littler,
    OrCondition,
    Parameter,
    ParameterEnum,
    ParameterType,
    Range,
)
from envinorma.parametrization.parametric_am import (
    _change_value,
    _date_parameters,
    _deactivate_alineas,
    _extract_am_regime,
    _extract_interval_midpoints,
    _extract_sorted_targets,
    _extract_surrounding_dates,
    _find_used_date,
    _generate_combinations,
    _generate_equal_option_dicts,
    _generate_options_dict,
    _is_satisfiable,
    _keep_aed_parameter,
    _keep_satisfiable,
    _mean,
    _used_date_parameter,
    apply_parameter_values_to_am,
    extract_parameters_from_parametrization,
    generate_all_am_versions,
    is_satisfied,
)

_NAC = NonApplicationCondition
_AS = AlternativeSection


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
    assert res == [('test == True', True), ('test != True', False)]


def test_generate_equal_option_dicts_2():
    parameter = Parameter('regime', ParameterType.REGIME)
    conditions: List[Condition] = [Equal(parameter, Regime.A), Equal(parameter, Regime.NC)]
    res = _generate_equal_option_dicts(conditions)
    expected = [
        ('regime == A', Regime.A),
        ('regime == E', Regime.E),
        ('regime == D', Regime.D),
        ('regime == NC', Regime.NC),
    ]
    assert expected == res


def test_generate_options_dict():
    parameter = Parameter('test', ParameterType.BOOLEAN)
    conditions: List[Condition] = [Equal(parameter, True), Equal(parameter, True)]
    res = _generate_options_dict(conditions)
    assert res == [('test == True', True), ('test != True', False)]


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
    str_dt_20 = '2020-01-01'
    str_dt_21 = '2021-01-01'
    expected = [
        (f'test < {str_dt_20}', datetime(2019, 12, 31)),
        (f'{str_dt_20} <= test < {str_dt_21}', datetime(2020, 7, 2, 1, 0)),
        (f'test >= {str_dt_21}', datetime(2021, 1, 2)),
    ]
    assert res == expected


def test_change_value():
    assert not _change_value(True)
    assert _change_value(False)
    assert _change_value(1) == 2
    assert _change_value(2.0) == 3
    assert _change_value(datetime(2020, 1, 1)) == datetime(2020, 1, 2)


def test_generate_combinations():
    parameter_1 = Parameter('test_1', ParameterType.DATE)
    parameter_2 = Parameter('test_2', ParameterType.BOOLEAN)
    options_1 = (parameter_1, [('test_1 < a', datetime(2021, 1, 1)), ('test_1 >= a', datetime(2022, 1, 1))])
    options_2 = (parameter_2, [('test_2 == True', True), ('test_2 != True', False)])
    res = _generate_combinations([options_1, options_2], False)
    expected: Combinations = {
        ('test_1 < a', 'test_2 == True'): {parameter_1: datetime(2021, 1, 1), parameter_2: True},
        ('test_1 < a', 'test_2 != True'): {parameter_1: datetime(2021, 1, 1), parameter_2: False},
        ('test_1 >= a', 'test_2 == True'): {parameter_1: datetime(2022, 1, 1), parameter_2: True},
        ('test_1 >= a', 'test_2 != True'): {parameter_1: datetime(2022, 1, 1), parameter_2: False},
    }
    assert expected == res

    parameter_1 = Parameter('test_1', ParameterType.DATE)
    parameter_2 = Parameter('test_2', ParameterType.BOOLEAN)
    options_1 = (parameter_1, [('test_1 < a', datetime(2021, 1, 1)), ('test_1 >= a', datetime(2022, 1, 1))])
    options_2 = (parameter_2, [('test_2 == True', True), ('test_2 != True', False)])
    res = _generate_combinations([options_1, options_2], True)
    expected: Combinations = {
        (): {},
        ('test_2 == True',): {parameter_2: True},
        ('test_2 != True',): {parameter_2: False},
        ('test_1 < a',): {parameter_1: datetime(2021, 1, 1)},
        ('test_1 < a', 'test_2 == True'): {parameter_1: datetime(2021, 1, 1), parameter_2: True},
        ('test_1 < a', 'test_2 != True'): {parameter_1: datetime(2021, 1, 1), parameter_2: False},
        ('test_1 >= a',): {parameter_1: datetime(2022, 1, 1)},
        ('test_1 >= a', 'test_2 == True'): {parameter_1: datetime(2022, 1, 1), parameter_2: True},
        ('test_1 >= a', 'test_2 != True'): {parameter_1: datetime(2022, 1, 1), parameter_2: False},
    }
    assert expected == res


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
    am = ArreteMinisteriel(_str('arrete du 10/10/10'), sections, [], None, id='FAKE_ID')

    parameter = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    is_installation_old = Equal(parameter, False)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None))
    parametrization = Parametrization(
        [_NAC(EntityReference(SectionReference(tuple()), None), is_installation_old, source)], [], []
    )

    new_am_1 = apply_parameter_values_to_am(am, parametrization, {parameter: False})
    assert not new_am_1.version_descriptor.applicable
    assert new_am_1.version_descriptor.applicability_warnings == [
        'Cet arrêté ne s\'applique pas à cette installation car le paramètre nouvelle-installation est égal à False.'
    ]

    new_am_2 = apply_parameter_values_to_am(am, parametrization, {parameter: True})
    assert new_am_2.version_descriptor.applicable
    assert new_am_2.version_descriptor.applicability_warnings == []

    new_am_3 = apply_parameter_values_to_am(am, parametrization, {})
    assert new_am_3.version_descriptor.applicable
    assert new_am_3.version_descriptor.applicability_warnings == [
        'Cet arrêté pourrait ne pas être applicable. C\'est le cas pour les installations dont le paramètre '
        'nouvelle-installation est égal à False.'
    ]


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
    am = ArreteMinisteriel(_str('arrete du 10/10/10'), sections, [], None, id='FAKE_ID')

    parameter = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    is_installation_old = Equal(parameter, False)
    is_installation_new = Equal(parameter, True)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [
            _NAC(EntityReference(SectionReference((0,)), None), is_installation_old, source),
            _NAC(EntityReference(SectionReference((3,)), [0]), is_installation_old, source),
        ],
        [_AS(SectionReference((1,)), new_text, is_installation_new, source)],
        [AMWarning(SectionReference((0,)), 'Fake warning')],
    )

    new_am_1 = apply_parameter_values_to_am(am, parametrization, {parameter: False})

    assert _all_alineas_inactive(new_am_1.sections[0])
    assert len(new_am_1.sections[0].applicability.warnings) == 2
    assert 'Fake warning' in itemgetter(0, 1)(new_am_1.sections[0].applicability.warnings)

    assert not new_am_1.sections[1].applicability.modified
    assert len(new_am_1.sections[1].applicability.warnings) == 0

    assert not new_am_1.sections[3].outer_alineas[0].active
    assert new_am_1.sections[3].outer_alineas[1].active
    assert len(new_am_1.sections[3].applicability.warnings) == 1

    new_am_2 = apply_parameter_values_to_am(am, parametrization, {parameter: True})

    assert _all_alineas_active(new_am_2.sections[0])
    assert len(new_am_2.sections[0].applicability.warnings) == 1

    assert new_am_2.sections[1].applicability.modified
    assert len(new_am_2.sections[1].applicability.warnings) == 1
    assert new_am_2.sections[1].outer_alineas[0].text == 'version modifiée'
    assert new_am_2.sections[1].applicability.previous_version is not None

    assert new_am_2.sections[3].outer_alineas[0].active
    assert new_am_2.sections[3].outer_alineas[1].active
    assert len(new_am_2.sections[3].applicability.warnings) == 0

    new_am_3 = apply_parameter_values_to_am(am, parametrization, {})
    assert _all_alineas_active(new_am_3.sections[0])
    assert len(new_am_3.sections[0].applicability.warnings) == 2

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
    source = ConditionSource('', EntityReference(SectionReference((2,)), None))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [_NAC(EntityReference(SectionReference((0,)), None), condition_1, source)],
        [_AS(SectionReference((1,)), new_text, condition_2, source)],
        [],
    )

    parameters = extract_parameters_from_parametrization(parametrization)
    assert len(parameters) == 1
    assert list(parameters)[0].id == 'nouvelle-installation'


def test_extract_parameters_from_parametrization_2():
    parameter_1 = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    condition_1 = Equal(parameter_1, True)
    parameter_2 = Parameter('nouvelle-installation-2', ParameterType.BOOLEAN)
    condition_2 = Equal(parameter_2, True)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [_NAC(EntityReference(SectionReference((0,)), None), condition_1, source)],
        [_AS(SectionReference((1,)), new_text, condition_2, source)],
        [],
    )

    parameters = extract_parameters_from_parametrization(parametrization)
    assert len(parameters) == 2
    assert copy(parameter_1) in parameters
    assert copy(parameter_2) in parameters


def test_generate_all_am_versions():
    sections = [
        StructuredText(_str('Art. 1'), [_str('Initial version 1')], [], None),
        StructuredText(_str('Art. 2'), [_str('Initial version 2')], [], None),
        StructuredText(_str('Art. 3'), [_str('condition source')], [], None),
    ]
    am = ArreteMinisteriel(_str('Arrete du 10/10/10'), sections, [], None, id='FAKE_ID')

    parameter = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    condition = Equal(parameter, False)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None))
    parametrization = Parametrization([_NAC(EntityReference(SectionReference((0,)), None), condition, source)], [], [])

    res = generate_all_am_versions(am, parametrization, False)
    assert len(res) == 3
    assert ('nouvelle-installation != False',) in res
    assert ('nouvelle-installation == False',) in res
    assert () in res
    assert _all_alineas_inactive(res[('nouvelle-installation == False',)].sections[0])
    assert _all_alineas_active(res[('nouvelle-installation != False',)].sections[0])
    assert _all_alineas_active(res[()].sections[0])
    assert len(res[()].sections[0].applicability.warnings) == 1

    res_2 = generate_all_am_versions(am, Parametrization([], [], []), False)
    assert len(res_2) == 1
    assert tuple() in res_2
    exp = Applicability(active=True, modified=False, warnings=[], previous_version=None)
    assert res_2[()].sections[0].applicability == exp


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


def _get_simple_text(sections: Optional[List[StructuredText]] = None) -> StructuredText:
    return StructuredText(_str('Conditions d\'application'), [_str('al 1'), _str('al 2')], sections or [], None)


def test_deactivate_alineas():
    nac = _NAC(
        EntityReference(SectionReference((0,)), None),
        Littler(ParameterEnum.DATE_INSTALLATION.value, datetime(2021, 1, 1)),
        ConditionSource('', EntityReference(SectionReference((1,)), None)),
    )
    res = _deactivate_alineas(_get_simple_text(), nac, {ParameterEnum.DATE_INSTALLATION.value: datetime(2020, 1, 1)})
    assert not res.applicability.active
    assert all([not al.active for al in res.outer_alineas])

    nac = _NAC(
        EntityReference(SectionReference((0,)), [0]),
        Littler(ParameterEnum.DATE_INSTALLATION.value, datetime(2021, 1, 1)),
        ConditionSource('', EntityReference(SectionReference((1,)), None)),
    )
    res = _deactivate_alineas(_get_simple_text(), nac, {ParameterEnum.DATE_INSTALLATION.value: datetime(2020, 1, 1)})
    assert res.applicability.active
    assert not res.outer_alineas[0].active
    assert res.outer_alineas[1].active

    nac = _NAC(
        EntityReference(SectionReference((0,)), None),
        Littler(ParameterEnum.DATE_INSTALLATION.value, datetime(2021, 1, 1)),
        ConditionSource('', EntityReference(SectionReference((1,)), None)),
    )
    res = _deactivate_alineas(
        _get_simple_text([_get_simple_text()]), nac, {ParameterEnum.DATE_INSTALLATION.value: datetime(2020, 1, 1)}
    )
    assert not res.applicability.active
    assert not res.sections[0].applicability.active


def test_extract_surrounding_dates():
    assert _extract_surrounding_dates(date.today(), []) == (None, None)

    dates = [date.today() + timedelta(days=2 * i + 1) for i in range(3)]
    assert _extract_surrounding_dates(date.today(), dates) == (None, dates[0])
    assert _extract_surrounding_dates(date.today() + timedelta(1), dates) == (dates[0], dates[1])
    assert _extract_surrounding_dates(date.today() + timedelta(2), dates) == (dates[0], dates[1])
    assert _extract_surrounding_dates(date.today() + timedelta(4), dates) == (dates[1], dates[2])
    assert _extract_surrounding_dates(date.today() + timedelta(6), dates) == (dates[2], None)


def _simple_nac(date_parameter: Parameter) -> NonApplicationCondition:
    return _NAC(
        EntityReference(SectionReference((0,)), None),
        Littler(date_parameter, datetime(2021, 1, 1)),
        ConditionSource('', EntityReference(SectionReference((1,)), None)),
    )


def test_find_used_date():
    declaration = ParameterEnum.DATE_DECLARATION.value
    enregistrement = ParameterEnum.DATE_ENREGISTREMENT.value
    autorisation = ParameterEnum.DATE_AUTORISATION.value
    installation = ParameterEnum.DATE_INSTALLATION.value

    assert _find_used_date(Parametrization([], [], [])) == declaration

    non_applicabilities = [_simple_nac(declaration)]
    assert _find_used_date(Parametrization(non_applicabilities, [], [])) == declaration

    non_applicabilities = [_simple_nac(installation)]
    assert _find_used_date(Parametrization(non_applicabilities, [], [])) == declaration

    non_applicabilities = [_simple_nac(enregistrement)]
    assert _find_used_date(Parametrization(non_applicabilities, [], [])) == enregistrement

    non_applicabilities = [_simple_nac(enregistrement), _simple_nac(installation)]
    assert _find_used_date(Parametrization(non_applicabilities, [], [])) == enregistrement

    with pytest.raises(ValueError):
        non_applicabilities = [_simple_nac(enregistrement), _simple_nac(declaration)]
        _find_used_date(Parametrization(non_applicabilities, [], []))

    with pytest.raises(ValueError):
        non_applicabilities = [_simple_nac(enregistrement), _simple_nac(declaration), _simple_nac(autorisation)]
        _find_used_date(Parametrization(non_applicabilities, [], []))


def _generate_classement(regime: str) -> Classement:
    return Classement('1234', Regime(regime), None)


def test_extract_am_regime():
    assert _extract_am_regime([]) is None
    assert _extract_am_regime([_generate_classement('A')]) == Regime.A
    assert _extract_am_regime([_generate_classement('E')]) == Regime.E
    assert _extract_am_regime([_generate_classement('D')]) == Regime.D
    assert _extract_am_regime([_generate_classement('D'), _generate_classement('A')]) is None


def test_keep_aed_parameter():
    declaration = ParameterEnum.DATE_DECLARATION.value
    enregistrement = ParameterEnum.DATE_ENREGISTREMENT.value
    autorisation = ParameterEnum.DATE_AUTORISATION.value

    assert _keep_aed_parameter(set(), None) is None
    assert _keep_aed_parameter(set(), Regime.A) is None
    assert _keep_aed_parameter(set(), Regime.D) is None
    assert _keep_aed_parameter({declaration}, Regime.D) == declaration
    assert _keep_aed_parameter({enregistrement}, None) == enregistrement
    assert _keep_aed_parameter({declaration, enregistrement}, Regime.D) == declaration
    assert _keep_aed_parameter({declaration, enregistrement}, Regime.A) is None
    assert _keep_aed_parameter({declaration, autorisation}, Regime.A) == autorisation
    with pytest.raises(ValueError):
        _keep_aed_parameter({declaration, autorisation}, None)
    with pytest.raises(ValueError):
        _keep_aed_parameter({autorisation, enregistrement}, None)


def _simple_nac_2(date_parameter: Parameter) -> NonApplicationCondition:
    return _NAC(
        EntityReference(SectionReference((0,)), None),
        Littler(date_parameter, date(2021, 1, 1)),
        ConditionSource('', EntityReference(SectionReference((1,)), None)),
    )


def test_date_parameters():
    enregistrement = ParameterEnum.DATE_ENREGISTREMENT.value
    autorisation = ParameterEnum.DATE_AUTORISATION.value
    installation = ParameterEnum.DATE_INSTALLATION.value

    non_applicabilities = []
    parametrization = Parametrization(non_applicabilities, [], [])
    parameter_values = {}
    expected = (DateParameterDescriptor(False), DateParameterDescriptor(False))
    assert _date_parameters(parametrization, parameter_values) == expected

    non_applicabilities = [_simple_nac_2(enregistrement)]
    parametrization = Parametrization(non_applicabilities, [], [])
    parameter_values = {}
    expected = (DateParameterDescriptor(True, True), DateParameterDescriptor(False))
    assert _date_parameters(parametrization, parameter_values) == expected

    non_applicabilities = [_simple_nac_2(enregistrement)]
    parametrization = Parametrization(non_applicabilities, [], [])
    parameter_values = {enregistrement: date(2022, 1, 1)}
    expected = (DateParameterDescriptor(True, False, date(2021, 1, 1), None), DateParameterDescriptor(False))
    assert _date_parameters(parametrization, parameter_values) == expected

    non_applicabilities = [_simple_nac_2(enregistrement)]
    parametrization = Parametrization(non_applicabilities, [], [])
    parameter_values = {enregistrement: date(2020, 1, 1)}
    expected = (DateParameterDescriptor(True, False, None, date(2021, 1, 1)), DateParameterDescriptor(False))
    assert _date_parameters(parametrization, parameter_values) == expected

    non_applicabilities = [_simple_nac_2(enregistrement), _simple_nac_2(autorisation)]
    parametrization = Parametrization(non_applicabilities, [], [])
    parameter_values = {enregistrement: date(2020, 1, 1), autorisation: date(2020, 1, 1)}
    with pytest.raises(ValueError):
        _date_parameters(parametrization, parameter_values)

    non_applicabilities = [_simple_nac_2(installation)]
    parametrization = Parametrization(non_applicabilities, [], [])
    parameter_values = {enregistrement: date(2020, 1, 1)}
    expected = (DateParameterDescriptor(False), DateParameterDescriptor(True, True))
    assert _date_parameters(parametrization, parameter_values) == expected

    non_applicabilities = [_simple_nac_2(installation)]
    parametrization = Parametrization(non_applicabilities, [], [])
    parameter_values = {installation: date(2020, 1, 1)}
    expected = (DateParameterDescriptor(False), DateParameterDescriptor(True, False, None, date(2021, 1, 1)))
    assert _date_parameters(parametrization, parameter_values) == expected


def test_is_satisfiable():
    enregistrement = ParameterEnum.DATE_ENREGISTREMENT.value
    regime = ParameterEnum.REGIME.value

    condition = Littler(enregistrement, date(2021, 1, 1))
    assert _is_satisfiable(condition, Regime.E)

    condition = Equal(regime, Regime.E)
    assert _is_satisfiable(condition, Regime.E)

    condition = Equal(regime, Regime.A)
    assert not _is_satisfiable(condition, Regime.E)

    condition = AndCondition([Equal(regime, Regime.A), Littler(enregistrement, date(2021, 1, 1))])
    assert not _is_satisfiable(condition, Regime.E)

    condition = OrCondition([Equal(regime, Regime.A), Littler(enregistrement, date(2021, 1, 1))])
    assert _is_satisfiable(condition, Regime.E)

    condition = AndCondition([Equal(regime, Regime.E), Littler(enregistrement, date(2021, 1, 1))])
    assert _is_satisfiable(condition, Regime.E)

    with pytest.raises(ValueError):
        condition = AndCondition([Littler(regime, Regime.E), Littler(enregistrement, date(2021, 1, 1))])
        _is_satisfiable(condition, Regime.E)


def test_keep_satisfiable():
    enregistrement = ParameterEnum.DATE_ENREGISTREMENT.value
    regime = ParameterEnum.REGIME.value

    assert _keep_satisfiable([], Regime.A) == []

    condition = Equal(regime, Regime.A)
    assert _keep_satisfiable([condition], Regime.E) == []

    condition = Equal(regime, Regime.E)
    assert _keep_satisfiable([condition], Regime.E) == [condition]

    condition = Equal(regime, Regime.E)
    condition_ = Littler(enregistrement, date(2021, 1, 1))
    assert _keep_satisfiable([condition, condition_], Regime.D) == [condition_]

    installation = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = Littler(installation, date(2021, 1, 1))
    dt_2 = Littler(installation, date(2022, 1, 1))
    conditions = [dt_1, AndCondition([dt_2, Equal(regime, Regime.A)]), Equal(regime, Regime.A)]
    assert _keep_satisfiable(conditions, Regime.E) == [dt_1]


def test_used_date_parameter():
    installation = ParameterEnum.DATE_INSTALLATION.value
    regime = ParameterEnum.REGIME.value
    source = ConditionSource('', EntityReference(SectionReference((1,)), None))
    target = EntityReference(SectionReference((0,)), None)
    dt_1 = Littler(installation, date(2021, 1, 1))
    dt_2 = Littler(installation, date(2022, 1, 1))
    nac_1 = _NAC(target, dt_1, source)
    nac_2 = _NAC(target, AndCondition([dt_2, Equal(regime, Regime.A)]), source)
    nac_3 = _NAC(target, Equal(regime, Regime.A), source)
    parametrization = Parametrization([nac_1, nac_2, nac_3], [], [])

    res = _used_date_parameter(installation, parametrization, {})
    assert res == DateParameterDescriptor(True, True)

    res = _used_date_parameter(installation, parametrization, {regime: Regime.A})
    assert res == DateParameterDescriptor(True, True)

    res = _used_date_parameter(installation, parametrization, {installation: date(2021, 5, 1)})
    assert res == DateParameterDescriptor(True, False, date(2021, 1, 1), date(2022, 1, 1))

    res = _used_date_parameter(installation, parametrization, {installation: date(2022, 5, 1)})
    assert res == DateParameterDescriptor(True, False, date(2022, 1, 1), None)

    res = _used_date_parameter(installation, parametrization, {installation: date(2021, 5, 1), regime: Regime.A})
    assert res == DateParameterDescriptor(True, False, date(2021, 1, 1), date(2022, 1, 1))

    res = _used_date_parameter(installation, parametrization, {installation: date(2022, 5, 1), regime: Regime.A})
    assert res == DateParameterDescriptor(True, False, date(2022, 1, 1), None)

    res = _used_date_parameter(installation, parametrization, {installation: date(2022, 5, 1), regime: Regime.E})
    assert res == DateParameterDescriptor(True, False, date(2021, 1, 1), None)

    res = _used_date_parameter(installation, parametrization, {installation: date(2020, 5, 1), regime: Regime.E})
    assert res == DateParameterDescriptor(True, False, None, date(2021, 1, 1))
