'''
Script for retrieving the list of ICPE documents
'''
import os
import random
from typing import List
from urllib.request import HTTPError, urlretrieve  # type: ignore

from tqdm import tqdm

from envinorma.data.document import Document, DocumentType
from envinorma.data_build.build.build_documents import load_documents
from envinorma.data_build.filenames import CQUEST_URL, DOCUMENTS_FOLDER, GEORISQUES_DOWNLOAD_URL

_BAR_FORMAT = '{l_bar}{r_bar}'


def _download_file_if_doesnt_exist(source: str, destination: str) -> bool:
    if os.path.exists(destination):
        print('file exists')
        return False
    try:
        urlretrieve(source, destination)
    except HTTPError as exc:
        print(source, exc)
        return True
    return False


def _download_document(url: str) -> None:
    full_url = CQUEST_URL + '/' + url
    destination = DOCUMENTS_FOLDER + '/' + url.replace('/', '_')
    found = _download_file_if_doesnt_exist(full_url, destination)
    if not found:
        print('Not found, attempting georisques.')
        source_georisques = GEORISQUES_DOWNLOAD_URL + '/' + url
        _download_file_if_doesnt_exist(source_georisques, destination)


def _download_documents(documents: List[Document]) -> None:
    for doc in tqdm(documents, 'Downloading documents.', bar_format=_BAR_FORMAT):
        _download_document(doc.url_doc)


if __name__ == '__main__':
    ALL_DOCS = [doc for doc in load_documents('all') if doc.type == DocumentType.AP]
    _download_documents(random.sample(ALL_DOCS, 100))
