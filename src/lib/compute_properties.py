import json
from lib.parametrization import Parametrization
from lib.manual_enrichments import get_manual_combinations, get_manual_enricher, get_manual_parametrization
from lib.parametric_am import generate_all_am_versions
from lib.am_enriching import add_references, remove_null_applicabilities
import os
import traceback
from copy import copy
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple, Union

from requests_oauthlib import OAuth2Session
from tqdm import tqdm

from lib.aida import Hyperlink, Anchor
from lib.data import Classement, check_am
from lib.legifrance_API import get_current_loda_via_cid_response, get_legifrance_client
from lib.texts_properties import LegifranceText, TextProperties, compute_am_diffs, compute_properties
from lib.am_structure_extraction import (
    ArreteMinisteriel,
    transform_arrete_ministeriel,
    load_legifrance_text,
    check_legifrance_dict,
    AMStructurationError,
)


class AMState(Enum):
    VIGUEUR = 'VIGUEUR'
    ABROGE = 'ABROGE'


@dataclass
class AMMetadata:
    cid: str
    aida_page: str
    page_name: str
    short_title: str
    classements: List[Classement]
    state: AMState
    publication_date: int
    nor: Optional[str] = None


@dataclass
class AMData:
    metadata: List[AMMetadata]
    nor_to_aida: Dict[str, str]
    aida_to_nor: Dict[str, str]


@dataclass
class AidaData:
    page_id_to_links: Dict[str, List[Hyperlink]]
    page_id_to_anchors: Dict[str, List[Anchor]]


@dataclass
class Data:
    aida: AidaData
    arretes_ministeriels: AMData


def parse_aida_title_date(date_str: str) -> int:
    return int(datetime.strptime(date_str, '%d/%m/%y').timestamp())


def load_am_metadata(dict_: Dict) -> AMMetadata:
    dict_copy = dict_.copy()
    dict_copy['aida_page'] = str(dict_copy['aida_page'])
    dict_copy['state'] = AMState(dict_copy['state'])
    dict_copy['classements'] = [Classement.from_dict(classement) for classement in dict_['classements']]
    return AMMetadata(**dict_copy)


def load_am_data() -> AMData:
    arretes_ministeriels = [load_am_metadata(x) for x in json.load(open('data/AM/arretes_ministeriels.json'))]
    nor_to_aida = {doc.nor: doc.aida_page for doc in arretes_ministeriels if doc.nor}
    aida_to_nor = {value: key for key, value in nor_to_aida.items()}
    return AMData(arretes_ministeriels, nor_to_aida, aida_to_nor)


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


@dataclass
class LegifranceAPIError:
    status_code: int
    content: str


@dataclass
class LegifranceTextFormatError:
    message: str
    stacktrace: str


@dataclass
class StructurationError:
    message: str
    stacktrace: str


@dataclass
class AMStructurationLog:
    legifrance_api_error: Optional[LegifranceAPIError] = None
    legifrance_text_format_error: Optional[LegifranceTextFormatError] = None
    structuration_error: Optional[StructurationError] = None
    properties: Optional[TextProperties] = None


def get_text_defined_id(text: AMMetadata) -> str:
    return text.nor or text.cid


def _get_legifrance_filename(metadata: AMMetadata) -> str:
    id_ = get_text_defined_id(metadata)
    return f'data/AM/legifrance_texts/{id_}.json'


def _get_structured_am_filename(metadata: AMMetadata) -> str:
    id_ = get_text_defined_id(metadata)
    return f'data/AM/structured_texts/{id_}.json'


def _get_parametrization_filename(metadata: AMMetadata) -> str:
    id_ = get_text_defined_id(metadata)
    return f'data/AM/parametrizations/{id_}.json'


def _get_enriched_am_filename(metadata: AMMetadata) -> str:
    id_ = get_text_defined_id(metadata)
    return f'data/AM/enriched_texts/{id_}.json'


def _get_parametric_ams_folder(metadata: AMMetadata) -> str:
    id_ = get_text_defined_id(metadata)
    return f'data/AM/parametric_texts/{id_}'


def _download_text_if_absent(metadata: AMMetadata, client: OAuth2Session) -> Optional[LegifranceAPIError]:
    filename = _get_legifrance_filename(metadata)
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
        return LegifranceTextFormatError(str(exc), traceback.format_exc())
    return None


def _structure_am(legifrance_text: LegifranceText) -> Tuple[Optional[ArreteMinisteriel], Optional[StructurationError]]:
    try:
        am = transform_arrete_ministeriel(legifrance_text)
        return am, None
    except Exception as exc:  # pylint: disable=broad-except
        return None, StructurationError(str(exc), traceback.format_exc())


_LEGIFRANCE_LODA_BASE_URL = 'https://www.legifrance.gouv.fr/loda/id/'


