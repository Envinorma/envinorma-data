import json
import traceback
from typing import Union, List, Dict


def write_json(obj: Union[Dict, List], filename: str, safe: bool = False) -> None:
    with open(filename, 'w') as file_:
        if not safe:
            json.dump(obj, file_, indent=4, sort_keys=True, ensure_ascii=False)
        else:
            try:
                json.dump(obj, file_, indent=4, sort_keys=True, ensure_ascii=False)
            except Exception:  # pylint: disable=broad-except
                print(traceback.format_exc())
