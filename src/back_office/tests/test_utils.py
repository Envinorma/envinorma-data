from back_office.utils import get_section_title, split_route
from lib.data import ArreteMinisteriel, EnrichedString, StructuredText


def _get_simple_text() -> StructuredText:
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [EnrichedString('bar')], [], None)
    return StructuredText(
        EnrichedString('All sections'), [EnrichedString('alinea'), EnrichedString('foo')], [section_1, section_2], None
    )


def test_get_section_title():
    am = ArreteMinisteriel(EnrichedString('AM'), [_get_simple_text()], [], '', None)
    assert get_section_title((), am) == 'Arrêté complet.'
    assert get_section_title((0,), am) == 'All sections'
    assert get_section_title((0, 0), am) == 'Section 1'
    assert get_section_title((0, 1), am) == 'Section 2'
    assert get_section_title((0, 0, 0), am) == 'Section 1.1'
    assert get_section_title((0, 0, 0, 1, 1), am) == None


def test_split_route():
    assert split_route('/') == ('/', '')
    assert split_route('/a') == ('/a', '')
    assert split_route('/a/') == ('/a', '/')
    assert split_route('/a/b') == ('/a', '/b')
    assert split_route('/a/b/') == ('/a', '/b/')
    assert split_route('/a/b/c') == ('/a', '/b/c')