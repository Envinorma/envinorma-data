import random
import shutil
import tempfile
from functools import lru_cache
from typing import Dict, Iterable, List, Literal

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
    # source ../../../Downloads/openrc.sh first
    # enter pw
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
        ocr(input_filename, output_filename, language=['fra'], progress_bar=False)  # type: ignore
    except PriorOcrFoundError:
        pass  # no work to do


def _upload_to_ovh(filename: str, destination: str) -> None:
    _upload_document('ap', _get_service(), filename, destination)


def _ovh_filename(georisques_id: str) -> str:
    return f'{georisques_id}.pdf'


def _download_ocr_and_upload_document(georisques_id: str):
    with tempfile.NamedTemporaryFile() as file_:
        download_document(_url(georisques_id), file_.name)
        _ocr(file_.name, file_.name)
        _upload_to_ovh(file_.name, _ovh_filename(georisques_id))


def _file_exists(filename: str, bucket_name: BucketName, service: SwiftService) -> bool:
    results: List[Dict] = list(service.stat(bucket_name, [filename]))  # type: ignore
    return results[0]['success']


def _already_uploaded(georisques_id: str) -> bool:
    return _file_exists(_ovh_filename(georisques_id), 'ap', _get_service())


def _get_bucket_object_names(bucket: BucketName, service: SwiftService) -> List[str]:
    return [x['name'] for x in list(service.list(bucket))[0]['listing']]


def _get_uploaded_ap_files() -> List[str]:
    return _get_bucket_object_names('ap', _get_service())


def _compute_advancement() -> None:
    remote_filenames = set(_get_uploaded_ap_files())
    ids = load_all_georisques_ids()
    expected_filenames = {_ovh_filename(x) for x in ids}
    still_to_upload = len(expected_filenames - remote_filenames)
    print(f'Advancement: {len(expected_filenames) - still_to_upload}/{len(expected_filenames)}')


def run() -> None:
    ids = load_all_georisques_ids()
    random.shuffle(ids)

    for id_ in typed_tqdm(ids):
        if _already_uploaded(id_):
            continue
        try:
            _download_ocr_and_upload_document(id_)
        except Exception as exc:
            print(f'Error when processing {id_}:\n{exc}')


run()
# _compute_advancement()
