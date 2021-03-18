import json
import os
import shutil
import zipfile
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import requests

from ap_exploration.models import ArretePrefectoral
from envinorma.config import config
from envinorma.data.text_elements import Title
from envinorma.data_build.georisques_data import GR_DOC_BASE_URL
from envinorma.io.alto import AltoFile, AltoPage
from envinorma.io.open_document import elements_to_open_document
from envinorma.utils import write_json

_AP_FOLDER = config.storage.ap_data_folder


def _get_ap_zip_path() -> str:
    to_replace = 'ap_exploration/db/ap.py'
    if to_replace not in __file__:
        raise ValueError(f'Expecting {to_replace} to be in {__file__}')
    return __file__.replace(to_replace, 'ap_exploration/db/ap.zip')


def _unzip_ap_folder_if_empty():
    path = _get_ap_zip_path()
    if not os.listdir(_AP_FOLDER):
        with zipfile.ZipFile(path, 'r') as zip_ref:
            zip_ref.extractall(_AP_FOLDER)
            for child in os.listdir(os.path.join(_AP_FOLDER, 'seed')):
                shutil.copytree(os.path.join(_AP_FOLDER, 'seed', child), os.path.join(_AP_FOLDER, child))


_unzip_ap_folder_if_empty()


def _get_ap_sample_path() -> str:
    to_replace = 'ap_exploration/db/ap.py'
    if to_replace not in __file__:
        raise ValueError(f'Expecting {to_replace} to be in {__file__}')
    return __file__.replace(to_replace, 'ap_exploration/db/gr_ap_sample.json')


def _check_georisques_url(url: str) -> None:
    pieces = url.split('/')
    if len(pieces) != 3:
        raise ValueError(f'Expecting two "/" in url, got {url}')
    if not pieces[-1].endswith('.pdf'):
        raise ValueError(f'Expecting url to end with ".pdf", got {url}')


def georisques_url_to_document_id(georisques_url: str) -> str:
    _check_georisques_url(georisques_url)
    return '_'.join(georisques_url.split('/'))[:-4]


def _check_georisques_document_id(document_id: str) -> None:
    pieces = document_id.split('_')
    if len(pieces) != 3:
        raise ValueError(f'Expecting two "_" in document_id, got {document_id}')


def georisques_document_id_to_url(document_id: str) -> str:
    _check_georisques_document_id(document_id)
    return '/'.join(document_id.split('_')) + '.pdf'


def georisques_full_url(document_id: str) -> str:
    return GR_DOC_BASE_URL + '/' + georisques_document_id_to_url(document_id)


def seems_georisques_document_id(document_id: str) -> bool:
    if len(document_id) != 36:
        return False
    if set(document_id[4:]) - set('abcdef0123456789'):
        return False
    if document_id[1] != '_' or document_id[3] != '_':
        return False
    return True


SAMPLE_DOC_IDS = [georisques_url_to_document_id(x) for x in json.load(open(_get_ap_sample_path()))]


@dataclass
class OCRProcessingStep:
    messsage: Optional[str]
    advancement: float
    done: bool

    def __post_init__(self) -> None:
        assert 0 <= self.advancement <= 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'OCRProcessingStep':
        return cls(**dict_)


@dataclass
class APExtractionStep:
    messsage: Optional[str]
    advancement: float
    done: bool

    def __post_init__(self) -> None:
        assert 0 <= self.advancement <= 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'APExtractionStep':
        return cls(**dict_)


def _document_folder(document_id: str) -> str:
    return os.path.join(_AP_FOLDER, document_id)


def _step_path(document_id: str) -> str:
    return os.path.join(_document_folder(document_id), 'step.json')


def _ap_extraction_step_path(document_id: str) -> str:
    return os.path.join(_document_folder(document_id), 'ap_step.json')


def input_pdf_path(document_id: str) -> str:
    return os.path.join(_document_folder(document_id), 'in.pdf')


def svg_path(document_id: str) -> str:
    return os.path.join(_document_folder(document_id), 'out.svg')


def alto_xml_path(document_id: str) -> str:
    return os.path.join(_document_folder(document_id), 'out.xml')


