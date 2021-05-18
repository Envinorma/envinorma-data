from datetime import date, datetime

from envinorma.data import (
    AMMetadata,
    AMSource,
    AMState,
    ArreteMinisteriel,
    Classement,
    EnrichedString,
    Regime,
    StructuredText,
    Table,
)
from envinorma.data.text_elements import Cell, Row
from envinorma.parametrization import (
    AlternativeSection,
    AMWarning,
    ConditionSource,
    EntityReference,
    Littler,
    NonApplicationCondition,
    Parameter,
    ParameterType,
    Parametrization,
    SectionReference,
    extract_conditions_from_parametrization,
)
from envinorma.parametrization.am_with_versions import apply_parametrization
from envinorma.parametrization.conditions import AndCondition, ConditionType, Range, extract_leaf_conditions
from envinorma.parametrization.parametric_am import (
    _generate_exhaustive_combinations,
    _generate_options_dicts,
    extract_parameters_from_parametrization,
    generate_all_am_versions,
)

_DATE = Parameter(id='date-d-installation', type=ParameterType.DATE)

_PARAMETRIZATION = Parametrization(
    application_conditions=[
        NonApplicationCondition(
            targeted_entity=EntityReference(
                section=SectionReference(path=(0,)), outer_alinea_indices=None, whole_arrete=False
            ),
            condition=AndCondition(
                conditions=[
                    Littler(parameter=_DATE, target=datetime(2021, 1, 1, 0, 0), strict=True, type=ConditionType.LITTLER)
                ],
                type=ConditionType.AND,
            ),
            source=ConditionSource(
                explanation='',
                reference=EntityReference(
                    section=SectionReference(path=(0,)), outer_alinea_indices=None, whole_arrete=False
                ),
            ),
            description='',
        )
    ],
    alternative_sections=[
        AlternativeSection(
            targeted_section=SectionReference(path=(1, 0)),
            new_text=StructuredText(
                title=EnrichedString(text='Article 2.1', links=[], table=None, active=True),
                outer_alineas=[EnrichedString(text='Contenu nouveau', links=[], table=None, active=True)],
                sections=[],
                applicability=None,
                lf_id=None,
                reference_str=None,
                annotations=None,
                id='d16d0fE7C7fc',
            ),
            condition=AndCondition(
                conditions=[Range(parameter=_DATE, left=datetime(2020, 1, 1, 0, 0), right=datetime(2021, 1, 1, 0, 0))],
                type=ConditionType.AND,
            ),
            source=ConditionSource(
                explanation='',
                reference=EntityReference(
                    section=SectionReference(path=(1,)), outer_alinea_indices=None, whole_arrete=False
                ),
            ),
            description='',
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
    publication_date=date(2020, 12, 15),
    installation_date_criterion=None,
    aida_url=None,
    legifrance_url=None,
    classements=[],
    classements_with_alineas=[],
    unique_version=False,
    summary=None,
    active=True,
    warning_inactive=None,
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
        publication_date=date.fromtimestamp(1612195449),
        source=AMSource('LEGIFRANCE'),
    )
    res = apply_parametrization('FACE_CID', _STRUCTURED_AM, _PARAMETRIZATION, md)
    assert res and len(res) == 4


def test_generate_all_am_versions():
    res = generate_all_am_versions(_STRUCTURED_AM, _PARAMETRIZATION, True)
    assert len(res) == 4


def test_generate_exhaustive_combinations():
    res = _generate_exhaustive_combinations(_PARAMETRIZATION, True)
    assert len(res) == 4


def test_generate_options_dicts():
    res = _generate_options_dicts(_PARAMETRIZATION, True)
    assert len(res) == 1
    options = res[0]
    assert len(options) == 3
    assert sorted(list(options.keys())) == [
        '2020-01-01 <= date-d-installation < 2021-01-01',
        'date-d-installation < 2020-01-01',
        'date-d-installation >= 2021-01-01',
    ]


def test_extract_parameters_from_parametrization():
    res = extract_parameters_from_parametrization(_PARAMETRIZATION)
    assert len(res) == 1
    assert list(res)[0] == _DATE


def test_extract_conditions_from_parametrization():
    res = extract_conditions_from_parametrization(_DATE, _PARAMETRIZATION)
    assert len(res) == 2


def test_extract_leaf_conditions():
    res = extract_leaf_conditions(_PARAMETRIZATION.application_conditions[0].condition, _DATE)
    assert len(res) == 1

    res = extract_leaf_conditions(_PARAMETRIZATION.alternative_sections[0].condition, _DATE)
    assert len(res) == 1
