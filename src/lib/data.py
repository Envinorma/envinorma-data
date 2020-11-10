from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import List, Dict, Optional, Any


class ArticleStatus(Enum):
    VIGUEUR = 'VIGUEUR'
    ABROGE = 'ABROGE'


@dataclass
class LegifranceSection:
    intOrdre: int
    title: str
    articles: List['LegifranceArticle']
    sections: List['LegifranceSection']
    etat: ArticleStatus


@dataclass
class LegifranceArticle:
    id: str
    content: str
    intOrdre: int
    num: Optional[str]
    etat: ArticleStatus

    def as_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'intOrdre': self.intOrdre,
            'num': self.num,
            'etat': self.etat.value,
        }


@dataclass
class LegifranceText:
    visa: str
    title: str
    articles: List[LegifranceArticle]
    sections: List[LegifranceSection]


def _load_legifrance_article(dict_: Dict[str, Any]) -> LegifranceArticle:
    return LegifranceArticle(
        dict_['id'], dict_['content'], dict_['intOrdre'], dict_['num'], ArticleStatus(dict_['etat'])
    )


def _load_legifrance_section(dict_: Dict[str, Any]) -> LegifranceSection:
    return LegifranceSection(
        dict_['intOrdre'],
        dict_['title'],
        [_load_legifrance_article(article) for article in dict_['articles']],
        [_load_legifrance_section(section) for section in dict_['sections']],
        ArticleStatus(dict_['etat']),
    )


def load_legifrance_text(dict_: Dict[str, Any]) -> LegifranceText:
    return LegifranceText(
        dict_['visa'],
        dict_['title'],
        [_load_legifrance_article(article) for article in dict_['articles']],
        [_load_legifrance_section(section) for section in dict_['sections']],
    )


@dataclass
class Link:
    target: str
    position: int
    content_size: int


@dataclass
class Cell:
    content: 'EnrichedString'
    colspan: int
    rowspan: int


@dataclass
class Row:
    cells: List[Cell]
    is_header: bool


@dataclass
class Table:
    rows: List[Row]


def empty_link_list() -> List[Link]:
    return []


@dataclass
class EnrichedString:
    text: str
    links: List[Link] = field(default_factory=empty_link_list)
    table: Optional[Table] = None


@dataclass
class Applicability:
    active: bool
    reason_inactive: Optional[str] = None
    modified: bool = False
    reason_modified: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Applicability':
        return Applicability(**dict_)


class Topic(Enum):
    INCENDIE = 'INCENDIE'
    BRUIT = 'BRUIT'


@dataclass
class Annotations:
    topic: Optional[Topic] = None
    prescriptive: bool = True
    guide: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.topic:
            res['topic'] = self.topic.value
        return res

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Annotations':
        new_dict = dict_.copy()
        new_dict['topic'] = Topic(dict_['topic'])
        return Annotations(**new_dict)


@dataclass
class StructuredText:
    title: EnrichedString
    outer_alineas: List[EnrichedString]
    sections: List['StructuredText']
    legifrance_article: Optional[LegifranceArticle]
    applicability: Optional[Applicability]
    reference_str: Optional[str] = None
    annotations: Optional[Annotations] = None

    def as_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['sections'] = [se.as_dict() for se in self.sections]
        res['legifrance_article'] = self.legifrance_article.as_dict() if self.legifrance_article else None
        res['applicability'] = self.applicability.as_dict() if self.applicability else None
        res['annotations'] = self.annotations.as_dict() if self.annotations else None
        return res


@dataclass
class ArreteMinisteriel:
    title: EnrichedString
    sections: List[StructuredText]
    visa: List[EnrichedString]
    short_title: str
    applicability: Optional[Applicability]

    def as_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['sections'] = [section.as_dict() for section in self.sections]
        res['applicability'] = self.applicability.as_dict() if self.applicability else None
        return res


def load_link(dict_: Dict[str, Any]) -> Link:
    return Link(dict_['target'], dict_['position'], dict_['content_size'])


def load_cell(dict_: Dict[str, Any]) -> Cell:
    return Cell(load_enriched_string(dict_['content']), dict_['colspan'], dict_['rowspan'])


def load_row(dict_: Dict[str, Any]) -> Row:
    return Row([load_cell(cell) for cell in dict_['cells']], dict_['is_header'])


def load_table(dict_: Dict[str, Any]) -> Table:
    return Table([load_row(row) for row in dict_['rows']])


def load_enriched_string(dict_: Dict[str, Any]) -> EnrichedString:
    links = [load_link(link) for link in dict_['links']]
    table = load_table(dict_['table']) if dict_['table'] else None
    return EnrichedString(dict_['text'], links, table)


def load_legifrance_article(dict_: Dict[str, Any]) -> LegifranceArticle:
    return LegifranceArticle(
        dict_['id'], dict_['content'], dict_['intOrdre'], dict_['num'], ArticleStatus(dict_['etat'])
    )


def load_structured_text(dict_: Dict[str, Any]) -> StructuredText:
    title = load_enriched_string(dict_['title'])
    outer_alineas = [load_enriched_string(al) for al in dict_['outer_alineas']]
    sections = [load_structured_text(sec) for sec in dict_['sections']]
    legifrance_article = load_legifrance_article(dict_['legifrance_article']) if dict_['legifrance_article'] else None
    applicability = Applicability.from_dict(dict_['applicability']) if dict_.get('applicability') else None
    return StructuredText(title, outer_alineas, sections, legifrance_article, applicability)


def load_arrete_ministeriel(dict_: Dict[str, Any]) -> ArreteMinisteriel:
    title = load_enriched_string(dict_['title'])
    sections = [load_structured_text(sec) for sec in dict_['sections']]
    visa = [load_enriched_string(vu) for vu in dict_['visa']]
    applicability = Applicability.from_dict(dict_['applicability']) if dict_.get('applicability') else None
    return ArreteMinisteriel(title, sections, visa, dict_['short_title'], applicability)


@dataclass
class TableReference:
    table: Table
    reference: str


@dataclass
class LinkReference:
    reference: str
    target: str
    text: str