def _build_legifrance_url(cid: str) -> str:
    return _LEGIFRANCE_LODA_BASE_URL + cid


_AIDA_BASE_URL = 'https://aida.ineris.fr/consultation_document/'


def _build_aida_url(page: str) -> str:
    return _AIDA_BASE_URL + page


def _add_metadata(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    am = copy(am)
    am.legifrance_url = _build_legifrance_url(metadata.cid)
    am.aida_url = _build_aida_url(metadata.aida_page)
    am.classements = metadata.classements
    return am


def _generate_parametric_descriptor(version_descriptor: Tuple[str, ...]) -> str:
    if not version_descriptor:
        return 'unique_version'
    return '_AND_'.join(version_descriptor).replace(' ', '_')


def _generate_parametric_filename(metadata: AMMetadata, version_descriptor: Tuple[str, ...]) -> str:
    return _get_parametric_ams_folder(metadata) + '/' + _generate_parametric_descriptor(version_descriptor) + '.json'


_ParametricAM = Tuple[Parametrization, Dict[str, List[str]]]


def _handle_manual_enrichments(
    am: ArreteMinisteriel, metadata: AMMetadata, dump_am: bool
) -> Tuple[ArreteMinisteriel, _ParametricAM]:
    id_ = get_text_defined_id(metadata)
    enriched_am = remove_null_applicabilities(get_manual_enricher(id_)(am))
    if dump_am:
        write_json(enriched_am.to_dict(), _get_enriched_am_filename(metadata))
    parametrization = get_manual_parametrization(id_)
    if dump_am:
        write_json(parametrization.to_dict(), _get_parametrization_filename(metadata))
    all_versions = generate_all_am_versions(enriched_am, parametrization, get_manual_combinations(id_))
    if dump_am:
        for version_desc, version in all_versions.items():
            filename = _generate_parametric_filename(metadata, version_desc)
            write_json(version.to_dict(), filename)
    diffs = {
        _generate_parametric_descriptor(desc): compute_am_diffs(am, modified_version)
        for desc, modified_version in all_versions.items()
    }
    return am, (parametrization, diffs)


def handle_am(
    metadata: AMMetadata, client: OAuth2Session, dump_am: bool = False, with_manual_enrichments: bool = False
) -> Tuple[Optional[ArreteMinisteriel], AMStructurationLog, Optional[_ParametricAM]]:
    api_result = _download_text_if_absent(metadata, client)
    if api_result:
        return None, AMStructurationLog(api_result), None
    legifrance_text_json = json.load(open(_get_legifrance_filename(metadata)))
    lf_format_error = _extract_legifrance_format_error(legifrance_text_json)
    if lf_format_error:
        return None, AMStructurationLog(api_result, lf_format_error), None
    legifrance_text = load_legifrance_text(legifrance_text_json)
    am, structuration_error = _structure_am(legifrance_text)
    if am:
        check_am(am)
        am = add_references(_add_metadata(am, metadata))
        check_am(am)
    if dump_am and am:
        write_json(am.to_dict(), _get_structured_am_filename(metadata))
    properties = compute_properties(legifrance_text, am)
    parametric_am = None
    if am and with_manual_enrichments:
        am, parametric_am = _handle_manual_enrichments(am, metadata, dump_am)
        check_am(am)
    return am, AMStructurationLog(api_result, lf_format_error, structuration_error, properties), parametric_am


def write_json(obj: Union[Dict, List], filename: str, safe: bool = False) -> None:
    if not safe:
        json.dump(obj, open(filename, 'w'), indent=4, sort_keys=True, ensure_ascii=False)
    else:
        try:
            json.dump(obj, open(filename, 'w'), indent=4, sort_keys=True, ensure_ascii=False)
        except Exception:  # pylint: disable=broad-except
            print(traceback.format_exc())


_ParametricAMs = Dict[str, _ParametricAM]
_AMStructurationLogs = Dict[str, AMStructurationLog]
_ArreteMinisteriels = Dict[str, ArreteMinisteriel]


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
    client = get_legifrance_client()
    am_cids = am_cids or set()
    for metadata in tqdm(data.arretes_ministeriels.metadata, 'Processsing AM...'):
        if am_cids and metadata.cid not in am_cids:
            continue
        am, cid_to_log[metadata.cid], param_am = handle_am(metadata, client, dump_am, with_manual_enrichments)
        if am:
            cid_to_am[metadata.cid] = am
        if param_am:
            cid_to_param[metadata.cid] = param_am
    if dump_log and not am_cids:
        write_json({cid: asdict(log) for cid, log in cid_to_log.items()}, 'data/AM/structuration_log.json', safe=True)
    return data, cid_to_log, cid_to_am, cid_to_param
