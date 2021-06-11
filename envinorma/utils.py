import json
import math
import random
import string
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, Iterable, List, Optional, TypeVar, Union

from tqdm import tqdm

AIDA_URL = 'https://aida.ineris.fr/consultation_document/'
LEGIFRANCE_LODA_BASE_URL = 'https://www.legifrance.gouv.fr/loda/id/'
AM1510_IDS = ('DEVP1706393A', 'JORFTEXT000034429274')


def jsonify(obj: Union[Dict, List]) -> str:
    return json.dumps(obj, indent=4, sort_keys=True, ensure_ascii=False)


def write_file(text: str, filename: str) -> None:
    with open(filename, 'w') as file_:
        file_.write(text)


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


def random_string(size: int = 6) -> str:
    return ''.join([random.choice(string.ascii_letters) for _ in range(size)])


T = TypeVar('T')


def ensure_not_none(candidate: Optional[T]) -> T:
    if not candidate:
        raise ValueError('Expecting non None argument')
    return candidate


def date_to_str(date: datetime) -> str:
    return date.strftime('%Y-%m-%d')


def str_to_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, '%Y-%m-%d')


def _split_string(str_: str, split_ranks: List[int]) -> List[str]:
    extended_ranks = [0] + split_ranks + [len(str_)]
    return [str_[start:end] for start, end in zip(extended_ranks, extended_ranks[1:])]


def snake_to_camel(key: str) -> str:
    split_marks = []
    for rank in range(1, len(key) - 1):
        letter_before = key[rank - 1]
        letter = key[rank]
        letter_after = key[rank + 1]
        if letter.isupper() and letter_after.islower():
            split_marks.append(rank)
        elif letter.isupper() and letter_before.islower():
            split_marks.append(rank)
    splits = _split_string(key, split_marks)
    return '_'.join([word.lower() for word in splits])


def batch(items: List[T], batch_size: int) -> List[List[T]]:
    if batch_size <= 0:
        raise ValueError(f'batch_size must be positive, got {batch_size}')
    return [items[i * batch_size : (i + 1) * batch_size] for i in range(math.ceil(len(items) / batch_size))]


def typed_tqdm(
    collection: Iterable[T], desc: Optional[str] = None, leave: bool = True, disable: bool = False
) -> Iterable[T]:
    return tqdm(collection, desc=desc, leave=leave, disable=disable)


def safely_replace(string: str, replaced_substring: str, new_substring: str) -> str:
    if replaced_substring not in string:
        raise ValueError(f'Expecting {replaced_substring} to be in {string}.')
    return string.replace(replaced_substring, new_substring)


def random_id(size: int = 12) -> str:
    return ''.join([random.choice(string.hexdigits) for _ in range(size)])


class AMStatus(Enum):
    PENDING_INITIALIZATION = 'pending-initialization'
    PENDING_STRUCTURE_VALIDATION = 'pending-structure-validation'
    PENDING_PARAMETRIZATION = 'pending-enrichment'
    VALIDATED = 'validated'

    def step(self) -> int:
        if self == AMStatus.PENDING_INITIALIZATION:
            return 0
        if self == AMStatus.PENDING_STRUCTURE_VALIDATION:
            return 1
        if self == AMStatus.PENDING_PARAMETRIZATION:
            return 2
        if self == AMStatus.VALIDATED:
            return 3
        raise NotImplementedError()
