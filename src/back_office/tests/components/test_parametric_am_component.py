from dataclasses import replace
from typing import List, Optional

from back_office.components.parametric_am import _extract_text_warnings
from lib.data import Applicability, StructuredText, estr


def _get_simple_text(active: bool, modified: bool, sections: Optional[List[StructuredText]] = None) -> StructuredText:
    als = [estr('al 1'), estr('al 2')]
    if not active:
        als = [replace(al, active=False) for al in als]
    if not modified:
        return StructuredText(estr('txt'), als, sections or [], Applicability())
    return StructuredText(
        estr('txt'), als, sections or [], Applicability(True, True, ['modified'], _get_simple_text(True, False))
    )


def test_extract_text_warnings():
    assert _extract_text_warnings(_get_simple_text(True, False)) == []
    assert len(_extract_text_warnings(_get_simple_text(True, True))) == 1
    assert len(_extract_text_warnings(_get_simple_text(False, True))) == 1
    assert len(_extract_text_warnings(_get_simple_text(False, False))) == 0

    subtexts = [_get_simple_text(True, False), _get_simple_text(True, False), _get_simple_text(True, False)]
    text = _get_simple_text(True, False, subtexts)
    assert _extract_text_warnings(text) == []

    subtexts = [_get_simple_text(True, False), _get_simple_text(True, True), _get_simple_text(True, False)]
    text = _get_simple_text(True, False, subtexts)
    assert len(_extract_text_warnings(text)) == 1
    assert _extract_text_warnings(text)[0][1] == subtexts[1].id

    subtexts = [_get_simple_text(True, False), _get_simple_text(True, True), _get_simple_text(True, True)]
    text = _get_simple_text(True, False, subtexts)
    assert len(_extract_text_warnings(text)) == 2
    assert _extract_text_warnings(text)[0][1] == subtexts[1].id
    assert _extract_text_warnings(text)[1][1] == subtexts[2].id

    subtexts = [_get_simple_text(True, False), _get_simple_text(True, True), _get_simple_text(True, True)]
    text = _get_simple_text(False, False, subtexts)
    assert len(_extract_text_warnings(text)) == 2
