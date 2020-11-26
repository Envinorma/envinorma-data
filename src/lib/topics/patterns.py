import re
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union
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
    ABROGATION_AM_PASSE = 'ABROGATION_AM_PASSE'
    ANNEXE_BO = 'ANNEXE_BO'
    DECHETS_BANALS = 'DECHETS_BANALS'
    BILAN_ENVIRONNEMENT = 'BILAN_ENVIRONNEMENT'
    BIOGAZ = 'BIOGAZ'
    BIOMASSE = 'BIOMASSE'
    BRULAGE = 'BRULAGE'
    CALENDRIER_APPLICATION = 'CALENDRIER_APPLICATION'
    CHANGEMENT_EXPLOITANT = 'CHANGEMENT_EXPLOITANT'
    COMBUSTIBLES = 'COMBUSTIBLES'
    CONDITIONS_APPLICATION = 'CONDITIONS_APPLICATION'
    CONDITIONS_REJET = 'CONDITIONS_REJET'
    CONFINEMENT = 'CONFINEMENT'
    CONSIGNES = 'CONSIGNES'
    CONSOMMATION_D_EAU = 'CONSOMMATION_D_EAU'
    COV = 'COV'
    DECLARATION_DES_EMISSIONS = 'DECLARATION_DES_EMISSIONS'
    DEFINITIONS = 'DEFINITIONS'
    DOSSIER = 'DOSSIER'
    EFFLUENTS = 'EFFLUENTS'
    ELECTRICITE_STATIQUE = 'ELECTRICITE_STATIQUE'
    EMISSIONS_AIR = 'EMISSIONS_AIR'
    EMISSIONS_ATMOSPHERE = 'EMISSIONS_ATMOSPHERE'
    ENTREE_VIGUEUR = 'ENTREE_VIGUEUR'
    ENTREPOSAGE = 'ENTREPOSAGE'
    ETANCHEITE = 'ETANCHEITE'
    EXPLOITATION = 'EXPLOITATION'
    FARINES_VIANDE_ET_OS = 'FARINES_VIANDE_ET_OS'
    FEU = 'FEU'
    FIN_EXPLOITATION = 'FIN_EXPLOITATION'
    FOUDRE = 'FOUDRE'
    GESTION_QUALITE = 'GESTION_QUALITE'
    HAUTEUR_CHEMINEE = 'HAUTEUR_CHEMINEE'
    INCENDIE = 'INCENDIE'
    INFO_REDACTION = 'INFO_REDACTION'
    INSTALLATIONS_ELECTRIQUES = 'INSTALLATIONS_ELECTRIQUES'
    JUSTIFICATIONS = 'JUSTIFICATIONS'
    LEGIONELLES = 'LEGIONELLES'
    MESURE_BRUIT = 'MESURE_BRUIT'
    METHODO = 'METHODO'
    METHODOLOGIE = 'METHODOLOGIE'
    MILIEU_AQUATIQUE = 'MILIEU_AQUATIQUE'
    MODIFICATIONS = 'MODIFICATIONS'
    DECHETS_NON_DANGEREUX = 'DECHETS_NON_DANGEREUX'
    NORME_TRANSFORMATION = 'NORME_TRANSFORMATION'
    POLLUTIONS_ACCIDENTS = 'POLLUTIONS_ACCIDENTS'
    POUSSIERES = 'POUSSIERES'
    PREFET = 'PREFET'
    PROPRETE = 'PROPRETE'
    RADIOACTIVITES = 'RADIOACTIVITES'
    RECENSEMENT = 'RECENSEMENT'
    RECYCLAGE = 'RECYCLAGE'
    REGISTRE = 'REGISTRE'
    REJETS_ACCIDENTELS = 'REJETS_ACCIDENTELS'
    REJETS_CHLORE = 'REJETS_CHLORE'
    RESERVES_DE_PRODUIT = 'RESERVES_DE_PRODUIT'
    RETENTION = 'RETENTION'
    RISQUE_INDIVIDUEL = 'RISQUE_INDIVIDUEL'
    SECURITE = 'SECURITE'
    DECHETS_SPECIAUX = 'DECHETS_SPECIAUX'
    SURVEILLANCE = 'SURVEILLANCE'
    SURVEILLANCE_EXPLOITATION = 'SURVEILLANCE_EXPLOITATION'
    TOITURE = 'TOITURE'
    VAPEURS = 'VAPEURS'
    VENTILATION = 'VENTILATION'
    VLE = 'VLE'


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
    escaped_short_title_pattern: str = field(init=False)
    escaped_pattern: str = field(init=False)

    @staticmethod
    def _check_consistency(short_title_patterns: List[str], other_patterns: List[str]) -> None:
        common_patterns = set(short_title_patterns) & set(other_patterns)
        if common_patterns:
            raise ValueError(f'There are common patterns in short title patterns and other patterns: {common_patterns}')

    def __post_init__(self):
        self._check_consistency(self.short_title_patterns, self.other_patterns)
        self.escaped_pattern = '|'.join([re.escape(pat) for pat in self.other_patterns])
        escaped_title_patterns = [re.escape(pat) for pat in self.short_title_patterns]
        if self.escaped_pattern:
            escaped_title_patterns.append(self.escaped_pattern)
        self.escaped_short_title_pattern = '|'.join(escaped_title_patterns)

    @staticmethod
    def from_raw_patterns(
        topic: TopicName, compatible_topics: List[TopicName], short_title_patterns: List[str], other_patterns: List[str]
    ) -> 'Topic':
        return Topic(topic, compatible_topics, _clean_patterns(short_title_patterns), _clean_patterns(other_patterns))


