import dash_html_components as html
from back_office.am_page import _diff_to_component, _diffline_is_special, _extract_char_positions


def test_diff_to_component():
    assert isinstance(_diff_to_component('+Hello', None, None), html.Span)
    assert _diff_to_component(' Hello', None, None) is None
    assert _diff_to_component(' Hello', '+', None) is not None
    assert _diff_to_component(' Hello', None, '-') is not None
    assert isinstance(_diff_to_component('+Hello', None, None), html.Span)
    assert isinstance(_diff_to_component('-Hello', None, None), html.Span)
    assert isinstance(_diff_to_component(' Hello', '+', '-'), str)


def test_extract_char_positions():
    assert _extract_char_positions('', '') == set()
    assert _extract_char_positions('', 'a') == set()
    assert _extract_char_positions('a', 'a') == {0}
    assert _extract_char_positions('a', ' a') == set()
    assert _extract_char_positions('aaa', 'a') == {0, 1, 2}
    assert _extract_char_positions(' aaa', 'a') == {1, 2, 3}
    assert _extract_char_positions(' aa a', 'a') == {1, 2, 4}


def test_diffline_is_special():
    assert not _diffline_is_special(None)
    assert not _diffline_is_special('')
    assert not _diffline_is_special(' ')
    assert _diffline_is_special('+')
    assert _diffline_is_special('-')
    assert _diffline_is_special('?')
