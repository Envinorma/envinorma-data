from dataclasses import dataclass
from typing import List, Optional, Tuple, Union
from lib.data import EnrichedString, StructuredText, Table
from lib.am_structure_extraction import split_alineas_in_sections


class Linebreak:
    pass


@dataclass
class Title:
    text: str
    level: int


TextElement = Union[Table, str, Title, Linebreak]


def _has_a_title(alineas: List[TextElement]) -> bool:
    for alinea in alineas:
        if isinstance(alinea, Title):
            return True
    return False


def _build_enriched_alineas(alineas: List[TextElement]) -> Tuple[List[EnrichedString], List[StructuredText]]:
    if _has_a_title(alineas):
        structured_text = build_structured_text(None, alineas)
        return structured_text.outer_alineas, structured_text.sections
    result: List[EnrichedString] = []
    for alinea in alineas:
        if isinstance(alinea, Table):
            result.append(EnrichedString('', table=alinea))
        elif isinstance(alinea, str):
            result.append(EnrichedString(alinea))
        elif isinstance(alinea, Linebreak):
            continue
        else:
            if isinstance(alinea, Title):
                print(alinea.text)
            raise ValueError(f'Unexpected element type {type(alinea)} here.')
    return result, []


def _extract_highest_title_level(elements: List[TextElement]) -> int:
    levels = [element.level for element in elements if isinstance(element, Title)]
    return min(levels) if levels else -1


def build_structured_text(title: Optional[TextElement], elements: List[TextElement]) -> StructuredText:
    if title and not isinstance(title, Title):
        raise ValueError(f'Expecting title to be of type Title not {type(title)}')
    built_title = EnrichedString('' if not title or not isinstance(title, Title) else title.text)
    highest_level = _extract_highest_title_level(elements)
    matches = [bool(isinstance(elt, Title) and elt.level == highest_level) for elt in elements]
    outer, subsections = split_alineas_in_sections(elements, matches)
    outer_alineas, previous_sections = _build_enriched_alineas(
        outer
    )  # There can be a lower level title in previous alineas
    built_subsections = [
        build_structured_text(
            alinea_group[0],
            alinea_group[1:],
        )
        for alinea_group in subsections
    ]
    return StructuredText(
        built_title,
        outer_alineas,
        previous_sections + built_subsections,
        None,
        None,
    )