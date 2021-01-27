from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from back_office.fetch_data import load_initial_am, load_parametrization, load_structured_am

from lib.am_enriching import (
    add_references,
    add_summary,
    add_table_inspection_sheet_data,
    detect_and_add_topics,
    remove_null_applicabilities,
)
from lib.data import AMMetadata, ArreteMinisteriel, add_metadata
from lib.manual_enrichments import get_manual_post_process
from lib.parametric_am import generate_all_am_versions
from lib.parametrization import Parametrization
from lib.topics.topics import TOPIC_ONTOLOGY

AMVersions = Dict[Tuple[str, ...], ArreteMinisteriel]


def _apply_parametrization(
    am_id: str, am: Optional[ArreteMinisteriel], parametrization: Parametrization
) -> Optional[AMVersions]:
    if not am:
        return
    enriched_am = remove_null_applicabilities(am)
    all_versions = generate_all_am_versions(enriched_am, parametrization)
    return {name: get_manual_post_process(am_id)(add_summary(am_), name) for name, am_ in all_versions.items()}


def _add_enrichments(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    return remove_null_applicabilities(
        add_table_inspection_sheet_data(
            detect_and_add_topics(add_references(add_metadata(am, metadata)), TOPIC_ONTOLOGY)
        )
    )


def _enrich_am(am: Optional[ArreteMinisteriel], metadata: AMMetadata) -> Optional[ArreteMinisteriel]:
    if not am:
        return None
    return _add_enrichments(am, metadata)


@dataclass
class FinalAM:
    base_am: Optional[ArreteMinisteriel]
    am_versions: Optional[AMVersions]


def generate_final_am(metadata: AMMetadata) -> FinalAM:
    cid = metadata.cid
    am = load_structured_am(cid) or load_initial_am(cid)
    if not am:
        raise ValueError('Expecting one AM to proceed.')
    am = _enrich_am(am, metadata)
    parametrization = load_parametrization(cid) or Parametrization([], [])
    am_versions = _apply_parametrization(cid, am, parametrization)
    return FinalAM(base_am=am, am_versions=am_versions)
