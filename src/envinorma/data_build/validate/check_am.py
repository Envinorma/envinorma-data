import json
import math
import os
from datetime import date
from typing import Dict, List, Optional, Tuple

from tqdm import tqdm

from envinorma.back_office.utils import AM1510_IDS
from envinorma.data import ArreteMinisteriel, DateCriterion, StructuredText
from envinorma.data.text_elements import Table
from envinorma.utils import str_to_date


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


def _print_input_id(func):
    def _func(am: ArreteMinisteriel):
        try:
            func(am)
        except:
            print(am.id)
            raise

    return _func


def _check_publication_date(publication_date: Optional[date]):
    if not publication_date:
        raise ValueError('Expecting publication_date to be defined')


@_print_input_id
def _check_am(am: ArreteMinisteriel) -> None:
    if am.id in AM1510_IDS:
        raise ValueError('1510 should not be in AM list as such')
    regimes = {clas.regime for clas in am.classements}
    if len(regimes) != 1:
        raise ValueError(regimes)
    assert am.summary is not None
    assert am.legifrance_url is not None
    assert am.aida_url is not None
    _check_references(am)
    _check_table_extraction(am)
    _check_publication_date(am.publication_date)


def _load_am_list(am_list_filename: str) -> List[ArreteMinisteriel]:
    return [ArreteMinisteriel.from_dict(x) for x in json.load(open(am_list_filename))]


def _load_enriched_am_list(enriched_output_folder: str) -> Dict[str, ArreteMinisteriel]:
    return {
        file_: ArreteMinisteriel.from_dict(json.load(open(os.path.join(enriched_output_folder, file_))))
        for file_ in os.listdir(enriched_output_folder)
    }


def check_ams(am_list_filename: str, enriched_output_folder: str) -> None:
    am_list = _load_am_list(am_list_filename)
    for am in tqdm(am_list, 'Checking AMs'):
        _check_am(am)
    all_ids = {am.id for am in am_list}
    assert 'JORFTEXT000034429274_A' in all_ids
    assert 'JORFTEXT000034429274_E' in all_ids
    assert 'JORFTEXT000034429274_D' in all_ids
    enriched_am = _load_enriched_am_list(enriched_output_folder)
    id_to_versions: Dict[str, Dict[str, ArreteMinisteriel]] = {}
    for version_name, am in tqdm(enriched_am.items(), 'Checking enriched AMs'):
        _check_am(am)
        if am.id not in id_to_versions:
            id_to_versions[am.id or ''] = {}
        id_to_versions[am.id or ''][version_name] = am
    for am_versions in tqdm(id_to_versions.values(), 'Checking enriched AM groups'):
        _check_enriched_am_group(am_versions)
