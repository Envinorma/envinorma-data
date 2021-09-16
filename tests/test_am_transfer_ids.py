from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.helpers.am_transfer_ids import (
    _build_titles_to_id_map,
    _common_unique_title_pairs,
    _common_unique_titles,
    _elements_present_once,
    transfer_ids_based_on_other_am,
)
from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import EnrichedString


def test_elements_present_once():
    assert _elements_present_once(['a', 'c', 'a', 'b', 'c']) == {'b'}


def test_common_unique_titles():
    titles = {'1': ['title 1', 'title 4'], '2': ['title 2'], '3': ['title 3'], '4': ['title 3']}
    other_titles = {'1': ['title 1', 'title 4'], '2': ['title 2'], '3': ['title 3']}
    assert _common_unique_titles(titles, other_titles) == {'title 2', 'title 4'}


def test_common_unique_title_pairs():
    titles = {'1': ['title 1', 'title 4'], '2': ['title 2'], '3': ['title 3'], '4': ['title 3']}
    other_titles = {'1': ['title 1', 'title 4'], '2': ['title 2'], '3': ['title 3']}
    assert _common_unique_title_pairs(titles, other_titles) == {('title 2',), ('title 1', 'title 4')}


def test_build_titles_to_id_map():
    titles = {
        '1': ['title 1', 'title 4'],
        '2': ['title 2'],
        '3': ['title 3'],
        '4': ['title 3'],
        '5': ['title 0', 'title 3'],
    }
    unique_titles = {'title 2', 'title 4'}
    unique_title_pairs = {('title 2',), ('title 1', 'title 4'), ('title 0', 'title 3')}
    assert _build_titles_to_id_map(titles, unique_titles, unique_title_pairs) == {
        ('title 2',): '2',
        ('title 4',): '1',
        ('title 0', 'title 3'): '5',
    }


def _build_am() -> ArreteMinisteriel:
    subsection1 = StructuredText(EnrichedString('A'), [], [], None)
    subsection2 = StructuredText(EnrichedString('A'), [], [], None)
    sections = [
        StructuredText(EnrichedString('Art. 1'), [], [subsection1], None),
        StructuredText(EnrichedString('Art. 2'), [], [subsection2], None),
        StructuredText(EnrichedString('Conditions d\'application'), [], [], None),
        StructuredText(EnrichedString('Art. 3'), [], [], None),
    ]
    return ArreteMinisteriel(EnrichedString('arrete du 10/10/10'), sections, [], None, id='FAKE_ID')


def test_transfer_ids_based_on_other_am():
    am = _build_am()
    other_am = _build_am()

    orphan_titles = transfer_ids_based_on_other_am(am, other_am)
    assert {sec.id for sec in am.descendent_sections()} == {sec.id for sec in other_am.descendent_sections()}
    assert orphan_titles == {}


def test_transfer_ids_based_on_other_am_2():
    # We build an ambiguity by having two sections with the same title
    # So ids won't be transferred
    am = _build_am()
    am.sections[1].title.text = 'Art. 1'
    other_am = _build_am()
    other_am.sections[1].title.text = 'Art. 1'

    orphan_titles = transfer_ids_based_on_other_am(am, other_am)
    assert other_am.sections[0].id != am.sections[0].id
    assert other_am.sections[1].id != am.sections[1].id
    assert other_am.sections[2].id == am.sections[2].id
    assert other_am.sections[3].id == am.sections[3].id
    assert orphan_titles == {
        other_am.sections[0].id: ['Art. 1'],
        other_am.sections[1].id: ['Art. 1'],
        other_am.sections[0].sections[0].id: ['Art. 1', 'A'],
        other_am.sections[1].sections[0].id: ['Art. 1', 'A'],
    }
