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
    EnrichedString,
    Regime,
    StructuredText,
)
from envinorma.parametrization.am_with_versions import generate_versions
from envinorma.parametrization.apply_parameter_values import (
    _deactivate_alineas,
    _extract_surrounding_dates,
    _is_satisfiable,
    apply_parameter_values_to_am,
)
from envinorma.parametrization.models import (
    AlternativeSection,
    AMWarning,
    AndCondition,
    ConditionSource,
    EntityReference,
    Equal,
    InapplicableSection,
    Littler,
    OrCondition,
    Parameter,
    ParameterEnum,
    ParameterType,
    Parametrization,
    SectionReference,
)
from envinorma.utils import ensure_not_none

_IS = InapplicableSection
_AS = AlternativeSection


def _random_string() -> str:
    return ''.join([random.choice(ascii_letters) for _ in range(9)])  # noqa: S311


def _random_enriched_string() -> EnrichedString:
    return EnrichedString(_random_string(), [], None)


def _str(text: Optional[str] = None) -> EnrichedString:
    return EnrichedString(text) if text else _random_enriched_string()


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
    source = ConditionSource(EntityReference(SectionReference((2,)), None))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [
            _IS(EntityReference(SectionReference((0,)), None), is_installation_old, source),
            _IS(EntityReference(SectionReference((3,)), [0]), is_installation_old, source),
        ],
        [_AS(SectionReference((1,)), new_text, is_installation_new, source)],
        [AMWarning(SectionReference((0,)), 'Fake warning')],
    )

    new_am_1 = apply_parameter_values_to_am(am, parametrization, {parameter: False})

    assert _all_alineas_inactive(new_am_1.sections[0])
    app: Applicability = ensure_not_none(new_am_1.sections[0].applicability)
    assert len(app.warnings) == 2
    assert 'Fake warning' in itemgetter(0, 1)(app.warnings)

    app_2: Applicability = ensure_not_none(new_am_1.sections[1].applicability)
    assert not app_2.modified
    assert len(app_2.warnings) == 0

    app_3: Applicability = ensure_not_none(new_am_1.sections[3].applicability)
    assert not new_am_1.sections[3].outer_alineas[0].active
    assert new_am_1.sections[3].outer_alineas[1].active
    assert len(app_3.warnings) == 1

    new_am_2 = apply_parameter_values_to_am(am, parametrization, {parameter: True})

    assert _all_alineas_active(new_am_2.sections[0])
    app_4: Applicability = ensure_not_none(new_am_2.sections[0].applicability)
    assert len(app_4.warnings) == 1

    app_5: Applicability = ensure_not_none(new_am_2.sections[1].applicability)
    assert app_5.modified
    assert len(app_5.warnings) == 1
    assert new_am_2.sections[1].outer_alineas[0].text == 'version modifiée'
    assert app_5.previous_version is not None

    assert new_am_2.sections[3].outer_alineas[0].active
    assert new_am_2.sections[3].outer_alineas[1].active
    app_6: Applicability = ensure_not_none(new_am_2.sections[3].applicability)
    assert len(app_6.warnings) == 0

    new_am_3 = apply_parameter_values_to_am(am, parametrization, {})
    assert _all_alineas_active(new_am_3.sections[0])
    app_7: Applicability = ensure_not_none(new_am_3.sections[0].applicability)
    assert len(app_7.warnings) == 2

    app_8: Applicability = ensure_not_none(new_am_3.sections[1].applicability)
    assert not app_8.modified
    assert len(app_8.warnings) == 1

    app_9: Applicability = ensure_not_none(new_am_3.sections[3].applicability)
    assert new_am_3.sections[3].outer_alineas[0].active
    assert new_am_3.sections[3].outer_alineas[1].active
    assert len(app_9.warnings) == 1


