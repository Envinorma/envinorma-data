from bs4 import BeautifulSoup, Tag
from typing import List
from lib.data import EnrichedString, Row, Cell
from lib.docx import (
    Style,_copy_soup,
    _extract_property_value,
    _extract_bool_property_value,
    _extract_bold,
    _extract_italic,
    _extract_size,
    _extract_font_name,
    _extract_color,
    _build_table_with_correct_rowspan,
    _is_header,
    _remove_table_inplace,
    _replace_small_tables,
    extract_table,
    extract_w_tag_style,
    get_docx_xml,
    remove_empty,
    remove_duplicate_line_break,
    extract_cell,
    extract_row,
)

_PREFIX = '''<?xml version="1.0" encoding="utf-8"?>\n<w:document mc:Ignorable="w14 wp14" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'''


def test__extract_property_value():
    tag = BeautifulSoup(f'{_PREFIX}<w:bottom w:color="#000000" w:sz="2.4" w:val="single"/>', 'lxml-xml')
    assert _extract_property_value(tag, 'bottom') == "single"
    assert _extract_property_value(tag, 'bottom', 'w:val') == "single"
    assert _extract_property_value(tag, 'bottom', 'w:color') == "#000000"


def test__extract_bool_property_value():
    tag = BeautifulSoup(f'{_PREFIX}<w:b w:val="0"/>', 'lxml-xml')
    assert not _extract_bool_property_value(tag, 'w:b')
    tag = BeautifulSoup(f'{_PREFIX}<w:b w:val="1"/>', 'lxml-xml')
    assert _extract_bool_property_value(tag, 'w:b')
    tag = BeautifulSoup(f'{_PREFIX}<w:b/>', 'lxml-xml')
    assert _extract_bool_property_value(tag, 'w:b')


def test__extract_bold():
    assert _extract_bold(BeautifulSoup(f'{_PREFIX}<b/>', 'lxml-xml'))


def test__extract_italic():
    assert _extract_italic(BeautifulSoup(f'{_PREFIX}<i/>', 'lxml-xml'))


def test__extract_size():
    assert _extract_size(BeautifulSoup(f'{_PREFIX}<sz w:val="10" />', 'lxml-xml')) == 10


def test__extract_font_name():
    assert (
        _extract_property_value(
            BeautifulSoup(f'{_PREFIX}<w:rFonts w:ascii="Times" />', 'lxml-xml'), 'rFonts', 'w:ascii'
        )
        == 'Times'
    )
    assert _extract_font_name(BeautifulSoup(f'{_PREFIX}<w:rFonts w:ascii="Times" />', 'lxml-xml')) == 'Times'


def test__extract_color():
    assert _extract_color(BeautifulSoup(f'{_PREFIX}<color w:val="FF0000" />', 'lxml-xml')) == 'FF0000'


def test_extract_w_tag_style():
    tag = BeautifulSoup(
        f'''{_PREFIX} <rPr>
    <w:rFonts w:ascii="Times" w:eastAsia="Times" w:hAnsi="Times"/>
    <w:b w:val="1"/>
    <w:i w:val="0"/>
    <w:color w:val="000000"/>
    <w:sz w:val="20"/>
</rPr>
''',
        'lxml-xml',
    )
    assert extract_w_tag_style(tag) == Style(True, False, 20, 'Times', '000000')


def test_remove_empty():
    assert remove_empty(['', '', 'Hello']) == ['Hello']
    assert remove_empty(['Hello']) == ['Hello']
    assert remove_empty([]) == []


def test_remove_duplicate_line_break():
    assert remove_duplicate_line_break('Hello\n\nPipa\nHow are you ?') == 'Hello\nPipa\nHow are you ?'


def _random_cell() -> Cell:
    return Cell(EnrichedString(''), 1, 1)


def _random_cells(n: int) -> List[Cell]:
    return [_random_cell() for _ in range(n)]


