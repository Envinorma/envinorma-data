import dash_html_components as html

from dash.development.base_component import Component
from envinorma.back_office.components import surline_text


def test_surline_text():
    assert surline_text('', set(), {}) == ''
    assert surline_text('foo bar', set(), {}) == 'foo bar'

    component = surline_text('foo bar', {0, 1, 2}, {})
    assert isinstance(component, Component)
    assert len(component.children or []) == 3
    assert (component.children or [])[0] == ''
    assert isinstance((component.children or [])[1], html.Span)
    assert (component.children or [])[2] == ' bar'

    component = surline_text('foo bar', {1, 2}, {})
    assert isinstance(component, Component)
    assert len(component.children or []) == 3
    assert (component.children or [])[0] == 'f'
    assert isinstance((component.children or [])[1], html.Span)
    assert (component.children or [])[2] == ' bar'

    component = surline_text('foo bar', {1, 2, 6}, {})
    assert isinstance(component, Component)
    assert len(component.children or []) == 4
    assert (component.children or [])[0] == 'f'
    assert isinstance((component.children or [])[1], html.Span)
    assert (component.children or [])[2] == ' ba'
    assert isinstance((component.children or [])[3], html.Span)
