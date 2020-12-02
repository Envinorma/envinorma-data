import re
from copy import copy
from dataclasses import replace
from typing import Dict, List, Optional, Set, Tuple

from lib.data import (
    Annotations,
    Applicability,
    ArreteMinisteriel,
    EnrichedString,
    Hyperlink,
    Link,
    Row,
    StructuredText,
    Summary,
    SummaryElement,
)
from lib.structure_detection import NUMBERING_PATTERNS, ROMAN_PATTERN, NumberingPattern, detect_longest_matched_string
from lib.topics.patterns import TopicName, tokenize
from lib.topics.topics import TopicOntology

Ints = Tuple[int, ...]


def _add_topic_in_text(text: StructuredText, topics: Dict[Ints, TopicName], path: Ints) -> StructuredText:
    result = copy(text)
    if path in topics:
        result.annotations = replace(text.annotations or Annotations(), topic=topics[path])
    result.sections = [_add_topic_in_text(sec, topics, path + (i,)) for i, sec in enumerate(text.sections)]
    return result


def add_topics(am: ArreteMinisteriel, topics: Dict[Ints, TopicName]) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [_add_topic_in_text(sec, topics, (i,)) for i, sec in enumerate(am.sections)]
    return result


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
    result = copy(text)
    title = text.title.text
    topic = _detect_main_topic(text, titles, ontology)
    if topic:
        result.annotations = replace(text.annotations or Annotations(), topic=topic)
    result.sections = [_detect_and_add_topic_in_text(sec, ontology, titles + [title]) for sec in text.sections]
    return result


def detect_and_add_topics(am: ArreteMinisteriel, ontology: TopicOntology) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [_detect_and_add_topic_in_text(sec, ontology, []) for sec in am.sections]
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


def _remove_text_sections(text: StructuredText, to_remove: Set[Ints], path: Ints) -> StructuredText:
    result = copy(text)
    result.sections = [
        _remove_text_sections(sec, to_remove, path + (i,))
        for i, sec in enumerate(text.sections)
        if path + (i,) not in to_remove
    ]
    return result


def remove_sections(am: ArreteMinisteriel, to_remove: Set[Ints]) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [
        _remove_text_sections(sec, to_remove, (i,)) for i, sec in enumerate(am.sections) if (i,) not in to_remove
    ]
    return result


def _is_probably_section_number(candidate: str) -> bool:
    if not candidate.isalpha():
        return True
    if len(candidate) <= 2:
        return True
    if re.match(ROMAN_PATTERN, candidate):
        return True
    return False


def _extract_article_prefix(title: str) -> Optional[str]:
    split = title.split(' ')
    if len(split) == 0:
        return None
    if len(split) == 1:
        return 'Art.'
    if split[1].lower() == 'annexe':
        return _extract_annexe_prefix(' '.join(split[1:]))
    article_number = split[1]
    if _is_probably_section_number(article_number):
        return 'Art. ' + article_number
    return 'Art. ?'


def _extract_annexe_prefix(title: str) -> Optional[str]:
    split = title.split(' ')
    if len(split) == 0:
        return None
    if len(split) == 1:
        return 'Annexe'
    annexe_number = split[1]
    if _is_probably_section_number(annexe_number):
        return 'Annexe ' + annexe_number
    return 'Annexe ?'


def _extract_special_prefix(title: str) -> Optional[str]:
    if title.lower()[:7] == 'article':
        return _extract_article_prefix(title)
    if title.lower()[:6] == 'annexe':
        return _extract_annexe_prefix(title)
    return None


def _extract_prefix(title: str) -> Optional[str]:
    special_prefix = _extract_special_prefix(title)
    if special_prefix:
        return special_prefix
    res = detect_longest_matched_string(title)
    return res.replace(' ', '') if res else res


