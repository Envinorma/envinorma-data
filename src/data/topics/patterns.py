import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple
from unidecode import unidecode


class TopicName(Enum):
    EPANDAGE = 'EPANDAGE'
    EAU = 'EAU'
    DECHETS = 'DECHETS'
    EXECUTION = 'EXECUTION'
    RISQUES = 'RISQUES'
    DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT = 'DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT'
    DISPOSITIONS_GENERALES = 'DISPOSITIONS_GENERALES'
    BRUIT_VIBRATIONS = 'BRUIT_VIBRATIONS'
    AIR_ODEURS = 'AIR_ODEURS'
    EMISSIONS = 'EMISSIONS'
    ACCIDENTS_POLLUTIONS = 'ACCIDENTS_POLLUTIONS'


# ANNEXE_BO, RESERVES, EXPLOITATION, DOSSIER, EXPLOITATION, LEGIONELLES, RADIOACTIVITES, GESTION_DECHETS_SUBSTANCES, EXPLOITATION, EMISSIONS_ATMOSPHERE, VLE, DEFINITIONS, PREFET, INCENDIE, SURVEILLANCE_EXPLOITATION, EMISSIONS_AIR, INCENDIE, FOUDRE, CONSOMMATION, POUSSIERES, VAPEURS, RISQUE_INDIVIDUEL, INCENDIE, SPECIAUX, FEU, TOITURE, VL, CONDITIONS_APPLICATION, FARINES_VIANDE_ET_OS, INDIVIDUELS, DEFINITIONS, COMBUSTIBLES, BIOMASSE, FEU, EXPLOITATION, DOSSIER, GESTION, CHANGEMENT_EXPLOITANT, INCENDIE, VAPEURS, CONSOMMATION, CONSOMMATION, EXPLOITATION, CHANGEMENT_EXPLOITANT, INCENDIE, EXPLOITATION, DOSSIER, REGISTRE, ABROGATION_AM_PASSE, EFFLUENTS, VAPEURS, VENTILATION, VL, SECURITE, ETANCHEITE, DECLARATION, FIN_EXPLOITATION, BIOGAZ, MODIFICATIONS, REGLES_TECHNIQUES, CONFINEMENT, REJETS_CHLORE, ENTREPOSAGE, VENTILATION, SURVEILLANCE, BRULAGE, ENTREPOSAGE, VL, NORME_TRANSFORMATION, VLE, SURVEILLANCE_EXPLOITATION, INSTALLATIONS_ELECTRIQUES, RECYCLAGE, BILAN_ENVIRONNEMENT, FIN_EXPLOITATION, NON_DANGEREUX, CONDITIONS_APPLICATION, CALENDRIER_APPLICATION, FEU, SURVEILLANCE_EXPLOITATION, EMISSIONS_ATMOSPHERE, METHODOLOGIE, HAUTEUR_CHEMINEE, BANALS, PREFET, CONDITIONS_REJET, JUSTIFICATIONS, VAPEURS, METHODOLOGIE, GESTION, VAPEURS, SURVEILLANCE_EXPLOITATION, GESTION_QUALITE, FIN_EXPLOITATION, BRULAGE, COV, RECENSEMENT, MESURE, METHODOLOGIE, HAUTEUR_CHEMINEE, REGISTRE_EXPLOITATION, ELECTRICITE_STATIQUE, SURVEILLANCE_EXPLOITATION, CONDITIONS_APPLICATION, FEU, PROPRETE, FARINES_VIANDE_ET_OS, ENTREE_VIGUEUR, INFO_REDACTION, CONSIGNES, DEFINITIONS, PREFET, SECURITE, VENTILATION, REJETS_ACCIDENTELS, METHODO, INCENDIE, VLE, CHANGEMENT_EXPLOITANT, INCENDIE, VL, GESTION, INCENDIE, EXPLOITATION, CONDITIONS_APPLICATION, EMISSIONS_ATMOSPHERE, VLE, EXPLOITATION, DOSSIER, DEFINITIONS, POLLUTIONS_ACCIDENTS, POUSSIERES, RETENTION, EMISSIONS_ATMOSPHERE, VLE, CONDITIONS_APPLICATION, DEFINITIONS, MILIEU_AQUATIQUE, COV, EMISSIONS_ATMOSPHERE, INCENDIE, INSTALLATIONS_ELECTRIQUES

Pattern = Tuple[str, ...]


