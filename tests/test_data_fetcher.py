import pytest

from envinorma.data_fetcher import _upsert_element


def test_upsert_element():
    assert _upsert_element('', [], -1) == ['']
    with pytest.raises(ValueError):
        _upsert_element('', [], 0)
    assert _upsert_element('new', ['old'], 0) == ['new']
    assert _upsert_element('new', ['old', 'unchanged'], 0) == ['new', 'unchanged']
    assert _upsert_element('new', ['unchanged'], -1) == ['unchanged', 'new']