def test_is_header():
    str_tag = f'''{_PREFIX}    <w:tc>
     <w:tcPr>
      <w:tcW w:type="dxa" w:w="3212"/>
      <w:tcBorders>
       <w:top w:color="000000" w:space="0" w:sz="2" w:val="single"/>
       <w:left w:color="000000" w:space="0" w:sz="2" w:val="single"/>
       <w:bottom w:color="000000" w:space="0" w:sz="2" w:val="single"/>
      </w:tcBorders>
     </w:tcPr>
     <w:p>
      <w:pPr>
       <w:pStyle w:val="TableHeading"/>
       <w:suppressLineNumbers/>
       <w:bidi w:val="0"/>
       <w:jc w:val="center"/>
       <w:rPr/>
      </w:pPr>
      <w:r>
       <w:rPr/>
       <w:t>
        AA
       </w:t>
      </w:r>
     </w:p>
    </w:tc>
'''
    tag = BeautifulSoup(
        str_tag,
        'lxml-xml',
    )
    assert _is_header(tag)

    tag = BeautifulSoup(
        str_tag.replace('w:val="TableHeading"', 'w:val="TableContent"'),
        'lxml-xml',
    )
    assert not _is_header(tag)

    tag = BeautifulSoup(
        str_tag.replace('w:val="TableHeading"', ''),
        'lxml-xml',
    )
    assert not _is_header(tag)


def test_extract_cell():
    tc_tag = '<w:tc>\n<w:tcPr>\n<w:tcW w:type="dxa" w:w="3212"/>\n<w:tcBorders>\n<w:top w:color="000000" w:space="0" w:sz="2" w:val="single"/>\n<w:left w:color="000000" w:space="0" w:sz="2" w:val="single"/>\n<w:bottom w:color="000000" w:space="0" w:sz="2" w:val="single"/>\n</w:tcBorders>\n</w:tcPr>\n<w:p>\n<w:pPr>\n<w:pStyle w:val="TableHeading"/>\n<w:suppressLineNumbers/>\n<w:bidi w:val="0"/>\n<w:jc w:val="center"/>\n<w:rPr/>\n</w:pPr>\n<w:r>\n<w:rPr/>\n<w:t>\n    AA\n   </w:t>\n</w:r>\n</w:p>\n</w:tc>'
    str_tag = f'<?xml version="1.0" encoding="utf-8"?>\n<w:document mc:Ignorable="w14 wp14" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"> {tc_tag}</w:document>'
    tag = BeautifulSoup(str_tag, 'lxml-xml').find('w:tc')
    if not isinstance(tag, Tag):
        raise ValueError(f'Expecting Tag, not {type(tag)}')
    is_header, cell, v_merge = extract_cell(tag)
    assert is_header
    assert cell.colspan == 1
    assert cell.rowspan == 1
    assert v_merge is None
    assert cell.content.text == tc_tag


def test_build_table_with_correct_rowspan():
    assert _build_table_with_correct_rowspan([], []).rows == []
    table = _build_table_with_correct_rowspan([Row(_random_cells(4), False)], [[None, None, None, None]])
    assert not table.rows[0].is_header
    table = _build_table_with_correct_rowspan([Row(_random_cells(4), True)], [[None, None, None, None]])
    assert table.rows[0].is_header
    assert [cell.colspan for cell in table.rows[0].cells] == [1, 1, 1, 1]
    assert [cell.rowspan for cell in table.rows[0].cells] == [1, 1, 1, 1]

    table = _build_table_with_correct_rowspan([Row(_random_cells(4), True)], [[None, 'restart', None, None]])
    assert [cell.colspan for cell in table.rows[0].cells] == [1, 1, 1, 1]
    assert [cell.rowspan for cell in table.rows[0].cells] == [1, 1, 1, 1]

    table = _build_table_with_correct_rowspan(
        [Row(_random_cells(1), True), Row(_random_cells(1), False), Row(_random_cells(1), False)],
        [['restart'], ['continue'], ['continue']],
    )
    assert [cell.colspan for cell in table.rows[0].cells] == [1]
    assert [cell.colspan for cell in table.rows[1].cells] == []
    assert [cell.colspan for cell in table.rows[2].cells] == []
    assert [cell.rowspan for cell in table.rows[0].cells] == [3]
    assert [cell.rowspan for cell in table.rows[1].cells] == []

    rows = [Row(_random_cells(4), True) for _ in range(3)]
    v_merge = [[None, 'restart', None, None], [None, 'continue', None, None], [None, 'continue', None, None]]
    table = _build_table_with_correct_rowspan(rows, v_merge)
    assert [cell.colspan for cell in table.rows[0].cells] == [1, 1, 1, 1]
    assert [cell.rowspan for cell in table.rows[0].cells] == [1, 3, 1, 1]
    assert [cell.rowspan for cell in table.rows[1].cells] == [1, 1, 1]
    assert [cell.rowspan for cell in table.rows[2].cells] == [1, 1, 1]

    rows = [Row(_random_cells(4), True) for _ in range(3)]
    v_merge = [[None, 'restart', None, None], [None, 'continue', None, None], [None, None, None, None]]
    table = _build_table_with_correct_rowspan(rows, v_merge)
    assert [cell.colspan for cell in table.rows[0].cells] == [1, 1, 1, 1]
    assert [cell.rowspan for cell in table.rows[0].cells] == [1, 2, 1, 1]
    assert [cell.rowspan for cell in table.rows[1].cells] == [1, 1, 1]
    assert [cell.rowspan for cell in table.rows[2].cells] == [1, 1, 1, 1]

    rows = [Row(_random_cells(3), True) for _ in range(4)]
    v_merge = [[None, 'restart', None], [None, 'continue', None], [None, 'restart', None], [None, 'continue', None]]
    table = _build_table_with_correct_rowspan(rows, v_merge)
    assert [cell.colspan for cell in table.rows[0].cells] == [1, 1, 1]
    assert [cell.rowspan for cell in table.rows[0].cells] == [1, 2, 1]
    assert [cell.rowspan for cell in table.rows[1].cells] == [1, 1]
    assert [cell.rowspan for cell in table.rows[2].cells] == [1, 2, 1]
    assert [cell.rowspan for cell in table.rows[3].cells] == [1, 1]


