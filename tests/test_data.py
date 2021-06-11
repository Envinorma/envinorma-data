import json
import random
from collections import Counter
from datetime import date
from string import ascii_letters
from typing import Optional

import pytest

from envinorma.models import (
    Annotations,
    Applicability,
    ArreteMinisteriel,
    Classement,
    ClassementWithAlineas,
    DateParameterDescriptor,
    EnrichedString,
    Link,
    Regime,
    StructuredText,
    Table,
    TopicName,
    VersionDescriptor,
    _contains_human_date,
    _is_probably_cid,
    extract_date_of_signature,
    extract_text_lines,
    group_classements_by_alineas,
    is_increasing,
    load_am_data,
    standardize_title_date,
    table_to_html,
)
from envinorma.models.text_elements import Cell, Row, estr


def _random_string() -> str:
    return ''.join([random.choice(ascii_letters) for _ in range(9)])


def _str(text: Optional[str] = None) -> EnrichedString:
    return EnrichedString(text or _random_string())


def _table() -> Table:
    return Table([Row([Cell(EnrichedString('bonjour'), 1, 1)], True)])


def _enriched_string_table() -> EnrichedString:
    return EnrichedString('', [], _table())


def _enriched_string_links() -> EnrichedString:
    return EnrichedString('abc', [Link('abc', 0, 4)], None)


def _leaf_section() -> StructuredText:
    app = Applicability(True, True, ['beware'], StructuredText(_str('abc'), [], [], None))
    annotations = Annotations(TopicName.AIR_ODEURS, True, 'guide')
    return StructuredText(_str('abc'), [_str('abc')], [], app, 'ref', annotations)


def _node_section() -> StructuredText:
    return StructuredText(
        _str('abc'),
        [_str('abc'), _enriched_string_table()],
        [_leaf_section()],
        None,
        'ref',
        Annotations(None, True, None),
    )


def test_arrete_ministeriel():
    am = ArreteMinisteriel(
        _str('Arrete du 01/01/10'),
        [_node_section()],
        [_enriched_string_links()],
        date(2010, 1, 1),
        'aida',
        'legifrance',
        classements=[Classement('1510', Regime.A, 'al')],
        classements_with_alineas=[ClassementWithAlineas('1510', Regime.A, ['al', 'albis'])],
        id='JORFTEXTid',
        version_descriptor=VersionDescriptor(
            True, [], DateParameterDescriptor(False), DateParameterDescriptor(True, True, None, date(2020, 1, 1))
        ),
    )
    dict_ = am.to_dict()
    new_dict = ArreteMinisteriel.from_dict(json.loads(json.dumps(dict_))).to_dict()

    assert new_dict == dict_


def test_structured_text():
    dict_ = _node_section().to_dict()
    new_dict = StructuredText.from_dict(dict_).to_dict()
    assert new_dict == dict_


def test_table():
    table_dict = _table().to_dict()
    new_dict = Table.from_dict(table_dict).to_dict()
    assert table_dict == new_dict


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
    sub_section_1 = StructuredText(_str('Section 1.1'), [], [], None)
    section_1 = StructuredText(_str('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(_str('Section 2'), [_str('bar')], [], None)
    return StructuredText(_str('AM '), [_str('alinea'), _str('foo')], [section_1, section_2], None)


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


def test_table_to_html():
    res = table_to_html(Table([Row([Cell(estr('test'), 1, 1)], False)]))
    assert res == '<table><tr><td>test</td></tr></table>'

    res = table_to_html(Table([Row([Cell(estr('test'), 2, 1)], False)]))
    assert res == '<table><tr><td colspan="2">test</td></tr></table>'

    res = table_to_html(Table([Row([Cell(estr('test'), 1, 2)], False)]))
    assert res == '<table><tr><td rowspan="2">test</td></tr></table>'

    res = table_to_html(Table([Row([Cell(estr('test'), 1, 2)], True)]))
    assert res == '<table><tr><th rowspan="2">test</th></tr></table>'


def test_extract_date_of_signature():
    with pytest.raises(ValueError):
        extract_date_of_signature('')
    with pytest.raises(ValueError):
        extract_date_of_signature('19/10/1993')
    with pytest.raises(ValueError):
        extract_date_of_signature('10/19/93')
    assert extract_date_of_signature('19/10/93') == date(1993, 10, 19)


def test_standardize_title_date():
    assert standardize_title_date('Arrêté du 10 octobre 2010 relatif à') == 'Arrêté du 10/10/10 relatif à'
    assert standardize_title_date('Arrêté du 31 octobre 2018 relatif à') == 'Arrêté du 31/10/18 relatif à'
    with pytest.raises(ValueError):
        standardize_title_date('Arrêté du 10 octobr 2010 relatif à')
    with pytest.raises(ValueError):
        standardize_title_date('Arrêté du 31 septembre 2010 relatif à')
    with pytest.raises(ValueError):
        standardize_title_date('Arrêté du 10')
    with pytest.raises(ValueError):
        standardize_title_date('Arrêté du 10/10/2010 relatif à')


def test_contains_human_date():
    assert _contains_human_date('Arrêté du 30 septembre 2010 relatif à')
    assert _contains_human_date('Arrêté du 10 octobre 2019')
    assert not _contains_human_date('Arrêté du 10/10/19')
    assert not _contains_human_date('10 octobre 2019')
