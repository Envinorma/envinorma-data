from typing import Dict, List, Optional, Set, Union

from envinorma.am_enriching import extract_topics
from envinorma.data import ArreteMinisteriel, StructuredText
from envinorma.topics.patterns import TopicName
from envinorma.topics.topics import TOPIC_ONTOLOGY
from .scrap_scructure_and_enrich_all_am import handle_all_am


def extract_all_am_topics(am: ArreteMinisteriel) -> List[Set[TopicName]]:
    return [extract_topics(section, [], TOPIC_ONTOLOGY) for section in am.sections]


def extract_paragraph_topics(arretes: List[ArreteMinisteriel]) -> List[Set[TopicName]]:
    return [topics for am in arretes for topics in extract_all_am_topics(am)]


# Occurrences of NB topics per paragraph
{
    1: 504,
    0: 358,
    2: 156,
    3: 140,
    4: 82,
    6: 49,
    5: 48,
    7: 20,
    8: 11,
    13: 10,
    12: 8,
    9: 8,
    11: 7,
    19: 5,
    18: 4,
    22: 3,
    26: 1,
    25: 4,
    24: 2,
    16: 4,
    15: 6,
    10: 8,
    32: 7,
    14: 7,
    20: 2,
    17: 1,
    31: 4,
    29: 4,
    36: 5,
    35: 5,
    33: 5,
    38: 2,
    30: 3,
    23: 2,
    34: 5,
    27: 2,
    37: 2,
    28: 1,
    21: 1,
}

# Occurrences
[
    ('PREFET', 413),
    ('EAU', 383),
    ('CONDITIONS_APPLICATION', 329),
    ('VLE', 230),
    ('DECHETS', 198),
    ('DISPOSITIONS_GENERALES', 167),
    ('INSTALLATIONS_ELECTRIQUES', 163),
    ('DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT', 163),
    ('AIR_ODEURS', 152),
    ('BRUIT_VIBRATIONS', 149),
    ('EXPLOITATION', 137),
    ('RISQUES', 133),
    ('DEFINITIONS', 118),
    ('SURVEILLANCE_EXPLOITATION', 106),
    ('EXECUTION', 104),
    ('EPANDAGE', 98),
    ('RETENTION', 95),
    ('ACCIDENTS_POLLUTIONS', 94),
    ('INCENDIE', 92),
    ('EMISSIONS_ATMOSPHERE', 92),
    ('DOSSIER', 90),
    ('SURVEILLANCE', 87),
    ('EMISSIONS', 81),
    ('CONSIGNES', 79),
    ('PROPRETE', 77),
    ('REGISTRE', 76),
    ('FIN_EXPLOITATION', 72),
    ('FEU', 66),
    ('VENTILATION', 62),
    ('BRULAGE', 62),
    ('MODIFICATIONS', 58),
    ('RECYCLAGE', 56),
    ('CHANGEMENT_EXPLOITANT', 52),
    ('EFFLUENTS', 52),
    ('POUSSIERES', 48),
    ('RISQUE_INDIVIDUEL', 46),
    ('TOITURE', 44),
    ('CONSOMMATION_D_EAU', 42),
    ('CONDITIONS_REJET', 42),
    ('INFO_REDACTION', 41),
    ('JUSTIFICATIONS', 37),
    ('MILIEU_AQUATIQUE', 30),
    ('HAUTEUR_CHEMINEE', 30),
    ('ABROGATION_AM_PASSE', 29),
    ('DECHETS_NON_DANGEREUX', 28),
    ('COV', 24),
    ('ENTREPOSAGE', 17),
    ('RADIOACTIVITES', 15),
    ('METHODOLOGIE', 15),
    ('DECLARATION_DES_EMISSIONS', 15),
    ('CONFINEMENT', 14),
    ('DECHETS_BANALS', 14),
    ('ELECTRICITE_STATIQUE', 13),
    ('FOUDRE', 12),
    ('MESURE_BRUIT', 12),
    ('SECURITE', 11),
    ('VAPEURS', 10),
    ('RESERVES_DE_PRODUIT', 10),
    ('DECHETS_SPECIAUX', 10),
    ('ETANCHEITE', 8),
    ('RECENSEMENT', 6),
    ('FARINES_VIANDE_ET_OS', 5),
    ('COMBUSTIBLES', 5),
    ('BIOGAZ', 4),
    ('ENTREE_VIGUEUR', 4),
    ('ANNEXE_BO', 3),
    ('BILAN_ENVIRONNEMENT', 2),
    ('NORME_TRANSFORMATION', 2),
    ('LEGIONELLES', 2),
    ('REJETS_CHLORE', 1),
    ('GESTION_QUALITE', 1),
    ('REJETS_ACCIDENTELS', 1),
    ('BIOMASSE', 1),
]

