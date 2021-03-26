from typing import Any, Dict, List

import pandas

from envinorma.data.document import Document, DocumentType
from envinorma.data.load import load_documents
from envinorma.data_build.filenames import GEORISQUES_DOWNLOAD_URL, Dataset, dataset_filename


def _rowify_ap(ap: Document) -> Dict[str, Any]:
    assert ap.type == ap.type.AP
    return {
        'installation_s3ic_id': ap.s3ic_id,
        'description': ap.description,
        'date': ap.date,
        'url': f'{GEORISQUES_DOWNLOAD_URL}/{ap.url}',
    }


def _build_aps_dataframe(aps: List[Document]) -> pandas.DataFrame:
    return pandas.DataFrame([_rowify_ap(ap) for ap in aps])


def dump_aps(dataset: Dataset) -> None:
    aps = [doc for doc in load_documents(dataset) if doc.type == DocumentType.AP]
    print(f'Found {len(aps)} AP for dataset {dataset}.')
    assert len(aps) >= 100, f'Expecting >= 100 aps, got {len(aps)}'
    dataframe = _build_aps_dataframe(aps)
    dataframe.to_csv(dataset_filename(dataset, 'aps'))


def dump_ap_datasets() -> None:
    dump_aps('all')
    dump_aps('idf')
    dump_aps('sample')
