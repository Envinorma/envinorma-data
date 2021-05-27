import json
import random
import re
import string
import warnings
from collections import Counter
from copy import copy
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime
from enum import Enum
from operator import attrgetter
from typing import Any, Dict, List, Optional, Tuple

from envinorma.data.arretes_ministeriels import ARRETES_MINISTERIELS
from envinorma.data.text_elements import EnrichedString, Link, Table, table_to_html
from envinorma.topics.patterns import TopicName
from envinorma.utils import AIDA_URL, str_to_date


@dataclass
class Applicability:
    active: bool = True
    modified: bool = False
    warnings: List[str] = field(default_factory=list)
    previous_version: Optional['StructuredText'] = None

    def __post_init__(self):
        if self.modified:
            if not self.previous_version:
                raise ValueError('when modified is True, previous_version must be provided.')

    def to_dict(self) -> Dict[str, Any]:
        dict_ = asdict(self)
        if self.previous_version:
            dict_['previous_version'] = self.previous_version.to_dict()
        return dict_

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Applicability':
        dict_ = dict_.copy()
        dict_['previous_version'] = (
            StructuredText.from_dict(dict_['previous_version']) if dict_['previous_version'] else None
        )
        return cls(**dict_)


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
        return cls(**new_dict)


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

    def __post_init__(self):
        assert isinstance(self.title, EnrichedString)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['title'] = self.title.to_dict()
        res['outer_alineas'] = [al.to_dict() for al in self.outer_alineas]
        res['sections'] = [se.to_dict() for se in self.sections]
        res['applicability'] = self.applicability.to_dict() if self.applicability else None
        res['annotations'] = self.annotations.to_dict() if self.annotations else None
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'StructuredText':
        dict_ = dict_.copy()
        dict_['title'] = EnrichedString.from_dict(dict_['title'])
        dict_['outer_alineas'] = [EnrichedString.from_dict(al) for al in dict_['outer_alineas']]
        dict_['sections'] = [StructuredText.from_dict(sec) for sec in dict_['sections']]
        dict_['applicability'] = Applicability.from_dict(dict_['applicability']) if dict_.get('applicability') else None
        dict_['annotations'] = Annotations.from_dict(dict_['annotations']) if dict_.get('annotations') else None
        return cls(**dict_)


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


def _is_probably_cid(candidate: str) -> bool:
    if 'FAKE' in candidate:
        return True  # for avoiding warning for fake cids, which contain FAKE by convention
    return candidate.startswith('JORFTEXT') or candidate.startswith('LEGITEXT')


def extract_short_title(input_title: str) -> str:
    return input_title.split('relatif')[0].split('fixant')[0].strip()


_DATE_PATTERN = r'^[0-9]{2}/[0-9]{2}/[0-9]{2}$'


def _extract_date(candidate_date: str) -> date:
    if not re.match(_DATE_PATTERN, candidate_date):
        raise ValueError(f'Expecting format {_DATE_PATTERN}. Got {candidate_date}.')
    return datetime.strptime(candidate_date, '%d/%m/%y').date()


def extract_date_of_signature(input_title: str) -> date:
    short_title = extract_short_title(input_title)
    candidate_date = (short_title.split() or [''])[-1]
    return _extract_date(candidate_date)


def _year(year_str: str) -> int:
    if not year_str.isdigit():
        raise ValueError(f'Expecting {year_str} to be a digit')
    return int(year_str)


_MONTH_TO_MONTH_RANK = {
    'janvier': 1,
    'février': 2,
    'mars': 3,
    'avril': 4,
    'mai': 5,
    'juin': 6,
    'juillet': 7,
    'août': 8,
    'septembre': 9,
    'octobre': 10,
    'novembre': 11,
    'décembre': 12,
}


def _month(french_month: str) -> int:
    if french_month not in _MONTH_TO_MONTH_RANK:
        raise ValueError(f'Expecting month to be in {_MONTH_TO_MONTH_RANK} got {french_month}')
    return _MONTH_TO_MONTH_RANK[french_month]


