from typing import Set

from pandas import DataFrame, Series


def _load_arretes_df() -> DataFrame:
    raise NotImplementedError


def _load_sections_df() -> DataFrame:
    raise NotImplementedError


def _load_alineas_df() -> DataFrame:
    raise NotImplementedError


def _extract_unique_values(series: Series) -> Set:
    raise NotImplementedError


def check_flat_ams_csv() -> None:
    arretes_df = _load_arretes_df()
    sections_df = _load_sections_df()
    alineas_df = _load_alineas_df()
    arrete_ids = _extract_unique_values(arretes_df['id'])
    arrete_referenced_ids = _extract_unique_values(arretes_df['enriched_from_id'])
    assert arrete_referenced_ids - arrete_ids - {None} == set(), ''

    arrete_ids = _extract_unique_values(arretes_df['id'])
    arrete_referenced_ids = _extract_unique_values(arretes_df['enriched_from_id'])
    assert arrete_referenced_ids - arrete_ids - {None} == set(), ''


# All am, sections, alineas have different ids
# references exists (ref to original am, ref to am, ref to section)
