import json
from lib.data import EnrichedString, StructuredText
from data.topics.patterns import TopicName, TOPIC_ONTOLOGY, TopicOntology
from typing import List, Set, Tuple
from collections import Counter

DATASET_JSON = json.load(open('data/topics/raw_exploration_dataset.json'))
TOPICS_COUNTER = Counter([topic for _, topics in DATASET_JSON for topic in topics.split('/')])
UNIQUE_TOPICS = {topic for topics in TOPICS_COUNTER for topic in topics.split('/')}


def extract_topic_titles(topic: str, dataset: List[Tuple[Tuple, str]]) -> List[str]:
    all_matched_titles = [tp[0] for tp, topics in dataset if topic in topics.split('/')]
    return [' > '.join(titles) for titles in all_matched_titles]


def _extract_topics_from_titles_and_content(
    all_titles: List[str], section_sentences: List[str], ontology: TopicOntology
) -> Set[TopicName]:
    title_topics = {topic for title in all_titles for topic in ontology.parse(title, True)}
    sentence_topics = {topic for sentence in section_sentences for topic in ontology.parse(sentence)}
    return title_topics.union(sentence_topics)


def _extract_topics(text: StructuredText, parent_titles: List[str], ontology: TopicOntology) -> Set[TopicName]:
    all_titles = parent_titles + [text.title.text]
    if text.sections:
        return {topic for section in text.sections for topic in _extract_topics(section, all_titles, ontology)}
    section_sentences = [al.text for al in text.outer_alineas if al.text]  # TODO: handle tables later
    return _extract_topics_from_titles_and_content(all_titles, section_sentences, ontology)


_Alineas = List[EnrichedString]
_Titles = List[str]
_Text = Tuple[_Titles, _Alineas]
_LabelizedText = Tuple[_Text, Set[TopicName]]


def _build_labelized_text(raw_text: Tuple[List, List], labels: str) -> _LabelizedText:
    text = raw_text[0], [EnrichedString.from_dict(dict_) for dict_ in raw_text[1]]
    topics = set()
    for topic in labels.split('/'):
        try:
            topics.add(TopicName(topic))
        except ValueError:
            print(f'Missing {topic}')
    return text, topics


def _load_dataset(dataset_json: List[Tuple]) -> List[_LabelizedText]:
    return [_build_labelized_text(*elt) for elt in dataset_json]


def compute_detection_performance(dataset: List[_LabelizedText], ontology: TopicOntology):
    all_labels = [label for _, label in dataset]
    texts = [
        (titles, StructuredText(EnrichedString(''), outer_alineas, [], None, None))
        for (titles, outer_alineas), _ in dataset
    ]

    predicted_labels = [_extract_topics(text, titles, ontology) for titles, text in texts]
    print(Counter([exp == pred for exp, pred in zip(all_labels, predicted_labels) if exp]))


if __name__ == '__main__':
    DATASET = _load_dataset(DATASET_JSON)
    compute_detection_performance(DATASET, TOPIC_ONTOLOGY)
