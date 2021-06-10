import json

from envinorma.am_enriching import (
    _remove_html,
    _split_rows,
    add_inspection_sheet_in_table_rows,
    add_topics,
    remove_prescriptive_power,
    remove_sections,
)
from envinorma.data import ArreteMinisteriel, EnrichedString, StructuredText, Table
from envinorma.data.text_elements import Cell, Row, estr
from envinorma.topics.patterns import TopicName


def test_add_topics():
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [], [], None)
    am = ArreteMinisteriel(EnrichedString('arrete du 10/10/10'), [section_1, section_2], [], None, id='FAKE_ID')

    am_with_topics = add_topics(
        am, {(0,): TopicName.INCENDIE, (0, 0): TopicName.INCENDIE, (1,): TopicName.BRUIT_VIBRATIONS}
    )
    assert am_with_topics.sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_topics.sections[0].sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_topics.sections[1].annotations.topic == TopicName.BRUIT_VIBRATIONS

    am_with_non_prescriptive = remove_prescriptive_power(am_with_topics, {(1,)})
    assert am_with_non_prescriptive.sections[0].annotations.prescriptive
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.prescriptive
    assert not am_with_non_prescriptive.sections[1].annotations.prescriptive

    assert am_with_non_prescriptive.sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_non_prescriptive.sections[1].annotations.topic == TopicName.BRUIT_VIBRATIONS


def test_remove_sections():
    sub_sub_sections = [
        StructuredText(EnrichedString('1.1. azeaze'), [], [], None),
        StructuredText(EnrichedString('1. 2. azeaze'), [], [], None),
    ]
    sub_sections = [StructuredText(EnrichedString('1. azeaze'), [], sub_sub_sections, None)]
    sections = [
        StructuredText(EnrichedString('Article 1. efzefz'), [], sub_sections, None),
        StructuredText(EnrichedString('2. zefez'), [], [], None),
        StructuredText(EnrichedString('A. zefze'), [], [], None),
    ]
    am = ArreteMinisteriel(EnrichedString('Arrete du 10/10/10'), sections, [], None, id='FAKE_ID')

    am_1 = remove_sections(am, {(0,)})
    assert len(am_1.sections) == 2
    assert len(am_1.sections[0].sections) == 0
    am_2 = remove_sections(am, {(1,)})
    assert len(am_2.sections) == 2
    assert len(am_2.sections[0].sections) == 1
    am_3 = remove_sections(am, {(0, 0)})
    assert len(am_3.sections) == 3
    assert len(am_3.sections[0].sections) == 0
    am_4 = remove_sections(am, {(0, 0, 1), (0, 0, 0)})
    assert len(am_4.sections) == 3
    assert len(am_4.sections[0].sections) == 1
    assert len(am_4.sections[0].sections[0].sections) == 0


def test_add_inspection_sheet_in_table_rows():
    string = EnrichedString('Hello')
    assert not add_inspection_sheet_in_table_rows(string).table
    assert add_inspection_sheet_in_table_rows(string).text == string.text

    header_cells = [Cell(EnrichedString('Header 1'), 1, 1), Cell(EnrichedString('Header 2'), 1, 1)]
    content_cells = [Cell(EnrichedString('content 1'), 1, 1), Cell(EnrichedString('content 2'), 1, 1)]
    string = EnrichedString('', table=Table([Row(header_cells, True), Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[0].text_in_inspection_sheet is None
    assert transformed_string.table.rows[1].text_in_inspection_sheet == 'Header 1\ncontent 1\nHeader 2\ncontent 2'

    header_cells = [Cell(EnrichedString('Header 1'), 2, 1), Cell(EnrichedString('Header 2'), 1, 1)]
    content_cells = [
        Cell(EnrichedString('content 1'), 1, 1),
        Cell(EnrichedString('content 2'), 1, 1),
        Cell(EnrichedString('content 3'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(header_cells, True), Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[0].text_in_inspection_sheet is None
    expected = 'Header 1\ncontent 1\nHeader 1\ncontent 2\nHeader 2\ncontent 3'
    assert transformed_string.table.rows[1].text_in_inspection_sheet == expected

    content_cells = [
        Cell(EnrichedString('content 1'), 1, 1),
        Cell(EnrichedString('content 2'), 1, 1),
        Cell(EnrichedString('content 3'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[0].text_in_inspection_sheet == 'content 1\ncontent 2\ncontent 3'

    content_cells = [
        Cell(EnrichedString('\n\n\ncontent\n\n 1'), 1, 1),
        Cell(EnrichedString('content\n\n 2'), 1, 1),
        Cell(EnrichedString('content 3\n\n'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[0].text_in_inspection_sheet == 'content\n 1\ncontent\n 2\ncontent 3'

    header_cells = [Cell(estr('A'), 1, 1), Cell(estr('B'), 2, 1)]
    content_cells = [Cell(estr('a'), 1, 1), Cell(estr('b'), 1, 1), Cell(estr('c'), 1, 1)]
    string = EnrichedString('', table=Table([Row(header_cells, True), Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[1].text_in_inspection_sheet == 'A\na\nB\nb\nB\nc'

    header_cells = [Cell(estr('A'), 1, 1), Cell(estr('B'), 1, 1), Cell(estr('C'), 1, 1)]
    row_1 = Row([Cell(estr('a'), 1, 2), Cell(estr('b'), 1, 1), Cell(estr('c'), 1, 1)], False)
    row_2 = Row([Cell(estr('d'), 1, 1), Cell(estr('e'), 1, 1)], False)
    string = EnrichedString('', table=Table([Row(header_cells, True), row_1, row_2]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[1].text_in_inspection_sheet == 'A\na\nB\nb\nC\nc'
    assert transformed_string.table.rows[2].text_in_inspection_sheet == 'A\na\nB\nd\nC\ne'


def test_remove_html():
    assert _remove_html('Hello<br/>How are you ?') == 'Hello\nHow are you ?'
    assert _remove_html('Hello    How are you ?') == 'Hello    How are you ?'
    assert _remove_html('') == ''
    assert _remove_html('<div></div>') == ''
    assert _remove_html('<a>URL</a>\n<p>P</p>') == 'URL\nP'


def test_split_rows():
    assert _split_rows([]) == ([], [])
    assert _split_rows([Row([], True)]) == ([Row([], True)], [])
    assert _split_rows([Row([], False)]) == ([], [Row([], False)])
    assert _split_rows([Row([], False), Row([], True)]) == ([], [Row([], False), Row([], True)])
    assert _split_rows([Row([], True), Row([], False)]) == ([Row([], True)], [Row([], False)])