_VERBOSE_NUMBERING_PATTERNS = [
    NUMBERING_PATTERNS[_pat].replace(' ', '')
    for _pat in (
        NumberingPattern.NUMERIC_D1,
        NumberingPattern.NUMERIC_D2,
        NumberingPattern.NUMERIC_D3,
        NumberingPattern.NUMERIC_D3_SPACE,
        NumberingPattern.NUMERIC_D4_SPACE,
        NumberingPattern.NUMERIC_D2_DASH,
        NumberingPattern.NUMERIC_D3_DASH,
    )
]


def _is_verbose_numbering(str_: str) -> bool:
    return any([re.match(pat, str_) for pat in _VERBOSE_NUMBERING_PATTERNS])


def _are_consecutive_verbose_numbering(str_1: str, str_2: str) -> bool:
    return _is_verbose_numbering(str_1) and _is_verbose_numbering(str_1) and str_2[: len(str_1)] == str_1


def _is_prefix(candidate: Optional[str], long_word: Optional[str]) -> bool:
    if not candidate or not long_word:
        return False
    candidate_strip = candidate.replace(' ', '')
    long_word_strip = long_word.replace(' ', '')
    return _are_consecutive_verbose_numbering(candidate_strip, long_word_strip)


_PREFIX_SEPARATOR = ' '


def _merge_prefix_list(prefixes: List[Optional[str]]) -> str:
    if len(prefixes) == 0:
        raise ValueError('should have at least one prefix')
    if len(prefixes) == 1:
        return prefixes[0] or '?'
    if _is_prefix(prefixes[0], prefixes[1]):
        return _merge_prefix_list(prefixes[1:])
    return (prefixes[0] or '?') + _PREFIX_SEPARATOR + _merge_prefix_list(prefixes[1:])


def add_references_in_section(section: StructuredText, previous_prefixes: List[Optional[str]]) -> StructuredText:
    result = copy(section)
    del section
    if previous_prefixes or result.legifrance_article:
        prefixes = previous_prefixes + [_extract_prefix(result.title.text)]
        result.reference_str = _merge_prefix_list(prefixes)
    else:
        prefixes = []
    result.sections = [add_references_in_section(subsection, prefixes) for subsection in result.sections]
    return result


def add_references(am: ArreteMinisteriel) -> ArreteMinisteriel:
    result = copy(am)
    result.sections = [add_references_in_section(section, []) for section in am.sections]
    return result


def _extract_titles_and_reference_pairs_from_section(text: StructuredText) -> List[Tuple[str, str]]:
    return [(text.title.text, text.reference_str or '')] + [
        pair for section in text.sections for pair in _extract_titles_and_reference_pairs_from_section(section)
    ]


def extract_titles_and_reference_pairs(am: ArreteMinisteriel) -> List[Tuple[str, str]]:
    return [pair for section in am.sections for pair in _extract_titles_and_reference_pairs_from_section(section)]


def _minify_section(text: StructuredText) -> StructuredText:
    return StructuredText(
        text.title,
        [],
        [_minify_section(sec) for sec in text.sections],
        replace(text.legifrance_article, content='') if text.legifrance_article else None,
        None,
    )


def _minify_am(am: ArreteMinisteriel) -> ArreteMinisteriel:
    return ArreteMinisteriel(am.title, [_minify_section(sec) for sec in am.sections], [], '', None, None)


def remove_null_applicabilities_in_section(paragraph: StructuredText) -> StructuredText:
    new_paragraph = copy(paragraph)
    del paragraph
    new_paragraph.applicability = new_paragraph.applicability or Applicability(True)
    new_paragraph.sections = [remove_null_applicabilities_in_section(section) for section in new_paragraph.sections]
    return new_paragraph


def remove_null_applicabilities(am: ArreteMinisteriel) -> ArreteMinisteriel:
    new_am = copy(am)
    del am
    new_am.applicability = new_am.applicability or Applicability(True)
    new_am.sections = [remove_null_applicabilities_in_section(section) for section in new_am.sections]
    return new_am


def generate_re_pattern_not_followed_by_alphanumeric(str_: str) -> str:
    return re.escape(str_) + r'(?![a-zA-Z0-9])'


