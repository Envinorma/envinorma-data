import re
from datetime import date
from typing import Any, Dict, List

import pandas
from tqdm import tqdm

_DIGITS = set('0123456789')


def _check_has_keys(record: Dict[str, Any], keys: List[str]) -> None:
    for key in keys:
        if key not in record:
            raise ValueError(f'Key {key} missing in record')


def _check_date(date_: str) -> None:
    assert isinstance(date_, str), f'{date_} is not str.'
    if len(date_) == 0:
        return
    date.fromisoformat(date_)


def _check_description(description: str) -> None:
    assert isinstance(description, str), f'{description} is not str.'


_GEORISQUES_ID_REGEXP = re.compile(r'[A-Z]{1}/[a-f0-9]{1}/[a-f0-9]{32}')


def _check_georisques_id(georisques_id: str) -> None:
    assert (
        re.match(_GEORISQUES_ID_REGEXP, georisques_id) and len(georisques_id) == 36
    ), f'id {georisques_id} has wrong format'


def _check_installation_s3ic_id(s3ic_id: str) -> None:
    if len(s3ic_id) != 10:
        raise ValueError(f's3ic_id must have length 10, got {len(s3ic_id)}')
    if set(s3ic_id) - _DIGITS != {'.'}:
        raise ValueError(f's3ic_id must have shape "xxxx.xxxxx", x being a digit. Got {s3ic_id}')


def _check_record(record: Dict[str, Any]) -> None:
    _check_has_keys(record, ['installation_s3ic_id', 'description', 'date', 'georisques_id'])
    _check_date(record['date'])
    _check_installation_s3ic_id(record['installation_s3ic_id'])
    _check_description(record['description'])
    _check_georisques_id(record['georisques_id'])


def _check_output(dataframe: pandas.DataFrame) -> None:
    for record in tqdm(dataframe.to_dict(orient='records'), 'Checking AP'):
        _check_record(record)


def check_documents_csv(filename: str) -> None:
    dataframe = pandas.read_csv(filename, dtype='str', index_col='Unnamed: 0', na_values=None).fillna('')
    _check_output(dataframe)
