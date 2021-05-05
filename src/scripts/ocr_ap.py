import random
import re
import shutil
import tempfile
import traceback
from functools import lru_cache
from typing import Dict, List, Literal, Set, Tuple

import requests
from ocrmypdf import Verbosity, configure_logging, ocr
from ocrmypdf.exceptions import PriorOcrFoundError
from swiftclient.service import SwiftService, SwiftUploadObject

from envinorma.data.load import load_all_georisques_ids
from envinorma.utils import typed_tqdm

GEORISQUES_DOWNLOAD_URL = 'http://documents.installationsclassees.developpement-durable.gouv.fr/commun'
BucketName = Literal['ap']
configure_logging(Verbosity.quiet)


def _check_upload(results: List[Dict]) -> None:
    for result in results:
        if not result.get('success'):
            raise ValueError(f'Failed Uploading document. Response:\n{result}')


def _upload_document(bucket_name: BucketName, service: SwiftService, source: str, destination: str) -> None:
    remote = SwiftUploadObject(source, object_name=destination)
    result = list(service.upload(bucket_name, [remote]))
    _check_upload(result)


def _check_auth(service: SwiftService) -> None:
    services = list(service.list())
    if len(services) != 1:
        return
    error = services[0].get('error')
    traceback = services[0].get('traceback')
    if error:
        raise ValueError(f'Probable error in authentication: {error}\n{traceback}')
    print('Service successfully started.')


@lru_cache
def _get_service() -> SwiftService:
    service = SwiftService()
    _check_auth(service)
    return service


def download_document(url: str, output_filename: str) -> None:
    req = requests.get(url, stream=True)
    if req.status_code == 200:
        with open(output_filename, 'wb') as f:
            req.raw.decode_content = True
            shutil.copyfileobj(req.raw, f)
    else:
        raise ValueError(f'Error when downloading document: {req.content.decode()}')


def _url(georisques_id: str) -> str:
    return f'{GEORISQUES_DOWNLOAD_URL}/{georisques_id}.pdf'


def _ocr(input_filename: str, output_filename: str) -> None:
    try:
        ocr(input_filename, output_filename, language=['fra'], progress_bar=False, jobs=1)  # type: ignore
    except PriorOcrFoundError:
        pass  # no work to do


def _upload_to_ovh(filename: str, destination: str) -> None:
    _upload_document('ap', _get_service(), filename, destination)


def _ovh_filename(georisques_id: str) -> str:
    return f'{georisques_id}.pdf'


def _ovh_error_filename(georisques_id: str) -> str:
    return f'{georisques_id}.error.txt'


def _download_ocr_and_upload_document(georisques_id: str):
    with tempfile.NamedTemporaryFile() as file_:
        download_document(_url(georisques_id), file_.name)
        _ocr(file_.name, file_.name)
        _upload_to_ovh(file_.name, _ovh_filename(georisques_id))


def _upload_error_file(georisques_id: str, error: str):
    with tempfile.NamedTemporaryFile(mode='w') as file_:
        file_.write(error)
        _upload_to_ovh(file_.name, _ovh_error_filename(georisques_id))


def _file_exists(filename: str, bucket_name: BucketName, service: SwiftService) -> bool:
    results: List[Dict] = list(service.stat(bucket_name, [filename]))  # type: ignore
    return results[0]['success']


def _file_already_processed(georisques_id: str) -> bool:
    ocred_file_exists = _file_exists(_ovh_filename(georisques_id), 'ap', _get_service())
    error_file_exists = _file_exists(_ovh_error_filename(georisques_id), 'ap', _get_service())
    return ocred_file_exists or error_file_exists


def _get_bucket_object_names(bucket: BucketName, service: SwiftService) -> List[str]:
    lists = list(service.list(bucket))
    return [x['name'] for list_ in lists for x in list_['listing']]


def _get_uploaded_ap_files() -> List[str]:
    return _get_bucket_object_names('ap', _get_service())


def _compute_advancement() -> None:
    ids_with_statuses = _fetch_already_processed_ids_with_statuses()
    error_ids = {id_ for id_, status in ids_with_statuses if status == 'error'}
    success_ids = {id_ for id_, status in ids_with_statuses if status == 'success'}
    all_ids = set(load_all_georisques_ids())
    print(f'Advancement: {len(error_ids | success_ids)}/{len(all_ids)}')
    print(f'Nb errors: {len(error_ids)}')


_GEORISQUES_ID_REGEXP = re.compile(r'^[A-Z]{1}/[a-f0-9]{1}/[a-f0-9]{32}')

_OCRStatus = Literal['error', 'success']


def _extract_status(file_extension: str) -> _OCRStatus:
    if file_extension == 'pdf':
        return 'success'
    if file_extension == 'error.txt':
        return 'error'
    raise ValueError(f'Unexpected file extension {file_extension}')


def _extract_id_and_status(filename: str) -> Tuple[str, _OCRStatus]:
    assert re.match(_GEORISQUES_ID_REGEXP, filename), f'filename {filename} does not contain id.'
    georisques_id, *extension = filename.split('.')
    return georisques_id, _extract_status('.'.join(extension))


def _extract_ids_and_statuses(filenames: Set[str]) -> Set[Tuple[str, _OCRStatus]]:
    return {_extract_id_and_status(filename) for filename in filenames if re.match(_GEORISQUES_ID_REGEXP, filename)}


def _fetch_already_processed_ids_with_statuses() -> Set[Tuple[str, _OCRStatus]]:
    remote_filenames = set(_get_uploaded_ap_files())
    return _extract_ids_and_statuses(remote_filenames)


def _fetch_already_processed_ids() -> Set[str]:
    return {id_ for id_, _ in _fetch_already_processed_ids_with_statuses()}


def _load_remaining_ids() -> List[str]:
    already_processed_ids = _fetch_already_processed_ids()
    ids_to_process = set(load_all_georisques_ids())
    return list(ids_to_process - already_processed_ids)


def run() -> None:
    ids = _load_remaining_ids()
    random.shuffle(ids)

    for id_ in typed_tqdm(ids):
        if _file_already_processed(id_):
            continue
        try:
            _download_ocr_and_upload_document(id_)
        except Exception:
            error = traceback.format_exc()
            _upload_error_file(id_, error)
            print(f'Error when processing {id_}:\n{error}')


if __name__ == '__main__':
    run()
    # _compute_advancement()
