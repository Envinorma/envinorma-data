import random
from collections import Counter
from copy import copy
from string import ascii_letters
from typing import Optional

from lib.data import (
    Annotations,
    Applicability,
    ArreteMinisteriel,
    Cell,
    Classement,
    ClassementWithAlineas,
    DateCriterion,
    EnrichedString,
    Link,
    Regime,
    Row,
    StructuredText,
    Table,
    TopicName,
    _is_probably_cid,
    count_cells,
    extract_text_lines,
    group_classements_by_alineas,
    is_increasing,
    load_am_data,
)


def _random_string() -> str:
    return ''.join([random.choice(ascii_letters) for _ in range(9)])


def _random_enriched_string() -> EnrichedString:
    return EnrichedString(_random_string(), [], None)


def _str(text: Optional[str] = None) -> EnrichedString:
    return EnrichedString(text) if text else _random_enriched_string()


_TABLE = Table([Row([Cell(EnrichedString('bonjour'), 1, 1)], True)])
_ENRICHED_STRING_TABLE = EnrichedString('', [], copy(_TABLE))
_ENRICHED_STRING_LINKS = EnrichedString('abc', [Link('abc', 0, 3)], None)
_ENRICHED_STRING_SIMPLE = EnrichedString('abc', [], None)
_LEAF_SECTION = StructuredText(
    copy(_ENRICHED_STRING_SIMPLE),
    [copy(_ENRICHED_STRING_SIMPLE)],
    [],
    Applicability(True, True, ['beware'], StructuredText(_str(), [], [], None)),
    'lf_id',
    'ref',
    Annotations(TopicName.AIR_ODEURS, True, 'guide'),
)
_NODE_SECTION = StructuredText(
    copy(_ENRICHED_STRING_SIMPLE),
    [copy(_ENRICHED_STRING_SIMPLE), copy(_ENRICHED_STRING_TABLE)],
    [_LEAF_SECTION],
    None,
    None,
    'ref',
    Annotations(None, True, None),
)


def test_arrete_ministeriel():
    am = ArreteMinisteriel(
        _ENRICHED_STRING_SIMPLE,
        [_NODE_SECTION],
        [_ENRICHED_STRING_LINKS],
        'short_title',
        DateCriterion('2020/07/23', '2021/07/23'),
        'aida',
        'legifrance',
        classements=[Classement('1510', Regime.A, 'al')],
        classements_with_alineas=[ClassementWithAlineas('1510', Regime.A, ['al', 'albis'])],
        unique_version=True,
        summary=None,
        id='JORFTEXTid',
        active=True,
        warning_inactive='warning',
    )
    dict_ = am.to_dict()
    new_dict = ArreteMinisteriel.from_dict(dict_).to_dict()
    assert new_dict == dict_


def test_structured_text():
    dict_ = _NODE_SECTION.to_dict()
    new_dict = StructuredText.from_dict(dict_).to_dict()
    assert new_dict == dict_


def test_table():
    dict_ = _TABLE.to_dict()
    new_dict = Table.from_dict(dict_).to_dict()
    assert new_dict == dict_


def test_is_increasing():
    assert is_increasing([])
    assert is_increasing([1])
    assert is_increasing([1, 3])
    assert is_increasing([1, 3, 4, 5])
    assert not is_increasing([1, 3, 4, 5, 1])
    assert not is_increasing([1, 1])


def test_am_list():
    am_data = load_am_data()
    for md in am_data.metadata:
        assert md.aida_page.isdigit()
        for classement in md.classements:
            assert classement.rubrique.isdigit()
            assert len(classement.rubrique) == 4
        classements = [(cl.rubrique, cl.regime, cl.alinea) for cl in md.classements]
        assert len(classements) >= 1
        most_common = Counter(classements).most_common()[0]
        if most_common[1] != 1:
            raise ValueError(most_common)
        assert most_common[1] == 1


def test_count_cells():
    assert count_cells(Table([])) == 0
    assert count_cells(Table([Row([], True)])) == 0
    cells = [Cell(EnrichedString(''), 1, 1)]
    assert count_cells(Table([Row(cells, True)])) == 1
    assert count_cells(Table([Row(cells, True)] * 3)) == 3


