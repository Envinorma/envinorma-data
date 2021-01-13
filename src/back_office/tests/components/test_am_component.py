import dash_html_components as html
from back_office.components.am_component import _get_html_heading_classname, _split_in_header_and_body_rows
from lib.data import Row


def test_get_html_heading_classname():
    assert isinstance(_get_html_heading_classname(1)(), html.H1)
    assert isinstance(_get_html_heading_classname(6)(), html.H6)
    assert isinstance(_get_html_heading_classname(7)(), html.H6)


def test_split_in_header_and_body_rows():
    assert _split_in_header_and_body_rows([]) == ([], [])
    header_row = Row([], True)
    body_row = Row([], False)
    assert _split_in_header_and_body_rows([header_row]) == ([header_row], [])
    assert _split_in_header_and_body_rows([header_row, header_row]) == ([header_row, header_row], [])
    assert _split_in_header_and_body_rows([header_row, body_row]) == ([header_row], [body_row])
    assert _split_in_header_and_body_rows([header_row, header_row, body_row]) == ([header_row, header_row], [body_row])
    assert _split_in_header_and_body_rows([body_row]) == ([], [body_row])
    assert _split_in_header_and_body_rows([body_row, header_row]) == ([], [body_row, header_row])
    assert _split_in_header_and_body_rows([header_row, body_row, header_row]) == ([header_row], [body_row, header_row])
