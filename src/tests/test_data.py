from copy import copy
from lib.data import (
    Annotations,
    Applicability,
    ArreteMinisteriel,
    ArticleStatus,
    Cell,
    DateCriterion,
    EnrichedString,
    LegifranceArticle,
    Link,
    Row,
    StructuredText,
    Table,
    TopicName,
    is_increasing,
)

_TABLE = Table([Row([Cell(EnrichedString('bonjour'), 1, 1)], True)])
_ENRICHED_STRING_TABLE = EnrichedString('', [], copy(_TABLE))
_ENRICHED_STRING_LINKS = EnrichedString('abc', [Link('abc', 0, 3)], None)
_ENRICHED_STRING_SIMPLE = EnrichedString('abc', [], None)
_LEAF_SECTION = StructuredText(
    copy(_ENRICHED_STRING_SIMPLE),
    [copy(_ENRICHED_STRING_SIMPLE)],
    [],
    LegifranceArticle('id', 'content', 0, '0', ArticleStatus.ABROGE),
    Applicability(True, 'ra', False, None, ['beware']),
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
