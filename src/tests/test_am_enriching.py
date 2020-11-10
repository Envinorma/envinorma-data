from lib.data import ArreteMinisteriel, EnrichedString, StructuredText, Topic
from lib.am_enriching import add_prescriptive_power, add_topics


def test_add_topics():
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None, None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None, None)
    section_2 = StructuredText(EnrichedString('Section 2'), [], [], None, None)
    am = ArreteMinisteriel(EnrichedString(''), [section_1, section_2], [], '', None)

    am_with_topics = add_topics(am, {(0,): Topic.INCENDIE, (0, 0): Topic.INCENDIE, (1,): Topic.BRUIT})
    assert am_with_topics.sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_topics.sections[0].sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_topics.sections[1].annotations.topic == Topic.BRUIT

    am_with_non_prescriptive = add_prescriptive_power(am_with_topics, {(1,)})
    assert am_with_non_prescriptive.sections[0].annotations.prescriptive
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.prescriptive
    assert not am_with_non_prescriptive.sections[1].annotations.prescriptive

    assert am_with_non_prescriptive.sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_non_prescriptive.sections[1].annotations.topic == Topic.BRUIT
