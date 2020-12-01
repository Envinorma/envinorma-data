import random
import string
from typing import Any, List


def check_same_lengths(lists: List[List[Any]]) -> None:

    lengths = [len(list_) for list_ in lists]
    if len(set(lengths)) > 1:
        raise ValueError(f'Expected lists to have same length, received lists with lengths {lengths}')


def build_data_file_name(path: str, format_: str = 'csv') -> str:
    return '/'.join(path.split('/')[:-1] + ['data.' + format_])


def random_id(prefix: str) -> str:
    return prefix + '_' + ''.join([random.choice(string.ascii_letters) for _ in range(6)])
