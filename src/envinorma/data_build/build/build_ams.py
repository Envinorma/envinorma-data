import json
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from tqdm import tqdm

from envinorma.back_office.fetch_data import (
    load_all_am_statuses,
    load_all_initial_am,
    load_all_parametrizations,
    load_all_structured_am,
)
from envinorma.back_office.generate_final_am import AMVersions, apply_parametrization, enrich_am
from envinorma.back_office.utils import AM1510_IDS, ID_TO_AM_MD, AMStatus
from envinorma.config import generate_parametric_descriptor
from envinorma.data import AMMetadata, ArreteMinisteriel
from envinorma.data_build.filenames import AM_LIST_FILENAME, ENRICHED_OUTPUT_FOLDER, UNIQUE_CLASSEMENTS_FILENAME
from envinorma.parametrization import Parametrization
from envinorma.utils import ensure_not_none, write_json

_ID_TO_AM_MD = {id_: md for id_, md in ID_TO_AM_MD.items() if not id_.startswith('FAKE')}


def _dump_am_versions(am_id: str, versions: AMVersions) -> None:
    for version_desc, version in versions.items():
        filename = am_id + '_' + generate_parametric_descriptor(version_desc) + '.json'
        full_path = os.path.join(ENRICHED_OUTPUT_FOLDER, filename)
        write_json(version.to_dict(), full_path)


def _copy_enriched_am(id_: str, am: ArreteMinisteriel, parametrization: Parametrization) -> None:
    versions = apply_parametrization(id_, am, parametrization, _ID_TO_AM_MD[id_])
    if versions:
        _dump_am_versions(id_, versions)


def _load_id_to_text() -> Dict[str, ArreteMinisteriel]:
    print('loading texts.')
    structured_texts = load_all_structured_am()
    id_to_structured_text = {text.id or '': text for text in structured_texts}
    initial_texts = load_all_initial_am()
    id_to_initial_text = {text.id or '': text for text in initial_texts}
    ids = set(id_to_structured_text) | set(id_to_initial_text)
    return {id_: ensure_not_none(id_to_structured_text.get(id_) or id_to_initial_text.get(id_)) for id_ in ids}


def _safe_enrich(am: Optional[ArreteMinisteriel], md: AMMetadata) -> ArreteMinisteriel:
    try:
        return ensure_not_none(enrich_am(ensure_not_none(am), md))
    except Exception:
        print(md.cid)
        raise


def _safe_load_id_to_text() -> Dict[str, ArreteMinisteriel]:
    id_to_text = _load_id_to_text()
    return {id_: _safe_enrich(id_to_text.get(id_), md) for id_, md in tqdm(_ID_TO_AM_MD.items(), 'Building AM list.')}


def _load_1510_am_no_date() -> List[Dict[str, Any]]:
    return [
        json.load(open(os.path.join(ENRICHED_OUTPUT_FOLDER, f'JORFTEXT000034429274_reg_{regime_str}_no_date.json')))
        for regime_str in ['A', 'E', 'D']
    ]


def _write_unique_classements_csv(filename: str) -> None:
    tuples = []
    keys = ['rubrique', 'regime', 'alinea']
    for am in _ID_TO_AM_MD.values():
        for cl in am.classements:
            if cl.state == cl.state.ACTIVE:
                tp = tuple([getattr(cl, key) if key != 'regime' else cl.regime.value for key in keys])
                tuples.append(tp)
    unique = pd.DataFrame(tuples, columns=keys).groupby(['rubrique', 'regime']).first()
    final_csv = unique.sort_values(by=['rubrique', 'regime']).reset_index()[keys]
    final_csv.to_csv(filename)


def generate_ams() -> None:
    _write_unique_classements_csv(UNIQUE_CLASSEMENTS_FILENAME)
    parametrizations = load_all_parametrizations()
    statuses = load_all_am_statuses()
    id_to_am = _safe_load_id_to_text()
    all_ams = [am.to_dict() for am_id, am in id_to_am.items() if am_id not in AM1510_IDS]
    for id_ in tqdm(_ID_TO_AM_MD, 'Enriching AM.'):
        if statuses[id_] == AMStatus.VALIDATED:
            _copy_enriched_am(id_, id_to_am[id_], parametrizations.get(id_) or Parametrization([], []))
            if id_ in AM1510_IDS:
                all_ams.extend(_load_1510_am_no_date())
    write_json(all_ams, AM_LIST_FILENAME, pretty=False)
