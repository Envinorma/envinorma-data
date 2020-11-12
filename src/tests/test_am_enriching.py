from lib.data import ArreteMinisteriel, EnrichedString, StructuredText, Topic
from lib.am_enriching import (
    remove_prescriptive_power,
    add_topics,
    add_references,
    _extract_special_prefix,
    _is_probably_section_number,
    _is_prefix,
    _merge_prefix_list,
)


def test_add_topics():
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None, None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None, None)
    section_2 = StructuredText(EnrichedString('Section 2'), [], [], None, None)
    am = ArreteMinisteriel(EnrichedString(''), [section_1, section_2], [], '', None)

    am_with_topics = add_topics(am, {(0,): Topic.INCENDIE, (0, 0): Topic.INCENDIE, (1,): Topic.BRUIT})
    assert am_with_topics.sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_topics.sections[0].sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_topics.sections[1].annotations.topic == Topic.BRUIT

    am_with_non_prescriptive = remove_prescriptive_power(am_with_topics, {(1,)})
    assert am_with_non_prescriptive.sections[0].annotations.prescriptive
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.prescriptive
    assert not am_with_non_prescriptive.sections[1].annotations.prescriptive

    assert am_with_non_prescriptive.sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_non_prescriptive.sections[1].annotations.topic == Topic.BRUIT


def test_extract_special_prefix():
    assert _extract_special_prefix('Annexe I') == 'Annexe I'
    assert _extract_special_prefix('ANNEXE I') == 'Annexe I'
    assert _extract_special_prefix('ANNEXE CONCERNANT LES DISPOSITIONS') == 'Annexe ?'
    assert _extract_special_prefix('Article fixant les dispositions') == 'Art. ?'
    assert _extract_special_prefix('Article 1') == 'Art. 1'
    assert _extract_special_prefix('Article 2.21') == 'Art. 2.21'
    assert _extract_special_prefix('Bonjour') is None


def test_is_probably_section_number():
    assert _is_probably_section_number('I.')
    assert _is_probably_section_number('1.1.')
    assert _is_probably_section_number('A.')
    assert _is_probably_section_number('III')
    assert _is_probably_section_number('a)')
    assert not _is_probably_section_number('Dispositions')
    assert not _is_probably_section_number('Bonjour')


def test_is_prefix():
    assert _is_prefix('1. ', '1.1.')
    assert _is_prefix('1. ', '1. 2.')
    assert _is_prefix('2. 4.', '2. 4. 1.')
    assert _is_prefix('1. ', '1. BONJOUR')
    assert not _is_prefix('1. ', '2. ')
    assert not _is_prefix('1. ', '2. 1. ')
    assert not _is_prefix('1. ', 'A.')


def test_merge_prefix_list():
    assert _merge_prefix_list(['1.', '2.', '3.', '4.']) == '1. 2. 3. 4.'
    assert _merge_prefix_list(['1.', '1.1.', '1.1.1.']) == '1.1.1.'
    assert _merge_prefix_list(['Art. 1.', '2.', '2. 1.']) == 'Art. 1. 2. 1.'
    assert _merge_prefix_list(['Section II', 'Chapitre 4', 'Art. 10']) == 'Section II Chapitre 4 Art. 10'


def test_add_references():
    sub_sections = [
        StructuredText(EnrichedString('1.1. azeaze'), [], [], None, None),
        StructuredText(EnrichedString('1. 2. azeaze'), [], [], None, None),
    ]
    sections = [
        StructuredText(EnrichedString('1. efzefz'), [], sub_sections, None, None),
        StructuredText(EnrichedString('2. zefez'), [], [], None, None),
        StructuredText(EnrichedString('A. zefze'), [], [], None, None),
        StructuredText(EnrichedString('a) zefze'), [], [], None, None),
        StructuredText(EnrichedString('V. zefze'), [], [], None, None),
        StructuredText(EnrichedString('ANNEXE I zefze'), [], [], None, None),
        StructuredText(EnrichedString('Article 18.1'), [], [], None, None),
        StructuredText(EnrichedString('Article 1'), [], [], None, None),
    ]
    am = ArreteMinisteriel(EnrichedString(''), sections, [], '', None)
    am_with_references = add_references(am)

    assert am_with_references.sections[0].reference_str == '1.'
    assert am_with_references.sections[0].sections[0].reference_str == '1.1.'
    assert am_with_references.sections[0].sections[1].reference_str == '1.2.'
    assert am_with_references.sections[1].reference_str == '2.'
    assert am_with_references.sections[2].reference_str == 'A.'
    assert am_with_references.sections[3].reference_str == 'a)'
    assert am_with_references.sections[4].reference_str == 'V.'
    assert am_with_references.sections[5].reference_str == 'Annexe I'
    assert am_with_references.sections[6].reference_str == 'Art. 18.1'
    assert am_with_references.sections[7].reference_str == 'Art. 1'