# Structure of table in test_data/table_docx.xml
# AA | BB | CC
# ------------
# DD |   EE
# ------------
# FF | GG | HH
#    |--------
#    | II | JJ


def test_extract_table():
    xml = open('test_data/table_docx.xml').read()
    table = extract_table(BeautifulSoup(xml, 'lxml-xml'))
    assert len(table.rows) == 4
    assert [len(row.cells) for row in table.rows] == [3, 2, 3, 2]
    assert [row.is_header for row in table.rows] == [True, False, False, False]
    expected_colspans = [
        [1, 1, 1],
        [1, 2],
        [1, 1, 1],
        [1, 1],
    ]
    expected_rowspans = [
        [1, 1, 1],
        [1, 1],
        [2, 1, 1],
        [1, 1],
    ]
    for i, row in enumerate(table.rows):
        assert [cell.rowspan == expected_rowspans[i][j] for j, cell in enumerate(row.cells)]
        assert [cell.colspan == expected_colspans[i][j] for j, cell in enumerate(row.cells)]


def test_extract_row():
    xml = open('test_data/table_docx.xml').read()
    soup = BeautifulSoup(xml, 'lxml-xml')
    rows = list(soup.find_all('w:tr'))
    assert len(extract_row(rows[0])[0].cells) == 3
    assert extract_row(rows[0])[0].is_header
    assert len(extract_row(rows[1])[0].cells) == 2
    assert len(extract_row(rows[2])[0].cells) == 3
    assert len(extract_row(rows[3])[0].cells) == 3
    for row in rows[1:]:
        assert not extract_row(row)[0].is_header


def test_get_docx_xml():
    xml = get_docx_xml('test_data/simple_table.docx')
    assert len(xml) == 6580


def test_remove_table_inplace():
    xml_str = open('test_data/table_docx.xml').read()
    soup = BeautifulSoup(xml_str, 'lxml-xml')
    assert len(list(soup.find_all('w:tbl'))) == 1
    assert len(list(soup.find_all('w:p'))) == 13
    assert len(list(soup.find_all('w:tc'))) == 11
    tag = soup.find('w:tbl')
    if not isinstance(tag, Tag):
        raise ValueError(f'Expecting tag, received {type(tag)}')
    table = extract_table(tag)
    _remove_table_inplace(soup, table, tag)
    assert len(list(soup.find_all('w:tbl'))) == 0
    assert len(list(soup.find_all('w:p'))) == 13
    assert len(list(soup.find_all('w:tc'))) == 0


def test_replace_small_tables():
    filename = 'test_data/small_table.docx'
    xml_str = get_docx_xml(filename)
    soup = BeautifulSoup(xml_str, 'lxml-xml')
    assert len(list(soup.find_all('w:tbl'))) == 1
    assert len(list(soup.find_all('w:p'))) == 5
    assert len(list(soup.find_all('w:tc'))) == 3
    soup = _replace_small_tables(soup)
    assert len(list(soup.find_all('w:tbl'))) == 0
    assert len(list(soup.find_all('w:p'))) == 6
    assert len(list(soup.find_all('w:tc'))) == 0


def test_copy_soup():
    filename = 'test_data/small_table.docx'
    xml_str = get_docx_xml(filename)
    soup = BeautifulSoup(xml_str, 'lxml-xml')
    soup_copy = _copy_soup(soup)
    assert id(soup) != id(soup_copy)