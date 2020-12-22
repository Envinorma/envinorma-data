from typing import List, Set, Tuple
from collections import Counter, defaultdict
from data.topics.raw_exploration_dataset import DATASET, _LabelizedText
from lib.data import EnrichedString, StructuredText
from lib.topics.patterns import TopicName, tokenize
from lib.topics.topics import TopicName, TOPIC_ONTOLOGY, TopicOntology

TOPICS_COUNTER = Counter([topic for _, topics in DATASET for topic in topics])
UNIQUE_TOPICS = set(TOPICS_COUNTER)


def extract_topic_titles(topic: str, dataset: List[Tuple[Tuple, str]]) -> List[str]:
    all_matched_titles = [tp[0] for tp, topics in dataset if topic in topics.split('/')]
    return [' > '.join(titles) for titles in all_matched_titles]


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


def _extract_topics(text: StructuredText, parent_titles: List[str], ontology: TopicOntology) -> Set[TopicName]:
    all_titles = parent_titles + [text.title.text]
    if text.sections:
        return {topic for section in text.sections for topic in _extract_topics(section, all_titles, ontology)}
    section_sentences = [al.text for al in text.outer_alineas if al.text]
    return _extract_topics_from_titles_and_content(all_titles, section_sentences, ontology)


def _detect_in_normal_texts(strs: List[str], ontology: TopicOntology) -> Set[TopicName]:
    return {topic for st in strs for topic in ontology.parse(st)}


def _detect_title_matched_patterns(title: str, ontology: TopicOntology, topic: TopicName) -> Set[str]:
    return ontology.detect_matched_patterns(title, topic, _is_sentence_short(title))


def _analyze_wrong_detection(
    labels: Set[TopicName], titles: List[str], text: StructuredText, ontology: TopicOntology
) -> List:
    all_titles = titles + [text.title.text]
    section_sentences = [al.text for al in text.outer_alineas if al.text]
    detected_topics = _detect_in_titles(all_titles, ontology).union(
        _detect_in_normal_texts(section_sentences, ontology)
    )
    wrong_detections = detected_topics - labels
    sentence_and_wrong_patterns = []
    if wrong_detections:
        for topic in wrong_detections:
            for title in all_titles:
                patterns = _detect_title_matched_patterns(title, ontology, topic)
                if patterns:
                    sentence_and_wrong_patterns.append((title, patterns, topic))
            for sentence in section_sentences:
                patterns = ontology.detect_matched_patterns(sentence, topic)
                if patterns:
                    sentence_and_wrong_patterns.append((sentence, patterns, topic))
    return sentence_and_wrong_patterns


def _analyze_missed_topics(
    labels: Set[TopicName], titles: List[str], text: StructuredText, ontology: TopicOntology
) -> Set[TopicName]:
    detected_topics = _extract_topics(text, titles, ontology)
    missing_topics = labels - detected_topics
    if missing_topics:
        return missing_topics
    return set()


def pretty_print(topic: TopicName, texts: List[Tuple[int, List[str], StructuredText]]) -> None:
    print(topic.value)
    for rank, titles, text in texts:
        print(rank)
        for title in titles:
            print(f'\t{title}')
        for al in text.outer_alineas:
            if al.table:
                print(f'\t\tTable')
            else:
                print(f'\t\t{al.text}')
        print()


def compute_detection_performance(dataset: List[_LabelizedText], ontology: TopicOntology):
    all_labels = [label for _, label in dataset]
    texts = [
        (titles, StructuredText(EnrichedString(''), outer_alineas, [], None)) for (titles, outer_alineas), _ in dataset
    ]
    missing_topics_to_elements = defaultdict(list)
    for rank, (labels, (titles, text)) in enumerate(zip(all_labels, texts)):
        wrong_detections = _analyze_wrong_detection(labels, titles, text, ontology)
        missing_topics = _analyze_missed_topics(labels, titles, text, ontology)
        if wrong_detections or missing_topics:
            print(rank)
            print(wrong_detections)
            print(f'Missing: {missing_topics}')
        for topic in missing_topics:
            missing_topics_to_elements[topic].append((rank, titles, text))
    for topic, texts_ in missing_topics_to_elements.items():
        pretty_print(topic, texts_)
    predicted_labels = [_extract_topics(text, titles, ontology) for titles, text in texts]
    print(Counter([exp == pred for exp, pred in zip(all_labels, predicted_labels) if exp]))


if __name__ == '__main__':
    compute_detection_performance(DATASET, TOPIC_ONTOLOGY)