def tokenize(str_: str) -> List[str]:
    return re.split(r'\W+', str_)


def normalize(pattern: str) -> str:
    lower_unidecoded = [str(unidecode(token.lower())) for token in tokenize(pattern)]
    return ' '.join(lower_unidecoded)


def _clean_patterns(patterns: List[str]) -> List[str]:
    return list({normalize(pattern) for pattern in patterns})


@dataclass
class Topic:
    topic_name: TopicName
    compatible_topics: List[TopicName]
    short_title_patterns: List[str]
    other_patterns: List[str]
    short_title_compiled: str = field(init=False)
    other_patterns_compiled: str = field(init=False)

    @staticmethod
    def _check_consistency(short_title_patterns: List[str], other_patterns: List[str]) -> None:
        common_patterns = set(short_title_patterns) & set(other_patterns)
        if common_patterns:
            raise ValueError(f'There are common patterns in short title patterns and other patterns: {common_patterns}')

    def __post_init__(self):
        self._check_consistency(self.short_title_patterns, self.other_patterns)
        self.short_title_compiled = '|'.join([re.escape(pat) for pat in self.short_title_patterns])
        print(self.short_title_compiled)
        self.other_patterns_compiled = '|'.join([re.escape(pat) for pat in self.other_patterns])
        print(self.other_patterns_compiled)

    @staticmethod
    def from_raw_patterns(
        topic: TopicName, compatible_topics: List[TopicName], short_title_patterns: List[str], other_patterns: List[str]
    ) -> 'Topic':
        return Topic(topic, compatible_topics, _clean_patterns(short_title_patterns), _clean_patterns(other_patterns))


@dataclass
class TopicOntology:
    topics: Dict[TopicName, Topic]
    pattern_to_topic: Dict[str, TopicName] = field(init=False)
    title_compiled_pattern: re.Pattern = field(init=False)
    general_compiled_pattern: re.Pattern = field(init=False)

    def __post_init__(self):
        self._check_consistency(self.topics.values())
        self.pattern_to_topic = {
            pattern: topic
            for topic, desc in self.topics.items()
            for pattern in desc.other_patterns + desc.short_title_patterns
        }
        if '' in self.pattern_to_topic:
            raise ValueError('Cannot have void pattern!')
        self.general_compiled_pattern = re.compile(
            '|'.join([topic.other_patterns_compiled for topic in self.topics.values() if topic.other_patterns_compiled])
        )
        self.title_compiled_pattern = re.compile(
            '|'.join(
                [
                    pattern
                    for topic in self.topics.values()
                    for pattern in [topic.short_title_compiled, topic.other_patterns_compiled]
                    if pattern
                ]
            )
        )

    @staticmethod
    def _check_consistency(topics: Iterable[Topic]) -> None:
        pattern_to_topic: Dict[str, TopicName] = {}
        errors: List[Tuple[str, TopicName, TopicName]] = []
        for topic in topics:
            for pattern in topic.short_title_patterns + topic.other_patterns:
                if pattern in pattern_to_topic:
                    errors.append((pattern, topic.topic_name, pattern_to_topic[pattern]))
        if errors:
            raise ValueError(f'Following patterns are repeated in distinct topics: {errors}')

    def parse(self, text: str, short_title: bool = False) -> Set[TopicName]:
        return parse(self, text, short_title)


def parse(ontology: TopicOntology, text: str, short_title: bool = False) -> Set[TopicName]:
    normalized_text = normalize(text)
    pattern = ontology.title_compiled_pattern if short_title else ontology.general_compiled_pattern
    matches = re.finditer(pattern, normalized_text)
    topics: Set[TopicName] = set()
    for match in matches:
        start, end = match.span()
        topics.add(ontology.pattern_to_topic[normalized_text[start:end]])
    return topics


def test_parse():
    topic = Topic.from_raw_patterns(TopicName.EAU, [], ["Eau"], ["Collecte et rejet des effluents"])
    ontology = TopicOntology({TopicName.EAU: topic})
    assert parse(ontology, 'il y a de l\'eau') == set()
    assert parse(ontology, 'il y a de l\'eau', True) == {TopicName.EAU}
    assert parse(ontology, 'il y a de l\'eau dans la collecte et rejet des effluents.') == {TopicName.EAU}


test_parse()

