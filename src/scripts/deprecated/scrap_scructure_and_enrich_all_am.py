import json
import os
import random
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from warnings import warn

from envinorma.am_enriching import (
    add_references,
    add_summary,
    add_table_inspection_sheet_data,
    detect_and_add_topics,
    remove_null_applicabilities,
)
from envinorma.config import AM_DATA_FOLDER, config
from envinorma.data import (
    AidaData,
    AMMetadata,
    AMStructurationLog,
    Anchor,
    ArreteMinisteriel,
    Data,
    Hyperlink,
    LegifranceAPIError,
    LegifranceText,
    LegifranceTextFormatError,
    StructurationError,
    add_metadata,
    check_am,
    load_am_data,
    load_legifrance_text,
)
from envinorma.data_build.manual_enrichments import (
    get_manual_combinations,
    get_manual_enricher,
    get_manual_parametrization,
    get_manual_post_process,
)
from envinorma.io.markdown import am_to_markdown
from envinorma.parametrization import Parametrization, add_am_signatures
from envinorma.parametrization.parametric_am import check_parametrization_is_still_valid, generate_all_am_versions
from envinorma.paths import (
    create_folder_and_generate_parametric_filename,
    generate_parametric_descriptor,
    get_enriched_am_filename,
    get_legifrance_filename,
    get_parametrization_filename,
    get_structured_am_filename,
)
from envinorma.structure.am_structure_extraction import (
    AMStructurationError,
    check_legifrance_dict,
    transform_arrete_ministeriel,
)
from envinorma.structure.texts_properties import compute_am_diffs, compute_am_signatures, compute_texts_properties
from envinorma.topics.topics import TOPIC_ONTOLOGY
from envinorma.utils import write_json
from legifrance.legifrance_API import get_current_loda_via_cid_response, get_legifrance_client
from requests_oauthlib import OAuth2Session
from tqdm import tqdm


def parse_aida_title_date(date_str: str) -> int:
    return int(datetime.strptime(date_str, '%d/%m/%y').timestamp())


def load_aida_data() -> AidaData:
    page_id_to_links = json.load(open('data/aida/hyperlinks/page_id_to_links.json'))
    page_id_to_anchors = json.load(open('data/aida/hyperlinks/page_id_to_anchors.json'))
    links = {
        aida_page: [Hyperlink(**link_doc) for link_doc in link_docs]
        for aida_page, link_docs in page_id_to_links.items()
    }
    anchors = {
        aida_page: [Anchor(**anchor_doc) for anchor_doc in anchor_docs]
        for aida_page, anchor_docs in page_id_to_anchors.items()
    }
    return AidaData(links, anchors)


def load_data() -> Data:
    return Data(load_aida_data(), load_am_data())


def _download_text_if_absent(metadata: AMMetadata, client: OAuth2Session) -> Optional[LegifranceAPIError]:
    filename = get_legifrance_filename(metadata.id)
    if os.path.exists(filename):
        return None
    response = get_current_loda_via_cid_response(metadata.cid, client)
    if 200 <= response.status_code < 300:
        write_json(response.json(), filename)
        return None
    return LegifranceAPIError(response.status_code, response.content.decode())


def _extract_legifrance_format_error(legifrance_text_json: Dict) -> Optional[LegifranceTextFormatError]:
    try:
        check_legifrance_dict(legifrance_text_json)
    except AMStructurationError as exc:
        print(exc)
        return LegifranceTextFormatError(str(exc), traceback.format_exc())
    return None


def _structure_am(
    cid: str, legifrance_text: LegifranceText
) -> Tuple[Optional[ArreteMinisteriel], Optional[StructurationError]]:
    try:
        random.seed(legifrance_text.title)  # avoid changing ids
        am = transform_arrete_ministeriel(legifrance_text)
        am.id = cid
        return am, None
    except Exception as exc:  # pylint: disable=broad-except
        print(exc)
        return None, StructurationError(str(exc), traceback.format_exc())


_ParametricAM = Tuple[Parametrization, Dict[str, List[str]]]


def _check_parametrization_not_deprecated(am: ArreteMinisteriel, am_id: str) -> None:
    filename = get_parametrization_filename(am_id)
    if not os.path.exists(filename):
        return
    previous_parametrization = Parametrization.from_dict(json.load(open(filename)))
    if not previous_parametrization.signatures:
        warn(f'Parametrization of AM with id {am_id} has no signatures, this should happen only once!')
        return
    is_valid, warnings = check_parametrization_is_still_valid(previous_parametrization, am)
    if not is_valid:
        raise ValueError(f'Parametrization of AM with id {am_id} is not valid. Change log: {warnings}')


