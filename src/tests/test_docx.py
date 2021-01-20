import os
import random
from typing import List

import bs4
import pytest
from bs4 import BeautifulSoup, Tag
from lib.data import Cell, EnrichedString, Row, Table
from lib.docx import (
    Style,
    _build_table_with_correct_rowspan,
    _check_is_tag,
    _copy_soup,
    _extract_bold,
    _extract_bool_property_value,
    _extract_color,
    _extract_elements,
    _extract_font_name,
    _extract_font_size_occurrences,
    _extract_italic,
    _extract_property_value,
    _extract_size,
    _extract_tags,
    _group_strings,
    _guess_body_font_size,
    _guess_title_level,
    _is_a_reference,
    _is_header,
    _is_title_beginning,
    _remove_table_inplace,
    _remove_tables_and_bodies,
    _replace_small_tables,
    _replace_tables_and_body_text_with_empty_p,
    build_structured_text_from_docx_xml,
    empty_soup,
    extract_cell,
    extract_headers,
    extract_row,
    extract_table,
    extract_w_tag_style,
    get_docx_xml,
    remove_duplicate_line_break,
    remove_empty,
    write_new_document,
)
from lib.structure_extraction import TextElement, Title

_PREFIX = '''<?xml version="1.0" encoding="utf-8"?>\n<w:document mc:Ignorable="w14 wp14" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'''


def test_extract_property_value():
    tag = BeautifulSoup(f'{_PREFIX}<w:bottom w:color="#000000" w:sz="2.4" w:val="single"/>', 'lxml-xml')
    assert _extract_property_value(tag, 'bottom') == "single"
    assert _extract_property_value(tag, 'bottom', 'w:val') == "single"
    assert _extract_property_value(tag, 'bottom', 'w:color') == "#000000"


def test_extract_bool_property_value():
    tag = BeautifulSoup(f'{_PREFIX}<w:b w:val="0"/>', 'lxml-xml')
    assert not _extract_bool_property_value(tag, 'b')
    tag = BeautifulSoup(f'{_PREFIX}<w:b w:val="1"/>', 'lxml-xml')
    assert _extract_bool_property_value(tag, 'b')
    tag = BeautifulSoup(f'{_PREFIX}<w:b/>', 'lxml-xml')
    assert _extract_bool_property_value(tag, 'b')


def test_extract_bold():
    tag = BeautifulSoup(f'{_PREFIX}<w:b w:val="0"/>', 'lxml-xml')
    assert not _extract_bold(tag)
    tag = BeautifulSoup(f'{_PREFIX}<w:b w:val="1"/>', 'lxml-xml')
    assert _extract_bold(tag)

    assert _extract_bold(BeautifulSoup(f'{_PREFIX}<w:b/>', 'lxml-xml'))
    assert not _extract_bold(BeautifulSoup(f'{_PREFIX}', 'lxml-xml'))


def test_extract_italic():
    assert _extract_italic(BeautifulSoup(f'{_PREFIX}<i/>', 'lxml-xml'))


def test_extract_size():
    assert _extract_size(BeautifulSoup(f'{_PREFIX}<sz w:val="10" />', 'lxml-xml')) == 10


def test_extract_font_name():
    assert (
        _extract_property_value(
            BeautifulSoup(f'{_PREFIX}<w:rFonts w:ascii="Times" />', 'lxml-xml'), 'rFonts', 'w:ascii'
        )
        == 'Times'
    )
    assert _extract_font_name(BeautifulSoup(f'{_PREFIX}<w:rFonts w:ascii="Times" />', 'lxml-xml')) == 'Times'


