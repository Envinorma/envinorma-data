from dataclasses import dataclass
import pytest

from envinorma.data_fetcher import _upsert_element


@dataclass
class Element:
    id: str
    value: str


def test_upsert_element():
    assert _upsert_element('', [], None) == ['']
    with pytest.raises(ValueError):
        _upsert_element('', [], 'id')
    assert _upsert_element(Element('0', 'new'), [Element('0', 'old')], '0') == [Element('0', 'new')]
    assert _upsert_element(Element('0', 'new'), [Element('0', 'old'), Element('1', 'unchanged')], '0') == [
        Element('0', 'new'),
        Element('1', 'unchanged'),
    ]
    assert _upsert_element(Element('0', 'new'), [Element('1', 'unchanged')], None) == [
        Element('1', 'unchanged'),
        Element('0', 'new'),
    ]