def test_extract_parameters_from_parametrization():
    parameter_1 = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    condition_1 = Equal(parameter_1, True)
    parameter_2 = Parameter('nouvelle-installation', ParameterType.BOOLEAN)
    condition_2 = Equal(parameter_2, True)
    source = ConditionSource(EntityReference(SectionReference((2,)), None))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [_IS(EntityReference(SectionReference((0,)), None), condition_1, source)],
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
    source = ConditionSource(EntityReference(SectionReference((2,)), None))
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    parametrization = Parametrization(
        [_IS(EntityReference(SectionReference((0,)), None), condition_1, source)],
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
    source = ConditionSource(EntityReference(SectionReference((2,)), None))
    parametrization = Parametrization([_IS(EntityReference(SectionReference((0,)), None), condition, source)], [], [])

    res = generate_versions(am, parametrization, False)
    assert len(res) == 3
    assert ('nouvelle-installation != False',) in res
    assert ('nouvelle-installation == False',) in res
    assert () in res
    assert _all_alineas_inactive(res[('nouvelle-installation == False',)].sections[0])
    assert _all_alineas_active(res[('nouvelle-installation != False',)].sections[0])
    assert _all_alineas_active(res[()].sections[0])
    app: Applicability = ensure_not_none(res[()].sections[0].applicability)
    assert len(app.warnings) == 1

    res_2 = generate_versions(am, Parametrization([], [], []), False)
    assert len(res_2) == 1
    assert () in res_2
    exp = Applicability(active=True, modified=False, warnings=[], previous_version=None)
    assert res_2[()].sections[0].applicability == exp


def _get_simple_text(sections: Optional[List[StructuredText]] = None) -> StructuredText:
    return StructuredText(_str('Conditions d\'application'), [_str('al 1'), _str('al 2')], sections or [], None)


def test_deactivate_alineas():
    nac = _IS(
        EntityReference(SectionReference((0,)), None),
        Littler(ParameterEnum.DATE_INSTALLATION.value, datetime(2021, 1, 1)),
        ConditionSource(EntityReference(SectionReference((1,)), None)),
    )
    res = _deactivate_alineas(_get_simple_text(), nac, {ParameterEnum.DATE_INSTALLATION.value: datetime(2020, 1, 1)})
    assert not res.applicability.active  # type: ignore
    assert all([not al.active for al in res.outer_alineas])

    nac = _IS(
        EntityReference(SectionReference((0,)), [0]),
        Littler(ParameterEnum.DATE_INSTALLATION.value, datetime(2021, 1, 1)),
        ConditionSource(EntityReference(SectionReference((1,)), None)),
    )
    res = _deactivate_alineas(_get_simple_text(), nac, {ParameterEnum.DATE_INSTALLATION.value: datetime(2020, 1, 1)})
    assert res.applicability.active  # type: ignore
    assert not res.outer_alineas[0].active
    assert res.outer_alineas[1].active

    nac = _IS(
        EntityReference(SectionReference((0,)), None),
        Littler(ParameterEnum.DATE_INSTALLATION.value, datetime(2021, 1, 1)),
        ConditionSource(EntityReference(SectionReference((1,)), None)),
    )
    res = _deactivate_alineas(
        _get_simple_text([_get_simple_text()]), nac, {ParameterEnum.DATE_INSTALLATION.value: datetime(2020, 1, 1)}
    )
    assert not res.applicability.active  # type: ignore
    assert not res.sections[0].applicability.active  # type: ignore


def test_extract_surrounding_dates():
    assert _extract_surrounding_dates(date.today(), []) == (None, None)

    dates = [date.today() + timedelta(days=2 * i + 1) for i in range(3)]
    assert _extract_surrounding_dates(date.today(), dates) == (None, dates[0])
    assert _extract_surrounding_dates(date.today() + timedelta(1), dates) == (dates[0], dates[1])
    assert _extract_surrounding_dates(date.today() + timedelta(2), dates) == (dates[0], dates[1])
    assert _extract_surrounding_dates(date.today() + timedelta(4), dates) == (dates[1], dates[2])
    assert _extract_surrounding_dates(date.today() + timedelta(6), dates) == (dates[2], None)


def test_is_satisfiable():
    enregistrement = ParameterEnum.DATE_ENREGISTREMENT.value
    regime = ParameterEnum.REGIME.value

    condition = Littler(enregistrement, date(2021, 1, 1))
    assert _is_satisfiable(condition, Regime.E)

    condition = Equal(regime, Regime.E)
    assert _is_satisfiable(condition, Regime.E)

    condition = Equal(regime, Regime.A)
    assert not _is_satisfiable(condition, Regime.E)

    condition = AndCondition(frozenset([Equal(regime, Regime.A), Littler(enregistrement, date(2021, 1, 1))]))
    assert not _is_satisfiable(condition, Regime.E)

    condition = OrCondition(frozenset([Equal(regime, Regime.A), Littler(enregistrement, date(2021, 1, 1))]))
    assert _is_satisfiable(condition, Regime.E)

    condition = AndCondition(frozenset([Equal(regime, Regime.E), Littler(enregistrement, date(2021, 1, 1))]))
    assert _is_satisfiable(condition, Regime.E)

    with pytest.raises(ValueError):
        condition = AndCondition(frozenset([Littler(regime, Regime.E), Littler(enregistrement, date(2021, 1, 1))]))
        _is_satisfiable(condition, Regime.E)
