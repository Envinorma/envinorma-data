"""Initialize AM databases for enrichment app.

This script is meant to initialize and fill tables of "am" database for AM enrichment app. 
It is meant to be run once and will probably not be run again.
"""
import json
import os
from typing import Optional

import psycopg2
from envinorma.back_office.fetch_data import (
    _upsert_new_parametrization,
    upsert_am_status,
    upsert_initial_am,
    upsert_structured_am,
)
from envinorma.back_office.utils import ID_TO_AM_MD, AMStatus
from envinorma.config import AM_DATA_FOLDER, config
from envinorma.data import ArreteMinisteriel
from envinorma.parametrization import Parametrization
from tqdm import tqdm

_CONNECTION = psycopg2.connect(config.storage.psql_dsn)


def _create_tables():
    commands = (
        """CREATE TABLE am_status (am_id VARCHAR(255) PRIMARY KEY, status VARCHAR(255) NOT NULL)""",
        """CREATE TABLE initial_am (am_id VARCHAR(255) PRIMARY KEY, data TEXT NOT NULL)""",
        """CREATE TABLE structured_am (am_id VARCHAR(255) PRIMARY KEY, data TEXT NOT NULL)""",
        """CREATE TABLE parametrization (am_id VARCHAR(255) PRIMARY KEY, data TEXT NOT NULL)""",
    )
    cur = _CONNECTION.cursor()
    for command in commands:
        cur.execute(command)
    _CONNECTION.commit()
    cur.close()


def _get_most_recent_filename(folder: str, with_default: bool = False) -> Optional[str]:
    files = os.listdir(folder)
    dates = list(sorted([file_ for file_ in files if file_ != 'default.json']))
    if not dates:
        if with_default and 'default.json' in files:
            return 'default.json'
        return None
    return dates[-1]


def get_structured_text_wip_folder(am_id: str) -> str:
    return os.path.join(AM_DATA_FOLDER, 'structured_texts', 'wip', am_id)


def get_parametrization_wip_folder(am_id: str) -> str:
    return os.path.join(AM_DATA_FOLDER, 'parametrizations', 'wip', am_id)


def _fill_tables():

    for am_id in ID_TO_AM_MD:
        upsert_am_status(am_id, AMStatus.PENDING_STRUCTURE_VALIDATION)

    for am_id in tqdm(ID_TO_AM_MD):
        filename = get_structured_text_wip_folder(am_id) + '/default.json'
        if os.path.exists(filename):
            upsert_initial_am(am_id, ArreteMinisteriel.from_dict(json.load(open(filename))))
        filename = _get_most_recent_filename(get_structured_text_wip_folder(am_id))
        if filename:
            upsert_structured_am(
                am_id,
                ArreteMinisteriel.from_dict(json.load(open(get_structured_text_wip_folder(am_id) + '/' + filename))),
            )

        filename = _get_most_recent_filename(get_parametrization_wip_folder(am_id), with_default=True)
        if filename:
            print('parametrization: ', filename)
            _upsert_new_parametrization(
                am_id,
                Parametrization.from_dict(json.load(open(get_parametrization_wip_folder(am_id) + '/' + filename))),
            )


if __name__ == '__main__':
    _create_tables()
    _fill_tables()
