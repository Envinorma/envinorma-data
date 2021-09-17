from collections import Counter
from typing import TYPE_CHECKING, Dict, List, Set, Tuple, TypeVar

if TYPE_CHECKING:
    # Only solution to avoid a circular import
    from envinorma.models.arrete_ministeriel import ArreteMinisteriel

T = TypeVar('T')


def _elements_present_once(elements: List[T]) -> Set[T]:
    elements_count = Counter(elements)
    return {element for element, count in elements_count.items() if count == 1}


def _common_unique_titles(
    section_id_to_titles: Dict[str, List[str]], other_section_id_to_titles: Dict[str, List[str]]
) -> Set[str]:
    titles = [titles[-1] for titles in section_id_to_titles.values()]
    other_titles = [titles[-1] for titles in other_section_id_to_titles.values()]
    return _elements_present_once(titles).intersection(_elements_present_once(other_titles))


def _common_unique_title_pairs(
    section_id_to_titles: Dict[str, List[str]], other_section_id_to_titles: Dict[str, List[str]]
) -> Set[Tuple[str, ...]]:
    title_pairs = [tuple(titles[-2:]) for titles in section_id_to_titles.values()]
    other_title_pairs = [tuple(titles[-2:]) for titles in other_section_id_to_titles.values()]
    return _elements_present_once(title_pairs).intersection(_elements_present_once(other_title_pairs))


def _build_titles_to_id_map(
    section_id_to_titles: Dict[str, List[str]], unique_titles: Set[str], unique_title_pairs: Set[Tuple[str, ...]]
) -> Dict[Tuple[str, ...], str]:
    titles_to_section_id: Dict[Tuple[str, ...], str] = {}
    for section_id, titles in section_id_to_titles.items():
        if titles[-1] in unique_titles:
            titles_to_section_id[(titles[-1],)] = section_id
        elif tuple(titles[-2:]) in unique_title_pairs:
            titles_to_section_id[tuple(titles[-2:])] = section_id
    return titles_to_section_id


def _transfer_ids(am: 'ArreteMinisteriel', id_map: Dict[str, str]) -> None:
    for section in am.descendent_sections():
        section.id = id_map.get(section.id, section.id)


def transfer_ids_based_on_other_am(am: 'ArreteMinisteriel', other_am: 'ArreteMinisteriel') -> Dict[str, List[str]]:
    """Set am sections ids based on the ids of sections of other_am.

    It uses title values to identify sections. If title is unique in both AM, ids are set to the same value.
    Otherwise, we use the pair (title, parent section title) to identify sections.
    If none matches, id is left unchanged.

    Args:
        am: the AM to modify
        other_am: the other AM to use as a reference

    Returns:
        ids_to_titles: a map from section ids to titles from other_am which were not found in am
    """
    section_id_to_titles = am.titles_sequences()
    other_section_id_to_titles = other_am.titles_sequences()
    unique_titles = _common_unique_titles(section_id_to_titles, other_section_id_to_titles)
    unique_title_pairs = _common_unique_title_pairs(section_id_to_titles, other_section_id_to_titles)
    titles_to_section_id = _build_titles_to_id_map(section_id_to_titles, unique_titles, unique_title_pairs)
    other_titles_to_section_id = _build_titles_to_id_map(other_section_id_to_titles, unique_titles, unique_title_pairs)
    id_map = {
        section_id: other_titles_to_section_id[titles]
        for titles, section_id in titles_to_section_id.items()
        if titles in other_titles_to_section_id
    }
    _transfer_ids(am, id_map)
    mapped_ids = set(id_map.values())
    return {id_: titles for id_, titles in other_section_id_to_titles.items() if id_ not in mapped_ids}
