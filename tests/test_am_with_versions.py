from datetime import date

from envinorma.models.am_metadata import AMMetadata, AMSource, AMState
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.classement import Classement, Regime
from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import Cell, EnrichedString, Row, Table
from envinorma.parametrization.am_with_versions import (
    _extract_am_regime,
    _generate_versions_and_postprocess,
    generate_versions,
)
from envinorma.parametrization.combinations import _generate_options_dicts, generate_exhaustive_combinations
from envinorma.parametrization.models.condition import AndCondition, Littler, Range, extract_leaf_conditions
from envinorma.parametrization.models.parameter import Parameter, ParameterType
from envinorma.parametrization.models.parametrization import (
    AlternativeSection,
    AMWarning,
    ConditionSource,
    EntityReference,
    InapplicableSection,
    Parametrization,
    SectionReference,
    extract_conditions_from_parametrization,
)

_DATE = Parameter(id='date-d-installation', type=ParameterType.DATE)
_NEW_TEXT = StructuredText(
    title=EnrichedString(text='Article 2.1'),
    outer_alineas=[EnrichedString(text='Contenu nouveau')],
    sections=[],
    applicability=None,
    reference_str=None,
    annotations=None,
    id='d16d0fE7C7fc',
)
_PARAMETRIZATION = Parametrization(
    inapplicable_sections=[
        InapplicableSection(
            targeted_entity=EntityReference(section=SectionReference(path=(0,)), outer_alinea_indices=None),
            condition=AndCondition(conditions=[Littler(parameter=_DATE, target=date(2021, 1, 1), strict=True)]),
            source=ConditionSource(
                reference=EntityReference(section=SectionReference(path=(0,)), outer_alinea_indices=None),
            ),
        )
    ],
    alternative_sections=[
        AlternativeSection(
            targeted_section=SectionReference(path=(1, 0)),
            new_text=_NEW_TEXT,
            condition=AndCondition(conditions=[Range(parameter=_DATE, left=date(2020, 1, 1), right=date(2021, 1, 1))]),
            source=ConditionSource(EntityReference(section=SectionReference(path=(1,)), outer_alinea_indices=None)),
        )
    ],
    warnings=[AMWarning(SectionReference(()), 'AM warning')],
)

_STRUCTURED_AM = ArreteMinisteriel(
    title=EnrichedString(text='Arrêté du 15/12/20', links=[], table=None, active=True),
    sections=[
        StructuredText(
            title=EnrichedString(text='Article 1', links=[], table=None, active=True),
            outer_alineas=[],
            sections=[
                StructuredText(
                    title=EnrichedString(text='Article 1.1', links=[], table=None, active=True),
                    outer_alineas=[],
                    sections=[
                        StructuredText(
                            title=EnrichedString(text='I.', links=[], table=None, active=True),
                            outer_alineas=[
                                EnrichedString(text='Test', links=[], table=None, active=True),
                                EnrichedString(text='ceci est le I', links=[], table=None, active=True),
                            ],
                            sections=[],
                            applicability=None,
                        ),
                        StructuredText(
                            title=EnrichedString(text='II.', links=[], table=None, active=True),
                            outer_alineas=[
                                EnrichedString(text='Test', links=[], table=None, active=True),
                                EnrichedString(text='ceci est le II', links=[], table=None, active=True),
                            ],
                            sections=[],
                            applicability=None,
                        ),
                    ],
                    applicability=None,
                )
            ],
            applicability=None,
        ),
        StructuredText(
            title=EnrichedString(text='Article 2', links=[], table=None, active=True),
            outer_alineas=[],
            sections=[
                StructuredText(
                    title=EnrichedString(text='Article 2.1', links=[], table=None, active=True),
                    outer_alineas=[
                        EnrichedString(text='Contenu', links=[], table=None, active=True),
                        EnrichedString(
                            text='',
                            links=[],
                            table=Table(
                                rows=[
                                    Row(
                                        cells=[
                                            Cell(
                                                content=EnrichedString(
                                                    text='Cellule 1', links=[], table=None, active=True
                                                ),
                                                colspan=1,
                                                rowspan=1,
                                            )
                                        ],
                                        is_header=False,
                                    ),
                                    Row(
                                        cells=[
                                            Cell(
                                                content=EnrichedString(
                                                    text='Cellule 2', links=[], table=None, active=True
                                                ),
                                                colspan=1,
                                                rowspan=1,
                                            )
                                        ],
                                        is_header=False,
                                    ),
                                ]
                            ),
                            active=True,
                        ),
                    ],
                    sections=[],
                    applicability=None,
                )
            ],
            applicability=None,
        ),
    ],
    visa=[],
    date_of_signature=date(2020, 12, 15),
    aida_url=None,
    legifrance_url=None,
    classements=[],
    classements_with_alineas=[],
    id='FAKE_ID',
)


def test_apply_parametrization():
    md = AMMetadata(
        aida_page='5619',
        title='Faux Arrêté du 01/02/21 relatif aux tests',
        nor='FAKE_NOR',
        classements=[Classement(regime=Regime('E'), rubrique='5000', alinea='A.2')],
        cid='FAKE_CID',
        state=AMState('VIGUEUR'),
        date_of_signature=date.fromtimestamp(1612195449),
        source=AMSource('LEGIFRANCE'),
    )
    res = _generate_versions_and_postprocess('FACE_CID', _STRUCTURED_AM, _PARAMETRIZATION, md)
    assert res and len(res) == 4


def test_generate_versions_and_postprocess():
    res = generate_versions(_STRUCTURED_AM, _PARAMETRIZATION, True)
    assert len(res) == 4


def test_generate_exhaustive_combinations():
    res = generate_exhaustive_combinations(_PARAMETRIZATION, True, None)
    assert len(res) == 4


def test_generate_options_dicts():
    res = _generate_options_dicts(_PARAMETRIZATION, True, None)
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


def _generate_classement(regime: str) -> Classement:
    return Classement('1234', Regime(regime), None)


def test_extract_am_regime():
    assert _extract_am_regime([]) is None
    assert _extract_am_regime([_generate_classement('A')]) == Regime.A
    assert _extract_am_regime([_generate_classement('E')]) == Regime.E
    assert _extract_am_regime([_generate_classement('D')]) == Regime.D
    assert _extract_am_regime([_generate_classement('D'), _generate_classement('A')]) is None
