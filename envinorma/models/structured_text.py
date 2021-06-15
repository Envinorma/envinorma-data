from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from envinorma.models.text_elements import EnrichedString
from envinorma.topics.patterns import TopicName
from envinorma.utils import random_id


@dataclass
class Annotations:
    topic: Optional[TopicName] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.topic:
            res['topic'] = self.topic.value
        return res

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Annotations':
        return cls(topic=TopicName(dict_['topic']) if dict_['topic'] else None)


@dataclass
class Applicability:
    """Describes the applicability of a StructuredText. It can either be applicable,
    inapplicable or applicable with modifications.

    Args:
        active (bool = True):
            True is the associated StructuredText is applicable.
        modified (bool = False):
            True is the associated StructuredText is modified in the considered context.
        warnings (List[str] = []):
            List of warnings for explaining why the section could be inactive, why it is modified
            of why it is inactive.
        previous_version (Optional[StructuredText] = None):
            if modified is True, the previous version from which it was modified.

    Raises:
        ValueError: when modified is True but previous_version is not given
    """

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
class StructuredText:
    """Section of a text. This data structure can contain sections itself.

    Args:
        title (EnrichedString):
            section title
        outer_alineas (List[EnrichedString]):
            alineas before the first sections
        sections (List[StructuredText]):
            list of subsections contained after alineas
        applicability (Optional[Applicability]):
            describes the applicability of the text in a certain context
        reference_str (Optional[str] = None):
            reference of the current section in the section tree (for human reader)
        annotations (Optional[Annotations] = None):
            misc annotations for enriching purposes
        id (str = field(default_factory=random_id)):
            identifier of the section
    """

    title: EnrichedString
    outer_alineas: List[EnrichedString]
    sections: List['StructuredText']
    applicability: Optional[Applicability]
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
        if 'lf_id' in dict_:
            del dict_['lf_id']  # retrocompatibility
        return cls(**dict_)

    def text_lines(self, level: int = 0) -> List[str]:
        title_lines = ['#' * level + (' ' if level else '') + self.title.text.strip()]
        alinea_lines = [line.strip() for al in self.outer_alineas for line in al.text_lines()]
        section_lines = [line for sec in self.sections for line in sec.text_lines(level + 1)]
        return title_lines + alinea_lines + section_lines
