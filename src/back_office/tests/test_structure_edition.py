import dash_html_components as html
from back_office.structure_edition import (
    _TABLEAU_PREFIX,
    _count_prefix_hashtags,
    _extract_first_different_word,
    _extract_text_area_words,
    _extract_words,
    _extract_words_outside_table,
    _keep_non_empty,
)
from lib.data import EnrichedString, StructuredText


def _get_simple_text() -> StructuredText:
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [EnrichedString('bar')], [], None)
    return StructuredText(
        EnrichedString('AM'), [EnrichedString('alinea'), EnrichedString('foo')], [section_1, section_2], None
    )


def test_extract_words_outside_table():
    assert _extract_words_outside_table(StructuredText(EnrichedString(''), [], [], None)) == []
    assert _extract_words_outside_table(StructuredText(EnrichedString('test'), [], [], None)) == ['test']
    assert _extract_words_outside_table(StructuredText(EnrichedString('test 2'), [], [], None)) == ['test', '2']
    am = _get_simple_text()
    assert _extract_words_outside_table(am) == [
        'AM',
        'alinea',
        'foo',
        'Section',
        '1',
        'Section',
        '1',
        '1',
        'Section',
        '2',
        'bar',
    ]


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
    assert _extract_text_area_words('hello how are you??') == ['hello', 'how', 'are', 'you']
    assert _extract_text_area_words('') == []
    assert _extract_text_area_words('?') == []
    assert _extract_text_area_words('\n') == []
    assert _extract_text_area_words('foo\nbar') == ['foo', 'bar']
    assert _extract_text_area_words('foo\nbar...') == ['foo', 'bar']
    assert _extract_text_area_words('foo\nbar...') == ['foo', 'bar']
    assert _extract_text_area_words(f'foo\nbar...\n{_TABLEAU_PREFIX}0 non reproduit - ne pas modifier!!') == [
        'foo',
        'bar',
    ]


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
