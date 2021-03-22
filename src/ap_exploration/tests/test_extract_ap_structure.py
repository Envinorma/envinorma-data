from ap_exploration.pages.ap_image.extract_ap_structure import _remove_lines
from envinorma.io.alto import AltoComposedBlock, AltoPage, AltoPrintSpace, AltoString, AltoTextBlock, AltoTextLine


def _str(text: str) -> AltoString:
    return AltoString(1, 1, 1, 1, text, 0.9, [])


def test_remove_lines():
    lines = [
        AltoTextLine(1, 1, 1, 1, [_str('a'), _str('a'), _str('c')]),
        AltoTextLine(1, 1, 1, 1, [_str('a'), _str('b'), _str('c')]),
        AltoTextLine(1, 1, 2, 1, [_str('a'), _str('b'), _str('c')]),
    ]
    text_block = AltoTextBlock('', 1, 1, 1, 1, lines)
    block = AltoComposedBlock('', 1, 1, 1, 1, [text_block])
    space = AltoPrintSpace(1, 1, 1, 1, 0, [block])
    page = AltoPage('', 1, 1, 1, 1, [space])
    res = _remove_lines(page, {AltoTextLine(1, 1, 1, 1, [_str('a'), _str('b'), _str('d')])})
    assert res == page
    res = _remove_lines(page, {AltoTextLine(1, 1, 1, 3, [_str('a'), _str('b'), _str('c')])})
    assert res == page
    res = _remove_lines(page, {AltoTextLine(1, 3, 1, 1, [_str('a'), _str('b'), _str('c')])})
    assert res == page

    lines = [
        AltoTextLine(1, 1, 1, 1, [_str('a'), _str('a'), _str('c')]),
        AltoTextLine(1, 1, 1, 1, [_str('a'), _str('b'), _str('c')]),
        AltoTextLine(1, 1, 2, 1, [_str('a'), _str('b'), _str('c')]),
    ]
    text_block = AltoTextBlock('', 1, 1, 1, 1, lines)
    block = AltoComposedBlock('', 1, 1, 1, 1, [text_block])
    space = AltoPrintSpace(1, 1, 1, 1, 0, [block])
    page = AltoPage('', 1, 1, 1, 1, [space])
    res = _remove_lines(page, {AltoTextLine(1, 1, 1, 1, [_str('a'), _str('b'), _str('c')])})

    lines = [
        AltoTextLine(1, 1, 1, 1, [_str('a'), _str('a'), _str('c')]),
        AltoTextLine(1, 1, 2, 1, [_str('a'), _str('b'), _str('c')]),
    ]
    text_block = AltoTextBlock('', 1, 1, 1, 1, lines)
    block = AltoComposedBlock('', 1, 1, 1, 1, [text_block])
    space = AltoPrintSpace(1, 1, 1, 1, 0, [block])
    page = AltoPage('', 1, 1, 1, 1, [space])
    assert res == page
