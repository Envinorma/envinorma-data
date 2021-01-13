import json
import random
import string
from collections import Counter
from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple

from lib.topics.patterns import TopicName
from lib.config import AM_DATA_FOLDER


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

    def to_dict(self):
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
    text_in_inspection_sheet: Optional[str] = None


@dataclass
class Table:
    rows: List[Row]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Table':
        return Table([load_row(row) for row in dict_['rows']])


def count_cells(table: Table) -> int:
    return sum([len(row.cells) for row in table.rows])


def empty_link_list() -> List[Link]:
    return []


@dataclass
class EnrichedString:
    text: str
    links: List[Link] = field(default_factory=empty_link_list)
    table: Optional[Table] = None

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'EnrichedString':
        links = [load_link(link) for link in dict_['links']]
        table = load_table(dict_['table']) if dict_['table'] else None
        return EnrichedString(dict_['text'], links, table)


@dataclass
class Applicability:
    active: bool
    reason_inactive: Optional[str] = None
    modified: bool = False
    reason_modified: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Applicability':
        return Applicability(**dict_)


@dataclass
class Annotations:
    topic: Optional[TopicName] = None
    prescriptive: bool = True
    guide: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.topic:
            res['topic'] = self.topic.value
        return res

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Annotations':
        new_dict = dict_.copy()
        new_dict['topic'] = TopicName(dict_['topic']) if dict_['topic'] else None
        return Annotations(**new_dict)


def random_id() -> str:
    return ''.join([random.choice(string.hexdigits) for _ in range(12)])


@dataclass
class StructuredText:
    title: EnrichedString
    outer_alineas: List[EnrichedString]
    sections: List['StructuredText']
    applicability: Optional[Applicability]
    lf_id: Optional[str] = None
    reference_str: Optional[str] = None
    annotations: Optional[Annotations] = None
    id: str = field(default_factory=random_id)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['sections'] = [se.to_dict() for se in self.sections]
        res['applicability'] = self.applicability.to_dict() if self.applicability else None
        res['annotations'] = self.annotations.to_dict() if self.annotations else None
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]):
        dict_ = dict_.copy()
        dict_['title'] = load_enriched_string(dict_['title'])
        dict_['outer_alineas'] = [load_enriched_string(al) for al in dict_['outer_alineas']]
        dict_['sections'] = [load_structured_text(sec) for sec in dict_['sections']]
        dict_['applicability'] = Applicability.from_dict(dict_['applicability']) if dict_.get('applicability') else None
        dict_['annotations'] = Annotations.from_dict(dict_['annotations']) if dict_.get('annotations') else None
        return StructuredText(**dict_)


@dataclass
class DateCriterion:
    left_date: Optional[str]
    right_date: Optional[str]

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'DateCriterion':
        dict_ = dict_.copy()
        dict_['left_date'] = dict_.get('left_date')
        dict_['right_date'] = dict_.get('right_date')
        return DateCriterion(**dict_)


class Regime(Enum):
    A = 'A'
    E = 'E'
    D = 'D'
    DC = 'DC'
    NC = 'NC'


class ClassementState(Enum):
    ACTIVE = 'ACTIVE'
    SUPPRIMEE = 'SUPPRIMEE'


