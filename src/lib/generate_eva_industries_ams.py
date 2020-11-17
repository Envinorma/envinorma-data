import json
from datetime import datetime
from lib.generate_1510_parametrization import build_1510_parametrization, generate_1510_combinations
from lib.am_enriching import add_references, add_topics, remove_null_applicabilities, remove_prescriptive_power
from typing import Callable, List, Dict, Set, Tuple, Optional

from lib.data import ArreteMinisteriel, EnrichedString, StructuredText, load_arrete_ministeriel, Topic
from lib.compute_properties import AMMetadata, handle_am, load_data, get_legifrance_client, write_json
from lib.parametric_am import (
    ApplicationCondition,
    ConditionSource,
    ConditionType,
    EntityReference,
    Greater,
    Parameter,
    ParameterType,
    Parametrization,
    SectionReference,
    Ints,
    build_simple_parametrization,
    generate_all_am_versions,
    Combinations,
)


def _find_metadata_with_nor(metadata: List[AMMetadata], nor: str) -> AMMetadata:
    for md in metadata:
        if md.nor == nor:
            return md
    raise ValueError(f'Could not find AM with nor {nor}')


def _generate_structured_am(nor: str) -> ArreteMinisteriel:
    data = load_data()
    metadata = _find_metadata_with_nor(data.arretes_ministeriels.metadata, nor)
    handle_am(metadata, get_legifrance_client(), True)
    return load_arrete_ministeriel(json.load(open(f'data/AM/structured_texts/{nor}.json')))


def _generate_filename(version_descriptor: Tuple[str, ...]) -> str:
    if not version_descriptor:
        return 'unique_version'
    return '_AND_'.join(version_descriptor).replace(' ', '_')


def _handle_nor(
    nor: str,
    parametrization: Parametrization,
    enricher: Callable[[ArreteMinisteriel], ArreteMinisteriel],
    combinations: Optional[Combinations] = None,
):
    am = _generate_structured_am(nor)
    enriched_am = add_references(enricher(am))
    write_json(enriched_am.as_dict(), f'data/AM/enriched_texts/{nor}.json')
    write_json(parametrization.to_dict(), f'data/AM/parametrizations/{nor}.json')
    all_versions = generate_all_am_versions(enriched_am, parametrization, combinations)

    for version_desc, version in all_versions.items():
        filename = f'data/AM/parametric_texts/{nor}/' + _generate_filename(version_desc) + '.json'
        write_json(version.as_dict(), filename)


# TREP1900331A
def _build_TREP1900331A_parametrization() -> Parametrization:
    new_articles = {
        tuple([3, 3, 1]): StructuredText(
            title=EnrichedString('Article 4.10.'),
            outer_alineas=[
                EnrichedString('Rétention et isolement.'),
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


def enrich_TREP1900331A(am: ArreteMinisteriel) -> ArreteMinisteriel:
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


# _handle_nor('TREP1900331A', _build_TREP1900331A_parametrization(), enrich_TREP1900331A)


# DEVP1329353A PAS LE BON AM!


def _build_DEVP1329353A_parametrization() -> Parametrization:
    source = ConditionSource(
        'Paragraphe décrivant ce qui s\'applique aux installations existantes',
        EntityReference(SectionReference((0,)), None),
    )
    condition = Greater(Parameter('date-d-installation', ParameterType.DATE), datetime(2013, 12, 10), False)
    application_conditions = [
        ApplicationCondition(EntityReference(SectionReference(()), None, True), condition, source)
    ]
    return Parametrization(application_conditions, [])


def enrich_DEVP1329353A(am: ArreteMinisteriel) -> ArreteMinisteriel:
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


# _handle_nor('DEVP1329353A', _build_DEVP1329353A_parametrization(), enrich_DEVP1329353A)

# DEVP1235896A
def _build_DEVP1235896A_parametrization() -> Parametrization:
    condition = Greater(
        Parameter('date-d-installation', ParameterType.DATE), datetime(2012, 11, 26, 0, 0), False, ConditionType.GREATER
    )
    source = ConditionSource(
        "Paragraphe décrivant ce qui s'applique aux installations existantes",
        EntityReference(section=SectionReference(path=(11, 1)), outer_alinea_indices=None, whole_arrete=False),
    )

    return Parametrization(
        [
            ApplicationCondition(
                EntityReference(
                    SectionReference(path=(2, 1)),
                    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
                    False,
                ),
                condition,
                source,
            ),
            ApplicationCondition(EntityReference(SectionReference(path=(2, 2)), None, False), condition, source),
            ApplicationCondition(EntityReference(SectionReference(path=(3, 2, 0)), None, False), condition, source),
            ApplicationCondition(EntityReference(SectionReference(path=(4, 1, 1)), [0], False), condition, source),
            ApplicationCondition(EntityReference(SectionReference(path=(4, 3, 1)), [1], False), condition, source),
        ],
        alternative_sections=[],
    )


def enrich_DEVP1235896A(am: ArreteMinisteriel) -> ArreteMinisteriel:
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


# _handle_nor('DEVP1235896A', _build_DEVP1235896A_parametrization(), enrich_DEVP1235896A)

# ATEP9760292A
def _build_ATEP9760292A_parametrization() -> Parametrization:
    return Parametrization([], alternative_sections=[])  # All is applicable


def enrich_ATEP9760292A(am: ArreteMinisteriel) -> ArreteMinisteriel:
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


# _handle_nor('ATEP9760292A', _build_ATEP9760292A_parametrization(), enrich_ATEP9760292A)

# _handle_nor('DEVP1706393A', build_1510_parametrization(), lambda x: x, generate_1510_combinations())
