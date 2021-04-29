from envinorma.back_office.utils import (
    AMStatus,
    check_backups,
    check_legifrance_diff_computed,
    get_section_title,
    get_traversed_titles,
    split_route,
)
from envinorma.data import ArreteMinisteriel, EnrichedString, StructuredText


def _get_simple_text() -> StructuredText:
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [EnrichedString('bar')], [], None)
    return StructuredText(
        EnrichedString('All sections'), [EnrichedString('alinea'), EnrichedString('foo')], [section_1, section_2], None
    )


def test_get_section_title():
    am = ArreteMinisteriel(EnrichedString('arrete du 10/10/10'), [_get_simple_text()], [], None, id='FAKE_ID')
    assert get_section_title((), am) == 'Arrêté complet.'
    assert get_section_title((0,), am) == 'All sections'
    assert get_section_title((0, 0), am) == 'Section 1'
    assert get_section_title((0, 1), am) == 'Section 2'
    assert get_section_title((0, 0, 0), am) == 'Section 1.1'
    assert get_section_title((0, 0, 0, 1, 1), am) == None


def test_get_traversed_titles():
    am = ArreteMinisteriel(EnrichedString('arrete du 10/10/10'), [_get_simple_text()], [], None, id='FAKE_ID')
    assert get_traversed_titles((), am) == ['Arrêté complet.']
    assert get_traversed_titles((0,), am) == ['All sections']
    assert get_traversed_titles((0, 0), am) == ['All sections', 'Section 1']
    assert get_traversed_titles((0, 1), am) == ['All sections', 'Section 2']
    assert get_traversed_titles((0, 2), am) is None
    assert get_traversed_titles((0, 0, 0), am) == ['All sections', 'Section 1', 'Section 1.1']
    assert get_traversed_titles((0, 0, 0, 1, 1), am) == None


def test_split_route():
    assert split_route('/') == ('/', '')
    assert split_route('/a') == ('/a', '')
    assert split_route('/a/') == ('/a', '/')
    assert split_route('/a/b') == ('/a', '/b')
    assert split_route('/a/b/') == ('/a', '/b/')
    assert split_route('/a/b/c') == ('/a', '/b/c')


def test_am_status_step():
    for element in AMStatus:
        assert isinstance(element.step(), int)


def test_check_backups():
    check_backups()


def test_check_legifrance_diff_computed():
    check_legifrance_diff_computed()
