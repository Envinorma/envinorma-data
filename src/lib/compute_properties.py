import json
import os
import traceback
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from requests_oauthlib import OAuth2Session
from typing import List, Dict, Optional, Tuple, Union
from tqdm import tqdm

from lib.legifrance_API import get_current_loda_via_cid_response, get_legifrance_client
from lib.texts_properties import LegifranceText, TextProperties, compute_properties
from lib.am_structure_extraction import (
    ArreteMinisteriel,
    transform_arrete_ministeriel,
    load_legifrance_text,
    check_legifrance_dict,
    AMStructurationError,
)
from lib.aida import Hyperlink, Anchor


class Regime(Enum):
    A = 'A'
    E = 'E'
    D = 'D'
    DC = 'DC'


class ClassementState(Enum):
    ACTIVE = 'ACTIVE'
    SUPPRIMEE = 'SUPPRIMEE'


@dataclass
class Classement:
    rubrique: int
    regime: Regime
    alinea: Optional[str] = None
    state: Optional[ClassementState] = None


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


def load_classement(classement: Dict) -> Classement:
    dict_copy = classement.copy()
    dict_copy['regime'] = Regime(dict_copy['regime'])
    dict_copy['alinea'] = dict_copy.get('alinea')
    dict_copy['state'] = ClassementState(classement['state']) if 'state' in classement else None
    return Classement(**dict_copy)


def parse_aida_title_date(date_str: str) -> int:
    return int(datetime.strptime(date_str, '%d/%m/%y').timestamp())


def load_am_metadata(dict_: Dict) -> AMMetadata:
    dict_copy = dict_.copy()
    dict_copy['aida_page'] = str(dict_copy['aida_page'])
    dict_copy['state'] = AMState(dict_copy['state'])
    dict_copy['classements'] = [load_classement(classement) for classement in dict_['classements']]
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


def handle_am(
    metadata: AMMetadata, client: OAuth2Session, dump_am: bool = False
) -> Tuple[Optional[ArreteMinisteriel], AMStructurationLog]:
    api_result = _download_text_if_absent(metadata, client)
    if api_result:
        return None, AMStructurationLog(api_result)
    legifrance_text_json = json.load(open(_get_legifrance_filename(metadata)))
    lf_format_error = _extract_legifrance_format_error(legifrance_text_json)
    if lf_format_error:
        return None, AMStructurationLog(api_result, lf_format_error)
    legifrance_text = load_legifrance_text(legifrance_text_json)
    am, structuration_error = _structure_am(legifrance_text)
    if dump_am and am:
        write_json(am.as_dict(), _get_structured_am_filename(metadata))
    properties = compute_properties(legifrance_text, am)
    return am, AMStructurationLog(api_result, lf_format_error, structuration_error, properties)


def write_json(obj: Union[Dict, List], filename: str, safe: bool = False) -> None:
    if not safe:
        json.dump(obj, open(filename, 'w'), indent=4, sort_keys=True, ensure_ascii=False)
    try:
        json.dump(obj, open(filename, 'w'), indent=4, sort_keys=True, ensure_ascii=False)
    except Exception:  # pylint: disable=broad-except
        print(traceback.format_exc())


def handle_all_am(dump_log: bool = True) -> Tuple[Data, Dict[str, AMStructurationLog], Dict[str, ArreteMinisteriel]]:
    data = load_data()
    cid_to_log: Dict[str, AMStructurationLog] = {}
    cid_to_am: Dict[str, ArreteMinisteriel] = {}
    client = get_legifrance_client()
    for metadata in tqdm(data.arretes_ministeriels.metadata, 'Processsing AM...'):
        am, cid_to_log[metadata.cid] = handle_am(metadata, client)
        if am:
            cid_to_am[metadata.cid] = am
    if dump_log:
        write_json({cid: asdict(log) for cid, log in cid_to_log.items()}, 'data/AM/structuration_log.json', safe=True)
    return data, cid_to_log, cid_to_am

