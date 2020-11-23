from datetime import datetime
from lib.am_enriching import add_topics, remove_null_applicabilities, remove_prescriptive_power
from typing import Callable, Dict, Optional, Set
from lib.parametric_am import Combinations
from lib.parametrization import (
    ConditionSource,
    EntityReference,
    Littler,
    NonApplicationCondition,
    Parameter,
    ParameterEnum,
    ParameterType,
    Parametrization,
    Ints,
    SectionReference,
    build_simple_parametrization,
)
from lib.data import ArreteMinisteriel, StructuredText, EnrichedString, Topic
from lib.manual_enrichments.generate_1510_parametrization import build_1510_parametrization, generate_1510_combinations


def identity(am: ArreteMinisteriel) -> ArreteMinisteriel:
    return am


def get_manual_enricher(id_: str) -> Callable[[ArreteMinisteriel], ArreteMinisteriel]:
    if id_ == 'TREP1900331A':
        return _enrich_TREP1900331A
    if id_ == 'DEVP1329353A':
        return _enrich_DEVP1329353A
    if id_ == 'ATEP9760290A':
        return _enrich_ATEP9760290A
    if id_ == 'ATEP9760292A':
        return _enrich_ATEP9760292A
    if id_ == 'DEVP1235896A':
        return _enrich_DEVP1235896A
    if id_ == 'DEVP1706393A':
        return identity
    raise ValueError(f'No manual enricher found for id_ {id_}')


def get_manual_parametrization(id_: str) -> Parametrization:
    if id_ == 'TREP1900331A':
        return _build_TREP1900331A_parametrization()
    if id_ == 'DEVP1329353A':
        return _build_DEVP1329353A_parametrization()
    if id_ == 'ATEP9760290A':
        return _build_ATEP9760290A_parametrization()
    if id_ == 'ATEP9760292A':
        return _build_ATEP9760292A_parametrization()
    if id_ == 'DEVP1235896A':
        return _build_DEVP1235896A_parametrization()
    if id_ == 'DEVP1706393A':
        return build_1510_parametrization()
    raise ValueError(f'No parametrization found for id_ {id_}')


def get_manual_combinations(id_: str) -> Optional[Combinations]:
    if id_ == 'TREP1900331A':
        return None
    if id_ == 'DEVP1329353A':
        return None
    if id_ == 'ATEP9760290A':
        return None
    if id_ == 'ATEP9760292A':
        return None
    if id_ == 'DEVP1235896A':
        return None
    if id_ == 'DEVP1706393A':
        return generate_1510_combinations()

    raise ValueError(f'No combinations found for id_ {id_}')


# TREP1900331A
def _build_TREP1900331A_parametrization() -> Parametrization:
    new_articles = {
        tuple([3, 3, 1]): StructuredText(
            title=EnrichedString('Article 4.10. - Rétention et isolement.'),
            outer_alineas=[
                EnrichedString(
                    'Toutes mesures sont prises pour recueillir l’ensemble des eaux et écoulements'
                    ' susceptibles d’être pollués lors d’un sinistre, y compris les eaux utilisées'
                    ' lors d’un incendie, afin que celles-ci soient récupérées ou traitées afin de'
                    ' prévenir toute pollution des sols, des égouts, des cours d’eau ou du milieu '
                    'naturel.'
                ),
                EnrichedString(
                    'En cas de recours à des systèmes de relevage autonomes, l’exploitant est en m'
                    'esure de justifier à tout instant d’un entretien et d’une maintenance rigoure'
                    'ux de ces dispositifs. Des tests réguliers sont par ailleurs menés sur ces éq'
                    'uipements.'
                ),
                EnrichedString(
                    'En cas de confinement interne, les orifices d’écoulement sont en position fer'
                    'mée par défaut. En cas de confinement externe, les orifices d’écoulement issu'
                    's de ces dispositifs sont munis d’un dispositif automatique d’obturation pour'
                    ' assurer ce confinement lorsque des eaux susceptibles d’être pollués y sont p'
                    'ortées. Tout moyen est mis en place pour éviter la propagation de l’incendie '
                    'par ces écoulements.'
                ),
                EnrichedString(
                    'Des dispositifs permettant l’obturation des réseaux d’évacuation des eaux de '
                    'ruissellement sont implantés de sorte à maintenir sur le site les eaux d’exti'
                    'nction d’un sinistre ou les épandages accidentels. Ils sont clairement signal'
                    'és et facilement accessibles et peuvent être mis en œuvre dans des délais bre'
                    'fs et à tout moment. Une consigne définit les modalités de mise en œuvre de c'
                    'es dispositifs. Cette consigne est affichée à l’accueil de l’établissement.'
                ),
            ],
            sections=[],
            legifrance_article=None,
            applicability=None,
        )
    }
    return build_simple_parametrization(
        [(1, 0), (3, 1, 0), (3, 1, 1), (3, 1, 2), (5, 1, 2)], new_articles, (10, 0), datetime(2019, 4, 9)
    )


