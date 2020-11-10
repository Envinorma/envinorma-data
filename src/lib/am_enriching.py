from copy import copy
from typing import Dict, Set
from dataclasses import replace
from lib.parametric_am import Ints
from lib.data import Annotations, ArreteMinisteriel, StructuredText, Topic


def _add_topic_in_text(text: StructuredText, topics: Dict[Ints, Topic], path: Ints) -> StructuredText:
    result = copy(text)
    if path in topics:
        result.annotations = replace(text.annotations or Annotations(), topic=topics[path])
    result.sections = [_add_topic_in_text(sec, topics, path + (i,)) for i, sec in enumerate(text.sections)]
    return result


def add_topics(am: ArreteMinisteriel, topics: Dict[Ints, Topic]) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [_add_topic_in_text(sec, topics, (i,)) for i, sec in enumerate(am.sections)]
    return result


def _add_prescriptive_power_in_text(
    text: StructuredText, non_prescriptive_sections: Set[Ints], path: Ints
) -> StructuredText:
    result = copy(text)
    if path in non_prescriptive_sections:
        result.annotations = replace(text.annotations or Annotations(), prescriptive=False)
    result.sections = [
        _add_prescriptive_power_in_text(sec, non_prescriptive_sections, path + (i,))
        for i, sec in enumerate(text.sections)
    ]
    return result


def remove_prescriptive_power(am: ArreteMinisteriel, non_prescriptive_sections: Set[Ints]) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [
        _add_prescriptive_power_in_text(sec, non_prescriptive_sections, (i,)) for i, sec in enumerate(am.sections)
    ]
    return result