_AMOrText = Union[ArreteMinisteriel, StructuredText]


def extract_all_no_topic_paragraphs(text: _AMOrText) -> List[StructuredText]:
    if text.sections:
        return [pg for section in text.sections for pg in extract_all_no_topic_paragraphs(section)]
    if isinstance(text, StructuredText):
        topic = text.annotations.topic if text.annotations else None
        if not topic and not text.sections:
            return [text]
    return []


def extract_no_topic_paragraphs(arretes: List[ArreteMinisteriel]) -> List[StructuredText]:
    return [text for arrete in arretes for text in extract_all_no_topic_paragraphs(arrete)]


def extract_all_am_main_topics(text: _AMOrText) -> List[Optional[TopicName]]:
    if text.sections:
        return [topic for section in text.sections for topic in extract_all_am_main_topics(section)]
    if isinstance(text, StructuredText):
        return [text.annotations.topic if text.annotations else None]
    return []


def extract_paragraph_main_topics(arretes: List[ArreteMinisteriel]) -> List[Optional[TopicName]]:
    return [topic for arrete in arretes for topic in extract_all_am_main_topics(arrete)]


# COUNTER:
{
    'DISPOSITIONS_GENERALES': 4916,
    'ACCIDENTS_POLLUTIONS': 1344,
    'NO TOPIC': 1002,
    'EAU': 893,
    'AIR_ODEURS': 860,
    'BRUIT_VIBRATIONS': 658,
    'DECHETS': 642,
    'RISQUES': 342,
    'EPANDAGE': 150,
    'EMISSIONS': 117,
    'INCENDIE': 101,
    'VAPEURS': 82,
    'BRULAGE': 63,
    'EMISSIONS_ATMOSPHERE': 50,
    'EFFLUENTS': 41,
    'INSTALLATIONS_ELECTRIQUES': 38,
    'FARINES_VIANDE_ET_OS': 20,
    'COMBUSTIBLES': 13,
    'BIOGAZ': 10,
    'RADIOACTIVITES': 6,
    'ELECTRICITE_STATIQUE': 4,
    'BIOMASSE': 4,
    'POUSSIERES': 1,
    'FOUDRE': 1,
    'COV': 1,
}


def count_nb_arrete_per_rubrique() -> Dict[str, int]:
    pass


def nb_cooccurrences_between_active_rubriques() -> Dict[str, int]:
    pass


def nb_available_documents_per_installation() -> Dict[int, int]:
    pass


def nb_available_documents_per_region() -> Dict[str, int]:
    pass


def nb_installations_per_region() -> Dict[str, int]:
    pass


def count_nb_active_classement() -> Dict[str, int]:
    pass


def count_nb_sections(section: _AMOrText) -> int:
    return sum([count_nb_sections(sub) for sub in section.sections]) + len(section.sections)


def load_all_am() -> Dict[str, ArreteMinisteriel]:
    _, _, cid_to_am, _ = handle_all_am(dump_am=False, with_manual_enrichments=False)
    return cid_to_am


# 219 AM
# 14876 sections
