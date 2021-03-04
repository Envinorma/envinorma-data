'''
Download last versions of AM and send them to envinorma-web
'''

import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from envinorma.back_office.fetch_data import (
    load_all_am_statuses,
    load_all_initial_am,
    load_all_parametrizations,
    load_all_structured_am,
)
from envinorma.back_office.generate_final_am import AMVersions, apply_parametrization, enrich_am
from envinorma.back_office.utils import ID_TO_AM_MD, AMStatus
from envinorma.config import generate_parametric_descriptor
from envinorma.data import ArreteMinisteriel, DateCriterion, StructuredText, Table
from envinorma.parametrization import Parametrization
from envinorma.utils import date_to_str, ensure_not_none, str_to_date, write_json
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
    versions = apply_parametrization(id_, am, parametrization, ID_TO_AM_MD[id_])
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
        for id_, md in tqdm(ID_TO_AM_MD.items(), 'Building AM list.')
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


def _extract_all_references(sections: List[StructuredText]) -> List[Optional[str]]:
    return [section.reference_str for section in sections] + [
        ref for section in sections for ref in _extract_all_references(section.sections)
    ]


def _check_references(am: ArreteMinisteriel) -> None:
    references = _extract_all_references(am.sections)
    nb_refs = len(references)
    if None in references:
        nb_none = len([x for x in references if x is None])
        raise ValueError(f'References must all be not None, found {nb_none}/{nb_refs} None')
    nb_empty_refs = len([x for x in references if not x])
    if nb_empty_refs / (nb_refs or 1) >= 0.95:
        raise ValueError(f'More than 95% of references are empty, found {nb_empty_refs}/{nb_refs} empty')


def _extract_all_tables(sections: List[StructuredText]) -> List[Table]:
    return [alinea.table for section in sections for alinea in section.outer_alineas if alinea.table] + [
        tb for section in sections for tb in _extract_all_tables(section.sections)
    ]


def _check_table_extraction(am: ArreteMinisteriel) -> None:
    tables = _extract_all_tables(am.sections)
    str_rows = [row.text_in_inspection_sheet for table in tables for row in table.rows if not row.is_header]
    nb_none = len([x for x in str_rows if x is None])
    nb_rows = len(str_rows)
    if nb_none:
        raise ValueError(f'text_in_inspection_sheet must all be not None, found {nb_none}/{nb_rows} None')
    nb_empty_str_rows = len([x for x in str_rows if not x])
    if nb_empty_str_rows / (nb_rows or 1) >= 0.95:
        raise ValueError(
            f'More than 95% of text_in_inspection_sheet are empty, found {nb_empty_str_rows}/{nb_rows} empty'
        )


def _parse_date(str_date: Optional[str]) -> Optional[float]:
    if str_date is None:
        return None
    return str_to_date(str_date).date().toordinal()


_Segment = Tuple[float, float]


def _is_a_partition(segments: List[_Segment]) -> bool:
    segments = sorted(segments)
    if not segments:
        return False
    if segments[0][0] != -math.inf:
        return False
    if segments[-1][1] != math.inf:
        return False
    for (_, l), (r, _) in zip(segments, segments[1:]):
        if l != r:
            return False
    return True


def _is_date_partition(criteria: List[DateCriterion]) -> bool:
    segments: List[_Segment] = [
        (_parse_date(cr.left_date) or -math.inf, _parse_date(cr.right_date) or math.inf) for cr in criteria
    ]
    return _is_a_partition(segments)


def _check_non_overlapping_installation_dates(ams: Dict[str, ArreteMinisteriel]) -> None:
    if len(ams) == 1:
        am = list(ams.values())[0]
        if not am.unique_version:
            raise ValueError('Expecting unique_version=True when only one AM.')
        return
    date_criteria: List[DateCriterion] = []
    no_date_criterion: List[str] = []
    for version_name, am in ams.items():
        if am.installation_date_criterion:
            date_criteria.append(am.installation_date_criterion)
        else:
            no_date_criterion.append(version_name)
    if len(no_date_criterion) != 1:
        raise ValueError(f'Expecting exactly one version with no date criterion, got {no_date_criterion}')
    if not _is_date_partition(date_criteria):
        raise ValueError(f'Expecting partition, this is not the case here {date_criteria}')


def _check_enriched_am_group(ams: Dict[str, ArreteMinisteriel]) -> None:
    ids = {am.id for am in ams.values()}
    if len(ids) != 1:
        raise ValueError(f'Expecting exactly one am_id in list, got ids={ids}')
    try:
        _check_non_overlapping_installation_dates(ams)
    except:
        print(list(ids)[0])
        raise


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
    _check_references(am)
    _check_table_extraction(am)


def _load_am_list() -> List[ArreteMinisteriel]:
    return [ArreteMinisteriel.from_dict(x) for x in json.load(open(_AM_LIST))]


def _load_enriched_am_list() -> Dict[str, ArreteMinisteriel]:
    return {
        file_: ArreteMinisteriel.from_dict(json.load(open(os.path.join(_ENRICHED_OUTPUT_FOLDER, file_))))
        for file_ in os.listdir(_ENRICHED_OUTPUT_FOLDER)
    }


def _check_classement_csv() -> None:
    filename = os.path.join(_OUTPUT_FOLDER, 'unique_classements.csv')
    csv = pd.read_csv(filename)
    expected_keys = ['regime', 'rubrique', 'alinea']
    for key in expected_keys:
        if key not in csv.keys():
            raise ValueError(f'Expecting key {key} in {csv.keys()}')
    nb_rows = csv.shape[0]
    nb_rows_no_repeat = csv.groupby(['rubrique', 'regime']).count().shape[0]
    if nb_rows != nb_rows_no_repeat:
        raise ValueError(
            f'Expecting {nb_rows} and {nb_rows_no_repeat} to be equal. It is not, '
            'so there are repeated couples in dataframe.'
        )


def _check_seeds() -> None:
    _check_classement_csv()
    am_list = _load_am_list()
    for am in tqdm(am_list, 'Checking AMs'):
        _check_am(am)
    all_ids = {am.id for am in am_list}
    assert 'JORFTEXT000034429274_A' in all_ids
    assert 'JORFTEXT000034429274_E' in all_ids
    assert 'JORFTEXT000034429274_D' in all_ids
    enriched_am = _load_enriched_am_list()
    id_to_versions: Dict[str, Dict[str, ArreteMinisteriel]] = {}
    for version_name, am in tqdm(enriched_am.items(), 'Checking enriched AMs'):
        _check_am(am)
        if am.id not in id_to_versions:
            id_to_versions[am.id or ''] = {}
        id_to_versions[am.id or ''][version_name] = am
    for am_versions in tqdm(id_to_versions.values(), 'Checking enriched AM groups'):
        _check_enriched_am_group(am_versions)


def _write_classements_csv() -> None:
    tuples = []
    keys = ['rubrique', 'regime', 'alinea']
    for am in ID_TO_AM_MD.values():
        for cl in am.classements:
            if cl.state == cl.state.ACTIVE:
                tp = tuple([getattr(cl, key) if key != 'regime' else cl.regime.value for key in keys])
                tuples.append(tp)
    unique = pd.DataFrame(tuples, columns=keys).groupby(['rubrique', 'regime']).first()
    final_csv = unique.sort_values(by=['rubrique', 'regime']).reset_index()[keys]
    filename = os.path.join(_OUTPUT_FOLDER, 'unique_classements.csv')
    final_csv.to_csv(filename)


def _generate_seeds() -> None:
    _write_classements_csv()
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


def run():
    _generate_seeds()
    _check_seeds()


if __name__ == '__main__':
    run()
