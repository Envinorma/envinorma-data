import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple

from unidecode import unidecode


class TopicName(Enum):
    UNNAMED = 'UNNAMED'
    EPANDAGE = 'EPANDAGE'
    EAU = 'EAU'
    DECHETS = 'DECHETS'
    EXECUTION = 'EXECUTION'
    RISQUES = 'RISQUES'
    IMPLANTATION_AMENAGEMENT = 'IMPLANTATION_AMENAGEMENT'
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
    METHODOLOGIE = 'METHODOLOGIE'
    MILIEU_AQUATIQUE = 'MILIEU_AQUATIQUE'
    MODIFICATIONS = 'MODIFICATIONS'
    DECHETS_NON_DANGEREUX = 'DECHETS_NON_DANGEREUX'
    NORME_TRANSFORMATION = 'NORME_TRANSFORMATION'
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


def merge_patterns(patterns: List[str]) -> str:
    return '|'.join([fr'\b({re.escape(pat)})\b' for pat in sorted(patterns)[::-1]])


@dataclass
class Topic:
    topic_name: TopicName
    metatopic: TopicName
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
        self.escaped_pattern = merge_patterns(self.other_patterns)
        self.escaped_short_title_pattern = merge_patterns(self.short_title_patterns + self.other_patterns)

    @staticmethod
    def from_raw_patterns(
        topic: TopicName,
        metatopic: TopicName,
        compatible_topics: List[TopicName],
        short_title_patterns: List[str],
        other_patterns: List[str],
    ) -> 'Topic':
        return Topic(
            topic, metatopic, compatible_topics, _clean_patterns(short_title_patterns), _clean_patterns(other_patterns)
        )

    @staticmethod
    def monotopic(
        patterns: List[str],
    ) -> 'Topic':
        return Topic(TopicName.UNNAMED, TopicName.UNNAMED, [], [], _clean_patterns(patterns))


