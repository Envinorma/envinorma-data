import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Seveso(Enum):
    NON_SEVESO = 'NS'
    SEUIL_HAUT = 'SH'
    SEUIL_BAS = 'SB'


class GRClassementActivite(Enum):
    ACTIVE = '1'
    INACTIVE = '0'


class GRRegime(Enum):
    AUTORISATION = 'Autorisation'
    ENREGISTREMENT = 'Enregistrement'
    INCONNU = 'Inconnu'


class GRIdRegime(Enum):
    AUTORISATION = 'A'
    ENREGISTREMENT = 'E'
    INCONNU = 'NC'


class FamilleNomenclature(Enum):
    OLD = 'xxx'
    ONE = '1xxx'
    TWO = '2xxx'
    THREE = '3xxx'
    FOUR = '4xxx'


def _split_string(str_: str, split_ranks: List[int]) -> List[str]:
    extended_ranks = [0] + split_ranks + [len(str_)]
    return [str_[start:end] for start, end in zip(extended_ranks, extended_ranks[1:])]


def _snake_to_camel(key: str) -> str:
    split_marks = []
    for rank in range(1, len(key) - 1):
        letter_before = key[rank - 1]
        letter = key[rank]
        letter_after = key[rank + 1]
        if letter.isupper() and letter_after.islower():
            split_marks.append(rank)
        elif letter.isupper() and letter_before.islower():
            split_marks.append(rank)
    splits = _split_string(key, split_marks)
    return '_'.join([word.lower() for word in splits])


@dataclass
class GRClassement:
    seveso: Seveso
    code_nomenclature: str
    alinea: Optional[str]
    date_autorisation: Optional[datetime]
    etat_activite: Optional[GRClassementActivite]
    regime: Optional[GRRegime]
    id_regime: Optional[GRIdRegime]
    activite_nomenclature_inst: str
    famille_nomenclature: Optional[FamilleNomenclature]
    volume_inst: Optional[str]
    unite: Optional[str]

    @staticmethod
    def from_georisques_dict(dict_: Dict[str, Any]) -> 'GRClassement':
        dict_ = {_snake_to_camel(key): value for key, value in dict_.items()}
        dict_['seveso'] = Seveso(dict_['seveso'])
        dict_['date_autorisation'] = (
            datetime.strptime(dict_['date_autorisation'], '%Y-%m-%d') if dict_['date_autorisation'] else None
        )
        dict_['etat_activite'] = GRClassementActivite(dict_['etat_activite']) if dict_['etat_activite'] else None
        dict_['regime'] = GRRegime(dict_['regime']) if dict_['regime'] else None
        dict_['id_regime'] = GRIdRegime(dict_['id_regime']) if dict_['id_regime'] else None
        dict_['famille_nomenclature'] = (
            FamilleNomenclature(dict_['famille_nomenclature']) if dict_['famille_nomenclature'] else None
        )

        return GRClassement(**dict_)


def load_all_classements() -> Dict[str, List[GRClassement]]:
    icpe_data = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/icpe_admin_data.json'))
    return {
        id_: [GRClassement.from_georisques_dict(classement) for classement in classements if classement['seveso']]
        for id_, classements in icpe_data.items()
    }


@dataclass
class GeorisquesInstallation:
    code_s3ic: str
    num_dep: str

    @staticmethod
    def from_georisques_dict(dict_: Dict[str, Any]) -> 'GeorisquesInstallation':
        return GeorisquesInstallation(dict_['code_s3ic'], dict_['num_dep'])


def load_all_installations() -> List[GeorisquesInstallation]:
    data = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/icpe.geojson'))
    return [GeorisquesInstallation.from_georisques_dict(doc['properties']) for doc in data['features']]


def build_data(
    id_to_classements: Dict[str, List[GRClassement]], installations: List[GeorisquesInstallation]
) -> List[Tuple[Optional[GRRegime], str, Optional[datetime], str]]:
    return [
        (classement.regime, classement.code_nomenclature, classement.date_autorisation, installation.num_dep)
        for installation in installations
        for classement in id_to_classements[installation.code_s3ic]
    ]