@dataclass
class Classement:
    rubrique: str
    regime: Regime
    alinea: Optional[str] = None
    state: ClassementState = ClassementState.ACTIVE

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'Classement':
        dict_ = dict_.copy()
        dict_['rubrique'] = str(dict_['rubrique'])
        dict_['regime'] = Regime(dict_['regime'])
        dict_['alinea'] = dict_.get('alinea')
        dict_['state'] = ClassementState(dict_.get('state') or ClassementState.ACTIVE.value)
        return Classement(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['regime'] = self.regime.value
        res['state'] = self.state.value
        return res


@dataclass
class ClassementWithAlineas:
    rubrique: str
    regime: Regime
    alineas: List[str]

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'ClassementWithAlineas':
        dict_ = dict_.copy()
        dict_['rubrique'] = str(dict_['rubrique'])
        dict_['regime'] = Regime(dict_['regime'])
        return ClassementWithAlineas(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['regime'] = self.regime.value
        return res


def group_classements_by_alineas(classements: List[Classement]) -> List[ClassementWithAlineas]:
    rubrique_regime_to_alineas: Dict[Tuple[str, Regime], List[str]] = {}
    for classement in classements:
        key = (classement.rubrique, classement.regime)
        if key not in rubrique_regime_to_alineas:
            rubrique_regime_to_alineas[key] = []
        if classement.alinea:
            rubrique_regime_to_alineas[key].append(classement.alinea)
    return [ClassementWithAlineas(rub, reg, als) for (rub, reg), als in rubrique_regime_to_alineas.items()]


@dataclass
class SummaryElement:
    section_id: str
    section_title: str
    depth: int

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'SummaryElement':
        return SummaryElement(**dict_)


@dataclass
class Summary:
    elements: List[SummaryElement]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'Summary':
        dict_ = dict_.copy()
        dict_['elements'] = [SummaryElement.from_dict(se) for se in dict_['elements']]
        return Summary(**dict_)


@dataclass
class ArreteMinisteriel:
    title: EnrichedString
    sections: List[StructuredText]
    visa: List[EnrichedString]
    short_title: str
    applicability: Optional[Applicability]
    installation_date_criterion: Optional[DateCriterion] = None
    aida_url: Optional[str] = None
    legifrance_url: Optional[str] = None
    classements: List[Classement] = field(default_factory=list)
    classements_with_alineas: List[ClassementWithAlineas] = field(default_factory=list)
    unique_version: bool = False
    summary: Optional[Summary] = None
    id: Optional[str] = field(default_factory=random_id)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['sections'] = [section.to_dict() for section in self.sections]
        res['applicability'] = self.applicability.to_dict() if self.applicability else None
        res['classements'] = [cl.to_dict() for cl in self.classements]
        res['classements_with_alineas'] = [cl.to_dict() for cl in self.classements_with_alineas]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'ArreteMinisteriel':
        dict_ = dict_.copy()
        dict_['title'] = load_enriched_string(dict_['title'])
        dict_['sections'] = [StructuredText.from_dict(sec) for sec in dict_['sections']]
        dict_['visa'] = [load_enriched_string(vu) for vu in dict_['visa']]
        dict_['applicability'] = Applicability.from_dict(dict_['applicability']) if dict_.get('applicability') else None
        dt_key = 'installation_date_criterion'
        dict_[dt_key] = DateCriterion.from_dict(dict_[dt_key]) if dict_.get(dt_key) else None
        classements = [Classement.from_dict(cl) for cl in dict_.get('classements') or []]
        dict_['classements'] = list(sorted(classements, key=lambda x: x.regime.value))
        classements_with_alineas = [
            ClassementWithAlineas.from_dict(cl) for cl in dict_.get('classements_with_alineas') or []
        ]
        dict_['classements_with_alineas'] = list(sorted(classements_with_alineas, key=lambda x: x.regime.value))
        dict_['summary'] = Summary.from_dict(dict_['summary']) if dict_.get('summary') else None
        return cls(**dict_)


def load_link(dict_: Dict[str, Any]) -> Link:
    return Link(dict_['target'], dict_['position'], dict_['content_size'])


def load_cell(dict_: Dict[str, Any]) -> Cell:
    return Cell(load_enriched_string(dict_['content']), dict_['colspan'], dict_['rowspan'])


def load_row(dict_: Dict[str, Any]) -> Row:
    return Row([load_cell(cell) for cell in dict_['cells']], dict_['is_header'])


def load_table(dict_: Dict[str, Any]) -> Table:
    return Table.from_dict(dict_)


def load_enriched_string(dict_: Dict[str, Any]) -> EnrichedString:
    return EnrichedString.from_dict(dict_)


def load_legifrance_article(dict_: Dict[str, Any]) -> LegifranceArticle:
    return LegifranceArticle(
        dict_['id'], dict_['content'], dict_['intOrdre'], dict_['num'], ArticleStatus(dict_['etat'])
    )


def load_structured_text(dict_: Dict[str, Any]) -> StructuredText:
    return StructuredText.from_dict(dict_)


def load_arrete_ministeriel(dict_: Dict[str, Any]) -> ArreteMinisteriel:
    return ArreteMinisteriel.from_dict(dict_)


@dataclass
class TableReference:
    table: Table
    reference: str


@dataclass
class LinkReference:
    reference: str
    target: str
    text: str


def check_enriched_string(str_: EnrichedString) -> None:
    if not isinstance(str_, EnrichedString):
        raise ValueError(f'Expecting EnrichedString, found {str_}')


def check_structured_text(text: StructuredText) -> None:
    check_enriched_string(text.title)
    for al in text.outer_alineas:
        check_enriched_string(al)
    for section in text.sections:
        check_structured_text(section)


def check_am(am: ArreteMinisteriel):
    check_enriched_string(am.title)
    for vu in am.visa:
        check_enriched_string(vu)
    for section in am.sections:
        check_structured_text(section)


@dataclass
class LegifranceTextProperties:
    structure: str
    nb_articles: int
    nb_non_numbered_articles: int
    nb_lost_vu_lines: int


@dataclass
class TitleInconsistency:
    titles: List[str]
    parent_section_title: str
    inconsistency: str


@dataclass
class AMProperties:
    structure: str
    nb_sections: int
    nb_articles: int
    nb_tables: int
    nb_empty_articles: int
    title_inconsistencies: List[TitleInconsistency]


@dataclass
class TextProperties:
    legifrance: LegifranceTextProperties
    am: Optional[AMProperties]


@dataclass
class LegifranceAPIError:
    status_code: int
    content: str


@dataclass
class LegifranceTextFormatError:
    message: str
    stacktrace: str


@dataclass
class StructurationError:
    message: str
    stacktrace: str


@dataclass
class AMStructurationLog:
    legifrance_api_error: Optional[LegifranceAPIError] = None
    legifrance_text_format_error: Optional[LegifranceTextFormatError] = None
    structuration_error: Optional[StructurationError] = None
    properties: Optional[TextProperties] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AMState(Enum):
    VIGUEUR = 'VIGUEUR'
    ABROGE = 'ABROGE'


@dataclass
class AMMetadata:
    cid: str
    aida_page: str
    page_name: str
    short_title: str
    classements: List[Classement]
    state: AMState
    publication_date: int
    nor: Optional[str] = None

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'AMMetadata':
        dict_ = dict_.copy()
        dict_['aida_page'] = str(dict_['aida_page'])
        dict_['state'] = AMState(dict_['state'])
        dict_['classements'] = [Classement.from_dict(classement) for classement in dict_['classements']]
        return AMMetadata(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        dict_ = asdict(self)
        dict_['state'] = self.state.value
        dict_['classements'] = [classement.to_dict() for classement in self.classements]
        return dict_


@dataclass
class AMData:
    metadata: List[AMMetadata]
    nor_to_aida: Dict[str, str]
    aida_to_nor: Dict[str, str]

    def __post_init__(self):
        ids = [am.nor or am.cid for am in self.metadata]
        non_unique_ids = [(x, cnt) for x, cnt in Counter(ids).most_common() if cnt > 1]
        if non_unique_ids:
            raise ValueError(f'There are non unique ids: {non_unique_ids}')

    @staticmethod
    def from_dict(dict_: List[Dict[str, Any]]) -> 'AMData':
        arretes_ministeriels = [AMMetadata.from_dict(x) for x in dict_]
        nor_to_aida = {doc.nor: doc.aida_page for doc in arretes_ministeriels if doc.nor}
        aida_to_nor = {value: key for key, value in nor_to_aida.items()}
        return AMData(arretes_ministeriels, nor_to_aida, aida_to_nor)


def load_am_data() -> AMData:
    filename = __file__.replace('lib/data.py', 'data/arretes_ministeriels.json')
    return AMData.from_dict(json.load(open(filename)))


@dataclass
class Hyperlink:
    content: str
    href: str


@dataclass
class Anchor:
    name: str
    anchored_text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AidaData:
    page_id_to_links: Dict[str, List[Hyperlink]]
    page_id_to_anchors: Dict[str, List[Anchor]]


@dataclass
class Data:
    aida: AidaData
    arretes_ministeriels: AMData


def get_text_defined_id(text: AMMetadata) -> str:
    return text.nor or text.cid


Ints = Tuple[int, ...]


@dataclass
class StructuredTextSignature:
    section_reference: Ints
    title: str
    outer_alineas_text: List[str]
    depth_in_am: int
    rank_in_section_list: int
    section_list_size: int

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'StructuredTextSignature':
        dict_ = dict_.copy()
        dict_['section_reference'] = tuple(dict_['section_reference'])
        return StructuredTextSignature(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['section_reference'] = list(self.section_reference)
        return res


def is_increasing(list_: List[float]) -> bool:
    if not list_:
        return True
    for a, b in zip(list_, list_[1:]):
        if a >= b:
            return False
    return True


@dataclass(frozen=True)
class RubriqueSimpleThresholds:
    code: str
    thresholds: List[float]
    regimes: List[Regime]
    alineas: List[str]
    unit: str
    variable_name: str

    def __post_init__(self):
        if len(self.thresholds) != len(self.regimes):
            raise ValueError(
                f'Expecting thresholds and regimes to have same lengths, received {self.thresholds} and {self.regimes}'
            )
        if not is_increasing(self.thresholds):
            raise ValueError(f'Expecting increasing thresholds, received {self.thresholds}')

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'RubriqueSimpleThresholds':
        dict_ = dict_.copy()
        dict_['regimes'] = [Regime(rg) for rg in dict_['regimes']]
        dict_['code'] = str(dict_['code'])
        return RubriqueSimpleThresholds(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['regimes'] = [rg.value for rg in self.regimes]
        return res


@dataclass
class Nomenclature:
    am_metadata_list: List[AMMetadata]
    simple_thresholds: Dict[str, RubriqueSimpleThresholds]
    rubrique_and_regime_to_am: Dict[Tuple[str, Regime], List[AMMetadata]] = field(init=False)

    def __post_init__(self):
        self.rubrique_and_regime_to_am = {}
        for md in self.am_metadata_list:
            for classement in md.classements:
                pair = (classement.rubrique, classement.regime)
                if pair not in self.rubrique_and_regime_to_am:
                    self.rubrique_and_regime_to_am[pair] = []
                self.rubrique_and_regime_to_am[pair].append(md)

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'Nomenclature':
        dict_ = dict_.copy()
        dict_['am_metadata_list'] = [AMMetadata.from_dict(dc) for dc in dict_['am_metadata_list']]
        dict_['simple_thresholds'] = {
            str(id_): RubriqueSimpleThresholds.from_dict(dc) for id_, dc in dict_['simple_thresholds'].items()
        }
        return Nomenclature(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        del res['rubrique_and_regime_to_am']
        res['am_metadata_list'] = [md.to_dict() for md in self.am_metadata_list]
        res['simple_thresholds'] = {id_: ts.to_dict() for id_, ts in self.simple_thresholds.items()}
        return res

    @staticmethod
    def load_default() -> 'Nomenclature':
        return Nomenclature.from_dict(json.load(open(f'{AM_DATA_FOLDER}/nomenclature.json')))


def am_to_text(am: ArreteMinisteriel) -> StructuredText:
    return StructuredText(am.title, [], am.sections, None)