def _enrich_TREP1900331A(am: ArreteMinisteriel) -> ArreteMinisteriel:
    topics: Dict[Ints, Topic] = {
        (4, 0, 0): Topic.EAU,
        (4, 0, 1): Topic.EAU,
        (4, 1, 0): Topic.EAU,
        (4, 1, 1): Topic.EAU,
        (4, 1, 2): Topic.EAU,
        (4, 1, 3): Topic.EAU,
        (4, 2, 0): Topic.EAU,
        (4, 2, 1): Topic.EAU,
        (4, 2, 2): Topic.EAU,
        (4, 2, 3): Topic.EAU,
        (4, 3, 0): Topic.EAU,
        (5, 0, 0): Topic.AIR,
        (5, 1, 0): Topic.AIR,
        (5, 1, 1): Topic.AIR,
        (5, 1, 2): Topic.AIR,
        (5, 2, 0): Topic.AIR,
        (5, 2, 1): Topic.AIR,
        (5, 2, 2): Topic.AIR,
        (5, 2, 3): Topic.AIR,
        (6, 0): Topic.BRUIT,
        (6, 1): Topic.BRUIT,
        (7, 0): Topic.DECHETS,
        (7, 1): Topic.DECHETS,
        (7, 2): Topic.DECHETS,
    }
    with_topics = add_topics(am, topics)
    non_prescriptive: Set[Ints] = {(9, 0), (10, 0), (0, 0), (0, 1), (0, 2), (0, 3), (0, 4)}
    return remove_prescriptive_power(with_topics, non_prescriptive)


# DEVP1329353A


def _build_DEVP1329353A_parametrization() -> Parametrization:
    source = ConditionSource(
        'Paragraphe décrivant ce qui s\'applique aux installations existantes',
        EntityReference(SectionReference((0,)), None),
    )
    description = f'''L'arrêté ne s'applique qu'aux sites dont la date d'installation est postérieure au 10/12/2013.'''
    condition = Littler(Parameter('date-d-installation', ParameterType.DATE), datetime(2013, 12, 10), True)
    application_conditions = [
        NonApplicationCondition(EntityReference(SectionReference(()), None, True), condition, source, description)
    ]
    return Parametrization(application_conditions, [])


def _enrich_DEVP1329353A(am: ArreteMinisteriel) -> ArreteMinisteriel:
    non_prescriptive: Set[Ints] = {(0,), (1,), (10,), (9,)}

    topics: Dict[Ints, Topic] = {
        (4,): Topic.EAU,
        (4, 0): Topic.EAU,
        (4, 0, 0): Topic.EAU,
        (4, 1): Topic.EAU,
        (4, 1, 0): Topic.EAU,
        (4, 1, 1): Topic.EAU,
        (4, 1, 2): Topic.EAU,
        (4, 2): Topic.EAU,
        (4, 2, 0): Topic.EAU,
        (4, 2, 1): Topic.EAU,
        (4, 2, 2): Topic.EAU,
        (4, 2, 3): Topic.EAU,
        (4, 2, 4): Topic.EAU,
        (4, 3): Topic.EAU,
        (4, 3, 0): Topic.EAU,
        (4, 3, 1): Topic.EAU,
        (4, 3, 2): Topic.EAU,
        (4, 3, 3): Topic.EAU,
        (4, 4): Topic.EAU,
        (4, 4, 0): Topic.EAU,
        (4, 4, 1): Topic.EAU,
        (5,): Topic.AIR,
        (5, 0): Topic.AIR,
        (5, 0, 0): Topic.AIR,
        (5, 1): Topic.AIR,
        (5, 1, 0): Topic.AIR,
        (5, 2): Topic.AIR,
        (5, 2, 0): Topic.AIR,
        (6,): Topic.BRUIT,
        (6, 0): Topic.BRUIT,
        (6, 1): Topic.BRUIT,
        (6, 2): Topic.BRUIT,
        (6, 3): Topic.BRUIT,
        (7,): Topic.DECHETS,
        (7, 0): Topic.DECHETS,
        (7, 1): Topic.DECHETS,
        (7, 2): Topic.DECHETS,
    }
    with_topics = add_topics(am, topics)
    return remove_prescriptive_power(with_topics, non_prescriptive)


