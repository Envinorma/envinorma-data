import json
import os
import traceback
from typing import Dict, List, Union

from lib.config import AM_DATA_FOLDER


def jsonify(obj: Union[Dict, List]) -> str:
    return json.dumps(obj, indent=4, sort_keys=True, ensure_ascii=False)


def write_json(obj: Union[Dict, List], filename: str, safe: bool = False, pretty: bool = True) -> None:
    indent = 4 if pretty else None
    with open(filename, 'w') as file_:
        if not safe:
            json.dump(obj, file_, indent=indent, sort_keys=True, ensure_ascii=False)
        else:
            try:
                json.dump(obj, file_, indent=indent, sort_keys=True, ensure_ascii=False)
            except Exception:  # pylint: disable=broad-except
                print(traceback.format_exc())


def get_structured_text_filename(am_id: str) -> str:
    return os.path.join(AM_DATA_FOLDER, 'structured_texts', am_id + '.json')


def get_structured_text_wip_folder(am_id: str) -> str:
    return os.path.join(AM_DATA_FOLDER, 'structured_texts', 'wip', am_id)


def get_parametrization_filename(am_id: str) -> str:
    return os.path.join(AM_DATA_FOLDER, 'parametrizations', am_id + '.json')


def get_parametrization_wip_folder(am_id: str) -> str:
    return os.path.join(AM_DATA_FOLDER, 'parametrizations', 'wip', am_id)


def get_state_file(am_id: str) -> str:
    return os.path.join(AM_DATA_FOLDER, 'states', am_id + '.json')
