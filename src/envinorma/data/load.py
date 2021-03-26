import json
from datetime import date
from typing import Any, Dict, List, Set, cast

import pandas
from tqdm import tqdm

from envinorma.data import Regime
from envinorma.data.classement import DetailedClassement
from envinorma.data.document import Document, DocumentType
from envinorma.data.installation import ActivityStatus, Installation, InstallationFamily, Seveso
from envinorma.data_build.build.build_installations import load_installations_csv
from envinorma.data_build.filenames import Dataset, dataset_filename


def _dataframe_record_to_installation(record: Dict[str, Any]) -> Installation:
    record['last_inspection'] = date.fromisoformat(record['last_inspection']) if record['last_inspection'] else None
    record['regime'] = Regime(record['regime'])
    record['seveso'] = Seveso(record['seveso'])
    record['family'] = InstallationFamily(record['family'])
    record['active'] = ActivityStatus(record['family'])
    return Installation(**record)


def load_installations(dataset: Dataset) -> List[Installation]:
    filename = dataset_filename(dataset, 'installations')
    dataframe = pandas.read_csv(filename, dtype='str', index_col='Unnamed: 0', na_values=None).fillna('')
    return [
        _dataframe_record_to_installation(cast(Dict, record))
        for record in tqdm(dataframe.to_dict(orient='records'), 'Loading installations', leave=False)
    ]


def load_installation_ids(dataset: Dataset = 'all') -> Set[str]:
    return {x for x in load_installations_csv(dataset).s3ic_id}


def _dataframe_record_to_classement(record: Dict[str, Any]) -> DetailedClassement:
    return DetailedClassement(**record)


def load_classements(dataset: Dataset) -> List[DetailedClassement]:
    filename = dataset_filename(dataset, 'classements')
    dataframe_with_nan = pandas.read_csv(filename, dtype='str', index_col='Unnamed: 0', na_values=None)
    dataframe = dataframe_with_nan.where(pandas.notnull(dataframe_with_nan), None)
    dataframe['volume'] = dataframe.volume.apply(lambda x: x or '')
    return [
        _dataframe_record_to_classement(cast(Dict, record))
        for record in tqdm(dataframe.to_dict(orient='records'), 'Loading classements', leave=False)
    ]


def load_documents(dataset: Dataset) -> List[Document]:
    return [Document.from_dict(doc) for doc in json.load(open(dataset_filename(dataset, 'documents', 'json')))]


def _dataframe_record_to_ap(record: Dict[str, Any]) -> Document:
    record = record.copy()
    record['s3ic_id'] = record['installation_s3ic_id']
    record['type'] = DocumentType.AP.value
    return Document.from_dict(**record)


def load_aps(dataset: Dataset) -> List[Document]:
    dataframe = pandas.read_csv(dataset_filename(dataset, 'aps'), dtype='str')
    return [
        _dataframe_record_to_ap(cast(Dict, record))
        for record in tqdm(dataframe.to_dict(orient='records'), 'Loading aps', leave=False)
    ]