def _get_ap_path(document_id: str) -> str:
    return os.path.join(_document_folder(document_id), 'ap.json')


def ap_odt_path(document_id: str) -> str:
    return os.path.join(_document_folder(document_id), 'ap.odt')


def _load_json(path: str):
    with open(path, 'r') as file_:
        return json.load(file_)


def load_processing_step(document_id: str) -> OCRProcessingStep:
    return OCRProcessingStep.from_dict(_load_json(_step_path(document_id)))


def has_processing_step(document_id: str) -> bool:
    return os.path.exists(_step_path(document_id))


def dump_processing_step(step: OCRProcessingStep, document_id: str):
    return write_json(step.to_dict(), _step_path(document_id))


def load_ap_extraction_step(document_id: str) -> APExtractionStep:
    return APExtractionStep.from_dict(_load_json(_ap_extraction_step_path(document_id)))


def has_ap_extraction_step(document_id: str) -> bool:
    return os.path.exists(_ap_extraction_step_path(document_id))


def dump_ap_extraction_step(step: APExtractionStep, document_id: str):
    return write_json(step.to_dict(), _ap_extraction_step_path(document_id))


def load_alto_pages_xml(document_id: str) -> List[str]:
    return _load_json(alto_xml_path(document_id))


def dump_alto_pages_xml(xml: List[str], document_id: str) -> None:
    write_json(xml, alto_xml_path(document_id))


def _ensure_one_page_and_get_it(alto: AltoFile) -> AltoPage:
    if len(alto.layout.pages) != 1:
        raise ValueError(f'Expecting exactly one page, got {len(alto.layout.pages)}')
    return alto.layout.pages[0]


def load_alto_pages(document_id: str) -> List[AltoPage]:
    step = load_processing_step(document_id)
    if not step.done:
        raise ValueError(f'Cannot load alto pages: processing not done yet. (OCRProcessingStep={step})')
    pages = load_alto_pages_xml(document_id)
    return [_ensure_one_page_and_get_it(AltoFile.from_xml(page)) for page in pages]


def _create_folder_if_inexistent(folder: str) -> None:
    if not os.path.exists(folder):
        os.mkdir(folder)


def download_georisques_document(document_id: str) -> None:
    _create_folder_if_inexistent(_document_folder(document_id))
    output_filename = input_pdf_path(document_id)
    download_document(georisques_full_url(document_id), output_filename)


def download_document(url: str, output_filename: str) -> None:
    req = requests.get(url, stream=True)
    if req.status_code == 200:
        with open(output_filename, 'wb') as f:
            req.raw.decode_content = True
            shutil.copyfileobj(req.raw, f)


def _pdf_exists(document_id: str) -> bool:
    return os.path.exists(os.path.join(_AP_FOLDER, document_id, 'in.pdf'))


def load_document_ids() -> List[str]:
    return [x for x in os.listdir(_AP_FOLDER) if _pdf_exists(x)]


def _ap_exists(document_id: str) -> bool:
    return os.path.exists(os.path.join(_AP_FOLDER, document_id, 'ap.json'))


def load_document_ids_having_ap() -> List[str]:
    return [x for x in os.listdir(_AP_FOLDER) if _ap_exists(x)]


def save_document(document_id: str, content: bytes) -> None:
    _create_folder_if_inexistent(_document_folder(document_id))
    path = input_pdf_path(document_id)
    with open(path, 'wb') as file_:
        file_.write(content)


def dump_ap(ap: ArretePrefectoral, document_id: str):
    return write_json(ap.to_dict(), _get_ap_path(document_id))


def load_ap(document_id: str) -> ArretePrefectoral:
    return ArretePrefectoral.from_dict(_load_json(_get_ap_path(document_id)))


def _ap_to_odt_file(ap: ArretePrefectoral, filename: str) -> None:
    all_text_elements = [Title(ap.title, 1), *ap.visas_considerant, *ap.content]
    elements_to_open_document(all_text_elements).write(filename)


def dump_ap_odt(ap: ArretePrefectoral, document_id: str):
    return _ap_to_odt_file(ap, ap_odt_path(document_id))
