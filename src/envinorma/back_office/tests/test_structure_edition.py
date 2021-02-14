from typing import List

from bs4 import BeautifulSoup
from envinorma.back_office.structure_edition import (
    _TABLE_MARK,
    _count_prefix_hashtags,
    _extract_element_words,
    _extract_first_different_word,
    _extract_text_area_words,
    _extract_words,
    _extract_words_from_structured_text,
    _keep_non_empty,
    _replace_tables,
)
from envinorma.data import EnrichedString, StructuredText, Table
from envinorma.structure import Title


def _get_simple_text() -> StructuredText:
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [EnrichedString('bar')], [], None)
    return StructuredText(
        EnrichedString('AM'), [EnrichedString('alinea'), EnrichedString('foo')], [section_1, section_2], None
    )


def test_extract_words_from_structured_text():
    assert _extract_words_from_structured_text(StructuredText(EnrichedString(''), [], [], None)) == []
    assert _extract_words_from_structured_text(StructuredText(EnrichedString('test'), [], [], None)) == ['test']
    assert _extract_words_from_structured_text(StructuredText(EnrichedString('test 2'), [], [], None)) == ['test', '2']
    table = EnrichedString('', table=Table([]))
    assert _extract_words_from_structured_text(StructuredText(EnrichedString('test 2'), [table], [], None)) == [
        'test',
        '2',
        _TABLE_MARK,
    ]
    am = _get_simple_text()
    expected = ['AM', 'alinea', 'foo', 'Section', '1', 'Section', '1', '1', 'Section', '2', 'bar']
    assert _extract_words_from_structured_text(am) == expected


def test_keep_non_empty():
    assert _keep_non_empty([]) == []
    assert _keep_non_empty(['']) == []
    assert _keep_non_empty(['', '']) == []
    assert _keep_non_empty([''] * 10) == []
    assert _keep_non_empty(['', 'foo']) == ['foo']
    assert _keep_non_empty(['foo']) == ['foo']


def test_extract_words():
    assert _extract_words('hello how are you??') == ['hello', 'how', 'are', 'you']
    assert _extract_words('') == []
    assert _extract_words('?') == []
    assert _extract_words('\n') == []
    assert _extract_words('foo\nbar') == ['foo', 'bar']
    assert _extract_words('foo\nbar...') == ['foo', 'bar']


def test_extract_text_area_words():
    def func(str_: str) -> List[str]:
        return _extract_text_area_words(BeautifulSoup(str_, 'html.parser'))

    assert func('<p>hello how are you??</p>') == ['hello', 'how', 'are', 'you']
    assert func('<p><br/></p>') == []
    assert func('<p>?</p>') == []
    assert func('<br/>') == []
    assert func('<p>foo<br/>bar</p>') == ['foo', 'bar']
    assert func('<p>foo<br/>bar...</p>') == ['foo', 'bar']
    assert func(f'<p>foo<br/>bar...<table><tr><td>unique cell</td></tr></table></p>') == ['foo', 'bar', _TABLE_MARK]


def test_extract_first_different_word():
    assert _extract_first_different_word(['Hello', 'how'], ['hello', 'how']) == 0
    assert _extract_first_different_word([], []) is None
    assert _extract_first_different_word(['foo'], ['foo']) is None
    assert _extract_first_different_word(['foo', 'bar'], ['foo', '']) == 1


def test_count_prefix_hashtags():
    assert _count_prefix_hashtags('') == 0
    assert _count_prefix_hashtags('###') == 3
    assert _count_prefix_hashtags(' ###') == 0
    assert _count_prefix_hashtags('###  ') == 3


def test_extract_element_words():
    assert _extract_element_words(['hello how are you??']) == ['hello', 'how', 'are', 'you']
    assert _extract_element_words(['']) == []
    assert _extract_element_words(['?']) == []
    assert _extract_element_words(['\n']) == []
    assert _extract_element_words(['foo\nbar']) == ['foo', 'bar']
    assert _extract_element_words(['foo\nbar...']) == ['foo', 'bar']
    assert _extract_element_words(['foo\nbar...']) == ['foo', 'bar']
    assert _extract_element_words(['foo\nbar...', Title('foo\nbar...', 1)]) == ['foo', 'bar', 'foo', 'bar']
    assert _extract_element_words([f'foo\nbar...', Table([])]) == ['foo', 'bar', _TABLE_MARK]
    expected = ['foo', 'bar', _TABLE_MARK, 'test', _TABLE_MARK, 'test']
    assert _extract_element_words([f'foo\nbar...', Table([]), 'test', Table([]), 'test']) == expected


def test_replace_tables():
    assert _replace_tables([], []) == []
    assert _replace_tables([''], []) == ['']
    assert _replace_tables(['', ''], []) == ['', '']
    title = Title('', 1)
    assert _replace_tables(['', '', title], []) == ['', '', title]
    table = Table([])
    assert _replace_tables(['', '', Table([])], [table]) == ['', '', table]
    assert _replace_tables(['', '', Table([])], [table]) == ['', '', table]
    assert _replace_tables([Table([]), '', '', Table([])], [table, table]) == [table, '', '', table]
