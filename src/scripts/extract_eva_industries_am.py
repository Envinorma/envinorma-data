'''
Group EVA industrie AMs.
'''
import json
import os
from typing import Any, Dict, List

from envinorma.data import ArreteMinisteriel
from envinorma.utils import write_json

_OUTPUT_FOLDER = 'eva_seeds'
_INPUT_FOLDER = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds'
_ENRICHED_INPUT_FOLDER = os.path.join(_INPUT_FOLDER, 'enriched_arretes')
_AM_LIST = os.path.join(_INPUT_FOLDER, 'am_list.json')
_AM_IDS = {'JORFTEXT000038358856', 'JORFTEXT000033560858', 'JORFTEXT000000552021', 'JORFTEXT000000369330'}


def _load_am_list() -> List[ArreteMinisteriel]:
    return [ArreteMinisteriel.from_dict(x) for x in json.load(open(_AM_LIST))]


def _load_enriched_am_list() -> Dict[str, Dict[str, ArreteMinisteriel]]:
    enriched_am = {
        file_: ArreteMinisteriel.from_dict(json.load(open(os.path.join(_ENRICHED_INPUT_FOLDER, file_))))
        for file_ in os.listdir(_ENRICHED_INPUT_FOLDER)
    }
    id_to_versions: Dict[str, Dict[str, ArreteMinisteriel]] = {}
    for version_name, am in enriched_am.items():
        if am.id not in id_to_versions:
            id_to_versions[am.id or ''] = {}
        id_to_versions[am.id or ''][version_name] = am
    return id_to_versions


def _dump_am(am: ArreteMinisteriel, filename: str) -> None:
    write_json(am.to_dict(), os.path.join(_OUTPUT_FOLDER, filename))


def _dump_ams() -> None:
    am_list = _load_am_list()
    enriched_am = _load_enriched_am_list()
    for am in am_list:
        if am.id in _AM_IDS:
            _dump_am(am, f'{am.id}.json')
    for am_id in _AM_IDS:
        for name, am in enriched_am[am_id].items():
            _dump_am(am, f'{name}.json')


def run():
    _dump_ams()


if __name__ == '__main__':
    run()
