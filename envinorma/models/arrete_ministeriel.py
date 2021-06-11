import re
import warnings
from copy import copy
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime
from operator import attrgetter
from typing import Any, Dict, List, Optional

from envinorma.models.classement import Classement, ClassementWithAlineas, group_classements_by_alineas
from envinorma.utils import AIDA_URL, LEGIFRANCE_LODA_BASE_URL, random_id

from .am_metadata import AMMetadata
from .structured_text import StructuredText
from .text_elements import EnrichedString


@dataclass(eq=True, frozen=True)
class DateParameterDescriptor:
    """
    Describes an AM version with regard to a specific date
    (e.g. the AM applicable to classements with installation date in a specific range.)

    is_used_in_parametrization
        is True if the corresponding date was used in the parametrization of the AM
    unknown_classement_date_version
        is defined if is_used_in_parametrization is True. It is true for the AM version
        corresponding to an unknown value of the date for the given classement.
    left_value
        is defined if is_used_in_parametrization is True. With right_value, it describes the date range of
        applicability of the AM. None corresponds to -infinity.
    right_value
        is defined if is_used_in_parametrization is True. With left_value, it describes the date range of
        applicability of the AM. None corresponds to +infinity.

    example:
        For an AM that changes version for date 2021-01-01, one of the generated version
        will have (
            is_used_in_parametrization=True,
            unknown_classement_date_version=False,
            left_value=None,
            right_value=2021-01-01
        )
        It corresponds to the classements whose date is known and whose date value is smaller than 2021-01-01.
    """

    is_used_in_parametrization: bool
    unknown_classement_date_version: Optional[bool] = None
    left_value: Optional[date] = None
    right_value: Optional[date] = None

    def __post_init__(self) -> None:
        if self.left_value:
            assert isinstance(self.left_value, date) and not isinstance(self.left_value, datetime)
        if self.right_value:
            assert isinstance(self.right_value, date) and not isinstance(self.right_value, datetime)
        if not self.is_used_in_parametrization:
            assert self.unknown_classement_date_version is None
            assert self.left_value is None
            assert self.right_value is None
        if self.unknown_classement_date_version in {False, True}:
            assert self.is_used_in_parametrization
        if self.is_used_in_parametrization and not self.unknown_classement_date_version:
            assert self.left_value is not None or self.right_value is not None

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
    date_de_mise_en_service: DateParameterDescriptor

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'VersionDescriptor':
        for key in ['aed_date', 'date_de_mise_en_service']:
            dict_[key] = DateParameterDescriptor.from_dict(dict_[key])
        return cls(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['aed_date'] = self.aed_date.to_dict()
        res['date_de_mise_en_service'] = self.date_de_mise_en_service.to_dict()
        return res


def _is_probably_cid(candidate: str) -> bool:
    if 'FAKE' in candidate:
        return True  # for avoiding warning for fake cids, which contain FAKE by convention
    return candidate.startswith('JORFTEXT') or candidate.startswith('LEGITEXT')


_MONTHS = r'(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)'
_PATTERN = r'Arrêté du (1er|[0-9]*) ' + _MONTHS + ' [0-9]{4}'


def _contains_human_date(title: str) -> bool:
    return re.match(_PATTERN, title) is not None


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


def _standardize_title_if_necessary(title: str) -> str:
    if title == 'Faux arrêté':  # Edge case for test text
        return 'Faux arrêté du 10/10/10'
    if _contains_human_date(title):
        return standardize_title_date(title)
    return title


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


@dataclass
class ArreteMinisteriel:
    title: EnrichedString
    sections: List[StructuredText]
    visa: List[EnrichedString]
    date_of_signature: Optional[date] = None
    aida_url: Optional[str] = None
    legifrance_url: Optional[str] = None
    classements: List[Classement] = field(default_factory=list)
    classements_with_alineas: List[ClassementWithAlineas] = field(default_factory=list)
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

        if not _is_probably_cid(self.id or ''):
            warnings.warn(f'AM id does not look like a CID : {self.id} (title={self.title.text})')

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
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
        dict_['version_descriptor'] = (
            VersionDescriptor.from_dict(dict_['version_descriptor']) if dict_.get('version_descriptor') else None
        )
        fields_ = set(map(attrgetter('name'), fields(cls)))
        return cls(**{key: value for key, value in dict_.items() if key in fields_})

    def to_text(self) -> StructuredText:
        return StructuredText(self.title, [], self.sections, None)


def _build_legifrance_url(cid: str) -> str:
    return LEGIFRANCE_LODA_BASE_URL + cid


def _build_aida_url(page: str) -> str:
    return AIDA_URL + page


def add_metadata(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    am = copy(am)
    am.legifrance_url = _build_legifrance_url(metadata.cid)
    am.aida_url = _build_aida_url(metadata.aida_page)
    am.classements = metadata.classements
    am.classements_with_alineas = group_classements_by_alineas(metadata.classements)
    return am
