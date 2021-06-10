from envinorma.data.text_elements import Table, Title
from envinorma.from_legifrance import _build_enriched_alineas, _extract_highest_title_level, build_structured_text


def test_build_enriched_alineas():
    assert _build_enriched_alineas(['Hello'])[0][0].text == 'Hello'
    assert _build_enriched_alineas([Table([])])[0][0].table.rows == []


def test_extract_highest_title_level():
    assert _extract_highest_title_level([]) == -1
    assert _extract_highest_title_level([Table([])]) == -1
    assert _extract_highest_title_level([Table([]), Title('', 1)]) == 1


def test_build_structured_text():
    elements = [Table([]), Title('title', 1)]
    result = build_structured_text('', elements)
    assert result.title.text == ''
    assert len(result.outer_alineas) == 1
    assert len(result.sections) == 1
    assert len(result.sections[0].outer_alineas) == 0
    assert len(result.sections[0].sections) == 0
    assert result.sections[0].title.text == 'title'
