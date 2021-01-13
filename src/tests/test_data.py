from copy import copy
from collections import Counter
from lib.data import (
    Annotations,
    Applicability,
    ArreteMinisteriel,
    Cell,
    Classement,
    DateCriterion,
    EnrichedString,
    Link,
    Regime,
    Row,
    StructuredText,
    Table,
    TopicName,
    count_cells,
    group_classements_by_alineas,
    is_increasing,
    load_am_data,
)

_TABLE = Table([Row([Cell(EnrichedString('bonjour'), 1, 1)], True)])
_ENRICHED_STRING_TABLE = EnrichedString('', [], copy(_TABLE))
_ENRICHED_STRING_LINKS = EnrichedString('abc', [Link('abc', 0, 3)], None)
_ENRICHED_STRING_SIMPLE = EnrichedString('abc', [], None)
_LEAF_SECTION = StructuredText(
    copy(_ENRICHED_STRING_SIMPLE),
    [copy(_ENRICHED_STRING_SIMPLE)],
    [],
    Applicability(True, 'ra', False, None, ['beware']),
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
        None,
        DateCriterion('2020/07/23', '2021/07/23'),
        'aida',
        'legifrance',
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
