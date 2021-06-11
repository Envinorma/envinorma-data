from typing import List, Optional, Tuple, TypeVar

from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import EnrichedString, Linebreak, Table, TextElement, Title

TP = TypeVar('TP')


def split_alineas_in_sections(alineas: List[TP], matches: List[bool]) -> Tuple[List[TP], List[List[TP]]]:
    found_any_match = False
    first_match = 0
    for first_match, match in enumerate(matches):
        if match:
            found_any_match = True
            break
    if not found_any_match:
        sections: List[List[TP]] = []
        return alineas, sections
    outer_alineas = alineas[:first_match]
    other_matches = [first_match + 1 + idx for idx, match in enumerate(matches[first_match + 1 :]) if match]
    sections = [alineas[a:b] for a, b in zip([first_match] + other_matches, other_matches + [len(matches)])]
    return (outer_alineas, sections)


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
    )


def _string_to_element(str_: EnrichedString) -> TextElement:
    if str_.table:
        return str_.table
    return str_.text


def structured_text_to_text_elements(text: StructuredText, level: int = 1) -> List[TextElement]:
    elements: List[TextElement] = []
    elements.append(Title(text.title.text, level, id=text.id))
    elements.extend([_string_to_element(st) for st in text.outer_alineas])
    for section in text.sections:
        elements.extend(structured_text_to_text_elements(section, level + 1))
    return elements
