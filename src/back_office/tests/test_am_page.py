import dash_html_components as html
from back_office.am_page import _diff_to_component, _diffline_is_special, _extract_char_positions, _surline_text
from dash.development.base_component import Component


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


def test_surline_text():
    assert _surline_text('', set(), {}) == ''
    assert _surline_text('foo bar', set(), {}) == 'foo bar'

    component = _surline_text('foo bar', {0, 1, 2}, {})
    assert isinstance(component, Component)
    assert len(component.children or []) == 3
    assert (component.children or [])[0] == ''
    assert isinstance((component.children or [])[1], html.Span)
    assert (component.children or [])[2] == ' bar'

    component = _surline_text('foo bar', {1, 2}, {})
    assert isinstance(component, Component)
    assert len(component.children or []) == 3
    assert (component.children or [])[0] == 'f'
    assert isinstance((component.children or [])[1], html.Span)
    assert (component.children or [])[2] == ' bar'

    component = _surline_text('foo bar', {1, 2, 6}, {})
    assert isinstance(component, Component)
    assert len(component.children or []) == 4
    assert (component.children or [])[0] == 'f'
    assert isinstance((component.children or [])[1], html.Span)
    assert (component.children or [])[2] == ' ba'
    assert isinstance((component.children or [])[3], html.Span)
