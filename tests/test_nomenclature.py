from envinorma.models.nomenclature import _is_increasing


def test_is_increasing():
    assert _is_increasing([])
    assert _is_increasing([1])
    assert _is_increasing([1, 3])
    assert _is_increasing([1, 3, 4, 5])
    assert not _is_increasing([1, 3, 4, 5, 1])
    assert not _is_increasing([1, 1])