ALL_TOPICS = [
    Topic.from_raw_patterns(
        TopicName.EAU,
        TopicName.EAU,
        [TopicName.EPANDAGE],
        ['Eau'],
        [
            'Collecte et rejet des effluents',
            'Collecte des effluents',
            'Réseau de collecte',
            'lixiviats',
            'eaux de ruissellement',
            'eaux résiduaires',
            "effluents d'élevage",
            'stockage des effluents',
            'RESSOURCE EN EAU',
            "Emissions dans l'eau",
            'surveillance des eaux souterraines',
            'bassin de stockage des eaux',
            'eau de ruissellement',
            'traitement des eaux',
            'eaux de ressuyage',
            'POLLUTION DES EAUX',
            "EMISSIONS DANS L'EAU",
        ],
    ),
    Topic.from_raw_patterns(
        TopicName.EPANDAGE,
        TopicName.EPANDAGE,
        [TopicName.EAU, TopicName.DECHETS],
        ['Epandage'],
        ["PLAN D'ÉPANDAGE", 'valorisées par épandage'],
    ),
    Topic.from_raw_patterns(
        TopicName.DECHETS,
        TopicName.DECHETS,
        [TopicName.EPANDAGE],
        ['dechets', 'dechet'],
        [
            'entreposage de déchets',
            'Stockage des déchets',
            'gestion des déchets',
            'Registre de sortie',
            'ADMISSION DES DECHETS',
            'Déchets entrants',
            'Registre des déchets',
        ],
    ),
    Topic.from_raw_patterns(
        TopicName.RISQUES,
        TopicName.RISQUES,
        [],
        ['Risques', 'Consignes de sécurité', 'PRÉVENTION DES RISQUES'],
        ['permis de feu', 'RISQUES INDUSTRIELS'],
    ),
    Topic.from_raw_patterns(
        TopicName.IMPLANTATION_AMENAGEMENT,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        [
            'Implantation',
            'Aménagement',
            'Accessibilité',
            'DISPOSITIONS CONSTRUCTIVES',
            'Résistance au feu',
            "CONSTRUCTION DE L'INSTALLATION",
        ],
        [],
    ),
    Topic.from_raw_patterns(
        TopicName.DISPOSITIONS_GENERALES,
        TopicName.DISPOSITIONS_GENERALES,
        [TopicName.IMPLANTATION_AMENAGEMENT],
        ['Dispositions générales', 'remise en état', "Conditions d'exploitation"],
        [],
    ),
    Topic.from_raw_patterns(
        TopicName.EXECUTION,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        ['Exécution', 'DISPOSITIONS APPLICABLES'],
        ['directeur général de la prévention des risques'],
    ),
    Topic.from_raw_patterns(
        TopicName.BRUIT_VIBRATIONS,
        TopicName.BRUIT_VIBRATIONS,
        [],
        [
            'Bruit et vibrations',
            'Mesure de bruit',
            'bruit',
            'VIBRATIONS',
            'NUISANCES ACOUSTIQUES',
            'émissions sonores',
            'Bruit ambiant',
            'niveaux de bruit admissibles',
        ],
        [],
    ),
    Topic.from_raw_patterns(
        TopicName.AIR_ODEURS,
        TopicName.AIR_ODEURS,
        [],
        ["Emissions dans l'air", 'Odeurs', 'Air', "Pollution de l'air", "Chlorure d'hydrogène"],
        [],
    ),
    Topic.from_raw_patterns(
        TopicName.EMISSIONS,
        TopicName.EMISSIONS,
        [TopicName.EMISSIONS_AIR, TopicName.EAU, TopicName.EMISSIONS_ATMOSPHERE],
        ['Surveillance des émissions', 'émissions polluantes', 'Emissions'],
        [],
    ),
    Topic.from_raw_patterns(
        TopicName.ACCIDENTS_POLLUTIONS,
        TopicName.ACCIDENTS_POLLUTIONS,
        [],
        [
            'Prévention des accidents et des pollutions',
            'pollutions accidentelles',
            'PRÉVENTION DES POLLUTIONS',
            'PRÉVENTION DES ACCIDENTS',
        ],
        ['Prévention des accidents et des pollutions accidentelles'],
    ),
    Topic.from_raw_patterns(
        TopicName.METHODOLOGIE,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        ['methodologie', 'Méthodes de référence', 'règles de calcul'],
        [],
    ),
    Topic.from_raw_patterns(
        TopicName.SURVEILLANCE_EXPLOITATION,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        ['surveillance de l exploitation', "Surveillance de l'installation"],
        ['personnes étrangères à l établissement', 'gardiennage ou télésurveillance'],
    ),
    Topic.from_raw_patterns(TopicName.CONSIGNES, TopicName.DISPOSITIONS_GENERALES, [], ['consignes'], []),
    Topic.from_raw_patterns(
        TopicName.MILIEU_AQUATIQUE, TopicName.EAU, [], ['milieu aquatique'], ['MILIEUX AQUATIQUES']
    ),
    Topic.from_raw_patterns(
        TopicName.INFO_REDACTION,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        [],
        ['la numérotation a été conservée pour permettre une homogénéité'],
    ),
    Topic.from_raw_patterns(TopicName.CONDITIONS_REJET, TopicName.EAU, [], ['conditions de rejet'], []),
    Topic.from_raw_patterns(TopicName.FOUDRE, TopicName.FOUDRE, [], ['foudre'], []),
    Topic.from_raw_patterns(TopicName.RECENSEMENT, TopicName.DISPOSITIONS_GENERALES, [], ['recensement'], []),
    Topic.from_raw_patterns(TopicName.POUSSIERES, TopicName.POUSSIERES, [], ['poussieres'], []),
    Topic.from_raw_patterns(TopicName.COV, TopicName.COV, [], ['cov', 'composés organiques volatils'], []),
    Topic.from_raw_patterns(TopicName.FEU, TopicName.INCENDIE, [], ['feu'], []),
    Topic.from_raw_patterns(
        TopicName.RADIOACTIVITES, TopicName.RADIOACTIVITES, [], ['radioactivites', 'radioactivite'], ['RADIOACTIFS']
    ),
    Topic.from_raw_patterns(
        TopicName.TOITURE,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        ['toiture', 'toitures'],
        ['Toitures et couvertures de toiture'],
    ),
    Topic.from_raw_patterns(
        TopicName.CONDITIONS_APPLICATION,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        [
            "conditions d'application",
            "champ d'application",
            'calendrier d application',
            'Modalités d application',
            'DISPOSITIONS APPLICABLES AUX INSTALLATIONS EXISTANTES',
        ],
        ['applicables aux installations'],
    ),
    Topic.from_raw_patterns(TopicName.BIOMASSE, TopicName.BIOMASSE, [], ['biomasse'], []),
    Topic.from_raw_patterns(
        TopicName.JUSTIFICATIONS,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        [],
        ['justifie en tant que de besoin toutes les dispositions prises'],
    ),
    Topic.from_raw_patterns(
        TopicName.FARINES_VIANDE_ET_OS, TopicName.FARINES_VIANDE_ET_OS, [], [], ['farines de viande']
    ),
    Topic.from_raw_patterns(TopicName.EFFLUENTS, TopicName.EFFLUENTS, [], ['effluents'], []),
    Topic.from_raw_patterns(
        TopicName.GESTION_QUALITE, TopicName.DISPOSITIONS_GENERALES, [], ['sgq', 'gestion de la qualité'], []
    ),
    Topic.from_raw_patterns(
        TopicName.ETANCHEITE, TopicName.DISPOSITIONS_GENERALES, [], ['etancheite'], ['relatives à l étanchéité']
    ),
    Topic.from_raw_patterns(TopicName.EMISSIONS_AIR, TopicName.AIR_ODEURS, [], ['emissions_air'], []),
    Topic.from_raw_patterns(
        TopicName.DECHETS_NON_DANGEREUX, TopicName.DECHETS, [], ['dechets non dangereux', 'dechet non dangereux'], []
    ),
    Topic.from_raw_patterns(
        TopicName.REGISTRE,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        ['registre'],
        ['tient à jour un registre', 'un registre des admissions'],
    ),
    Topic.from_raw_patterns(TopicName.DECHETS_BANALS, TopicName.DECHETS, [], ['dechets banals'], []),
    Topic.from_raw_patterns(
        TopicName.INCENDIE, TopicName.INCENDIE, [], ['incendie'], ["opérations d'extinction", "bouches d'incendie"]
    ),
    Topic.from_raw_patterns(
        TopicName.SECURITE,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        ['organisation de la sécurité', 'Dispositions de sécurité'],
        [],
    ),
    Topic.from_raw_patterns(TopicName.BRULAGE, TopicName.BRULAGE, [], ['brulage'], []),
    Topic.from_raw_patterns(
        TopicName.DECLARATION_DES_EMISSIONS, TopicName.EMISSIONS, [], ['Déclaration annuelle des émissions'], []
    ),
    Topic.from_raw_patterns(
        TopicName.REJETS_CHLORE,
        TopicName.ACCIDENTS_POLLUTIONS,
        [],
        ['rejets de chlore'],
        ['neutralisation des rejets de chlore'],
    ),
    Topic.from_raw_patterns(
        TopicName.ANNEXE_BO,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        [],
        ["annexe est publiée au Bulletin officiel du ministère de l'écologie"],
    ),
    Topic.from_raw_patterns(
        TopicName.DEFINITIONS,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        ['definitions', 'définition'],
        ['Au sens du présent arrêté, on entend par'],
    ),
    Topic.from_raw_patterns(
        TopicName.CHANGEMENT_EXPLOITANT, TopicName.DISPOSITIONS_GENERALES, [], ["changement d'exploitant"], []
    ),
    Topic.from_raw_patterns(
        TopicName.RESERVES_DE_PRODUIT,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        [],
        ['exploitant dispose de réserves suffisantes de produits'],
    ),
    Topic.from_raw_patterns(
        TopicName.ELECTRICITE_STATIQUE, TopicName.ELECTRICITE_STATIQUE, [], [], ['electricite statique']
    ),
    Topic.from_raw_patterns(TopicName.BIOGAZ, TopicName.BIOGAZ, [], ['biogaz'], []),
    Topic.from_raw_patterns(TopicName.CONFINEMENT, TopicName.DISPOSITIONS_GENERALES, [], ['confinement'], []),
    Topic.from_raw_patterns(
        TopicName.MESURE_BRUIT,
        TopicName.BRUIT_VIBRATIONS,
        [],
        ['MÉTHODE DE MESURE DES ÉMISSIONS SONORES', 'RÈGLES TECHNIQUES APPLICABLES EN MATIÈRE DE VIBRATIONS'],
        [],
    ),
    Topic.from_raw_patterns(
        TopicName.VAPEURS, TopicName.VAPEURS, [], ['vapeurs'], ['COLLECTE DES VAPEURS', 'retenue des vapeurs']
    ),
    Topic.from_raw_patterns(TopicName.RISQUE_INDIVIDUEL, TopicName.RISQUES, [], ['Protection individuelle'], []),
    Topic.from_raw_patterns(TopicName.LEGIONELLES, TopicName.LEGIONELLES, [], ['legionelles'], []),
    Topic.from_raw_patterns(TopicName.EXPLOITATION, TopicName.DISPOSITIONS_GENERALES, [], ['exploitation'], []),
    Topic.from_raw_patterns(
        TopicName.VENTILATION, TopicName.DISPOSITIONS_GENERALES, [], ['ventilation', 'ventilations'], []
    ),
    Topic.from_raw_patterns(
        TopicName.FIN_EXPLOITATION,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        ["fin d'exploitation"],
        ['en fin d exploitation'],
    ),
    Topic.from_raw_patterns(TopicName.SURVEILLANCE, TopicName.DISPOSITIONS_GENERALES, [], ['surveillance'], []),
    Topic.from_raw_patterns(
        TopicName.CONSOMMATION_D_EAU, TopicName.EAU, [], ["consommation d'eau"], ["limiter la quantité d'eau"]
    ),
    Topic.from_raw_patterns(
        TopicName.NORME_TRANSFORMATION, TopicName.DISPOSITIONS_GENERALES, [], ['NORMES DE TRANSFORMATION'], []
    ),
    Topic.from_raw_patterns(TopicName.PROPRETE, TopicName.DISPOSITIONS_GENERALES, [], ['proprete'], []),
    Topic.from_raw_patterns(TopicName.PREFET, TopicName.DISPOSITIONS_GENERALES, [], [], ['prefet']),
    Topic.from_raw_patterns(
        TopicName.INSTALLATIONS_ELECTRIQUES, TopicName.INSTALLATIONS_ELECTRIQUES, [], [], ['installations electriques']
    ),
    Topic.from_raw_patterns(
        TopicName.HAUTEUR_CHEMINEE,
        TopicName.DISPOSITIONS_GENERALES,
        [],
        [],
        ['hauteur des cheminees', 'hauteur de cheminee', 'HAUTEURS DE CHEMINÉE'],
    ),
    Topic.from_raw_patterns(
        TopicName.ABROGATION_AM_PASSE, TopicName.DISPOSITIONS_GENERALES, [], [], ['A abrogé les dispositions']
    ),
    Topic.from_raw_patterns(TopicName.MODIFICATIONS, TopicName.DISPOSITIONS_GENERALES, [], ['modifications'], []),
    Topic.from_raw_patterns(
        TopicName.RETENTION, TopicName.DISPOSITIONS_GENERALES, [], ['retention'], ['rétention déportée']
    ),
    Topic.from_raw_patterns(
        TopicName.BILAN_ENVIRONNEMENT, TopicName.DISPOSITIONS_GENERALES, [], ['Bilan environnement'], []
    ),
    Topic.from_raw_patterns(TopicName.ENTREPOSAGE, TopicName.DISPOSITIONS_GENERALES, [], ['entreposage'], []),
    Topic.from_raw_patterns(TopicName.ENTREE_VIGUEUR, TopicName.DISPOSITIONS_GENERALES, [], ['Entrée en vigueur'], []),
    Topic.from_raw_patterns(
        TopicName.VLE, TopicName.DISPOSITIONS_GENERALES, [], ['valeurs limites'], ['valeurs limites d emission']
    ),
    Topic.from_raw_patterns(
        TopicName.EMISSIONS_ATMOSPHERE,
        TopicName.EMISSIONS_ATMOSPHERE,
        [],
        [],
        ['POLLUTION ATMOSPHÉRIQUE', 'REJETS À L ATMOSPHÈRE'],
    ),
    Topic.from_raw_patterns(TopicName.RECYCLAGE, TopicName.DECHETS, [], ['recyclage'], []),
    Topic.from_raw_patterns(
        TopicName.REJETS_ACCIDENTELS, TopicName.ACCIDENTS_POLLUTIONS, [], ['Rejets accidentels'], []
    ),
    Topic.from_raw_patterns(TopicName.DECHETS_SPECIAUX, TopicName.DECHETS, [], ['Déchets industriels spéciaux'], []),
    Topic.from_raw_patterns(TopicName.COMBUSTIBLES, TopicName.COMBUSTIBLES, [], ['combustibles'], []),
    Topic.from_raw_patterns(TopicName.DOSSIER, TopicName.DISPOSITIONS_GENERALES, [], ['dossier'], []),
]