# DEVP1235896A [Not the right AM]
def _build_DEVP1235896A_parametrization() -> Parametrization:
    description = (
        f'''Le paragraphe ne s'applique qu'aux sites dont la date d'installation est postérieure au 26/11/2012.'''
    )
    description_modif_1 = (
        f'''Pour les sites dont la date d'installation est postérieure au 26/11/2012, '''
        '''seuls les alineas concernant le dossier d'exploitation s'appliquent'''
    )
    old_installation = Littler(ParameterEnum.DATE_INSTALLATION.value, datetime(2012, 11, 26, 0, 0), True)
    # new_installation = Greater(ParameterEnum.DATE_INSTALLATION.value, datetime(2012, 11, 26, 0, 0), False)
    source = ConditionSource(
        "Paragraphe décrivant ce qui s'applique aux installations existantes",
        EntityReference(section=SectionReference(path=(11, 1)), outer_alinea_indices=None, whole_arrete=False),
    )

    return Parametrization(
        [
            NonApplicationCondition(
                EntityReference(
                    SectionReference(path=(2, 1)),
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
                    False,
                ),
                old_installation,
                source,
                description=description_modif_1,
            ),
            NonApplicationCondition(
                EntityReference(SectionReference(path=(2, 2)), None, False), old_installation, source, description
            ),
            NonApplicationCondition(
                EntityReference(SectionReference(path=(3, 2, 0)), None, False), old_installation, source, description
            ),
            NonApplicationCondition(
                EntityReference(SectionReference(path=(4, 1, 1)), [0], False), old_installation, source, description
            ),
            NonApplicationCondition(
                EntityReference(SectionReference(path=(4, 3, 1)), [1], False), old_installation, source, description
            ),
        ],
        alternative_sections=[],
    )


def _enrich_DEVP1235896A(am: ArreteMinisteriel) -> ArreteMinisteriel:
    topics: Dict[Ints, Topic] = {
        (4,): Topic.EAU,
        (4, 0): Topic.EAU,
        (4, 0, 0): Topic.EAU,
        (4, 1): Topic.EAU,
        (4, 1, 0): Topic.EAU,
        (4, 1, 1): Topic.EAU,
        (4, 1, 2): Topic.EAU,
        (4, 2): Topic.EAU,
        (4, 2, 0): Topic.EAU,
        (4, 2, 1): Topic.EAU,
        (4, 2, 2): Topic.EAU,
        (4, 2, 3): Topic.EAU,
        (4, 2, 4): Topic.EAU,
        (4, 3): Topic.EAU,
        (4, 3, 0): Topic.EAU,
        (4, 3, 1): Topic.EAU,
        (4, 3, 2): Topic.EAU,
        (4, 3, 3): Topic.EAU,
        (4, 4): Topic.EAU,
        (4, 4, 0): Topic.EAU,
        (4, 4, 1): Topic.EAU,
        (5,): Topic.AIR,
        (5, 0): Topic.AIR,
        (5, 0, 0): Topic.AIR,
        (5, 1): Topic.AIR,
        (5, 1, 0): Topic.AIR,
        (5, 1, 1): Topic.AIR,
        (5, 2): Topic.AIR,
        (5, 2, 0): Topic.AIR,
        (5, 2, 1): Topic.AIR,
        (5, 2, 1, 0): Topic.AIR,
        (5, 2, 1, 1): Topic.AIR,
        (5, 2, 2): Topic.AIR,
        (7,): Topic.BRUIT,
        (7, 0): Topic.BRUIT,
        (7, 1): Topic.BRUIT,
        (7, 2): Topic.BRUIT,
        (7, 3): Topic.BRUIT,
        (7, 4): Topic.BRUIT,
        (7, 5): Topic.BRUIT,
        (7, 6): Topic.BRUIT,
        (7, 7): Topic.BRUIT,
        (7, 7, 0): Topic.BRUIT,
        (7, 7, 1): Topic.BRUIT,
        (7, 7, 2): Topic.BRUIT,
        (7, 8): Topic.BRUIT,
        (7, 8, 0): Topic.BRUIT,
        (7, 8, 1): Topic.BRUIT,
        (7, 8, 2): Topic.BRUIT,
        (8,): Topic.DECHETS,
        (8, 0): Topic.DECHETS,
        (8, 1): Topic.DECHETS,
        (8, 2): Topic.DECHETS,
    }
    non_prescriptive: Set[Ints] = {(0,), (1,), (10,), (11, 0), (11, 1)}
    with_topics = add_topics(am, topics)
    return remove_prescriptive_power(with_topics, non_prescriptive)


# ATEP9760292A
def _build_ATEP9760292A_parametrization() -> Parametrization:
    return Parametrization([], alternative_sections=[])  # All is applicable


