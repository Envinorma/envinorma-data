from bs4 import BeautifulSoup

from envinorma.io.parse_html import (
    _extract_cell_data,
    _extract_text_elements_with_linebreaks,
    extract_table,
    extract_text_elements,
    merge_between_linebreaks,
)
from envinorma.models import Table
from envinorma.models.text_elements import Linebreak, Title


def test_cell_data_extraction():
    input_ = BeautifulSoup(
        "<br/>NIVEAU DE BRUIT AMBIANT EXISTANT \n      <br/>\n"
        "    dans les zones à émergence réglementée \n      <br/>\n"
        "    (incluant le bruit de l'installation)",
        'html.parser',
    )
    assert _extract_cell_data(input_).text == (
        "NIVEAU DE BRUIT AMBIANT EXISTANT\n"
        "dans les zones à émergence réglementée\n"
        "(incluant le bruit de l'installation)"
    )


def _soup(x: str) -> BeautifulSoup:
    return BeautifulSoup(x, 'html.parser')


def test_extract_text_elements():
    assert extract_text_elements(_soup('')) == []

    assert extract_text_elements(_soup('')) == []
    assert extract_text_elements(_soup('\n')) == ['\n']
    res = extract_text_elements(_soup('\n<table><tr><td></td></tr></table>'))
    assert len(res) == 2
    assert isinstance(res[1], Table)

    res = extract_text_elements(_soup('Test\n<table><tr><td></td></tr></table>'))
    assert len(res) == 2
    assert res[0] == 'Test\n'
    assert isinstance(res[1], Table)

    res = extract_text_elements(_soup('Test\nTest'))
    assert len(res) == 1
    assert res[0] == 'Test\nTest'

    res = extract_text_elements(_soup('Test\nTest\n<h1>Test</h1>'))
    assert len(res) == 2
    assert res[0] == 'Test\nTest\n'
    title = res[1]
    assert isinstance(title, Title)
    assert title.text == 'Test'
    assert title.level == 1

    res = extract_text_elements(_soup('<h1 id="a">Test</h1>'))
    assert res == [Title('Test', 1, 'a')]


def test_merge_between_linebreaks():
    assert merge_between_linebreaks([]) == []
    assert merge_between_linebreaks(['TEST', Linebreak(), 'TEST']) == ['TEST', 'TEST']
    assert merge_between_linebreaks(['TEST', 'TEST', Linebreak(), 'TEST']) == ['TESTTEST', 'TEST']
    assert merge_between_linebreaks(['TEST', Table([]), 'TEST', Linebreak(), 'TEST']) == [
        'TEST',
        Table([]),
        'TEST',
        'TEST',
    ]
    assert merge_between_linebreaks(['TEST\nTEST']) == ['TEST\nTEST']


def test_extract_text_elements_with_linebreaks():
    res = _extract_text_elements_with_linebreaks(_soup('<h1 id="a">Test</h1>'))
    assert res == [Title('Test', level=1, id='a')]


def test_extract_table():
    res = extract_table('<table><tr><td><a>test</a>test</td></tr></table>')
    assert len(res.rows) == 1
    assert len(res.rows[0].cells) == 1
    assert res.rows[0].cells[0].content.text == 'testtest'
    res = extract_table('<table><tr><td><a>testtest</a></td></tr></table>')
    assert len(res.rows) == 1
    assert len(res.rows[0].cells) == 1
    assert res.rows[0].cells[0].content.text == 'testtest'
    res = extract_table('<table><tr><td><p>test</p>test</td></tr></table>')
    assert len(res.rows) == 1
    assert len(res.rows[0].cells) == 1
    assert res.rows[0].cells[0].content.text == 'test\ntest'
    res = extract_table('<table><tr><td>test test</td></tr></table>')
    assert len(res.rows) == 1
    assert len(res.rows[0].cells) == 1
    assert res.rows[0].cells[0].content.text == 'test test'


def test_extract_cell_data():
    _extract_cell_data(_soup('<a>test</a>test')).text == 'testtest'
