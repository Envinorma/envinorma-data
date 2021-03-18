import math

from scripts.generate_seeds import _is_a_partition


def test_is_partition():
    assert _is_a_partition([(-math.inf, math.inf)])
    assert _is_a_partition([(-math.inf, 1), (1, math.inf)])
    assert _is_a_partition([(-math.inf, 1), (1, 10), (10, math.inf)])
    assert _is_a_partition([(-math.inf, 1), (1, 10), (10, 20), (20, math.inf)])
    assert _is_a_partition([(20, math.inf), (-math.inf, 1), (1, 10), (10, 20)])
    assert not _is_a_partition([(-math.inf, 1), (1, 20), (10, 20), (20, math.inf)])
    assert not _is_a_partition([(-math.inf, 1), (1, 10), (10, 20), (20, 30)])
    assert not _is_a_partition([])
