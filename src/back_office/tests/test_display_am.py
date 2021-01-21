from lib.data import Applicability, EnrichedString, StructuredText
from typing import List, Optional
from back_office.display_am import _extract_text_modifications, _extract_text_inapplicabilities


def _get_applicability(active: bool, modified: bool) -> Applicability:
    return Applicability(active, 'inapplicable' if not active else None, modified, 'modifié' if modified else None)


def _get_simple_text(
    applicability: Optional[Applicability], sections: Optional[List[StructuredText]] = None
) -> StructuredText:
    return StructuredText(
        EnrichedString('txt'),
        [EnrichedString('al 1'), EnrichedString('al 2')],
        sections or [],
        applicability,
    )


def test_extract_text_modifications():
    assert _extract_text_modifications(_get_simple_text(_get_applicability(True, False))) == []
    assert len(_extract_text_modifications(_get_simple_text(_get_applicability(True, True)))) == 1
    assert len(_extract_text_modifications(_get_simple_text(_get_applicability(False, True)))) == 1
    assert len(_extract_text_modifications(_get_simple_text(_get_applicability(False, False)))) == 0

    subtexts = [
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(True, False)),
    ]
    text = _get_simple_text(_get_applicability(True, False), subtexts)
    assert _extract_text_modifications(text) == []

    subtexts = [
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(True, True)),
        _get_simple_text(_get_applicability(True, False)),
    ]
    text = _get_simple_text(_get_applicability(True, False), subtexts)
    assert len(_extract_text_modifications(text)) == 1
    assert _extract_text_modifications(text)[0] == subtexts[1]

    subtexts = [
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(True, True)),
        _get_simple_text(_get_applicability(True, True)),
    ]
    text = _get_simple_text(_get_applicability(True, False), subtexts)
    assert len(_extract_text_modifications(text)) == 2
    assert _extract_text_modifications(text)[0] == subtexts[1]
    assert _extract_text_modifications(text)[1] == subtexts[2]

    subtexts = [
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(True, True)),
        _get_simple_text(_get_applicability(True, True)),
    ]
    text = _get_simple_text(_get_applicability(False, False), subtexts)
    assert len(_extract_text_modifications(text)) == 0


def test_extract_text_inapplicabilities():
    assert len(_extract_text_inapplicabilities(_get_simple_text(_get_applicability(True, True)))) == 0
    assert len(_extract_text_inapplicabilities(_get_simple_text(_get_applicability(True, False)))) == 0
    assert len(_extract_text_inapplicabilities(_get_simple_text(_get_applicability(False, True)))) == 1
    assert len(_extract_text_inapplicabilities(_get_simple_text(_get_applicability(False, False)))) == 1

    subtexts = [
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(True, False)),
    ]
    text = _get_simple_text(_get_applicability(True, False), subtexts)
    assert _extract_text_inapplicabilities(text) == []

    subtexts = [
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(False, False)),
        _get_simple_text(_get_applicability(True, False)),
    ]
    text = _get_simple_text(_get_applicability(True, False), subtexts)
    assert len(_extract_text_inapplicabilities(text)) == 1
    assert _extract_text_inapplicabilities(text)[0] == subtexts[1]

    subtexts = [
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(False, False)),
        _get_simple_text(_get_applicability(False, False)),
    ]
    text = _get_simple_text(_get_applicability(True, False), subtexts)
    assert len(_extract_text_inapplicabilities(text)) == 2
    assert _extract_text_inapplicabilities(text)[0] == subtexts[1]
    assert _extract_text_inapplicabilities(text)[1] == subtexts[2]

    subtexts = [
        _get_simple_text(_get_applicability(True, False)),
        _get_simple_text(_get_applicability(False, False)),
        _get_simple_text(_get_applicability(False, False)),
    ]
    text = _get_simple_text(_get_applicability(True, True), subtexts)
    assert len(_extract_text_inapplicabilities(text)) == 0