def _day(day_str: str) -> int:
    if day_str == '1er':
        return 1
    if not day_str.isdigit():
        raise ValueError(f'Expecting {day_str} to be a digit')
    return int(day_str)


def _read_human_french_date(day_str: str, french_month: str, year_str: str) -> date:
    return date(_year(year_str), _month(french_month), _day(day_str))


def _standardize_date(day_str: str, french_month: str, year_str: str) -> str:
    date_ = _read_human_french_date(day_str, french_month, year_str)
    return date_.strftime('%d/%m/%y')


def standardize_title_date(title: str) -> str:
    words = title.split()
    if len(words) <= 5:
        raise ValueError(f'Expecting title to have at least 5 words, got {len(words)} (title={title}).')
    new_words = words[:2] + [_standardize_date(*words[2:5])] + words[5:]
    return ' '.join(new_words)


_MONTHS = r'(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)'
_PATTERN = rf'Arrêté du (1er|[0-9]*) ' + _MONTHS + ' [0-9]{4}'


def _contains_human_date(title: str) -> bool:
    return re.match(_PATTERN, title) is not None


def _standardize_title_if_necessary(title: str) -> str:
    if title == 'Faux arrêté':  # Edge case for test text
        return 'Faux arrêté du 10/10/10'
    if _contains_human_date(title):
        return standardize_title_date(title)
    return title


