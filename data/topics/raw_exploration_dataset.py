"""Dataset for topic model assessment."""
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

from envinorma.models.text_elements import EnrichedString
from envinorma.topics.patterns import TopicName

LABELS = {
    0: {TopicName.BRUIT_VIBRATIONS},
    1: {TopicName.EXECUTION},
    2: {TopicName.BRULAGE, TopicName.DECHETS},
    3: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.EAU},
    4: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    5: {TopicName.EXPLOITATION, TopicName.ACCIDENTS_POLLUTIONS, TopicName.SURVEILLANCE_EXPLOITATION},
    6: {TopicName.ANNEXE_BO},
    7: {TopicName.DISPOSITIONS_GENERALES, TopicName.RESERVES_DE_PRODUIT},
    8: {TopicName.DISPOSITIONS_GENERALES, TopicName.DOSSIER},
    9: {TopicName.CONSIGNES, TopicName.EXPLOITATION, TopicName.LEGIONELLES},
    10: {TopicName.RISQUES},
    11: {TopicName.RADIOACTIVITES},
    12: {TopicName.EMISSIONS},
    13: {TopicName.DECHETS},
    14: {TopicName.AIR_ODEURS},
    15: {TopicName.EXPLOITATION},
    16: {TopicName.ACCIDENTS_POLLUTIONS, TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    17: {TopicName.EMISSIONS_ATMOSPHERE, TopicName.VLE},
    18: {TopicName.EAU},
    19: {TopicName.DEFINITIONS},
    20: {TopicName.DECHETS},
    21: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.ACCIDENTS_POLLUTIONS},
    22: {TopicName.EMISSIONS},
    23: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.DISPOSITIONS_GENERALES, TopicName.PREFET},
    24: {TopicName.BRUIT_VIBRATIONS},
    25: {TopicName.EPANDAGE, TopicName.PREFET},
    26: {TopicName.INCENDIE, TopicName.PREFET, TopicName.RISQUES},
    27: {TopicName.EXPLOITATION, TopicName.SURVEILLANCE_EXPLOITATION},
    28: {TopicName.EAU},
    29: {TopicName.AIR_ODEURS},
    30: {TopicName.RISQUES},
    31: {TopicName.DECHETS},
    32: {TopicName.AIR_ODEURS, TopicName.EMISSIONS},
    33: {TopicName.RISQUES},
    34: {TopicName.RISQUES},
    35: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.INCENDIE},
    36: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    37: {TopicName.AIR_ODEURS},
    38: {TopicName.EAU},
    39: {TopicName.DECHETS},
    40: {TopicName.ACCIDENTS_POLLUTIONS},
    41: {TopicName.AIR_ODEURS},
    42: {TopicName.ACCIDENTS_POLLUTIONS, TopicName.EAU},
    43: {TopicName.EAU, TopicName.EMISSIONS},
    44: {TopicName.RISQUES},
    45: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.FOUDRE, TopicName.RISQUES},
    46: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    47: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    48: {TopicName.CONSOMMATION_D_EAU, TopicName.EAU},
    49: {TopicName.DISPOSITIONS_GENERALES, TopicName.POUSSIERES},
    50: {TopicName.VAPEURS},
    51: {TopicName.EAU},
    52: {TopicName.RISQUES, TopicName.RISQUE_INDIVIDUEL},
    53: {TopicName.INCENDIE, TopicName.RISQUES},
    54: {TopicName.EXECUTION},
    55: {TopicName.EAU, TopicName.EPANDAGE},
    56: {TopicName.DECHETS, TopicName.EAU},
    57: {TopicName.DECHETS, TopicName.DECHETS_SPECIAUX},
    58: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.FEU, TopicName.TOITURE},
    59: {TopicName.BRUIT_VIBRATIONS, TopicName.VLE},
    60: {TopicName.CONDITIONS_APPLICATION, TopicName.EXECUTION},
    61: {TopicName.EAU, TopicName.PREFET},
    62: {TopicName.FARINES_VIANDE_ET_OS},
    63: {TopicName.ACCIDENTS_POLLUTIONS},
    64: {TopicName.RISQUES, TopicName.RISQUE_INDIVIDUEL},
    65: {TopicName.DEFINITIONS, TopicName.DISPOSITIONS_GENERALES},
    66: {TopicName.DECHETS},
    67: {TopicName.BIOMASSE, TopicName.COMBUSTIBLES},
    68: {TopicName.EAU},
    69: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.FEU},
    70: {TopicName.DISPOSITIONS_GENERALES, TopicName.DOSSIER, TopicName.PREFET},
    71: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    72: {TopicName.DECHETS},
    73: {TopicName.CHANGEMENT_EXPLOITANT, TopicName.DISPOSITIONS_GENERALES, TopicName.PREFET},
    74: {TopicName.INCENDIE, TopicName.RISQUES, TopicName.PREFET},
    75: {TopicName.VAPEURS},
    76: {TopicName.ACCIDENTS_POLLUTIONS},
    77: {TopicName.AIR_ODEURS, TopicName.EMISSIONS},
    78: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    79: {TopicName.CONSOMMATION_D_EAU, TopicName.EAU},
    80: {TopicName.CONSOMMATION_D_EAU, TopicName.EAU, TopicName.PREFET},
    81: {TopicName.EXPLOITATION, TopicName.REGISTRE},
    82: {TopicName.CHANGEMENT_EXPLOITANT, TopicName.DISPOSITIONS_GENERALES, TopicName.PREFET},
    83: {TopicName.EAU, TopicName.EPANDAGE},
    84: {TopicName.INCENDIE, TopicName.RISQUES},
    85: {TopicName.DOSSIER, TopicName.DISPOSITIONS_GENERALES},
    86: {TopicName.DECHETS},
    87: {TopicName.RISQUES},
    88: {TopicName.ABROGATION_AM_PASSE},
    89: {TopicName.EAU, TopicName.EFFLUENTS},
    90: {TopicName.VAPEURS},
    91: {TopicName.ACCIDENTS_POLLUTIONS, TopicName.VENTILATION},
    92: {TopicName.EAU, TopicName.EPANDAGE},
    93: {TopicName.BRUIT_VIBRATIONS, TopicName.VLE},
    94: {TopicName.SECURITE},
    95: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.ETANCHEITE},
    96: {TopicName.RISQUES},
    97: {TopicName.DECLARATION_DES_EMISSIONS, TopicName.EMISSIONS},
    98: {TopicName.FIN_EXPLOITATION},
    99: {TopicName.EAU},
    100: {TopicName.AIR_ODEURS, TopicName.BIOGAZ},
    101: {TopicName.DISPOSITIONS_GENERALES, TopicName.MODIFICATIONS, TopicName.PREFET},
    102: {TopicName.MESURE_BRUIT},
    103: {TopicName.CONFINEMENT, TopicName.REJETS_CHLORE},
    104: {TopicName.DECHETS, TopicName.ENTREPOSAGE, TopicName.RISQUES},
    105: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.VENTILATION},
    106: {TopicName.BRUIT_VIBRATIONS},
    107: {TopicName.BRUIT_VIBRATIONS, TopicName.SURVEILLANCE},
    108: {TopicName.BRULAGE, TopicName.DECHETS},
    109: {TopicName.DECHETS, TopicName.ENTREPOSAGE},
    110: {TopicName.BRUIT_VIBRATIONS, TopicName.VLE},
    111: {TopicName.NORME_TRANSFORMATION},
    112: {TopicName.EAU, TopicName.VLE},
    113: {TopicName.SURVEILLANCE_EXPLOITATION, TopicName.EXPLOITATION},
    114: {TopicName.EAU},
    115: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.INSTALLATIONS_ELECTRIQUES},
    116: {TopicName.DECHETS, TopicName.RECYCLAGE},
    117: {TopicName.BILAN_ENVIRONNEMENT, TopicName.PREFET},
    118: {TopicName.DISPOSITIONS_GENERALES, TopicName.FIN_EXPLOITATION},
    119: {TopicName.DECHETS, TopicName.DECHETS_NON_DANGEREUX},
    120: {TopicName.CONDITIONS_APPLICATION},
    121: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.FEU},
    122: {TopicName.DISPOSITIONS_GENERALES, TopicName.SURVEILLANCE_EXPLOITATION},
    123: {TopicName.EXECUTION},
    124: {TopicName.EMISSIONS_ATMOSPHERE},
    125: {TopicName.HAUTEUR_CHEMINEE},
    126: {TopicName.DECHETS, TopicName.DECHETS_BANALS},
    127: {TopicName.PREFET},
    128: {TopicName.AIR_ODEURS, TopicName.CONDITIONS_REJET, TopicName.VLE},
    129: {TopicName.EAU, TopicName.EPANDAGE, TopicName.PREFET},
    130: {TopicName.DISPOSITIONS_GENERALES, TopicName.JUSTIFICATIONS},
    131: {TopicName.VAPEURS},
    132: {TopicName.METHODOLOGIE},
    133: {TopicName.DECHETS},
    134: {TopicName.VAPEURS},
    135: {TopicName.SURVEILLANCE_EXPLOITATION, TopicName.SURVEILLANCE},
    136: {TopicName.EMISSIONS},
    137: {TopicName.GESTION_QUALITE},
    138: {TopicName.CONDITIONS_APPLICATION},
    139: {TopicName.EPANDAGE, TopicName.PREFET},
    140: {TopicName.DISPOSITIONS_GENERALES, TopicName.FIN_EXPLOITATION, TopicName.INFO_REDACTION},
    141: {TopicName.BRULAGE, TopicName.DECHETS},
    142: {TopicName.RISQUES},
    143: {TopicName.COV, TopicName.ACCIDENTS_POLLUTIONS},
    144: {TopicName.RECENSEMENT, TopicName.RISQUES},
    145: {TopicName.MESURE_BRUIT, TopicName.DEFINITIONS},
    146: {TopicName.HAUTEUR_CHEMINEE, TopicName.METHODOLOGIE},
    147: {TopicName.REGISTRE},
    148: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.ELECTRICITE_STATIQUE},
    149: {TopicName.DISPOSITIONS_GENERALES, TopicName.SURVEILLANCE_EXPLOITATION},
    150: {TopicName.EAU},
    151: {TopicName.CONDITIONS_APPLICATION, TopicName.EXECUTION},
    152: {TopicName.ACCIDENTS_POLLUTIONS, TopicName.FEU},
    153: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    154: {TopicName.ACCIDENTS_POLLUTIONS, TopicName.PROPRETE},
    155: {TopicName.FARINES_VIANDE_ET_OS},
    156: {TopicName.ENTREE_VIGUEUR, TopicName.EXECUTION},
    157: {TopicName.INFO_REDACTION},
    158: {TopicName.RISQUES},
    159: {TopicName.DEFINITIONS},
    160: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    161: {TopicName.PREFET},
    162: {TopicName.ACCIDENTS_POLLUTIONS, TopicName.SECURITE, TopicName.VENTILATION},
    163: {TopicName.EAU, TopicName.REJETS_ACCIDENTELS},
    164: {TopicName.MESURE_BRUIT},
    165: {TopicName.ACCIDENTS_POLLUTIONS, TopicName.INCENDIE, TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    166: {TopicName.AIR_ODEURS, TopicName.VLE},
    167: {TopicName.CHANGEMENT_EXPLOITANT, TopicName.DISPOSITIONS_GENERALES, TopicName.PREFET},
    168: {TopicName.INCENDIE, TopicName.RISQUES},
    169: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    170: {TopicName.EPANDAGE},
    171: {TopicName.MESURE_BRUIT, TopicName.VLE},
    172: {TopicName.DECHETS},
    173: {TopicName.INCENDIE, TopicName.PREFET},
    174: {TopicName.DECHETS},
    175: {TopicName.EXPLOITATION},
    176: {TopicName.CONDITIONS_APPLICATION, TopicName.DISPOSITIONS_GENERALES},
    177: {TopicName.EMISSIONS_ATMOSPHERE, TopicName.VLE},
    178: {TopicName.EXPLOITATION, TopicName.REGISTRE},
    179: {TopicName.DEFINITIONS},
    180: {TopicName.ACCIDENTS_POLLUTIONS},
    181: {TopicName.ACCIDENTS_POLLUTIONS},
    182: {TopicName.AIR_ODEURS, TopicName.POUSSIERES, TopicName.VLE},
    183: {TopicName.EXECUTION},
    184: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT, TopicName.RETENTION},
    185: {TopicName.EMISSIONS_ATMOSPHERE, TopicName.VLE},
    186: {TopicName.CONDITIONS_APPLICATION, TopicName.EXECUTION},
    187: {TopicName.DISPOSITIONS_CONSTRUCTIVES_AMENAGEMENT},
    188: {TopicName.DEFINITIONS, TopicName.DISPOSITIONS_GENERALES},
    189: {TopicName.EAU, TopicName.MILIEU_AQUATIQUE},
    190: {TopicName.AIR_ODEURS, TopicName.COV, TopicName.PREFET},
    191: {TopicName.DECHETS},
    192: {TopicName.EAU, TopicName.EPANDAGE},
    193: {TopicName.EMISSIONS_ATMOSPHERE},
    194: {TopicName.INCENDIE},
    195: {TopicName.EAU, TopicName.PREFET},
    196: {TopicName.RISQUES},
    197: {TopicName.INSTALLATIONS_ELECTRIQUES},
}

_Alineas = List[EnrichedString]
_Titles = List[str]
_Text = Tuple[_Titles, _Alineas]
_LabelizedText = Tuple[_Text, Set[TopicName]]


def _build_labelized_text(raw_text: Tuple[int, List[str], List[Dict]], labels: Set[TopicName]) -> _LabelizedText:
    text = raw_text[1], [EnrichedString.from_dict(dict_) for dict_ in raw_text[2]]
    return text, labels


def _load_dataset(
    texts: List[Tuple[int, List[str], List[Dict]]], labels: Dict[int, Set[TopicName]]
) -> List[_LabelizedText]:
    return [_build_labelized_text(text, labels[index]) for index, text in enumerate(texts)]


_PATH = Path(__file__).parent / 'raw_exploration_dataset.json'
TEXTS = json.load(open(_PATH))
DATASET = _load_dataset(TEXTS, LABELS)
