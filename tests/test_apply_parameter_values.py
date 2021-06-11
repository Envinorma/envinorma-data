import random
from copy import copy
from datetime import date, datetime, timedelta
from operator import itemgetter
from string import ascii_letters
from typing import List, Optional

import pytest

from envinorma.models.arrete_ministeriel import ArreteMinisteriel, DateParameterDescriptor
from envinorma.models.classement import Regime
from envinorma.models.structured_text import Applicability, StructuredText
from envinorma.models.text_elements import EnrichedString
from envinorma.parametrization.am_with_versions import generate_versions
from envinorma.parametrization.apply_parameter_values import (
    _date_parameters,
    _deactivate_alineas,
    _extract_surrounding_dates,
    _find_used_date,
    _is_satisfiable,
    _keep_satisfiable,
    _used_date_parameter,
    apply_parameter_values_to_am,
)
from envinorma.parametrization.models.condition import AndCondition, Equal, Littler, OrCondition
from envinorma.parametrization.models.parameter import Parameter, ParameterEnum, ParameterType
from envinorma.parametrization.models.parametrization import (
    AlternativeSection,
    AMWarning,
    ConditionSource,
    EntityReference,
    NonApplicationCondition,
    Parametrization,
    SectionReference,
)

_NAC = NonApplicationCondition
_AS = AlternativeSection


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

    parameters = parametrization.extract_parameters()
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

    parameters = parametrization.extract_parameters()
    assert len(parameters) == 2
    assert copy(parameter_1) in parameters
    assert copy(parameter_2) in parameters


def test_generate_versions():
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

    res = generate_versions(am, parametrization, False)
    assert len(res) == 3
    assert ('nouvelle-installation != False',) in res
    assert ('nouvelle-installation == False',) in res
    assert () in res
    assert _all_alineas_inactive(res[('nouvelle-installation == False',)].sections[0])
    assert _all_alineas_active(res[('nouvelle-installation != False',)].sections[0])
    assert _all_alineas_active(res[()].sections[0])
    assert len(res[()].sections[0].applicability.warnings) == 1

    res_2 = generate_versions(am, Parametrization([], [], []), False)
    assert len(res_2) == 1
    assert tuple() in res_2
    exp = Applicability(active=True, modified=False, warnings=[], previous_version=None)
    assert res_2[()].sections[0].applicability == exp


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
