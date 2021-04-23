from typing import Literal

from swiftclient.service import SwiftService, SwiftUploadObject

BucketName = Literal['ap']


def upload_document(bucket_name: BucketName, service: SwiftService, source: str, destination: str) -> None:
    remote = SwiftUploadObject(source, object_name=destination)
    service.upload(bucket_name, [remote])  # TODO: Check output


def _get_service() -> SwiftService:
    # source ../../../Downloads/openrc.sh first
    # enter pw
    service = SwiftService()
    # print(list(service.list())) # TODO: check ok
    return service


def _download_ocr_and_upload_document(georisques_id: str):
    ...
    # TODO
    # Download -> f1
    # from ocrmypdf import ocr
    # ocr(f1, f2, language=['fra'])
    # Upload f2
    # remove f1 and f2