@dataclass
class TopicOntology:
    topics: List[Topic]
    pattern_to_topic: Dict[str, TopicName] = field(init=False)
    title_compiled_pattern: re.Pattern = field(init=False)
    general_compiled_pattern: re.Pattern = field(init=False)
    topic_name_to_topic: Dict[TopicName, Topic] = field(init=False)

    def __post_init__(self):
        self._check_consistency(self.topics)
        self.pattern_to_topic = {
            pattern: desc.topic_name
            for desc in self.topics
            for pattern in desc.other_patterns + desc.short_title_patterns
        }
        self.topic_name_to_topic = {topic.topic_name: topic for topic in self.topics}
        if '' in self.pattern_to_topic:
            raise ValueError('Cannot have void pattern!')
        self.general_compiled_pattern = re.compile(
            '|'.join([topic.escaped_pattern for topic in self.topics if topic.escaped_pattern])
        )
        self.title_compiled_pattern = re.compile(
            '|'.join([topic.escaped_short_title_pattern for topic in self.topics if topic.escaped_short_title_pattern])
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

    def detect_matched_patterns(self, text: str, topic: Optional[TopicName], short_title: bool = False) -> Set[str]:
        return detect_matched_patterns(self, text, topic, short_title)


def _extract_substring(text: str, start: int, end: int) -> str:
    return text[start:end]


def detect_matched_patterns(
    ontology: TopicOntology, text: str, topic: Optional[TopicName], short_title: bool = False
) -> Set[str]:
    normalized_text = normalize(text)
    if topic:
        pattern = re.compile(
            ontology.topic_name_to_topic[topic].escaped_short_title_pattern
            if short_title
            else ontology.topic_name_to_topic[topic].escaped_pattern
        )
    else:
        pattern = ontology.title_compiled_pattern if short_title else ontology.general_compiled_pattern
    matches = re.finditer(pattern, normalized_text)
    return {_extract_substring(normalized_text, *match.span()) for match in matches}


def parse(ontology: TopicOntology, text: str, short_title: bool = False) -> Set[TopicName]:
    return {ontology.pattern_to_topic[match] for match in detect_matched_patterns(ontology, text, None, short_title)}


TOPIC_ONTOLOGY = TopicOntology(
    [
        Topic.from_raw_patterns(
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
        Topic.from_raw_patterns(
            TopicName.EPANDAGE, [TopicName.EAU, TopicName.DECHETS], ["Epandage"], ["PLAN D'ÉPANDAGE"]
        ),
        Topic.from_raw_patterns(
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
        Topic.from_raw_patterns(
            TopicName.RISQUES,
            [],
            ["Risques", 'Consignes de sécurité', 'PRÉVENTION DES RISQUES', 'foudre', 'Protection individuelle'],
            ["RISQUES D'INCENDIE", 'permis de feu', 'Moyens de lutte contre l\'incendie'],
        ),
        Topic.from_raw_patterns(
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
        Topic.from_raw_patterns(
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
        Topic.from_raw_patterns(
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
        Topic.from_raw_patterns(
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
        Topic.from_raw_patterns(
            TopicName.AIR_ODEURS,
            [],
            ['Emissions dans l\'air', 'Odeurs', 'Air', 'Pollution de l\'air', 'Chlorure d\'hydrogène'],
            [],
        ),
        Topic.from_raw_patterns(TopicName.EMISSIONS, [], ['Surveillance des émissions', 'émissions polluantes'], []),
        Topic.from_raw_patterns(
            TopicName.ACCIDENTS_POLLUTIONS,
            [],
            ['Prévention des accidents et des pollutions', 'pollutions accidentelles'],
            [],
        ),
        Topic.from_raw_patterns(TopicName.METHODOLOGIE, [], ['methodologie'], []),
        Topic.from_raw_patterns(TopicName.SURVEILLANCE_EXPLOITATION, [], ['surveillance de l exploitation'], []),
        Topic.from_raw_patterns(TopicName.CONSIGNES, [], ['consignes'], []),
        Topic.from_raw_patterns(TopicName.MILIEU_AQUATIQUE, [], ['milieu aquatique'], []),
        Topic.from_raw_patterns(
            TopicName.INFO_REDACTION, [], [], ['la numérotation a été conservée pour permettre une homogénéité']
        ),
        Topic.from_raw_patterns(TopicName.CONDITIONS_REJET, [], ['conditions de rejet'], []),
        Topic.from_raw_patterns(TopicName.FOUDRE, [], ['foudre'], []),
        Topic.from_raw_patterns(TopicName.RECENSEMENT, [], ['recensement'], []),
        Topic.from_raw_patterns(TopicName.POUSSIERES, [], ['poussieres'], []),
        Topic.from_raw_patterns(TopicName.COV, [], ['cov', 'composés organiques volatils'], []),
        Topic.from_raw_patterns(TopicName.FEU, [], ['feu'], []),
        Topic.from_raw_patterns(TopicName.RADIOACTIVITES, [], ['radioactivites', 'radioactivite'], []),
        Topic.from_raw_patterns(TopicName.TOITURE, [], ['toiture', 'toitures'], []),
        Topic.from_raw_patterns(
            TopicName.CONDITIONS_APPLICATION, [], ['conditions d\'application', 'champ d\'application'], []
        ),
        Topic.from_raw_patterns(TopicName.BIOMASSE, [], ['biomasse'], []),
        Topic.from_raw_patterns(
            TopicName.JUSTIFICATIONS, [], [], ['justifie en tant que de besoin toutes les dispositions prises']
        ),
        Topic.from_raw_patterns(TopicName.FARINES_VIANDE_ET_OS, [], ['farines de viande'], []),
        Topic.from_raw_patterns(TopicName.EFFLUENTS, [], ['effluents'], []),
        Topic.from_raw_patterns(TopicName.GESTION_QUALITE, [], ['sgq', 'gestion de la qualité'], []),
        Topic.from_raw_patterns(TopicName.ETANCHEITE, [], ['etancheite'], []),
        Topic.from_raw_patterns(TopicName.EMISSIONS_AIR, [], ['emissions_air'], []),
        Topic.from_raw_patterns(
            TopicName.DECHETS_NON_DANGEREUX, [], ['dechets non dangereux', 'dechet non dangereux'], []
        ),
        Topic.from_raw_patterns(TopicName.REGISTRE, [], ['registre'], []),
        Topic.from_raw_patterns(TopicName.DECHETS_BANALS, [], ['dechets banals'], []),
        Topic.from_raw_patterns(TopicName.INCENDIE, [], ['incendie'], []),
        Topic.from_raw_patterns(TopicName.SECURITE, [], ['organisation de la sécurité'], []),
        Topic.from_raw_patterns(TopicName.BRULAGE, [], ['brulage'], []),
        Topic.from_raw_patterns(TopicName.DECLARATION_DES_EMISSIONS, [], ['Déclaration annuelle des émissions'], []),
        Topic.from_raw_patterns(TopicName.REJETS_CHLORE, [], ['rejets de chlore'], []),
        Topic.from_raw_patterns(
            TopicName.ANNEXE_BO, [], [], ['annexe est publiée au Bulletin officiel du ministère de l\'écologie']
        ),
        Topic.from_raw_patterns(TopicName.DEFINITIONS, [], ['definitions'], []),
        Topic.from_raw_patterns(TopicName.CHANGEMENT_EXPLOITANT, [], ['changement d\'exploitant'], []),
        Topic.from_raw_patterns(
            TopicName.RESERVES_DE_PRODUIT, [], [], ['exploitant dispose de réserves suffisantes de produits']
        ),
        Topic.from_raw_patterns(TopicName.ELECTRICITE_STATIQUE, [], [], ['electricite statique']),
        Topic.from_raw_patterns(TopicName.BIOGAZ, [], ['biogaz'], []),
        Topic.from_raw_patterns(TopicName.CONFINEMENT, [], ['confinement'], []),
        Topic.from_raw_patterns(
            TopicName.MESURE_BRUIT,
            [],
            ['MÉTHODE DE MESURE DES ÉMISSIONS SONORES', 'RÈGLES TECHNIQUES APPLICABLES EN MATIÈRE DE VIBRATIONS'],
            [],
        ),
        Topic.from_raw_patterns(TopicName.VAPEURS, [], ['vapeurs'], []),
        Topic.from_raw_patterns(TopicName.POLLUTIONS_ACCIDENTS, [], ['accidents et des pollutions'], []),
        Topic.from_raw_patterns(TopicName.RISQUE_INDIVIDUEL, [], ['Protection individuelle'], []),
        Topic.from_raw_patterns(TopicName.LEGIONELLES, [], ['legionelles'], []),
        Topic.from_raw_patterns(TopicName.EXPLOITATION, [], ['exploitation'], []),
        Topic.from_raw_patterns(TopicName.VENTILATION, [], ['ventilation'], []),
        Topic.from_raw_patterns(TopicName.FIN_EXPLOITATION, [], ['fin d\'exploitation'], []),
        Topic.from_raw_patterns(TopicName.SURVEILLANCE, [], ['surveillance'], []),
        Topic.from_raw_patterns(TopicName.CONSOMMATION_D_EAU, [], ['consommation d\'eau'], []),
        Topic.from_raw_patterns(TopicName.NORME_TRANSFORMATION, [], ['NORMES DE TRANSFORMATION'], []),
        Topic.from_raw_patterns(TopicName.PROPRETE, [], ['proprete'], []),
        Topic.from_raw_patterns(TopicName.PREFET, [], [], ['prefet']),
        Topic.from_raw_patterns(TopicName.INSTALLATIONS_ELECTRIQUES, [], [], ['installations electriques']),
        Topic.from_raw_patterns(TopicName.CALENDRIER_APPLICATION, [], [], ['calendrier d\'application']),
        Topic.from_raw_patterns(TopicName.HAUTEUR_CHEMINEE, [], [], ['hauteur des cheminees', 'hauteur de cheminee']),
        Topic.from_raw_patterns(TopicName.METHODO, [], ['règles de calcul'], []),
        Topic.from_raw_patterns(TopicName.ABROGATION_AM_PASSE, [], [], ['A abrogé les dispositions']),
        Topic.from_raw_patterns(TopicName.MODIFICATIONS, [], ['modifications'], []),
        Topic.from_raw_patterns(TopicName.RETENTION, [], ['retention'], []),
        Topic.from_raw_patterns(TopicName.BILAN_ENVIRONNEMENT, [], ['Bilan environnement'], []),
        Topic.from_raw_patterns(TopicName.ENTREPOSAGE, [], ['entreposage'], []),
        Topic.from_raw_patterns(TopicName.ENTREE_VIGUEUR, [], ['Entrée en vigueur'], []),
        Topic.from_raw_patterns(TopicName.VLE, [], ['valeurs limites'], ['valeurs limites d emission']),
        Topic.from_raw_patterns(TopicName.EMISSIONS_ATMOSPHERE, [], [], ['POLLUTION ATMOSPHÉRIQUE']),
        Topic.from_raw_patterns(TopicName.RECYCLAGE, [], ['recyclage'], []),
        Topic.from_raw_patterns(TopicName.REJETS_ACCIDENTELS, [], ['Rejets accidentels'], []),
        Topic.from_raw_patterns(TopicName.DECHETS_SPECIAUX, [], ['Déchets industriels spéciaux'], []),
        Topic.from_raw_patterns(TopicName.COMBUSTIBLES, [], ['combustibles'], []),
    ]
)
