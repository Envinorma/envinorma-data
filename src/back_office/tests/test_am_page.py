import dash_html_components as html
from back_office.am_page import (
    _diff_to_component,
    _diffline_is_special,
    _extract_char_positions,
    _extract_text_lines,
    _surline_text,
)
from dash.development.base_component import Component
from lib.data import EnrichedString, StructuredText


def test_diff_to_component():
    assert isinstance(_diff_to_component('+Hello', None, None), html.Span)
    assert _diff_to_component(' Hello', None, None) is None
    assert _diff_to_component(' Hello', '+', None) is not None
    assert _diff_to_component(' Hello', None, '-') is not None
    assert isinstance(_diff_to_component('+Hello', None, None), html.Span)
    assert isinstance(_diff_to_component('-Hello', None, None), html.Span)
    assert isinstance(_diff_to_component(' Hello', '+', '-'), str)


def _get_simple_text() -> StructuredText:
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [EnrichedString('bar')], [], None)
    return StructuredText(
        EnrichedString('AM '), [EnrichedString('alinea'), EnrichedString('foo')], [section_1, section_2], None
    )


_TEXT_A = StructuredText(
    title=EnrichedString(
        text='6. Schématisation des différents types de joints mentionnés :', links=[], table=None, active=True
    ),
    outer_alineas=[
        EnrichedString(text='Vous pouvez consulter les schémas dans le', links=[], table=None, active=True),
        EnrichedString(text='JO\nn° 265 du 16/11/2010 texte numéro 21', links=[], table=None, active=True),
    ],
    sections=[],
    applicability=None,
    lf_id=None,
    reference_str='Annexe 2 6.',
    annotations=None,
    id='0bEB0b14A96f',
)
_TEXT_B = StructuredText(
    title=EnrichedString(
        text='6. Schématisation des différents types de joints mentionnés :', links=[], table=None, active=True
    ),
    outer_alineas=[
        EnrichedString(text='Vous pouvez consulter les schémas dans le', links=[], table=None, active=True),
        EnrichedString(text='JO n° 265 du 16/11/2010 texte numéro 21', links=[], table=None, active=True),
    ],
    sections=[],
    applicability=None,
    lf_id=None,
    reference_str=None,
    annotations=None,
    id='AA51E55feD6F',
)


def test_extract_text_lines():
    assert _extract_text_lines(_get_simple_text()) == [
        'AM',
        'alinea',
        'foo',
        '# Section 1',
        '## Section 1.1',
        '# Section 2',
        'bar',
    ]
    assert _extract_text_lines(StructuredText(EnrichedString(' A'), [], [], None)) == ['A']
    assert _extract_text_lines(StructuredText(EnrichedString(' A'), [EnrichedString('')], [], None)) == ['A', '']
    assert _extract_text_lines(_TEXT_A) == [
        '6. Schématisation des différents types de joints mentionnés :',
        'Vous pouvez consulter les schémas dans le',
        'JO',
        'n° 265 du 16/11/2010 texte numéro 21',
    ]

    assert _extract_text_lines(_TEXT_B) == [
        '6. Schématisation des différents types de joints mentionnés :',
        'Vous pouvez consulter les schémas dans le',
        'JO n° 265 du 16/11/2010 texte numéro 21',
    ]


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
