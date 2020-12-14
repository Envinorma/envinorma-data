import json
from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from tqdm import tqdm
from typing import Any, Dict, List, Optional


class Seveso(Enum):
    NON_SEVESO = 'NS'
    SEUIL_HAUT = 'SH'
    SEUIL_BAS = 'SB'
    EMPTY = ''


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
    date_autorisation: Optional[date]
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
            datetime.strptime(dict_['date_autorisation'], '%Y-%m-%d').date() if dict_['date_autorisation'] else None
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
        for id_, classements in tqdm(icpe_data.items())
    }


class DocumentType(Enum):
    AP = 'Arrêté préfectoral'
    RAPPORT = 'Rapport'
    VISITE = 'Visite'
    APMED = 'Arrêté de mise en demeure'
    SANCTION = 'Arrêté de sanction'
    AUTRE = 'Autre'
    SUITE = "Suite d'inspection"
    INFO_PUBLIC = 'Information du public (DI Seveso art. 14)'


@dataclass
class GRDocument:
    date_doc: Optional[date]
    type_doc: DocumentType
    description_doc: str
    url_doc: str

    @staticmethod
    def from_georisques_dict(dict_: Dict[str, Any]) -> 'GRDocument':
        dict_ = {_snake_to_camel(key): value for key, value in dict_.items()}
        dict_['type_doc'] = DocumentType(dict_['type_doc'])
        dict_['date_doc'] = datetime.strptime(dict_['date_doc'], '%Y-%m-%d').date() if dict_['date_doc'] else None
        return GRDocument(**dict_)


def _is_null(doc: Dict[str, Any]) -> bool:
    return all([value is None for value in doc.values()])


def load_all_documents() -> Dict[str, List[GRDocument]]:
    icpe_data = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/georisques_documents.json'))
    return {
        id_: [GRDocument.from_georisques_dict(doc) for doc in docs if not _is_null(doc)]
        for id_, docs in icpe_data.items()
    }


class InstallationFamily(Enum):
    BOVINS = 'Bovins'
    INDUSTRIES = 'Industries'
    CARRIERES = 'Carrières'
    PORCS = 'Porcs'
    VOLAILLES = 'Volailles'


class ActivityStatus(Enum):
    EN_FONCTIONNEMENT = 'En fonctionnement'
    EN_CONSTRUCTION = 'En construction'
    CESSATION_DECLAREE = 'Cessation déclarée'
    A_L_ARRET = 'A l\'arrêt'
    RECOLEMENT_FAIT = 'Récolement fait'


@dataclass
class GeorisquesInstallation:
    s3ic_id: str
    num_dep: str
    region: Optional[str]
    department: Optional[str]
    city: str
    name: str
    lat: float
    lon: float
    last_inspection: Optional[date]
    regime: GRIdRegime
    seveso: Seveso
    family: InstallationFamily
    active: ActivityStatus
    code_postal: str
    code_insee: str
    code_naf: str

    @staticmethod
    def from_georisques_dict(dict_: Dict[str, Any]) -> 'GeorisquesInstallation':
        return GeorisquesInstallation(
            s3ic_id=dict_['properties']['code_s3ic'],
            num_dep=dict_['properties']['num_dep'],
            region=dict_['regionInst'],
            department=dict_['departementInst'],
            city=dict_['communeInst'],
            name=dict_['nomInst'],
            lat=dict_['geometry']['coordinates'][1],
            lon=dict_['geometry']['coordinates'][0],
            last_inspection=datetime.strptime(dict_['derInspection'], '%Y-%m-%d').date()
            if dict_['derInspection']
            else None,
            regime=GRIdRegime(dict_['properties']['regime']),
            seveso=Seveso(dict_['properties']['seveso']),
            family=InstallationFamily(dict_['properties']['famille_ic']),
            active=ActivityStatus(dict_['etatActiviteInst']),
            code_postal=dict_['codePostal'],
            code_insee=dict_['codeInsee'],
            code_naf=dict_['properties']['code_naf'],
        )


def load_all_installations() -> List[GeorisquesInstallation]:
    data_geojson = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/icpe.geojson'))
    id_to_data_geojson = {doc['properties']['code_s3ic']: doc for doc in data_geojson['features']}

    data_georisques = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/georisques_icpe_scrap.json'))
    id_to_data_georisques = {doc['idInst']: doc for doc in data_georisques}

    diff = id_to_data_geojson.keys() ^ id_to_data_georisques.keys()
    if diff:
        print(f'{len(diff)} installations lack one source of data and are therefore skipped.')
    common = id_to_data_geojson.keys() & id_to_data_georisques.keys()
    union = [{**id_to_data_georisques[id_], **id_to_data_geojson[id_]} for id_ in common]
    return [GeorisquesInstallation.from_georisques_dict(doc) for doc in tqdm(union)]
