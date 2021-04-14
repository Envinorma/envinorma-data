import json
import os
from typing import Dict, List

from tqdm import tqdm

from envinorma.data import ArreteMinisteriel


def load_am_list(am_list_filename: str) -> List[ArreteMinisteriel]:
    return [ArreteMinisteriel.from_dict(x) for x in json.load(open(am_list_filename))]


def load_enriched_am(enriched_output_folder: str) -> Dict[str, ArreteMinisteriel]:
    return {
        file_: ArreteMinisteriel.from_dict(json.load(open(os.path.join(enriched_output_folder, file_))))
        for file_ in os.listdir(enriched_output_folder)
    }


def _group_enriched_am(enriched_am: Dict[str, ArreteMinisteriel]) -> Dict[str, Dict[str, ArreteMinisteriel]]:
    id_to_versions: Dict[str, Dict[str, ArreteMinisteriel]] = {}
    for version_name, am in tqdm(enriched_am.items(), 'Checking enriched AMs'):
        if am.id not in id_to_versions:
            id_to_versions[am.id or ''] = {}
        id_to_versions[am.id or ''][version_name] = am
    return id_to_versions


def load_enriched_am_groups(enriched_output_folder: str) -> Dict[str, Dict[str, ArreteMinisteriel]]:
    return _group_enriched_am(load_enriched_am(enriched_output_folder))
