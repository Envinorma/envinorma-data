import json
import os
import pathlib
from datetime import date
from typing import Dict, List

from ap_exploration.data import Acte, Etablissement, Prescription
from ap_exploration.db.ap_sample import AP_FOLDER

_PRESCRIPTION_FOLDER = os.path.join(AP_FOLDER, 'prescriptions')


def _load_actes() -> List[Acte]:
    here = pathlib.Path(__file__)
    filename = here.parent.joinpath('actes.json')
    return [Acte.from_dict(x) for x in json.load(open(filename))]


def _contains_recent_act(acts: List[Acte]) -> bool:
    return max([act.date_acte or date(1800, 1, 1) for act in acts], default=date(1800, 1, 1)) >= date(2019, 1, 1)


def _fetch_data() -> Dict[str, List[Acte]]:
    actes = _load_actes()
    res: Dict[Etablissement, List[Acte]] = {}
    for acte in actes:
        if acte.etablissement not in res:
            res[acte.etablissement] = []
        res[acte.etablissement].append(acte)
    to_keep = {'0065.06689'}
    return {x.id: y for x, y in res.items() if _contains_recent_act(y) or x.code_s3ic in to_keep}


_ETABLISSEMENT_ID_TO_ACTES: Dict[str, List[Acte]] = _fetch_data()
_ETABLISSEMENTS = {actes[0].etablissement.id: actes[0].etablissement for actes in _ETABLISSEMENT_ID_TO_ACTES.values()}
_ACTES = {acte.id: acte for actes in _ETABLISSEMENT_ID_TO_ACTES.values() for acte in actes}


def fetch_acte(acte_id: str) -> Acte:
    if acte_id not in _ACTES:
        raise ValueError(f'Acte with id {acte_id} not found.')
    return _ACTES[acte_id]


def fetch_etablissement(etablissement_id: str) -> Etablissement:
    if etablissement_id not in _ETABLISSEMENTS:
        raise ValueError(f'Etablissement with id {etablissement_id} not found.')
    return _ETABLISSEMENTS[etablissement_id]


def fetch_etablissement_actes(etablissement_id: str) -> List[Acte]:
    if etablissement_id not in _ETABLISSEMENT_ID_TO_ACTES:
        raise ValueError(f'Etablissement with id {etablissement_id} not found.')
    return _ETABLISSEMENT_ID_TO_ACTES[etablissement_id]


def fetch_etablissement_to_actes() -> Dict[Etablissement, List[Acte]]:
    return {actes[0].etablissement: actes for actes in _ETABLISSEMENT_ID_TO_ACTES.values()}


def _prescription_filename(ap_id: str) -> str:
    return os.path.join(_PRESCRIPTION_FOLDER, ap_id + '.json')


def fetch_ap_prescriptions(ap_id: str) -> List[Prescription]:
    filename = _prescription_filename(ap_id)
    if not os.path.exists(filename):
        return []
    return [Prescription.from_dict(x) for x in json.load(open(filename))]


def replace_prescriptions(ap_id: str, new_prescriptions: List[Prescription]) -> None:
    filename = _prescription_filename(ap_id)
    if len(filename) > 100:
        raise ValueError(filename)
    json.dump([x.to_dict() for x in new_prescriptions], open(filename, 'w'))


def add_prescriptions(ap_id: str, new_prescriptions: List[Prescription]) -> None:
    replace_prescriptions(ap_id, fetch_ap_prescriptions(ap_id) + new_prescriptions)
