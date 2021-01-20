from lib.topics.topics import TOPIC_ONTOLOGY
from typing import Dict, Optional, Tuple

from back_office.utils import load_am, load_am_state, load_parametrization
from lib.am_enriching import (
    add_references,
    add_summary,
    add_table_inspection_sheet_data,
    detect_and_add_topics,
    remove_null_applicabilities,
)
from lib.data import AMMetadata, ArreteMinisteriel, add_metadata, load_am_data
from lib.manual_enrichments import get_manual_post_process
from lib.parametric_am import generate_all_am_versions
from lib.parametrization import Parametrization
from lib.paths import create_folder_and_generate_parametric_filename
from lib.utils import write_json

TEST_ID = 'JORFTEXT000023081678'

_AMVersions = Dict[Tuple[str, ...], ArreteMinisteriel]


def _apply_parametrization(
    am_id: str, am: Optional[ArreteMinisteriel], parametrization: Parametrization
) -> Optional[_AMVersions]:
    if not am:
        return
    enriched_am = remove_null_applicabilities(am)
    all_versions = generate_all_am_versions(enriched_am, parametrization)
    return {name: get_manual_post_process(am_id)(add_summary(am_), name) for name, am_ in all_versions.items()}


def add_enrichments(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    return remove_null_applicabilities(
        add_table_inspection_sheet_data(
            detect_and_add_topics(add_references(add_metadata(am, metadata)), TOPIC_ONTOLOGY)
        )
    )


def _enrich_am(am: Optional[ArreteMinisteriel], metadata: AMMetadata) -> Optional[ArreteMinisteriel]:
    if not am:
        return None
    return add_enrichments(am, metadata)


def _dump(am_id: str, versions: Optional[_AMVersions]) -> None:
    if not versions:
        return
    for version_desc, version in versions.items():
        filename = create_folder_and_generate_parametric_filename(am_id, version_desc)
        write_json(version.to_dict(), filename)


def _get_am_metadata(am_id: str) -> AMMetadata:
    ams = load_am_data()
    for metadata in ams.metadata:
        if metadata.cid == am_id:
            return metadata
    raise ValueError(f'AM {am_id} not found.')


def handle_am(am_id: str) -> Optional[ArreteMinisteriel]:
    metadata = _get_am_metadata(am_id)
    cid = metadata.cid
    am_state = load_am_state(cid)
    am = load_am(cid, am_state)
    am = _enrich_am(am, metadata)
    parametrization = load_parametrization(cid, am_state)
    am_versions = _apply_parametrization(cid, am, parametrization)
    _dump(cid, am_versions)
    return am