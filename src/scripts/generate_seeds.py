'''
Download last versions of AM and send them to envinorma-web
'''
import json
import os
from typing import Any, Dict, List

from envinorma.back_office.fetch_data import (
    load_all_am_statuses,
    load_all_initial_am,
    load_all_parametrizations,
    load_all_structured_am,
)
from envinorma.back_office.generate_final_am import AMVersions, apply_parametrization, enrich_am
from envinorma.back_office.utils import ID_TO_AM_MD, AMStatus
from envinorma.config import generate_parametric_descriptor
from envinorma.data import ArreteMinisteriel
from envinorma.parametrization import Parametrization
from envinorma.utils import ensure_not_none, write_json
from tqdm import tqdm

_OUTPUT_FOLDER = 'seeds'
_OUTPUT_FOLDER = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds'
_ENRICHED_OUTPUT_FOLDER = os.path.join(_OUTPUT_FOLDER, 'enriched_arretes')
_AM_LIST = os.path.join(_OUTPUT_FOLDER, 'am_list.json')
_1510_IDS = ('DEVP1706393A', 'JORFTEXT000034429274')


def _dump_am_versions(am_id: str, versions: AMVersions) -> None:
    for version_desc, version in versions.items():
        filename = am_id + '_' + generate_parametric_descriptor(version_desc) + '.json'
        full_path = os.path.join(_ENRICHED_OUTPUT_FOLDER, filename)
        write_json(version.to_dict(), full_path)


def _copy_enriched_am(id_: str, am: ArreteMinisteriel, parametrization: Parametrization) -> None:
    versions = apply_parametrization(id_, am, parametrization)
    if versions:
        _dump_am_versions(id_, versions)


def _load_id_to_text() -> Dict[str, ArreteMinisteriel]:
    print('loading texts.')
    structured_texts = load_all_structured_am()
    id_to_structured_text = {text.id: text for text in structured_texts}
    initial_texts = load_all_initial_am()
    id_to_initial_text = {text.id: text for text in initial_texts}
    return {
        id_: ensure_not_none(
            enrich_am(ensure_not_none(id_to_structured_text.get(id_) or id_to_initial_text.get(id_)), md)
        )
        for id_, md in tqdm(ID_TO_AM_MD.items())
    }


def _load_1510_am_no_date() -> List[Dict[str, Any]]:
    return [
        json.load(open(os.path.join(_ENRICHED_OUTPUT_FOLDER, f'JORFTEXT000034429274_reg_{regime_str}_no_date.json')))
        for regime_str in ['A', 'E', 'D']
    ]


def print_input_id(func):
    def _func(am: ArreteMinisteriel):
        try:
            func(am)
        except:
            print(am.id)
            raise

    return _func


@print_input_id
def _check_am(am: ArreteMinisteriel) -> None:
    if am.id in _1510_IDS:
        raise ValueError('1510 should not be in AM list as such')
    regimes = {clas.regime for clas in am.classements}
    if len(regimes) != 1:
        raise ValueError(regimes)
    assert am.summary is not None
    assert am.legifrance_url is not None
    assert am.aida_url is not None


def _load_am_list() -> List[ArreteMinisteriel]:
    return [ArreteMinisteriel.from_dict(x) for x in json.load(open(_AM_LIST))]


def _load_enriched_am_list() -> List[ArreteMinisteriel]:
    return [
        ArreteMinisteriel.from_dict(json.load(open(os.path.join(_ENRICHED_OUTPUT_FOLDER, file_))))
        for file_ in os.listdir(_ENRICHED_OUTPUT_FOLDER)
    ]


def _check_seeds() -> None:
    am_list = _load_am_list()
    for am in am_list:
        _check_am(am)
    all_ids = {am.id for am in am_list}
    assert 'JORFTEXT000034429274_A' in all_ids
    assert 'JORFTEXT000034429274_E' in all_ids
    assert 'JORFTEXT000034429274_D' in all_ids
    enriched_am = _load_enriched_am_list()
    for am in enriched_am:
        _check_am(am)


def run():
    parametrizations = load_all_parametrizations()
    statuses = load_all_am_statuses()
    id_to_am = _load_id_to_text()
    all_ams = [am.to_dict() for am_id, am in id_to_am.items() if am_id not in _1510_IDS]
    for id_ in tqdm(ID_TO_AM_MD):
        if statuses[id_] == AMStatus.VALIDATED:
            _copy_enriched_am(id_, id_to_am[id_], parametrizations[id_])
            if id_ in _1510_IDS:
                all_ams.extend(_load_1510_am_no_date())
    write_json(all_ams, _AM_LIST, pretty=False)
    _check_seeds()


if __name__ == '__main__':
    run()
