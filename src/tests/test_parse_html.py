from lib.structure_extraction import Linebreak, Title
from lib.data import Table
from bs4 import BeautifulSoup
from lib.parse_html import _extract_cell_data, extract_text_elements, merge_between_linebreaks


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