TOPIC_ONTOLOGY = TopicOntology(
    {
        TopicName.EAU: Topic.from_raw_patterns(
            TopicName.EAU,
            [TopicName.EPANDAGE],
            ["Eau"],
            [
                "Collecte et rejet des effluents",
                "Collecte des effluents",
                "Réseau de collecte",
                "lixiviats",
                "eaux de ruissellement",
                'Traitement des effluents',
                "eaux résiduaires",
                "effluents d'élevage",
                "stockage des effluents",
                'RESSOURCE EN EAU',
                "Emissions dans l'eau",
                "surveillance des eaux souterraines",
                "bassin de stockage des eaux",
                "eau de ruissellement",
                "CONSOMMATION D'EAU",
                "traitement des eaux",
                "eaux de ressuyage",
                "POLLUTION DES EAUX",
                "EMISSIONS DANS L'EAU",
                'MILIEUX AQUATIQUES',
            ],
        ),
        TopicName.EPANDAGE: Topic.from_raw_patterns(
            TopicName.EPANDAGE, [TopicName.EAU, TopicName.DECHETS], ["Epandage"], ["PLAN D'ÉPANDAGE"]
        ),
        TopicName.DECHETS: Topic.from_raw_patterns(
            TopicName.DECHETS,
            [TopicName.EPANDAGE],
            ["dechets", "dechet", 'brulage', 'Recyclage'],
            [
                "entreposage de déchets",
                'gestion des déchets',
                'Registre de sortie',
                "Déchets industriels spéciaux",
                "ADMISSION DES DECHETS",
                'Déchets entrants',
                'Registre des déchets',
                'Récupération recyclage',
                'Déchets non dangereux',
                'Déchets banals',
            ],
        ),
        TopicName.RISQUES: Topic.from_raw_patterns(
            TopicName.RISQUES,
            [],
            ["Risques", 'Consignes de sécurité', 'PRÉVENTION DES RISQUES', 'foudre', 'Protection individuelle'],
            ["RISQUES D'INCENDIE", 'permis de feu', 'Moyens de lutte contre l\'incendie'],
        ),
        TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT: Topic.from_raw_patterns(
            TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT,
            [],
            [
                'Implantation',
                'Aménagement',
                'Accessibilité',
                'DISPOSITIONS CONSTRUCTIVES',
                'Toitures',
                'Résistance au feu',
            ],
            ['Comportement au feu des bâtiments', 'Toitures et couvertures de toiture'],
        ),
        TopicName.DISPOSITIONS_GENERALES: Topic.from_raw_patterns(
            TopicName.DISPOSITIONS_GENERALES,
            [TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT],
            [
                'Dispositions générales',
                'Surveillance de l\'installation',
                'Surveillance de l\'exploitation',
                'Changement d\'exploitant',
                'ORGANISATION DE LA SÉCURITÉ',
                'fin d\'exploitation',
                'remise en état',
                "Conditions d'exploitation",
            ],
            [],
        ),
        TopicName.EXECUTION: Topic.from_raw_patterns(
            TopicName.EXECUTION,
            [],
            [
                'Exécution',
                'Entrée en vigueur',
                'conditions d\'application',
                'définitions',
                'DISPOSITIONS APPLICABLES',
                'champ d\'application',
            ],
            [],
        ),
        TopicName.BRUIT_VIBRATIONS: Topic.from_raw_patterns(
            TopicName.BRUIT_VIBRATIONS,
            [],
            [
                'Bruit et vibrations',
                'Mesure de bruit',
                'VIBRATIONS',
                'Valeurs limites de bruit',
                'NUISANCES ACOUSTIQUES',
                'émissions sonores',
                'Bruit ambiant',
                'niveaux de bruit admissibles',
            ],
            [],
        ),
        TopicName.AIR_ODEURS: Topic.from_raw_patterns(
            TopicName.AIR_ODEURS,
            [],
            ['Emissions dans l\'air', 'Odeurs', 'Air', 'Pollution de l\'air', 'Chlorure d\'hydrogène'],
            [],
        ),
        TopicName.EMISSIONS: Topic.from_raw_patterns(
            TopicName.EMISSIONS, [], ['Surveillance des émissions', 'émissions polluantes'], []
        ),
        TopicName.ACCIDENTS_POLLUTIONS: Topic.from_raw_patterns(
            TopicName.ACCIDENTS_POLLUTIONS,
            [],
            ['Prévention des accidents et des pollutions', 'pollutions accidentelles'],
            [],
        ),
    }
)
