import argparse
import json
import random
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import pandas
from envinorma.data import Nomenclature, Regime, RubriqueSimpleThresholds
from envinorma.utils import write_json
from tqdm import tqdm


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
    theoretical_regime: Optional[Regime] = None

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

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['seveso'] = self.seveso.value
        if self.date_autorisation:
            res['date_autorisation'] = self.date_autorisation.strftime('%Y-%m-%d')
        if self.etat_activite:
            res['etat_activite'] = self.etat_activite.value
        if self.regime:
            res['regime'] = self.regime.value
        if self.id_regime:
            res['id_regime'] = self.id_regime.value
        if self.famille_nomenclature:
            res['famille_nomenclature'] = self.famille_nomenclature.value
        return res


def load_all_classements() -> Dict[str, List[GRClassement]]:
    icpe_data = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/icpe_admin_data.json'))
    return {
        id_: [GRClassement.from_georisques_dict(classement) for classement in classements if classement['seveso']]
        for id_, classements in tqdm(icpe_data.items(), 'Initializing classements.')
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

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type_doc'] = self.type_doc.value
        if self.date_doc:
            res['date_doc'] = self.date_doc.strftime('%Y-%m-%d')
        return res


def _is_null(doc: Dict[str, Any]) -> bool:
    return all([value is None for value in doc.values()])


def load_all_documents() -> Dict[str, List[GRDocument]]:
    icpe_data = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/georisques_documents.json'))
    return {
        id_.replace('-', '.'): [GRDocument.from_georisques_dict(doc) for doc in docs if not _is_null(doc)]
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
    classements: Optional[List[GRClassement]] = None
    documents: Optional[List[GRDocument]] = None

    def __post_init__(self) -> None:
        assert len(self.num_dep) <= 4
        assert isinstance(self.s3ic_id, str)
        if self.last_inspection:
            if not isinstance(self.last_inspection, (date, datetime)):
                print(self.last_inspection)
            assert isinstance(self.last_inspection, (date, datetime))

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

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.last_inspection:
            res['last_inspection'] = self.last_inspection.strftime('%Y-%m-%d')
        res['regime'] = self.regime.value
        res['seveso'] = self.seveso.value
        res['family'] = self.family.value
        res['active'] = self.active.value
        if self.classements:
            res['classements'] = [cl.to_dict() for cl in self.classements]
        if self.documents:
            res['documents'] = [cl.to_dict() for cl in self.documents]
        return res


def _dataframe_row_to_installation(row: Tuple) -> GeorisquesInstallation:
    (
        s3ic_id,
        num_dep,
        region,
        department,
        city,
        name,
        lat,
        lon,
        last_inspection,
        regime,
        seveso,
        family,
        active,
        code_postal,
        code_insee,
        code_naf,
    ) = row
    return GeorisquesInstallation(
        s3ic_id=s3ic_id,
        num_dep=num_dep,
        region=region,
        department=department,
        city=city,
        name=name,
        lat=lat,
        lon=lon,
        last_inspection=date.fromisoformat(last_inspection) if last_inspection else None,
        regime=GRIdRegime(regime),
        seveso=Seveso(seveso),
        family=InstallationFamily(family),
        active=ActivityStatus(active),
        code_postal=code_postal,
        code_insee=code_insee,
        code_naf=code_naf,
    )


def _compute_regime(value: float, rubrique: RubriqueSimpleThresholds) -> Regime:
    for i, threshold in enumerate(rubrique.thresholds[::-1]):
        if value >= threshold:
            return rubrique.regimes[len(rubrique.regimes) - 1 - i]
    return Regime.NC


def _extract_float_value(volume_str: Optional[str]) -> float:
    if not volume_str:
        raise ValueError('Expecting volume to extract value.')
    try:
        return float(volume_str)
    except ValueError:
        raise ValueError(f'Unhandled value: {volume_str}')


def _deduce_regime(classement: GRClassement, rubrique: RubriqueSimpleThresholds) -> Optional[Regime]:
    if classement.volume_inst is None:
        return None
    value = _extract_float_value(classement.volume_inst)
    return _compute_regime(value, rubrique)


def _is_in_nomenclature(code: str, nomenclature: Nomenclature) -> bool:
    if code and code in nomenclature.simple_thresholds:
        return True
    return False


def deduce_regime_if_possible(classement: GRClassement, nomenclature: Nomenclature) -> Optional[Regime]:
    if _is_in_nomenclature(classement.code_nomenclature, nomenclature):
        return _deduce_regime(classement, nomenclature.simple_thresholds[classement.code_nomenclature])
    return None


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
    return [GeorisquesInstallation.from_georisques_dict(doc) for doc in tqdm(union, 'Initializing installations.')]


def add_theoretical_regime(
    classements: Dict[str, List[GRClassement]], nomenclature: Nomenclature
) -> Dict[str, List[GRClassement]]:
    return {
        id_: [replace(cl, theoretical_regime=deduce_regime_if_possible(cl, nomenclature)) for cl in clss]
        for id_, clss in classements.items()
    }


def load_installations_with_classements_and_docs() -> List[GeorisquesInstallation]:
    nomenclature = Nomenclature.load_default()
    installations = load_all_installations()
    classements = add_theoretical_regime(load_all_classements(), nomenclature)
    documents = load_all_documents()

    for installation in installations:
        installation.classements = classements.get(installation.s3ic_id)
        installation.documents = documents.get(installation.s3ic_id.replace('.', '-'))
    return installations


def _dump_installations() -> None:
    installations = load_installations_with_classements_and_docs()
    installations_dict = [it.to_dict() for it in installations]
    write_json(installations_dict, 'installations.json')


def _clean_dict(dict_: Dict[str, Any]) -> Dict[str, Any]:
    del dict_['documents']
    del dict_['classements']
    return dict_


def _dump_installations_csv(installations: List[GeorisquesInstallation], sample: bool) -> None:
    data_frame = pandas.DataFrame([_clean_dict(it.to_dict()) for it in installations], dtype='str')
    filename_suffix = '_sample' if sample else ''
    print(f'Dumping {len(data_frame)} installations.')
    data_frame.to_csv(f'installations{filename_suffix}.csv')


def check_installations_csv(filename: str) -> None:
    dataframe = pandas.read_csv(filename, dtype='str', index_col='Unnamed: 0', na_values=None).fillna('')
    for row in dataframe.to_numpy():
        _dataframe_row_to_installation(row)


def _dump_classements_csv(installations: List[GeorisquesInstallation], sample: bool) -> None:
    dicts = []
    for installation in installations:
        for item in installation.classements or []:
            if item.etat_activite != GRClassementActivite.ACTIVE:
                continue
            dict_ = item.to_dict()
            dict_['s3ic_id'] = installation.s3ic_id
            dicts.append(dict_)
    data_frame = pandas.DataFrame(dicts, dtype='str')
    print(f'Dumping {len(data_frame)} classements.')
    filename_suffix = '_sample' if sample else ''
    data_frame.to_csv(f'classements{filename_suffix}.csv')


def load_idf_installation_ids() -> Set[str]:
    installations = load_all_installations()
    idf_ids = {installation.s3ic_id for installation in installations if installation.region == 'ILE-DE-FRANCE'}
    print(f'found {len(idf_ids)} installations in ILE-DE-FRANCE')
    return idf_ids


GR_DOC_BASE_URL = 'http://documents.installationsclassees.developpement-durable.gouv.fr/commun'


def _rowify_doc(id_: str, ap: GRDocument) -> Dict[str, Any]:
    return {
        'installation_s3ic_id': id_,
        'description': ap.description_doc,
        'date': ap.date_doc,
        'url': f'{GR_DOC_BASE_URL}/{ap.url_doc}',
    }


def _build_aps_dataframe(installation_ids_and_aps: List[Tuple[str, GRDocument]]) -> pandas.DataFrame:
    dicts = [_rowify_doc(id, ap) for id, ap in installation_ids_and_aps]
    return pandas.DataFrame(dicts)


def _dump_idf_aps() -> None:
    installation_id_to_documents = load_all_documents()
    idf_ids = load_idf_installation_ids()
    all_idf_aps = [
        (installation_id, doc)
        for installation_id, docs in installation_id_to_documents.items()
        for doc in docs
        if installation_id in idf_ids
        if doc.type_doc == DocumentType.AP
    ]
    print(f'Found {len(all_idf_aps)} AP in IDF.')
    dataframe = _build_aps_dataframe(all_idf_aps)
    dataframe.to_csv('aps.csv')


def _dump_documents_csv(installations: List[GeorisquesInstallation], sample: bool) -> None:
    dicts = []
    for installation in installations:
        for doc in installation.documents or []:
            dict_ = doc.to_dict()
            dict_['installation_id'] = installation.s3ic_id
            dicts.append(dict_)
    data_frame = pandas.DataFrame(dicts, dtype='str')
    filename_suffix = '_sample' if sample else ''
    print(f'Dumping {len(data_frame)} documents.')
    data_frame.to_csv(f'documents{filename_suffix}.csv')


def _dump_csvs(sample: bool = False, only_idf: bool = False) -> None:
    installations = load_installations_with_classements_and_docs()
    if only_idf:
        installations = [
            ins
            for ins in installations
            if ins.region == 'ILE-DE-FRANCE' and ins.active == ActivityStatus.EN_FONCTIONNEMENT
        ]
        print(f'{len(installations)} found in île-de-France')
    if sample:
        random.seed(1)
        installations = random.sample(installations, 200)
    _dump_installations_csv(installations, sample)
    _dump_classements_csv(installations, sample)
    _dump_documents_csv(installations, sample)
    _dump_idf_aps()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--all', nargs='?', const=True, default=False, help='Dump idf csvs')
    parser.add_argument('-p', '--ap', nargs='?', const=True, default=False, help='Dump idf AP')
    args = parser.parse_args()
    if args.all:
        _dump_csvs(False, True)
    if args.ap:
        _dump_idf_aps()


if __name__ == '__main__':
    main()