@dataclass(eq=True, frozen=True)
class DateParameterDescriptor:
    """
    Describes an AM version with regard to a specific date
    (e.g. the AM applicable to classements with installation date in a specific range.)

    is_used
        is True if the corresponding date was used in the parametrization of the AM
    known_value
        is defined if is_used is True. It is true for the AM version
        corresponding to an unknown value of the date for the given classement.
    left_value
        is defined if is_used is True. With right_value, it describes the date range of
        applicability of the AM. None corresponds to -infinity.
    right_value
        is defined if is_used is True. With left_value, it describes the date range of
        applicability of the AM. None corresponds to +infinity.

    example:
        For an AM that changes version for date 2021-01-01, one of the generated version
        will have (is_used=True, known_value=True, left_value=None, right_value=2021-01-01).
        It corresponds to the classements whose date is known and whose date value is smaller than 2021-01-01.
    """

    is_used: bool
    known_value: Optional[bool] = None
    left_value: Optional[date] = None
    right_value: Optional[date] = None

    def __post_init__(self) -> None:
        if self.left_value:
            assert isinstance(self.left_value, date) and not isinstance(self.left_value, datetime)
        if self.right_value:
            assert isinstance(self.right_value, date) and not isinstance(self.right_value, datetime)
        if not self.is_used:
            assert self.known_value is None
            assert self.left_value is None
            assert self.right_value is None
        if self.known_value in {False, True}:
            assert self.is_used
        if self.known_value == False:
            assert self.left_value is None
            assert self.right_value is None

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'DateParameterDescriptor':
        dict_ = dict_.copy()
        for key in ('left_value', 'right_value'):
            dict_[key] = date.fromisoformat(dict_[key]) if dict_[key] else None
        return cls(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['left_value'] = str(self.left_value) if self.left_value else None
        res['right_value'] = str(self.right_value) if self.right_value else None
        return res


@dataclass
class VersionDescriptor:
    applicable: bool
    applicability_warnings: List[str]
    aed_date: DateParameterDescriptor
    installation_date: DateParameterDescriptor

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'VersionDescriptor':
        for key in ['aed_date', 'installation_date']:
            dict_[key] = DateParameterDescriptor.from_dict(dict_[key])
        return cls(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['aed_date'] = self.aed_date.to_dict()
        res['installation_date'] = self.installation_date.to_dict()
        return res


@dataclass
class ArreteMinisteriel:
    title: EnrichedString
    sections: List[StructuredText]
    visa: List[EnrichedString]
    publication_date: Optional[date] = None
    date_of_signature: Optional[date] = None
    aida_url: Optional[str] = None
    legifrance_url: Optional[str] = None
    classements: List[Classement] = field(default_factory=list)
    classements_with_alineas: List[ClassementWithAlineas] = field(default_factory=list)
    summary: Optional[Summary] = None
    id: Optional[str] = field(default_factory=random_id)
    version_descriptor: Optional[VersionDescriptor] = None

    @property
    def short_title(self) -> str:
        return extract_short_title(self.title.text)

    def __post_init__(self):
        self.title.text = _standardize_title_if_necessary(self.title.text)
        if self.date_of_signature is None:
            self.date_of_signature = extract_date_of_signature(self.title.text)
        else:
            assert self.date_of_signature == extract_date_of_signature(
                self.title.text
            ), f'{self.date_of_signature} and {self.title.text} are inconsistent'

        # Below date must be kept as long as publication_date keeps being used in web app, remove after
        # (because publication_date is not the right term.)
        self.publication_date = self.date_of_signature

        if not _is_probably_cid(self.id or ''):
            warnings.warn(f'AM id does not look like a CID : {self.id} (title={self.title.text})')

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if res['publication_date']:
            res['publication_date'] = str(res['publication_date'])
        if res['date_of_signature']:
            res['date_of_signature'] = str(res['date_of_signature'])
        res['title'] = self.title.to_dict()
        res['visa'] = [vi.to_dict() for vi in self.visa]
        res['sections'] = [section.to_dict() for section in self.sections]
        res['classements'] = [cl.to_dict() for cl in self.classements]
        res['classements_with_alineas'] = [cl.to_dict() for cl in self.classements_with_alineas]
        if self.version_descriptor:
            res['version_descriptor'] = self.version_descriptor.to_dict()
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'ArreteMinisteriel':
        dict_ = dict_.copy()
        if 'short_title' in dict_:
            del dict_['short_title']
        dict_['title'] = EnrichedString.from_dict(dict_['title'])
        dict_['publication_date'] = (
            date.fromisoformat(dict_['publication_date']) if dict_.get('publication_date') else None
        )
        dict_['date_of_signature'] = (
            date.fromisoformat(dict_['date_of_signature']) if dict_.get('date_of_signature') else None
        )
        dict_['sections'] = [StructuredText.from_dict(sec) for sec in dict_['sections']]
        dict_['visa'] = [EnrichedString.from_dict(vu) for vu in dict_['visa']]
        classements = [Classement.from_dict(cl) for cl in dict_.get('classements') or []]
        dict_['classements'] = list(sorted(classements, key=lambda x: x.regime.value))
        classements_with_alineas = [
            ClassementWithAlineas.from_dict(cl) for cl in dict_.get('classements_with_alineas') or []
        ]
        dict_['classements_with_alineas'] = list(sorted(classements_with_alineas, key=lambda x: x.regime.value))
        dict_['summary'] = Summary.from_dict(dict_['summary']) if dict_.get('summary') else None
        dict_['version_descriptor'] = (
            VersionDescriptor.from_dict(dict_['version_descriptor']) if dict_.get('version_descriptor') else None
        )
        fields_ = set(map(attrgetter('name'), fields(cls)))
        return cls(**{key: value for key, value in dict_.items() if key in fields_})


def load_link(dict_: Dict[str, Any]) -> Link:
    return Link(dict_['target'], dict_['position'], dict_['content_size'])


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


class AMState(Enum):
    VIGUEUR = 'VIGUEUR'
    ABROGE = 'ABROGE'
    DELETED = 'DELETED'


class AMSource(Enum):
    LEGIFRANCE = 'LEGIFRANCE'
    AIDA = 'AIDA'


DELETE_REASON_MIN_NB_CHARS = 10


@dataclass
class AMMetadata:
    cid: str
    aida_page: str
    title: str
    classements: List[Classement]
    state: AMState
    date_of_signature: date
    source: AMSource
    nor: Optional[str] = None
    reason_deleted: Optional[str] = None

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'AMMetadata':
        dict_ = dict_.copy()
        dict_['aida_page'] = str(dict_['aida_page'])
        dict_['state'] = AMState(dict_['state'])
        dict_['source'] = AMSource(dict_['source'])
        date_of_signature = date.fromtimestamp(dict_['date_of_signature'])
        dict_['date_of_signature'] = date_of_signature
        if 'publication_date' in dict_:
            del dict_['publication_date']
        dict_['classements'] = [Classement.from_dict(classement) for classement in dict_['classements']]
        return AMMetadata(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        dict_ = asdict(self)
        dict_['state'] = self.state.value
        dict_['source'] = self.source.value
        dict_['date_of_signature'] = int(datetime.fromordinal(self.date_of_signature.toordinal()).timestamp())
        dict_['classements'] = [classement.to_dict() for classement in self.classements]
        return dict_


_LEGIFRANCE_LODA_BASE_URL = 'https://www.legifrance.gouv.fr/loda/id/'


def _build_legifrance_url(cid: str) -> str:
    return _LEGIFRANCE_LODA_BASE_URL + cid


def _build_aida_url(page: str) -> str:
    return AIDA_URL + page


def add_metadata(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    am = copy(am)
    am.legifrance_url = _build_legifrance_url(metadata.cid)
    am.aida_url = _build_aida_url(metadata.aida_page)
    am.classements = metadata.classements
    am.classements_with_alineas = group_classements_by_alineas(metadata.classements)
    return am


@dataclass
class AMData:
    metadata: List[AMMetadata]

    def __post_init__(self):
        ids = [am.nor or am.cid for am in self.metadata]
        non_unique_ids = [(x, cnt) for x, cnt in Counter(ids).most_common() if cnt > 1]
        if non_unique_ids:
            raise ValueError(f'There are non unique ids: {non_unique_ids}')

    @staticmethod
    def from_dict(dict_: List[Dict[str, Any]]) -> 'AMData':
        arretes_ministeriels = [AMMetadata.from_dict(x) for x in dict_]
        return AMData(arretes_ministeriels)


def load_am_data() -> AMData:
    return AMData.from_dict(ARRETES_MINISTERIELS)


_AM = load_am_data()
ALL_ID_TO_AM_MD = {am.cid: am for am in _AM.metadata}


def get_text_defined_id(text: AMMetadata) -> str:
    return text.nor or text.cid


Ints = Tuple[int, ...]


def dump_path(path: Ints) -> str:
    return json.dumps(path)


def load_path(path_str: str) -> Ints:
    return tuple(json.loads(path_str))


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


def am_to_text(am: ArreteMinisteriel) -> StructuredText:
    return StructuredText(am.title, [], am.sections, Applicability())


def add_title_default_numbering(text: StructuredText, prefix: str = '', rank: int = 0) -> StructuredText:
    text = copy(text)
    new_prefix = prefix + f'{rank+1}.'
    text.title.text = f'{new_prefix} {text.title.text}'
    text.sections = [add_title_default_numbering(section, new_prefix, i) for i, section in enumerate(text.sections)]
    return text


def _split_html_in_lines(html: str) -> List[str]:
    html = html.replace('<br/>', '').replace('>', '>\n').replace('<', '\n<')
    return [x.strip() for x in html.split('\n')]


def _extract_alineas_lines(alinea: EnrichedString) -> List[str]:
    if alinea.table:
        return _split_html_in_lines(table_to_html(alinea.table))
    return alinea.text.split('\n')


def extract_text_lines(text: StructuredText, level: int = 0) -> List[str]:
    title_lines = ['#' * level + (' ' if level else '') + text.title.text.strip()]
    alinea_lines = [line.strip() for al in text.outer_alineas for line in _extract_alineas_lines(al)]
    section_lines = [line for sec in text.sections for line in extract_text_lines(sec, level + 1)]
    return title_lines + alinea_lines + section_lines


def ensure_rubrique(candidate: str) -> str:
    if len(candidate) != 4 or candidate[0] not in '1234':
        raise ValueError(f'Incorrect rubrique value, got {candidate}')
    try:
        int(candidate)
    except ValueError:
        raise ValueError(f'Incorrect rubrique value, got {candidate}')
    return candidate