def _handle_manual_enrichments(
    am: ArreteMinisteriel, am_id: str, dump_am: bool
) -> Tuple[ArreteMinisteriel, _ParametricAM]:
    enriched_am = remove_null_applicabilities(get_manual_enricher(am_id)(am))
    if dump_am:
        write_json(enriched_am.to_dict(), get_enriched_am_filename(am_id))
    parametrization = get_manual_parametrization(am_id)
    _check_parametrization_not_deprecated(am, am_id)
    if dump_am:
        parametrization = add_am_signatures(parametrization, compute_am_signatures(am))
        write_json(parametrization.to_dict(), get_parametrization_filename(am_id))
    all_versions = generate_all_am_versions(enriched_am, parametrization, True, get_manual_combinations(am_id))
    if dump_am:
        all_versions_with_summary = {
            name: get_manual_post_process(am_id)(add_summary(am_), name) for name, am_ in all_versions.items()
        }
        for version_desc, version in all_versions_with_summary.items():
            filename = create_folder_and_generate_parametric_filename(am_id, version_desc)
            write_json(version.to_dict(), filename)
    diffs = {
        generate_parametric_descriptor(desc): compute_am_diffs(am, modified_version, am_to_markdown)
        for desc, modified_version in all_versions.items()
    }
    return am, (parametrization, diffs)


def _enrich_am(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    return add_table_inspection_sheet_data(
        detect_and_add_topics(add_references(add_metadata(am, metadata)), TOPIC_ONTOLOGY)
    )


def handle_am(
    metadata: AMMetadata, client: OAuth2Session, dump_am: bool = False, with_manual_enrichments: bool = False
) -> Tuple[Optional[ArreteMinisteriel], AMStructurationLog, Optional[_ParametricAM]]:
    api_result = _download_text_if_absent(metadata, client)
    if api_result:
        return None, AMStructurationLog(api_result), None
    legifrance_text_json = json.load(open(get_legifrance_filename(metadata.id)))
    lf_format_error = _extract_legifrance_format_error(legifrance_text_json)
    if lf_format_error:
        return None, AMStructurationLog(api_result, lf_format_error), None
    legifrance_text = load_legifrance_text(legifrance_text_json)
    am, structuration_error = _structure_am(metadata.cid, legifrance_text)
    if am:
        check_am(am)
        am = _enrich_am(am, metadata)
        check_am(am)
    if dump_am and am:
        write_json(am.to_dict(), get_structured_am_filename(metadata.id))
    properties = compute_texts_properties(legifrance_text, am)
    parametric_am = None
    if am and with_manual_enrichments:
        am, parametric_am = _handle_manual_enrichments(am, metadata.id, dump_am)
        check_am(am)
    return am, AMStructurationLog(api_result, lf_format_error, structuration_error, properties), parametric_am


_ParametricAMs = Dict[str, _ParametricAM]
_AMStructurationLogs = Dict[str, AMStructurationLog]
_ArreteMinisteriels = Dict[str, ArreteMinisteriel]


def _ensure_metadata(obj: Any) -> AMMetadata:
    if not isinstance(obj, AMMetadata):
        raise ValueError(f'Wrong type {type(obj)}')
    return obj


def handle_all_am(
    dump_log: bool = True,
    dump_am: bool = False,
    am_cids: Optional[Set[str]] = None,
    with_manual_enrichments: bool = False,
) -> Tuple[Data, _AMStructurationLogs, _ArreteMinisteriels, _ParametricAMs]:
    data = load_data()
    cid_to_log: _AMStructurationLogs = {}
    cid_to_am: _ArreteMinisteriels = {}
    cid_to_param: _ParametricAMs = {}
    client = get_legifrance_client(config.legifrance.client_id, config.legifrance.client_secret)
    am_cids = am_cids or set()
    for metadata in tqdm(data.arretes_ministeriels.metadata, 'Processsing AM...'):
        metadata = _ensure_metadata(metadata)
        if am_cids and metadata.cid not in am_cids:
            continue
        am, cid_to_log[metadata.cid], param_am = handle_am(metadata, client, dump_am, with_manual_enrichments)
        if am:
            cid_to_am[metadata.cid] = am
        if param_am:
            cid_to_param[metadata.cid] = param_am
    if dump_log and not am_cids:
        write_json(
            {cid: log.to_dict() for cid, log in cid_to_log.items()},
            f'{AM_DATA_FOLDER}/structuration_log.json',
            safe=True,
        )
    return data, cid_to_log, cid_to_am, cid_to_param


if __name__ == '__main__':
    random.seed(0)  # to avoid having different ids
    # am_cids = {'JORFTEXT000038358856', 'JORFTEXT000000369330', 'JORFTEXT000000552021', 'JORFTEXT000034429274'}
    am_cids = None  # all_am
    handle_all_am(True, True, am_cids, True)
