import json
from typing import Tuple

DELETE_REASON_MIN_NB_CHARS = 10


Ints = Tuple[int, ...]


def dump_path(path: Ints) -> str:
    return json.dumps(path)


def load_path(path_str: str) -> Ints:
    return tuple(json.loads(path_str))
