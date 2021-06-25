from copy import copy
from dataclasses import replace
from typing import Dict, List, Optional, Set

from envinorma.models import Ints
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.structured_text import Annotations, StructuredText
from envinorma.topics.patterns import TopicName, tokenize
from envinorma.topics.topics import TopicOntology


def _add_topic_in_text(text: StructuredText, topics: Dict[Ints, TopicName], path: Ints) -> StructuredText:
    text_copy = copy(text)
    if path in topics:
        text_copy.annotations = replace(text.annotations or Annotations(), topic=topics[path])
    text_copy.sections = [_add_topic_in_text(sec, topics, path + (i,)) for i, sec in enumerate(text.sections)]
    return text_copy


def add_topics(am: ArreteMinisteriel, topics: Dict[Ints, TopicName]) -> ArreteMinisteriel:
    am_copy = copy(am)
    am_copy.sections = [_add_topic_in_text(sec, topics, (i,)) for i, sec in enumerate(am.sections)]
    return am_copy


def _is_sentence_short(title: str) -> bool:
    return len(tokenize(title)) <= 10


def _detect_in_title(title: str, ontology: TopicOntology) -> Set[TopicName]:
    return ontology.parse(title, _is_sentence_short(title))


def _detect_in_titles(titles: List[str], ontology: TopicOntology) -> Set[TopicName]:
    return {topic for title in titles for topic in _detect_in_title(title, ontology)}


def _extract_topics_from_titles_and_content(
    all_titles: List[str], section_sentences: List[str], ontology: TopicOntology
) -> Set[TopicName]:
    title_topics = _detect_in_titles(all_titles, ontology)
    sentence_topics = {topic for sentence in section_sentences for topic in ontology.parse(sentence)}
    return title_topics.union(sentence_topics)


def extract_topics(text: StructuredText, parent_titles: List[str], ontology: TopicOntology) -> Set[TopicName]:
    all_titles = parent_titles + [text.title.text]
    if text.sections:
        return {topic for section in text.sections for topic in extract_topics(section, all_titles, ontology)}
    section_sentences = [al.text for al in text.outer_alineas if al.text]
    return _extract_topics_from_titles_and_content(all_titles, section_sentences, ontology)


def _detect_main_topic(text: StructuredText, parent_titles: List[str], ontology: TopicOntology) -> Optional[TopicName]:
    topics = extract_topics(text, parent_titles, ontology)
    return ontology.deduce_main_topic(topics)


def _detect_and_add_topic_in_text(text: StructuredText, ontology: TopicOntology, titles: List[str]) -> StructuredText:
    text_copy = copy(text)
    title = text.title.text
    topic = _detect_main_topic(text, titles, ontology)
    if topic:
        text_copy.annotations = replace(text.annotations or Annotations(), topic=topic)
    text_copy.sections = [_detect_and_add_topic_in_text(sec, ontology, titles + [title]) for sec in text.sections]
    return text_copy


def detect_and_add_topics(am: ArreteMinisteriel, ontology: TopicOntology) -> ArreteMinisteriel:
    am_copy = copy(am)
    am_copy.sections = [_detect_and_add_topic_in_text(sec, ontology, []) for sec in am.sections]
    return am_copy
