from ap_exploration.data import Prescription, PrescriptionStatus
import pytest
from envinorma.data import Cell, EnrichedString, Row
from ap_exploration.pages.ap.add_prescriptions import (
    _elements_to_prescription,
    _ensure_tables_or_strs,
    _extract_elements_from_soup,
    _extract_prescriptions,
    _split_between_prescription_marks,
    _PrescriptionBeginMark,
)
from bs4 import BeautifulSoup
from envinorma.structure import Linebreak, Title, Table


def _soup(x: str) -> BeautifulSoup:
    return BeautifulSoup(x, 'html.parser')


def test_extract_elements_from_soup():
    assert _extract_elements_from_soup(_soup('')) == []
    assert _extract_elements_from_soup(_soup('\n')) == ['\n']
    res = _extract_elements_from_soup(_soup('\n<table><tr><td></td></tr></table>'))
    assert res == ['\n', Table([Row([Cell(EnrichedString(''), 1, 1)], False)])]

    res = _extract_elements_from_soup(_soup('Test\n<table><tr><td></td></tr></table>'))
    assert res == ['Test\n', Table([Row([Cell(EnrichedString(''), 1, 1)], False)])]

    res = _extract_elements_from_soup(_soup('Test\nTest'))
    assert res == ['Test\nTest']

    res = _extract_elements_from_soup(_soup('Test\nTest\n<h1>Test</h1>'))
    assert res == ['Test\nTest\n', Linebreak(), 'Test', Linebreak()]

    res = _extract_elements_from_soup(_soup('<h1 id="a">Test</h1>'))
    assert res == [Linebreak(), 'Test', Linebreak()]

    res = _extract_elements_from_soup(
        _soup('<span class="hola">hihi</span><h1 id="a">Test</h1><span class="badge">hihi</span>')
    )
    assert res == ['hihi', Linebreak(), 'Test', Linebreak(), _PrescriptionBeginMark()]


def test_ensure_tables_or_strs():
    _ensure_tables_or_strs([])
    _ensure_tables_or_strs([Table([])])
    _ensure_tables_or_strs([Table([]), ''])
    _ensure_tables_or_strs(['', 'zeoihd'])
    with pytest.raises(ValueError):
        _ensure_tables_or_strs(['', 'zeoihd', Title('', 1)])
    with pytest.raises(ValueError):
        _ensure_tables_or_strs(['', 'zeoihd', Linebreak()])
    with pytest.raises(ValueError):
        _ensure_tables_or_strs([Linebreak()])


def test_elements_to_prescription():
    assert _elements_to_prescription('', [Table([])]) == Prescription(
        '', '', [Table([])], PrescriptionStatus.EN_VIGUEUR
    )
    assert _elements_to_prescription('', []) == Prescription('', '', [], PrescriptionStatus.EN_VIGUEUR)
    assert _elements_to_prescription('id', ['title', Table([])]) == Prescription(
        'id', 'title', [Table([])], PrescriptionStatus.EN_VIGUEUR
    )
    assert _elements_to_prescription('id', ['title', Table([]), 'hola']) == Prescription(
        'id', 'title', [Table([]), 'hola'], PrescriptionStatus.EN_VIGUEUR
    )


def test_split_between_prescription_marks():
    assert _split_between_prescription_marks(['hihi', Title('Test', 1, 'a'), _PrescriptionBeginMark()]) == [[]]
    assert _split_between_prescription_marks(['hihi', Title('Test', 1, 'a'), _PrescriptionBeginMark(), '']) == [['']]
    assert _split_between_prescription_marks(['hihi', Title('Test', 1, 'a'), _PrescriptionBeginMark(), 'a', 'b']) == [
        ['a', 'b']
    ]
    assert _split_between_prescription_marks(
        ['hihi', Title('', 3), _PrescriptionBeginMark(), 'a', _PrescriptionBeginMark(), 'b']
    ) == [['a'], ['b']]


def test_extract_prescriptions():
    res = _extract_prescriptions(
        'id', '<span class="hola">hihi</span><h1 id="a">Test</h1><span class="badge">hihi</span>'
    )
    assert res == []
    res = _extract_prescriptions(
        'id', '<span class="hola">hihi</span><h1 id="a">Test</h1><span class="badge">hihi</span>title'
    )
    assert res == [Prescription('id', 'title', [], PrescriptionStatus.EN_VIGUEUR)]
    res = _extract_prescriptions('id', 'TST<span class="badge">hihi</span>title<p>a</p>b<a>c</a>')
    assert res == [Prescription('id', 'title', ['a', 'bc'], PrescriptionStatus.EN_VIGUEUR)]
