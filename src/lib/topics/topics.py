import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from lib.topics.patterns import ALL_TOPICS, Topic, TopicName, merge_patterns, normalize


@dataclass
class TopicOntology:
    topics: List[Topic]
    pattern_to_topic: Dict[str, TopicName] = field(init=False)
    title_compiled_pattern: re.Pattern = field(init=False)
    general_compiled_pattern: re.Pattern = field(init=False)
    topic_name_to_topic: Dict[TopicName, Topic] = field(init=False)

    def __post_init__(self):
        self._check_consistency(self.topics)
        self.pattern_to_topic = {
            pattern: desc.topic_name
            for desc in self.topics
            for pattern in desc.other_patterns + desc.short_title_patterns
        }
        self.topic_name_to_topic = {topic.topic_name: topic for topic in self.topics}
        if '' in self.pattern_to_topic:
            raise ValueError('Cannot have void pattern!')
        other_patterns = [pattern for topic in self.topics for pattern in topic.other_patterns]
        all_patterns = [pattern for topic in self.topics for pattern in topic.short_title_patterns] + other_patterns
        self.general_compiled_pattern = re.compile(merge_patterns(other_patterns))
        self.title_compiled_pattern = re.compile(merge_patterns(all_patterns))

    @staticmethod
    def _check_consistency(topics: Iterable[Topic]) -> None:
        pattern_to_topic: Dict[str, TopicName] = {}
        errors: List[Tuple[str, TopicName, TopicName]] = []
        for topic in topics:
            for pattern in topic.short_title_patterns + topic.other_patterns:
                if pattern in pattern_to_topic:
                    errors.append((pattern, topic.topic_name, pattern_to_topic[pattern]))
                else:
                    pattern_to_topic[pattern] = topic.topic_name
        if errors:
            raise ValueError(f'Following patterns are repeated in distinct topics: {errors}')

    def parse(self, text: str, short_title: bool = False) -> Set[TopicName]:
        return parse(self, text, short_title)

    def detect_matched_patterns(self, text: str, topic: Optional[TopicName], short_title: bool = False) -> Set[str]:
        return detect_matched_patterns(self, text, topic, short_title)

    def deduce_main_topic(self, topics: Iterable[TopicName]) -> Optional[TopicName]:
        if not topics:
            return None
        return _deduce_main_topic([self.topic_name_to_topic[name] for name in topics])


def _deduce_main_topic(topics: List[Topic]) -> TopicName:
    if not topics:
        raise ValueError('Need at least one topic.')
    non_generic_metatopics = [topic.metatopic for topic in topics if topic != TopicName.DISPOSITIONS_GENERALES]
    if not non_generic_metatopics:
        return TopicName.DISPOSITIONS_GENERALES
    return sorted([topic.metatopic for topic in topics], key=lambda x: x.value)[0]


def _extract_substring(text: str, start: int, end: int) -> str:
    return text[start:end]


def detect_matched_patterns(
    ontology: TopicOntology, text: str, topic: Optional[TopicName], short_title: bool = False
) -> Set[str]:
    normalized_text = normalize(text)
    if topic:
        pattern = re.compile(
            ontology.topic_name_to_topic[topic].escaped_short_title_pattern
            if short_title
            else ontology.topic_name_to_topic[topic].escaped_pattern
        )
    else:
        pattern = ontology.title_compiled_pattern if short_title else ontology.general_compiled_pattern
    if not pattern.pattern:
        return set()
    matches = re.finditer(pattern, normalized_text)
    return {_extract_substring(normalized_text, *match.span()) for match in matches}


def parse(ontology: TopicOntology, text: str, short_title: bool = False) -> Set[TopicName]:
    return {ontology.pattern_to_topic[match] for match in detect_matched_patterns(ontology, text, None, short_title)}


TOPIC_ONTOLOGY = TopicOntology(ALL_TOPICS)
