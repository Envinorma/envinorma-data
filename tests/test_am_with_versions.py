from datetime import date

from envinorma.models.condition import AndCondition, Littler, Range, extract_leaf_conditions
from envinorma.models.parameter import Parameter, ParameterType
from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import EnrichedString
from envinorma.parametrization.combinations import _generate_options_dicts, generate_exhaustive_combinations
from envinorma.parametrization.models.parametrization import (
    AlternativeSection,
    AMWarning,
    InapplicableSection,
    Parametrization,
    extract_conditions_from_parametrization,
)

_DATE = Parameter(id='date-d-installation', type=ParameterType.DATE)
_NEW_TEXT = StructuredText(
    title=EnrichedString(text='Article 2.1'),
    outer_alineas=[EnrichedString(text='Contenu nouveau')],
    sections=[],
    applicability=None,
    reference=None,
    annotations=None,
    id='d16d0fE7C7fc',
)
_PARAMETRIZATION = Parametrization(
    inapplicable_sections=[
        InapplicableSection(
            section_id='abcdef',
            alineas=None,
            condition=AndCondition(
                conditions=frozenset([Littler(parameter=_DATE, target=date(2021, 1, 1), strict=True)])
            ),
        )
    ],
    alternative_sections=[
        AlternativeSection(
            section_id='123456',
            new_text=_NEW_TEXT,
            condition=AndCondition(
                conditions=frozenset([Range(parameter=_DATE, left=date(2020, 1, 1), right=date(2021, 1, 1))])
            ),
        )
    ],
    warnings=[AMWarning('ABCDEF', 'AM warning')],
)


def test_generate_exhaustive_combinations():
    res = generate_exhaustive_combinations(_PARAMETRIZATION)
    assert len(res) == 4


def test_generate_options_dicts():
    res = _generate_options_dicts(_PARAMETRIZATION)
    expected = [
        'date-d-installation < 2020-01-01',
        '2020-01-01 <= date-d-installation < 2021-01-01',
        'date-d-installation >= 2021-01-01',
    ]
    assert [name for _, options in res for name, _ in options] == expected


def test_extract_parameters_from_parametrization():
    res = _PARAMETRIZATION.extract_parameters()
    assert len(res) == 1
    assert list(res)[0] == _DATE


def test_extract_conditions_from_parametrization():
    res = extract_conditions_from_parametrization(_DATE, _PARAMETRIZATION)
    assert res == [
        Littler(parameter=_DATE, target=date(2021, 1, 1), strict=True),
        Range(parameter=_DATE, left=date(2020, 1, 1), right=date(2021, 1, 1)),
    ]


def test_extract_leaf_conditions():
    res = extract_leaf_conditions(_PARAMETRIZATION.inapplicable_sections[0].condition, _DATE)
    assert len(res) == 1

    res = extract_leaf_conditions(_PARAMETRIZATION.alternative_sections[0].condition, _DATE)
    assert len(res) == 1
