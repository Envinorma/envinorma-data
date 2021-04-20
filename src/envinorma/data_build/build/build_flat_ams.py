import json
import random
from typing import List, Optional, Tuple, TypeVar

import pandas
from tqdm import tqdm

from envinorma.data import ArreteMinisteriel, StructuredText
from envinorma.data.flat_am import FlatAlinea, FlatArreteMinisteriel, FlatSection
from envinorma.data_build.filenames import am_dataset_filename
from envinorma.data_build.load import load_am_list, load_enriched_am_groups
from envinorma.utils import ensure_not_none

_FlatElements = Tuple[FlatArreteMinisteriel, List[FlatSection], List[FlatAlinea]]


def _generate_am_version_id(am: ArreteMinisteriel, enriched: bool, enriched_rank: Optional[int]) -> str:
    am_id = ensure_not_none(am.id)
    if not enriched:
        return am_id
    version_not_none = ensure_not_none(enriched_rank)
    return f'{am_id}_{version_not_none}'


def _build_flat_am(am: ArreteMinisteriel, enriched: bool, am_id: str) -> FlatArreteMinisteriel:
    am_id_int = _generate_am_id_int(am_id)
    original_am_id = ensure_not_none(am.id)
    return FlatArreteMinisteriel(
        am_id_int,
        original_am_id,
        am.short_title,
        am.title.text,
        am.unique_version,
        am.installation_date_criterion.left_date if am.installation_date_criterion else None,
        am.installation_date_criterion.right_date if am.installation_date_criterion else None,
        ensure_not_none(am.aida_url),
        ensure_not_none(am.legifrance_url),
        am.classements_with_alineas,
        None if not enriched else _generate_am_id_int(original_am_id),
    )


_TextOrAM = TypeVar('_TextOrAM', ArreteMinisteriel, StructuredText)


def _extract_section_with_depths(obj: _TextOrAM, depth: int = 0) -> List[Tuple[StructuredText, int]]:
    result: List[Tuple[StructuredText, int]] = []
    for section in obj.sections:
        result.append((section, depth))
        result.extend(_extract_section_with_depths(section, depth + 1))
    return result


def _extract_text_content(text: Optional[StructuredText]) -> Optional[str]:
    if not text:
        return None
    return '\n'.join(
        [text.title.text]
        + [al.text for al in text.outer_alineas]
        + [ensure_not_none(_extract_text_content(sec)) for sec in text.sections]
    )


_ID_RANGE = 10 ** 18


def _generate_alinea_id(am_id: str, section_rank: int, alinea_rank: int) -> int:
    random.seed((am_id, section_rank, alinea_rank))
    return random.randint(0, _ID_RANGE)


def _generate_am_id_int(am_id: str) -> int:
    random.seed(am_id)
    return random.randint(0, _ID_RANGE)


def _generate_section_id(am_id: str, section_rank: int) -> int:
    random.seed((am_id, section_rank))
    return random.randint(0, _ID_RANGE)


def _build_flat_sections(am: ArreteMinisteriel, am_id: str) -> List[FlatSection]:
    section_with_levels = _extract_section_with_depths(am)
    return [
        FlatSection(
            _generate_section_id(am_id, rank),
            rank=rank,
            title=section.title.text,
            level=depth,
            active=ensure_not_none(section.applicability).active,
            modified=ensure_not_none(section.applicability).modified,
            warnings='\n'.join(ensure_not_none(section.applicability).warnings),
            reference_str=section.reference_str or '',
            previous_version=_extract_text_content(ensure_not_none(section.applicability).previous_version) or '',
            arrete_id=_generate_am_id_int(am_id),
        )
        for rank, (section, depth) in enumerate(section_with_levels)
    ]


def _build_section_alineas(section: StructuredText, am_id: str, section_rank: int) -> List[FlatAlinea]:
    return [
        FlatAlinea(
            _generate_alinea_id(am_id, section_rank, al_rank),
            al_rank,
            al.active if al.active is not None else True,
            al.text,
            json.dumps(al.table.to_dict(), ensure_ascii=False) if al.table else '',
            _generate_section_id(am_id, section_rank),
        )
        for al_rank, al in enumerate(section.outer_alineas)
    ]


def _build_flat_alineas(am: ArreteMinisteriel, am_id: str) -> List[FlatAlinea]:
    section_with_levels = _extract_section_with_depths(am)
    return [
        al
        for section_rank, (section, _) in enumerate(section_with_levels)
        for al in _build_section_alineas(section, am_id, section_rank)
    ]


def _build_flat_elements(am: ArreteMinisteriel, enriched: bool, enriched_rank: Optional[int]) -> _FlatElements:
    am_id = _generate_am_version_id(am, enriched, enriched_rank)
    return _build_flat_am(am, enriched, am_id), _build_flat_sections(am, am_id), _build_flat_alineas(am, am_id)


def _dump_flat_ams(flat_ams: List[FlatArreteMinisteriel]) -> None:
    filename = am_dataset_filename('arretes')
    records = [obj.to_dict() for obj in flat_ams]
    for rec in records:
        rec['classements_with_alineas'] = json.dumps(rec['classements_with_alineas'], ensure_ascii=False)
        rec['enriched_from_id'] = str(rec['enriched_from_id']) if rec['enriched_from_id'] else ''
    dataframe = pandas.DataFrame(records)
    dataframe.to_csv(filename)


def _dump_flat_sections(flat_sections: List[FlatSection]) -> None:
    filename = am_dataset_filename('sections')
    records = [obj.to_dict() for obj in flat_sections]
    dataframe = pandas.DataFrame(records)
    dataframe.to_csv(filename)


def _dump_flat_alineas(flat_alineas: List[FlatAlinea]) -> None:
    filename = am_dataset_filename('alineas')
    records = [obj.to_dict() for obj in flat_alineas]
    dataframe = pandas.DataFrame(records)
    dataframe.to_csv(filename)


def _dump_flat_elements(all_elements: List[_FlatElements]) -> None:
    flat_ams = [am for am, _, _ in all_elements]
    flat_sections = [sec for _, sections, _ in all_elements for sec in sections]
    flat_alineas = [al for _, _, alineas in all_elements for al in alineas]
    _dump_flat_ams(flat_ams)
    _dump_flat_sections(flat_sections)
    _dump_flat_alineas(flat_alineas)


def build_flat_ams(am_list_filename: str, enriched_output_folder: str) -> None:
    am_list = load_am_list(am_list_filename)
    enriched_am_groups = load_enriched_am_groups(enriched_output_folder)

    ams_with_characteristics: List[Tuple[ArreteMinisteriel, bool, Optional[int]]] = [
        *[(am, False, None) for am in sorted(am_list, key=lambda x: x.id or '')],
        *[
            (am, True, rank)
            for _, am_group in sorted(enriched_am_groups.items())
            for rank, (_, am) in enumerate(sorted(am_group.items()))
        ],
    ]
    all_elements = [_build_flat_elements(*am) for am in tqdm(ams_with_characteristics, 'Building flat AMs')]
    _dump_flat_elements(all_elements)
