from collections import Counter
from math import sqrt
from typing import Dict


def _norm_2(dict_: Dict[str, int]) -> float:
    return sqrt(sum([x ** 2 for x in dict_.values()]))


def _normalized_scalar_product(dict_1: Dict[str, int], dict_2: Dict[str, int]) -> float:
    common_keys = {*dict_1.keys(), *dict_2.keys()}
    numerator = sum([dict_1.get(key, 0) * dict_2.get(key, 0) for key in common_keys])
    denominator = (_norm_2(dict_1) * _norm_2(dict_2)) or 1
    return numerator / denominator


def text_proximity(str_1: str, str_2: str) -> float:
    """Compute proximity between two strings and the scalar product between word counters.

    Args:
        str_1 (str): string 1
        str_2 (str): string 2

    Returns:
        float: Proximity score (between 0 and 1)
    """
    tokens_1 = Counter(str_1.split(' '))
    tokens_2 = Counter(str_2.split(' '))
    return _normalized_scalar_product(tokens_1, tokens_2)
