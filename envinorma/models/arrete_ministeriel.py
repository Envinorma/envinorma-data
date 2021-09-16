import warnings
from copy import copy
from dataclasses import asdict, dataclass, field, fields
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from envinorma.topics.patterns import TopicName
from envinorma.utils import random_id

from .am_applicability import AMApplicability
from .classement import Classement, ClassementWithAlineas
from .helpers import (
    extract_date_of_signature,
    extract_short_title,
    standardize_title_if_necessary,
    transfer_ids_based_on_other_am,
)
from .lost_topic import LostTopic
from .structured_text import Annotations, EnrichedString, StructuredText


def _is_probably_cid(candidate: str) -> bool:
    if 'FAKE' in candidate:
        return True  # for avoiding warning for fake cids, which contain FAKE by convention
    return candidate.startswith('JORFTEXT') or candidate.startswith('LEGITEXT')


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
        orphan_titles (Optional[Dict[str, str]]):
            TODO
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
    orphan_titles: Optional[Dict[str, List[str]]] = None

    @property
    def short_title(self) -> str:
        return extract_short_title(self.title.text)

    def __post_init__(self):
        self.title.text = standardize_title_if_necessary(self.title.text)
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

    def descendent_sections(self) -> List[StructuredText]:
        descendent_sections = self.sections.copy()
        for section in self.sections:
            descendent_sections.extend(section.descendent_sections())
        return descendent_sections

    def section_id_to_topic(self) -> Dict[str, TopicName]:
        return {
            section.id: section.annotations.topic
            for section in self.descendent_sections()
            if section.annotations and section.annotations.topic
        }

    def titles_sequences(self) -> Dict[str, List[str]]:
        return {
            section_id: titles_sequence
            for section in self.sections
            for section_id, titles_sequence in section.titles_sequences().items()
        }

    def _lost_topics(self, not_found_topics: Dict[str, TopicName]) -> List[LostTopic]:
        if not not_found_topics:
            return []
        return [LostTopic(topic, (self.orphan_titles or {})[id_], id_) for id_, topic in not_found_topics.items()]

    def set_topics(self, section_id_to_topic: Dict[str, TopicName]) -> List[LostTopic]:
        descendent_sections = self.descendent_sections()
        for section in descendent_sections:
            section.annotations = section.annotations or Annotations()
            section.annotations.topic = section_id_to_topic.get(section.id)
        section_ids = {section.id for section in descendent_sections}
        not_found_topics = {id_: topic for id_, topic in section_id_to_topic.items() if id_ not in section_ids}
        return self._lost_topics(not_found_topics)

    def change_ids_based_on_other_am(self, am: 'ArreteMinisteriel') -> None:
        self.orphan_titles = transfer_ids_based_on_other_am(self, am)

    def create_copy_with_new_content(
        self, new_sections: List[StructuredText]
    ) -> Tuple['ArreteMinisteriel', List[LostTopic]]:
        section_id_to_topic = self.section_id_to_topic()
        new_am = copy(self)
        new_am.sections = new_sections
        new_am.change_ids_based_on_other_am(self)
        lost_topics = new_am.set_topics(section_id_to_topic)
        return new_am, lost_topics
