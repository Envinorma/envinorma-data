import re
from copy import copy
from dataclasses import replace
from typing import Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup

from envinorma.data import (
    Annotations,
    Applicability,
    ArreteMinisteriel,
    EnrichedString,
    Hyperlink,
    Link,
    StructuredText,
    Summary,
    SummaryElement,
    Table,
)
from envinorma.data.text_elements import Cell, Row, table_to_list
from envinorma.structure.title_detection import (
    NUMBERING_PATTERNS,
    ROMAN_PATTERN,
    NumberingPattern,
    detect_longest_matched_string,
)
from envinorma.topics.patterns import TopicName, tokenize
from envinorma.topics.topics import TopicOntology

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
    if title.lower().startswith('article'):
        return _extract_article_prefix(title)
    if title.lower().startswith('annexe'):
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
    if candidate.lower().startswith('annexe') and long_word.lower().startswith('annexe'):
        return True
    candidate_strip = candidate.replace(' ', '')
    long_word_strip = long_word.replace(' ', '')
    return _are_consecutive_verbose_numbering(candidate_strip, long_word_strip)


_PREFIX_SEPARATOR = ' '
_ANNEXE_OR_ARTICLE = ('annexe', 'article')


def _annexe_or_article(title: str) -> bool:
    for prefix in _ANNEXE_OR_ARTICLE:
        if title.lower().startswith(prefix):
            return True
    return False


def _cut_before_annexe_or_article(titles: List[str]) -> List[str]:
    for i, title in enumerate(titles):
        if _annexe_or_article(title):
            return titles[i:]
    return []


def _remove_empty(elements: List[str]) -> List[str]:
    return [el for el in elements if el]


def _merge_prefixes(prefixes: List[Optional[str]]) -> str:
    if len(prefixes) == 1:
        return prefixes[0] or ''
    if _is_prefix(prefixes[0], prefixes[1]):
        return _merge_prefixes(prefixes[1:])
    to_merge = _remove_empty([prefixes[0] or '', _merge_prefixes(prefixes[1:])])
    return _PREFIX_SEPARATOR.join(to_merge)


def _merge_titles(titles: List[str]) -> str:
    if len(titles) == 0:
        raise ValueError('should have at least one prefix')
    filtered_titles = _cut_before_annexe_or_article(titles)
    if len(filtered_titles) == 0:
        return ''
    prefixes = [_extract_prefix(title) for title in filtered_titles]
    return _merge_prefixes(prefixes)


def _add_references_in_section(text: StructuredText, titles: List[str]) -> StructuredText:
    titles = titles + [text.title.text]
    return replace(
        text,
        reference_str=_merge_titles(titles),
        sections=[_add_references_in_section(section, titles) for section in text.sections],
    )


def add_references(am: ArreteMinisteriel) -> ArreteMinisteriel:
    return replace(am, sections=[_add_references_in_section(section, []) for section in am.sections])


def _extract_titles_and_reference_pairs_from_section(text: StructuredText) -> List[Tuple[str, str]]:
    return [(text.title.text, text.reference_str or '')] + [
        pair for section in text.sections for pair in _extract_titles_and_reference_pairs_from_section(section)
    ]


def extract_titles_and_reference_pairs(am: ArreteMinisteriel) -> List[Tuple[str, str]]:
    return [pair for section in am.sections for pair in _extract_titles_and_reference_pairs_from_section(section)]


def _minify_section(text: StructuredText) -> StructuredText:
    return StructuredText(text.title, [], [_minify_section(sec) for sec in text.sections], None, lf_id=text.lf_id)


def remove_null_applicabilities_in_section(paragraph: StructuredText) -> StructuredText:
    new_paragraph = copy(paragraph)
    del paragraph
    new_paragraph.applicability = new_paragraph.applicability or Applicability()
    new_paragraph.sections = [remove_null_applicabilities_in_section(section) for section in new_paragraph.sections]
    return new_paragraph