def generate_found_links(str_to_parse: str, str_to_target: Dict[str, str]) -> List[Link]:
    return [
        (Link(target=target, position=match.span()[0], content_size=len(str_)))
        for str_, target in str_to_target.items()
        for match in re.finditer(generate_re_pattern_not_followed_by_alphanumeric(str_), str_to_parse)
    ]


def add_links_in_enriched_string(enriched_str: EnrichedString, str_to_target: Dict[str, str]) -> EnrichedString:
    enriched_str = copy(enriched_str)
    enriched_str.links = enriched_str.links + generate_found_links(enriched_str.text, str_to_target)
    return enriched_str


def add_links_in_section(section: StructuredText, str_to_target: Dict[str, str]) -> StructuredText:
    section_copy = copy(section)
    section_copy.title = add_links_in_enriched_string(section.title, str_to_target)
    section_copy.outer_alineas = [
        add_links_in_enriched_string(alinea, str_to_target) for alinea in section.outer_alineas
    ]
    section_copy.sections = [add_links_in_section(subsection, str_to_target) for subsection in section.sections]
    return section_copy


def add_links_to_am(text: ArreteMinisteriel, new_hyperlinks: List[Hyperlink]) -> ArreteMinisteriel:
    str_to_target = {link.content: link.href for link in new_hyperlinks}
    output_text = copy(text)
    output_text.sections = [add_links_in_section(section, str_to_target) for section in text.sections]
    output_text.visa = [add_links_in_enriched_string(str_, str_to_target) for str_ in text.visa]
    return output_text


def _remove_last_word(sentence: str) -> str:
    return ' '.join(sentence.split(' ')[:-1])


MAX_TITLE_LEN = 64


def _shorten_summary_text(title: str, max_len: int = MAX_TITLE_LEN) -> str:
    if len(title) > max_len:
        return _remove_last_word(title[:max_len]) + ' [...]'
    return title


def _extract_summary_elements(text: StructuredText, depth: int) -> List[SummaryElement]:
    child_elements = [element for section in text.sections for element in _extract_summary_elements(section, depth + 1)]
    if not text.id:
        raise ValueError('Cannot generate summary without section ids.')
    return [SummaryElement(text.id, _shorten_summary_text(text.title.text), depth)] + child_elements


def _compute_summary(text: ArreteMinisteriel) -> Summary:
    return Summary([element for section in text.sections for element in _extract_summary_elements(section, 0)])


def add_summary(text: ArreteMinisteriel) -> ArreteMinisteriel:
    return replace(text, summary=_compute_summary(text))


def _extract_headers(rows: List[Row]) -> List[str]:
    if not rows or not rows[0].is_header:
        return []
    return [cell.content.text for cell in rows[0].cells for _ in range(cell.colspan)]


def _build_text_for_inspection_sheet(headers: List[str], row: Row) -> str:
    lines = []
    for header, cell in zip(headers, row.cells):
        lines.append(header)
        lines.append(cell.content.text)
    return '\n'.join(lines)


def add_inspection_sheet_in_table_rows(string: EnrichedString) -> EnrichedString:
    if not string.table:
        return string
    string = copy(string)
    headers = _extract_headers(string.table.rows)
    string.table.rows = [
        replace(row, text_in_inspection_sheet=_build_text_for_inspection_sheet(headers, row))
        if not row.is_header
        else row
        for row in string.table.rows
    ]
    return string


def add_table_inspection_sheet_data_in_section(section: StructuredText) -> StructuredText:
    section = copy(section)
    section.outer_alineas = [add_inspection_sheet_in_table_rows(alinea) for alinea in section.outer_alineas]
    section.sections = [add_table_inspection_sheet_data_in_section(subsection) for subsection in section.sections]
    return section


def add_table_inspection_sheet_data(am: ArreteMinisteriel) -> ArreteMinisteriel:
    am = copy(am)
    am.sections = [add_table_inspection_sheet_data_in_section(subsection) for subsection in am.sections]
    return am
