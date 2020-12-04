import os
import json
import requests
import random
from typing import List
from tqdm import tqdm
from urllib.request import urlretrieve, HTTPError

from lib.utils import write_json
from lib.georisques_data import DocumentType, GRDocument, load_all_documents

_DATA_FOLDER = '/Users/remidelbouys/EnviNorma/brouillons/data'
_DOCUMENTS_FOLDER = '/Users/remidelbouys/EnviNorma/brouillons/data/icpe_documents'
_GEORISQUES_URL = 'https://www.georisques.gouv.fr/webappReport/ws'
_BAR_FORMAT = '{l_bar}{r_bar}'
_CQUEST_URL = 'http://data.cquest.org/icpe/commun'
_GEORISQUES_DOWNLOAD_URL = 'http://documents.installationsclassees.developpement-durable.gouv.fr/commun'


def _load_icpe_ids() -> List[str]:
    data = json.load(open(f'{_DATA_FOLDER}/icpe.geojson'))
    return [doc['properties']['code_s3ic'].replace('.', '-') for doc in data['features']]


def _download_georisques_document_references():
    ids = _load_icpe_ids()
    filename = f'{_DATA_FOLDER}/georisques_documents.json'
    res = json.load(open(filename)) if os.path.exists(filename) else {}
    for i, id_ in enumerate(tqdm(ids, bar_format=_BAR_FORMAT)):
        if id_ in res:
            continue
        if i in {45000, 50000}:
            write_json(res, filename)
        response = requests.get(f'{_GEORISQUES_URL}/installations/etablissement/{id_}/texte')
        try:
            res[id_] = response.json()
        except Exception:  # pylint: disable=broad-except
            print(id_, response.content.decode())

    json.dump(res, open(filename, 'w'), ensure_ascii=False)


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
    full_url = _CQUEST_URL + '/' + url
    destination = _DOCUMENTS_FOLDER + '/' + url.replace('/', '_')
    found = _download_file_if_doesnt_exist(full_url, destination)
    if not found:
        print('Not found, attempting georisques.')
        source_georisques = _GEORISQUES_DOWNLOAD_URL + '/' + url
        _download_file_if_doesnt_exist(source_georisques, destination)


def _download_documents(documents: List[GRDocument]) -> None:
    for doc in tqdm(documents, 'Downloading documents.', bar_format=_BAR_FORMAT):
        _download_document(doc.url_doc)


if __name__ == '__main__':
    ALL_DOCS = [doc for docs in load_all_documents().values() for doc in docs if doc.type_doc == DocumentType.AP]
    _download_documents(random.sample(ALL_DOCS, 100))