def remove_null_applicabilities(am: ArreteMinisteriel) -> ArreteMinisteriel:
    am = copy(am)
    am.sections = [remove_null_applicabilities_in_section(section) for section in am.sections]
    return am


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


def _remove_unnecessary_line_breaks(string: str) -> str:
    pieces = string.split('\n')
    return '\n'.join([x for x in pieces if x])


def _build_text_for_inspection_sheet(headers: List[str], row: Row) -> str:
    cell_texts = [cell.content.text for cell in row.cells]
    if not headers:
        return _remove_unnecessary_line_breaks('\n'.join(cell_texts))
    lines = []
    for header, cell in zip(headers, cell_texts):
        lines.append(header)
        lines.append(cell)
    return _remove_unnecessary_line_breaks('\n'.join(lines))


def _incorporate(elements: List[str], elements_: List[str]) -> List[str]:
    lines = []
    for elt, elt_ in zip(elements, elements_):
        lines.append(elt)
        lines.append(elt_)
    return lines


def _merge_header_and_row(headers: List[str], cell_texts: List[str]) -> str:
    if not headers:
        lines = cell_texts
    else:
        lines = _incorporate(headers, cell_texts)
    return _remove_unnecessary_line_breaks('\n'.join(lines))


def _build_texts_for_inspection_sheet(headers: List[str], rows: List[Row]) -> List[str]:
    all_cell_texts = table_to_list(Table(rows))
    return [_merge_header_and_row(headers, cell_texts) for cell_texts in all_cell_texts]


def _split_rows(rows: List[Row]) -> Tuple[List[Row], List[Row]]:
    if not rows:
        return [], []
    i = 0
    for i, row in enumerate(rows):
        if not row.is_header:
            break
    if rows[i].is_header:
        i += 1
    return rows[:i], rows[i:]


def add_inspection_sheet_in_table_rows(string: EnrichedString) -> EnrichedString:
    table = string.table
    if not table:
        return string
    headers = _extract_headers(table.rows)
    top_header_rows, other_rows = _split_rows(table.rows)
    texts = [''] * len(top_header_rows) + _build_texts_for_inspection_sheet(headers, other_rows)
    new_rows = [
        replace(row, text_in_inspection_sheet=texts[row_rank]) if not row.is_header else row
        for row_rank, row in enumerate(table.rows)
    ]
    return replace(string, table=replace(table, rows=new_rows))


def add_table_inspection_sheet_data_in_section(section: StructuredText) -> StructuredText:
    section = copy(section)
    section.outer_alineas = [add_inspection_sheet_in_table_rows(alinea) for alinea in section.outer_alineas]
    section.sections = [add_table_inspection_sheet_data_in_section(subsection) for subsection in section.sections]
    return section


def add_table_inspection_sheet_data(am: ArreteMinisteriel) -> ArreteMinisteriel:
    return replace(am, sections=[add_table_inspection_sheet_data_in_section(subsection) for subsection in am.sections])


def _remove_html(str_: str) -> str:
    return '\n'.join(list(BeautifulSoup(f'<div>{str_}</div>', 'html.parser').stripped_strings))


def _remove_html_cell(cell: Cell) -> Cell:
    cell = copy(cell)
    cell.content.text = _remove_html(cell.content.text)
    return cell


def _remove_html_row(row: Row) -> Row:
    row = copy(row)
    row.cells = [_remove_html_cell(cell) for cell in row.cells]
    return row


def _remove_html_table(table: Table) -> Table:
    table = copy(table)
    table.rows = [_remove_html_row(row) for row in table.rows]
    return table


def _remove_html_string(text: EnrichedString) -> EnrichedString:
    if not text.table:
        return text
    return replace(text, table=_remove_html_table(text.table))


def _remove_table_html(text: StructuredText) -> StructuredText:
    text = copy(text)
    text.outer_alineas = [_remove_html_string(st) for st in text.outer_alineas]
    text.sections = [_remove_table_html(sec) for sec in text.sections]
    return text