def test_group_classements_by_alineas():
    assert group_classements_by_alineas([]) == []

    res = group_classements_by_alineas([Classement('1510', Regime.A)])
    assert len(res) == 1
    assert res[0].alineas == []
    assert res[0].rubrique == '1510'
    assert res[0].regime == Regime.A

    res = group_classements_by_alineas([Classement('1510', Regime.A, 'C')])
    assert len(res) == 1
    assert res[0].alineas == ['C']
    assert res[0].rubrique == '1510'
    assert res[0].regime == Regime.A

    res = group_classements_by_alineas([Classement('1510', Regime.A, 'C'), Classement('1510', Regime.A, 'D')])
    assert len(res) == 1
    assert res[0].alineas == ['C', 'D']
    assert res[0].rubrique == '1510'
    assert res[0].regime == Regime.A

    res = group_classements_by_alineas([Classement('1510', Regime.A, 'C'), Classement('1520', Regime.A, 'D')])
    assert len(res) == 2
    assert res[0].alineas == ['C']
    assert res[0].rubrique == '1510'
    assert res[0].regime == Regime.A
    assert res[1].alineas == ['D']
    assert res[1].rubrique == '1520'
    assert res[1].regime == Regime.A

    res = group_classements_by_alineas([Classement('1510', Regime.A, 'C'), Classement('1510', Regime.E, 'D')])
    assert len(res) == 2
    assert res[0].alineas == ['C']
    assert res[0].rubrique == '1510'
    assert res[0].regime == Regime.A
    assert res[1].alineas == ['D']
    assert res[1].rubrique == '1510'
    assert res[1].regime == Regime.E


def test_is_probably_cid():
    assert _is_probably_cid('JORFTEXT')
    assert _is_probably_cid('LEGITEXT')
    assert _is_probably_cid('LEGITEXT34234')
    assert _is_probably_cid('FAKE_CID')
    assert _is_probably_cid('FAKETEXT0000324')
    assert not _is_probably_cid('')
    assert not _is_probably_cid('JORFTEX')


def _get_simple_text() -> StructuredText:
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [EnrichedString('bar')], [], None)
    return StructuredText(
        EnrichedString('AM '), [EnrichedString('alinea'), EnrichedString('foo')], [section_1, section_2], None
    )


_TEXT_A = StructuredText(
    title=EnrichedString(
        text='6. Schématisation des différents types de joints mentionnés :', links=[], table=None, active=True
    ),
    outer_alineas=[
        EnrichedString(text='Vous pouvez consulter les schémas dans le', links=[], table=None, active=True),
        EnrichedString(text='JO\nn° 265 du 16/11/2010 texte numéro 21', links=[], table=None, active=True),
    ],
    sections=[],
    applicability=None,
    lf_id=None,
    reference_str='Annexe 2 6.',
    annotations=None,
    id='0bEB0b14A96f',
)
_TEXT_B = StructuredText(
    title=EnrichedString(
        text='6. Schématisation des différents types de joints mentionnés :', links=[], table=None, active=True
    ),
    outer_alineas=[
        EnrichedString(text='Vous pouvez consulter les schémas dans le', links=[], table=None, active=True),
        EnrichedString(text='JO n° 265 du 16/11/2010 texte numéro 21', links=[], table=None, active=True),
    ],
    sections=[],
    applicability=None,
    lf_id=None,
    reference_str=None,
    annotations=None,
    id='AA51E55feD6F',
)


def test_extract_text_lines():
    assert extract_text_lines(_get_simple_text()) == [
        'AM',
        'alinea',
        'foo',
        '# Section 1',
        '## Section 1.1',
        '# Section 2',
        'bar',
    ]
    assert extract_text_lines(StructuredText(EnrichedString(' A'), [], [], None)) == ['A']
    assert extract_text_lines(StructuredText(EnrichedString(' A'), [EnrichedString('')], [], None)) == ['A', '']
    assert extract_text_lines(_TEXT_A) == [
        '6. Schématisation des différents types de joints mentionnés :',
        'Vous pouvez consulter les schémas dans le',
        'JO',
        'n° 265 du 16/11/2010 texte numéro 21',
    ]

    assert extract_text_lines(_TEXT_B) == [
        '6. Schématisation des différents types de joints mentionnés :',
        'Vous pouvez consulter les schémas dans le',
        'JO n° 265 du 16/11/2010 texte numéro 21',
    ]
