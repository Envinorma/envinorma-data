"""Generate very simple topics for AMs."""
import re
from copy import copy
from typing import Counter, List, Optional, Union

from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.structured_text import Annotations, StructuredText
from envinorma.models.text_elements import Title
from envinorma.topics.patterns import TopicName, merge_patterns, normalize

_Section = Union[StructuredText, ArreteMinisteriel]

_ONTOLOGY_RAW = {
    TopicName.DISPOSITIONS_GENERALES: ['dispositions générales'],
    TopicName.IMPLANTATION_AMENAGEMENT: ['implantation'],
    TopicName.EXPLOITATION: ['exploitation entretien', 'exploitation et entretien'],
    TopicName.RISQUES: ['risques', 'accident', 'accidents'],
    TopicName.EAU: ['eau', 'eaux'],
    TopicName.AIR_ODEURS: ['air', 'odeurs', 'pollution atmosphérique'],
    TopicName.DECHETS: ['déchets', 'dechet'],
    TopicName.BRUIT_VIBRATIONS: ['bruit', 'bruits', 'vibrations', 'nuisances acoustiques'],
    TopicName.FIN_EXPLOITATION: ['remise en état', "Fin d'exploitation"],
}

SIMPLE_ONTOLOGY = {topic: merge_patterns(list(map(normalize, patterns))) for topic, patterns in _ONTOLOGY_RAW.items()}


def _extract_titles(section: _Section, depth: int) -> List[Title]:
    return [Title(section.title.text, depth)] + [
        title for sec in section.sections for title in _extract_titles(sec, depth + 1)
    ]


def _detect(text: str) -> Optional[TopicName]:
    prepared_text = normalize(text)
    for topic, patterns in SIMPLE_ONTOLOGY.items():
        if list(re.finditer(patterns, prepared_text)):
            return topic
    return None


_MAX_DEPTH = 6
_MIN_NB_MATCHES = 3


def _detect_first_matching_depth(section: _Section) -> Optional[int]:
    titles = _extract_titles(section, 0)
    matching_titles = [title for title in titles if _detect(title.text)]
    depths = [title.level for title in matching_titles]
    if not depths:
        return None
    occurrences = Counter(depths)
    for depth in range(1, _MAX_DEPTH):
        if occurrences[depth] >= _MIN_NB_MATCHES:
            return depth
    return None


def _detect_and_add_topics(section: StructuredText, matching_depth: int, current_depth: int = 0) -> StructuredText:
    section = copy(section)
    topic = _detect(section.title.text) if matching_depth == current_depth else None
    section.annotations = Annotations(topic)
    section.sections = [_detect_and_add_topics(sec, matching_depth, current_depth + 1) for sec in section.sections]
    return section


def add_simple_topics(am: ArreteMinisteriel) -> ArreteMinisteriel:
    """Add simple topics to AM sections.

    We first look for the depth in the am structure at which at least 3 titles match the ontology.
    Then we detect topics for all titles at this depth.

    Args:
        am (ArreteMinisteriel): arrete ministeriel to decorate.

    Returns:
        ArreteMinisteriel: arrete ministeriel with simple topics where detected.
    """
    target_depth = _detect_first_matching_depth(am)
    if target_depth is None or target_depth == 0:
        return am
    am = copy(am)
    am.sections = [_detect_and_add_topics(sec, target_depth, 1) for sec in am.sections]
    return am
