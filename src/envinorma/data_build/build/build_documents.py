import json
import os
from typing import Dict, List

import requests
from tqdm import tqdm

from envinorma.data.document import Document
from envinorma.data.load import load_documents, load_installation_ids
from envinorma.data_build.filenames import GEORISQUES_URL, Dataset, dataset_filename
from envinorma.utils import batch, typed_tqdm, write_json


def _no_docs(dicts: List[Dict]) -> bool:
    return len(dicts) == 1 and all([x is None for x in dicts[0].values()])


def _download_batch(s3ic_ids: List[str]) -> List[Document]:
    res: List[Document] = []
    for id_ in typed_tqdm(s3ic_ids, desc='Fetching document references', leave=False):
        remote_id = id_.replace('.', '-')
        response = requests.get(f'{GEORISQUES_URL}/installations/etablissement/{remote_id}/texte')
        try:
            dicts = response.json()
            if _no_docs(dicts):
                continue
            docs = [Document.from_georisques_dict(dict_, id_) for dict_ in dicts]
            res.extend(docs)
        except Exception as exc:  # pylint: disable=broad-except
            print(id_, str(exc), response.content.decode())
    return res


def _dump_docs(docs: List[Document], filename: str) -> None:
    json_ = [doc.to_dict() for doc in docs]
    write_json(json_, filename, pretty=False)
    print(f'Downloaded {len(docs)} documents in batch {filename}')


def _download_if_inexistent(filename: str, s3ic_ids: List[str]) -> None:
    if not os.path.exists(filename):
        docs = _download_batch(s3ic_ids)
        _dump_docs(docs, filename)
        return
    print(f'Batch {filename} exists')


def _load_batch(filename: str) -> Dict[str, List[Dict]]:
    with open(filename) as file_:
        return json.load(file_)


def _combine_and_dump(batch_filenames: List[str], output_filename: str) -> None:
    result = [doc for batch_filename in batch_filenames for doc in _load_batch(batch_filename)]
    write_json(result, output_filename, pretty=False)


def _create_if_inexistent(folder: str) -> None:
    if not os.path.exists(folder):
        os.mkdir(folder)


def download_georisques_documents(dataset: Dataset = 'all') -> None:
    s3ic_ids = sorted(list(load_installation_ids(dataset)))
    folder = f'docs_dl_batches_{dataset}'
    _create_if_inexistent(folder)
    batches = batch(s3ic_ids, 1000)
    filenames = [f'{folder}/{batch_id}.json' for batch_id in range(len(batches))]
    for filename, batch_ in tqdm(list(zip(filenames, batches)), 'Downloading document batches'):
        _download_if_inexistent(filename, batch_)
    _combine_and_dump(filenames, dataset_filename(dataset, 'documents', 'json'))


def _filter_and_dump(all_documents: List[Document], dataset: Dataset) -> None:
    doc_ids = load_installation_ids(dataset)
    docs = [doc for doc in all_documents if doc.s3ic_id in doc_ids]
    _dump_docs(docs, dataset_filename(dataset, 'documents', 'json'))
    print(f'documents dataset {dataset} has {len(docs)} rows')
    assert len(docs) >= 100, f'Expecting >= 100 docs, got {len(docs)}'


def build_all_document_datasets() -> None:
    all_documents = load_documents('all')
    _filter_and_dump(all_documents, 'sample')
    _filter_and_dump(all_documents, 'idf')