def test_extract_color():
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

    tag = BeautifulSoup(
        str_tag.replace('<w:pStyle w:val="TableHeading"/>', ''),
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
    assert len(list(soup.find_all('w:p'))) == 12
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
    assert len(list(soup.find_all('w:p'))) == 5
    assert len(list(soup.find_all('w:tc'))) == 0


def test_copy_soup():
    filename = 'test_data/small_table.docx'
    xml_str = get_docx_xml(filename)
    soup = BeautifulSoup(xml_str, 'lxml-xml')
    soup_copy = _copy_soup(soup)
    assert id(soup) != id(soup_copy)


def test_docx_writing():
    filename = 'test_data/small_table.docx'
    xml = get_docx_xml(filename)
    output = ''.join([random.choice('abcdef') for _ in range(10)]) + '.docx'
    write_new_document(filename, str(xml), output)
    xml_2 = get_docx_xml(output)
    assert xml == xml_2
    os.remove(output)


def test_is_title_beginning():
    assert _is_title_beginning('TITRE 9 – Dispositions à caractère administratif')
    assert _is_title_beginning('Chapitre 7.4 - Prévention des pollutions accidentelles')
    assert _is_title_beginning('Article 7.3.4. Travaux d’entretien et de maintenance')
    assert not _is_title_beginning('Chapitr 7.4 - Prévention des pollutions accidentelles')
    assert not _is_title_beginning('')


def test_group_strings():
    split_strings = [
        'TITRE 7 - Prévention',
        'des risques technologiques',
        'Chapitre',
        '7.1 - Caractérisation',
        'des risques',
        'Article 7.1.1. Inventaire des substances ou préparations',
        'dangereuses présentes dans',
        'l’établissement',
        'Article 7.1.2. Zonage interne à',
        'l’établissement',
    ]
    res = _group_strings(split_strings)
    assert len(res) == 4
    assert res[0] == 'TITRE 7 - Prévention des risques technologiques'
    assert res[1] == 'Chapitre 7.1 - Caractérisation des risques'
    assert (
        res[2] == 'Article 7.1.1. Inventaire des substances ou préparations dangereuses présentes dans l’établissement'
    )
    assert res[3] == 'Article 7.1.2. Zonage interne à l’établissement'


def test_empty_soup():
    assert empty_soup(BeautifulSoup('', 'html.parser'))
    assert empty_soup(BeautifulSoup('<a></a>', 'html.parser'))
    assert empty_soup(BeautifulSoup('<a> </a>', 'html.parser'))
    assert not empty_soup(BeautifulSoup('<a>envinorma</a>', 'html.parser'))


def test_extract_headers():
    assert extract_headers(BeautifulSoup('', 'html.parser')) == []
    xml = get_docx_xml('test_data/small_text.docx')
    soup = BeautifulSoup(xml, 'lxml-xml')
    assert extract_headers(soup) == [
        'Article 6.2.3. Auto surveillance des niveaux sonores',
        'Chapitre 6.3 – Vibrations',
    ]


def test_replace_tables_and_body_text_with_empty_p():
    xml = get_docx_xml('test_data/small_text.docx')
    soup = BeautifulSoup(xml, 'lxml-xml')
    new_soup = _replace_tables_and_body_text_with_empty_p(soup)
    assert list(new_soup.stripped_strings) == [
        'Article 6.2.3. Auto surveillance des niveaux sonores',
        'Chapitre 6.3 – Vibrations',
    ]

    xml = ''
    soup = BeautifulSoup(xml, 'lxml-xml')
    new_soup = _replace_tables_and_body_text_with_empty_p(soup, 10)
    assert list(new_soup.stripped_strings) == []


def test_guess_body_font_size():
    xml = get_docx_xml('test_data/small_text.docx')
    soup = BeautifulSoup(xml, 'lxml-xml')
    assert _guess_body_font_size(soup) == 24

    xml = '<w></w>'
    soup = BeautifulSoup(xml, 'lxml-xml')
    with pytest.raises(ValueError):
        _guess_body_font_size(soup)


def test_extract_font_size_occurrences():
    assert _extract_font_size_occurrences({}) == {}
    assert _extract_font_size_occurrences({Style(True, True, 1, '', ''): 10}) == {1: 10}
    assert _extract_font_size_occurrences(
        {Style(True, True, 1, '', ''): 1, Style(True, False, 1, '', ''): 10, Style(True, True, 3, '', ''): 9}
    ) == {1: 11, 3: 9}


def test_is_a_reference():
    assert _is_a_reference('REF_ZRGezf')
    assert _is_a_reference('REF_gergZE')
    assert not _is_a_reference('REF_EBbrr')
    assert not _is_a_reference('REF_EZRRffff')
    assert not _is_a_reference('EZREZRR')


def _find_first_r_tag(soup: BeautifulSoup) -> List[bs4.Tag]:
    return [_check_is_tag(soup.find('w:r'))]


def test_extract_tags():
    xml = get_docx_xml('test_data/small_text.docx')
    soup = BeautifulSoup(xml, 'lxml-xml')
    new_soup, references = _extract_tags(soup, _find_first_r_tag)
    assert len(references) == 1
    assert list(references.keys())[0] in str(new_soup)
    assert len(list(new_soup.stripped_strings)) != len(list(soup.stripped_strings))


def test_remove_tables_and_bodies():
    xml = get_docx_xml('test_data/small_text.docx')
    soup = BeautifulSoup(xml, 'lxml-xml')
    new_soup, references_tb, references_body = _remove_tables_and_bodies(soup)
    assert len(references_tb) == 0
    assert len(references_body) == 4
    for ref in references_body:
        assert ref in str(new_soup)


def test_guess_title_level():
    assert _guess_title_level('TITRE 1: Dechets') == 1
    assert _guess_title_level('CECI EST UNE SECTION') == 1
    assert _guess_title_level('Article 1.1') == 2
    assert _guess_title_level('Article 1.1.1') == 3
    assert _guess_title_level('Chapitre 1.1.1.4') == 4
    assert _guess_title_level('Chapitre 1.1.1.4.5') == 4


def check_is_title(element: TextElement) -> Title:
    if isinstance(element, Title):
        return element
    raise ValueError(f'Received {type(element)}, not Title')


def test_extract_elements():
    xml = get_docx_xml('test_data/small_text.docx')
    soup = BeautifulSoup(xml, 'lxml-xml')
    elements = _extract_elements(soup)
    assert len(elements) == 6
    for element in elements:
        assert not isinstance(element, Table)
    assert isinstance(elements[0], str)
    assert isinstance(elements[1], str)
    assert isinstance(elements[2], Title) and check_is_title(elements[2]).level == 3
    assert isinstance(elements[3], str)
    assert isinstance(elements[4], Title) and check_is_title(elements[4]).level == 2
    assert isinstance(elements[5], str)


def test_build_structured_text_from_docx_xml():
    xml = get_docx_xml('test_data/small_text.docx')
    res = build_structured_text_from_docx_xml(xml)
    assert res.title.text == ''
    assert len(res.sections) == 2
    assert len(res.sections[0].sections) == 0
    assert res.sections[0].title.text == 'Article 6.2.3. Auto surveillance des niveaux sonores'
    assert len(res.sections[1].sections) == 0
    assert res.sections[1].title.text == 'Chapitre 6.3 – Vibrations'
