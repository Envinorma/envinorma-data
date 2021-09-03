import re
import warnings
from copy import copy
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from envinorma.utils import AIDA_URL, LEGIFRANCE_LODA_BASE_URL, random_id

from .am_metadata import AMMetadata
from .classement import Classement, ClassementWithAlineas, group_classements_by_alineas
from .condition import Condition, load_condition
from .structured_text import StructuredText
from .text_elements import EnrichedString


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
class AMApplicability:
    warnings: List[str] = field(default_factory=list)
    condition_of_inapplicability: Optional[Condition] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.condition_of_inapplicability:
            res['condition_of_inapplicability'] = self.condition_of_inapplicability.to_dict()
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AMApplicability':
        dict_ = dict_.copy()
        if dict_.get('condition_of_inapplicability'):
            dict_['condition_of_inapplicability'] = load_condition(dict_['condition_of_inapplicability'])
        return cls(**dict_)


@dataclass
class ArreteMinisteriel:
    """Dataclass for ICPE arrete ministeriels (AM).

    Args:
        title (EnrichedString):
            title of the arrete ministeriel
        sections (List[StructuredText]):
            actual content of the AM (recursive data class, a section contains alineas and subsections)
        visa (List[EnrichedString]):
            list of visa
        date_of_signature (Optional[date]):
            date of signature of the AM. It is expected to be consistent with the AM title
            (ie. title should contain the date of signature.)
        aida_url (Optional[str]):
            optional url to the AIDA version of the arrete
        legifrance_url (Optional[str]):
            optional url to the Legifrance version of the arrete
        classements (List[Classement]):
            List of classements for which this AM is applicable, with (Rubrique, Regime) couples potentially
            repeated for several alineas
        classements_with_alineas (List[ClassementWithAlineas] = field(default_factory=list)):
            List of classements for which this AM is applicable, groupped by (Rubrique, Regime) couples
        id (Optional[str]):
            CID of the AM (of the form JORFTEXT... or LEGITEXT...)
        is_transverse (bool):
            True if the AM is transverse.
        nickname (Optional[str]):
            Optional nickname for the AM. (mainly for transverse AMs)
        applicability (Optional[AMApplicability]):
            Optional applicability descriptor of the AM.
    """

    title: EnrichedString
    sections: List[StructuredText]
    visa: List[EnrichedString]
    date_of_signature: Optional[date] = None
    aida_url: Optional[str] = None
    legifrance_url: Optional[str] = None
    classements: List[Classement] = field(default_factory=list)
    classements_with_alineas: List[ClassementWithAlineas] = field(default_factory=list)
    id: Optional[str] = field(default_factory=random_id)
    is_transverse: bool = False
    nickname: Optional[str] = None
    applicability: AMApplicability = field(default_factory=AMApplicability)

    @property
    def short_title(self) -> str:
        return extract_short_title(self.title.text)

    def __post_init__(self):
        self.title.text = _standardize_title_if_necessary(self.title.text)
        if self.date_of_signature is None:
            self.date_of_signature = extract_date_of_signature(self.title.text)
        elif self.date_of_signature != extract_date_of_signature(self.title.text):
            raise AssertionError(f'{self.date_of_signature} and {self.title.text} are inconsistent')

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
        res['applicability'] = self.applicability.to_dict()
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
        dict_['classements'] = sorted(classements, key=lambda x: x.regime.value)
        classements_with_alineas = [
            ClassementWithAlineas.from_dict(cl) for cl in dict_.get('classements_with_alineas') or []
        ]
        dict_['classements_with_alineas'] = sorted(classements_with_alineas, key=lambda x: x.regime.value)
        if 'applicability' in dict_:
            dict_['applicability'] = AMApplicability.from_dict(dict_['applicability'])
        fields_ = {field_.name for field_ in fields(cls)}
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
    am.is_transverse = metadata.is_transverse
    am.nickname = metadata.nickname
    return am