def _enrich_ATEP9760292A(am: ArreteMinisteriel) -> ArreteMinisteriel:
    topics: Dict[Ints, Topic] = {
        (4, 0, 4): Topic.EAU,
        (4, 0, 4, 7): Topic.EAU,
        (4, 0, 5): Topic.AIR,
        (4, 0, 5, 0): Topic.AIR,
        (4, 0, 5, 3): Topic.AIR,
        (4, 0, 5, 4): Topic.AIR,
        (4, 0, 5, 5): Topic.AIR,
        (4, 0, 6): Topic.DECHETS,
        (4, 0, 6, 0): Topic.DECHETS,
        (4, 0, 6, 1): Topic.DECHETS,
        (4, 0, 6, 2): Topic.DECHETS,
        (4, 0, 6, 3): Topic.DECHETS,
        (4, 0, 6, 4): Topic.DECHETS,
        (4, 0, 7): Topic.BRUIT,
        (4, 0, 7, 0): Topic.BRUIT,
        (4, 0, 7, 1): Topic.BRUIT,
        (4, 0, 7, 2): Topic.BRUIT,
        (4, 0, 7, 3): Topic.BRUIT,
    }
    non_prescriptive: Set[Ints] = {
        (0,),
        (1,),
        (2,),
        (3,),
        (4, 0, 0, 0),
        (4, 0, 0, 1),
        (4, 0, 0, 5),
        (4, 0, 0, 6),
        (4, 0, 0, 7),
        (4, 0, 1, 0),
        (4, 0, 1, 2),
        (4, 0, 1, 3),
        (4, 0, 1, 5),
        (4, 0, 1, 8),
        (4, 0, 1, 9),
        (4, 0, 2, 2),
        (4, 0, 2, 4),
        (4, 0, 4, 0),
        (4, 0, 4, 1),
        (4, 0, 4, 2),
        (4, 0, 4, 3),
        (4, 0, 4, 4),
        (4, 0, 4, 5),
        (4, 0, 4, 6),
        (4, 0, 3, 2),
        (4, 0, 3, 3),
        (4, 0, 3, 4),
        (4, 0, 3, 5),
        (4, 0, 3, 7),
        (4, 0, 4, 8),
        (4, 0, 5, 1),
        (4, 0, 5, 2),
        (4, 1),
    }
    with_topics = add_topics(am, topics)
    return remove_null_applicabilities(remove_prescriptive_power(with_topics, non_prescriptive))


# ATEP9760292A
def _build_ATEP9760290A_parametrization() -> Parametrization:
    return Parametrization([], alternative_sections=[])  # All is applicable


def _enrich_ATEP9760290A(am: ArreteMinisteriel) -> ArreteMinisteriel:
    topics: Dict[Ints, Topic] = {
        (4, 0, 4): Topic.EAU,
        (4, 0, 4, 0): Topic.EAU,
        (4, 0, 4, 1): Topic.EAU,
        (4, 0, 4, 2): Topic.EAU,
        (4, 0, 4, 3): Topic.EAU,
        (4, 0, 4, 4): Topic.EAU,
        (4, 0, 4, 4, 0): Topic.EAU,
        (4, 0, 4, 4, 1): Topic.EAU,
        (4, 0, 4, 4, 2): Topic.EAU,
        (4, 0, 4, 5): Topic.EAU,
        (4, 0, 4, 6): Topic.EAU,
        (4, 0, 4, 7): Topic.EAU,
        (4, 0, 4, 8): Topic.EAU,
        (4, 0, 5): Topic.EAU,
        (4, 0, 5, 0): Topic.EAU,
        (4, 0, 5, 1): Topic.EAU,
        (4, 0, 5, 2): Topic.EAU,
        (4, 0, 5, 3): Topic.EAU,
        (4, 0, 6): Topic.DECHETS,
        (4, 0, 6, 0): Topic.DECHETS,
        (4, 0, 6, 1): Topic.DECHETS,
        (4, 0, 6, 2): Topic.DECHETS,
        (4, 0, 6, 3): Topic.DECHETS,
        (4, 0, 6, 4): Topic.DECHETS,
        (4, 0, 7): Topic.BRUIT,
        (4, 0, 7, 0): Topic.BRUIT,
        (4, 0, 7, 1): Topic.BRUIT,
        (4, 0, 7, 2): Topic.BRUIT,
        (4, 0, 7, 3): Topic.BRUIT,
    }
    non_prescriptive: Set[Ints] = {(0,), (1,), (2,), (3,), (4, 1)}
    with_topics = add_topics(am, topics)
    return remove_null_applicabilities(remove_prescriptive_power(with_topics, non_prescriptive))
