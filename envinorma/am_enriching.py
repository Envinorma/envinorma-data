from copy import copy
from dataclasses import replace
from typing import Dict, List, Optional, Set, Tuple

from bs4 import BeautifulSoup

from envinorma.data import Annotations, Applicability, ArreteMinisteriel, EnrichedString, StructuredText, Table
from envinorma.data.text_elements import Cell, Row, table_to_list
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


def _minify_section(text: StructuredText) -> StructuredText:
    return StructuredText(text.title, [], [_minify_section(sec) for sec in text.sections], None)


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
