from envinorma.enriching.topic_detection import add_topics
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import EnrichedString
from envinorma.topics.patterns import TopicName


def test_add_topics():
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [], [], None)
    am = ArreteMinisteriel(EnrichedString('arrete du 10/10/10'), [section_1, section_2], [], None, id='FAKE_ID')

    am_with_topics = add_topics(
        am, {(0,): TopicName.INCENDIE, (0, 0): TopicName.INCENDIE, (1,): TopicName.BRUIT_VIBRATIONS}
    )
    assert am_with_topics.sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_topics.sections[0].sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_topics.sections[1].annotations.topic == TopicName.BRUIT_VIBRATIONS
