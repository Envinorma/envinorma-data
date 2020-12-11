from bs4 import BeautifulSoup
from lib.docx import (
    Style,
    _extract_property_value,
    _extract_bool_property_value,
    _extract_bold,
    _extract_italic,
    _extract_size,
    _extract_font_name,
    _extract_color,
    extract_w_tag_style,
    remove_empty,
    remove_duplicate_line_break,
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
