from envinorma.enriching.table_row_inline_content import _add_inline_content_in_table_rows, _split_rows
from envinorma.models.text_elements import Cell, EnrichedString, Row, Table, estr


def test_add_inline_content_in_table_rows():
    string = EnrichedString('Hello')
    assert not _add_inline_content_in_table_rows(string).table
    assert _add_inline_content_in_table_rows(string).text == string.text

    header_cells = [Cell(EnrichedString('Header 1'), 1, 1), Cell(EnrichedString('Header 2'), 1, 1)]
    content_cells = [Cell(EnrichedString('content 1'), 1, 1), Cell(EnrichedString('content 2'), 1, 1)]
    string = EnrichedString('', table=Table([Row(header_cells, True), Row(content_cells, False)]))
    transformed_string = _add_inline_content_in_table_rows(string)
    assert transformed_string.table.rows[0].inline_content is None
    assert transformed_string.table.rows[1].inline_content == 'Header 1\ncontent 1\nHeader 2\ncontent 2'

    header_cells = [Cell(EnrichedString('Header 1'), 2, 1), Cell(EnrichedString('Header 2'), 1, 1)]
    content_cells = [
        Cell(EnrichedString('content 1'), 1, 1),
        Cell(EnrichedString('content 2'), 1, 1),
        Cell(EnrichedString('content 3'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(header_cells, True), Row(content_cells, False)]))
    transformed_string = _add_inline_content_in_table_rows(string)
    assert transformed_string.table.rows[0].inline_content is None
    expected = 'Header 1\ncontent 1\nHeader 1\ncontent 2\nHeader 2\ncontent 3'
    assert transformed_string.table.rows[1].inline_content == expected

    content_cells = [
        Cell(EnrichedString('content 1'), 1, 1),
        Cell(EnrichedString('content 2'), 1, 1),
        Cell(EnrichedString('content 3'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(content_cells, False)]))
    transformed_string = _add_inline_content_in_table_rows(string)
    assert transformed_string.table.rows[0].inline_content == 'content 1\ncontent 2\ncontent 3'

    content_cells = [
        Cell(EnrichedString('\n\n\ncontent\n\n 1'), 1, 1),
        Cell(EnrichedString('content\n\n 2'), 1, 1),
        Cell(EnrichedString('content 3\n\n'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(content_cells, False)]))
    transformed_string = _add_inline_content_in_table_rows(string)
    assert transformed_string.table.rows[0].inline_content == 'content\n 1\ncontent\n 2\ncontent 3'

    header_cells = [Cell(estr('A'), 1, 1), Cell(estr('B'), 2, 1)]
    content_cells = [Cell(estr('a'), 1, 1), Cell(estr('b'), 1, 1), Cell(estr('c'), 1, 1)]
    string = EnrichedString('', table=Table([Row(header_cells, True), Row(content_cells, False)]))
    transformed_string = _add_inline_content_in_table_rows(string)
    assert transformed_string.table.rows[1].inline_content == 'A\na\nB\nb\nB\nc'

    header_cells = [Cell(estr('A'), 1, 1), Cell(estr('B'), 1, 1), Cell(estr('C'), 1, 1)]
    row_1 = Row([Cell(estr('a'), 1, 2), Cell(estr('b'), 1, 1), Cell(estr('c'), 1, 1)], False)
    row_2 = Row([Cell(estr('d'), 1, 1), Cell(estr('e'), 1, 1)], False)
    string = EnrichedString('', table=Table([Row(header_cells, True), row_1, row_2]))
    transformed_string = _add_inline_content_in_table_rows(string)
    assert transformed_string.table.rows[1].inline_content == 'A\na\nB\nb\nC\nc'
    assert transformed_string.table.rows[2].inline_content == 'A\na\nB\nd\nC\ne'


def test_split_rows():
    assert _split_rows([]) == ([], [])
    assert _split_rows([Row([], True)]) == ([Row([], True)], [])
    assert _split_rows([Row([], False)]) == ([], [Row([], False)])
    assert _split_rows([Row([], False), Row([], True)]) == ([], [Row([], False), Row([], True)])
    assert _split_rows([Row([], True), Row([], False)]) == ([Row([], True)], [Row([], False)])
