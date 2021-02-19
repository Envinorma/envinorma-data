'''
Download last versions of AM and send them to envinorma-web
'''
from typing import Dict
from envinorma.config import generate_parametric_descriptor
from envinorma.back_office.generate_final_am import AMVersions, apply_parametrization
from envinorma.parametrization import Parametrization
from envinorma.data import ArreteMinisteriel, add_metadata
import os

from envinorma.back_office.fetch_data import (
    load_all_am_statuses,
    load_all_initial_am,
    load_all_parametrizations,
    load_all_structured_am,
)
from envinorma.back_office.utils import ID_TO_AM_MD, AMStatus
from envinorma.utils import ensure_not_none, write_json
from tqdm import tqdm

_OUTPUT_FOLDER = 'seeds'
_OUTPUT_FOLDER = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds'
_ENRICHED_OUTPUT_FOLDER = os.path.join(_OUTPUT_FOLDER, 'enriched_arretes')


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
    structured_texts = load_all_structured_am()
    id_to_structured_text = {text.id: text for text in structured_texts}
    initial_texts = load_all_initial_am()
    id_to_initial_text = {text.id: text for text in initial_texts}
    return {
        id_: add_metadata(ensure_not_none(id_to_structured_text.get(id_) or id_to_initial_text.get(id_)), md)
        for id_, md in ID_TO_AM_MD.items()
    }


def run():
    parametrizations = load_all_parametrizations()
    statuses = load_all_am_statuses()
    id_to_am = _load_id_to_text()
    all_ams = [am.to_dict() for am in id_to_am.values()]
    write_json(all_ams, os.path.join(_OUTPUT_FOLDER, 'am_list.json'), pretty=False)
    for id_ in tqdm(ID_TO_AM_MD):
        if statuses[id_] == AMStatus.VALIDATED:
            _copy_enriched_am(id_, id_to_am[id_], parametrizations[id_])


if __name__ == '__main__':
    run()
