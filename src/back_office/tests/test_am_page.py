import dash_html_components as html
from back_office.am_page import _diff_to_component, _extract_text_lines
from lib.data import EnrichedString, StructuredText


def test_diff_to_component():
    assert isinstance(_diff_to_component('+Hello', None, None), html.Tr)
    assert _diff_to_component(' Hello', None, None) is None
    assert _diff_to_component('@@', None, None) is None
    assert _diff_to_component('---       ', None, None) is None
    assert _diff_to_component('+++', None, None) is None
    assert _diff_to_component(' Hello', '+', None) is not None
    assert _diff_to_component(' Hello', None, '-') is not None
    assert len(_diff_to_component('+Hello', None, None).children or []) == 2
    assert len(_diff_to_component('-Hello', None, None).children or []) == 2
    assert (_diff_to_component('-Hello', None, None).children or [])[0].className == 'table-danger'
    assert not hasattr((_diff_to_component('-Hello', None, None).children or [])[1], 'className')
    assert (_diff_to_component('+Hello', None, None).children or [])[1].className == 'table-success'
    assert not hasattr((_diff_to_component('+Hello', None, None).children or [])[0], 'className')


def _get_simple_text() -> StructuredText:
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [EnrichedString('bar')], [], None)
    return StructuredText(
        EnrichedString('AM '), [EnrichedString('alinea'), EnrichedString('foo')], [section_1, section_2], None
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
