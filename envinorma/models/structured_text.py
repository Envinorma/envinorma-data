from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

from envinorma.topics.patterns import TopicName
from envinorma.utils import random_id

from .condition import Condition, load_condition
from .helpers.condition_satisfiability import could_be_simultaneously_satisfied_with
from .text_elements import EnrichedString


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
    """Describes the applicability of a StructuredText.

    A StructuredText can either be applicable, inapplicable or applicable with modifications.

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
class PotentialInapplicability:
    condition: Condition
    alineas: Optional[List[int]]
    subsections_are_inapplicable: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            'condition': self.condition.to_dict(),
            'alineas': self.alineas,
            'subsections_are_inapplicable': self.subsections_are_inapplicable,
        }

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'PotentialInapplicability':
        dict_ = dict_.copy()
        dict_['condition'] = load_condition(dict_['condition'])
        return cls(**dict_)

    def similar_to(self, other: 'PotentialInapplicability') -> bool:
        """Whether the two potential inapplicabilities are equal except for the condition.

        Returns:
            whether the two potential inapplicabilities are equal except for the condition.
        """
        if self.alineas != other.alineas:
            return False
        if self.subsections_are_inapplicable != other.subsections_are_inapplicable:
            return False
        return True

    def is_compatible_with(self, other: 'InapplicabilityOrModification') -> bool:
        """Whether the two objects are compatible.

        The two objects are compatible if they are similar or if the conditions of the object
        cannot be simultaneously satisfied.

        Returns:
            Whether the two objects are compatible.
        """
        if isinstance(other, PotentialInapplicability):
            if self.similar_to(other):
                return True
        return not could_be_simultaneously_satisfied_with(self.condition, other.condition)


def _alinea_content(string: EnrichedString) -> str:
    if string.table:
        return string.table.to_html()
    return string.text


def _alineas_content(strings: List[EnrichedString]) -> List[str]:
    return [_alinea_content(str_) for str_ in strings]


@dataclass
class PotentialModification:
    condition: Condition
    new_version: 'StructuredText'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'condition': self.condition.to_dict(),
            'new_version': self.new_version.to_dict(),
        }

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'PotentialModification':
        dict_ = dict_.copy()
        dict_['condition'] = load_condition(dict_['condition'])
        dict_['new_version'] = StructuredText.from_dict(dict_['new_version'])
        return cls(**dict_)

    def similar_to(self, other: 'PotentialModification') -> bool:
        """Whether the two potential modifications are equal except for the condition.

        Returns:
            whether the two potential modifications are equal except for the condition.
        """
        if self.new_version.title.text != other.new_version.title.text:
            return False
        if _alineas_content(self.new_version.outer_alineas) != _alineas_content(other.new_version.outer_alineas):
            return False
        return True

    def is_compatible_with(self, other: 'InapplicabilityOrModification') -> bool:
        """Whether the two objects are compatible.

        The two objects are compatible if they are similar or if the conditions of the object
        cannot be simultaneously satisfied.

        Returns:
            Whether the two objects are compatible.
        """
        if isinstance(other, PotentialModification):
            if self.similar_to(other):
                return True
        return not could_be_simultaneously_satisfied_with(self.condition, other.condition)


InapplicabilityOrModification = Union[PotentialInapplicability, PotentialModification]


@dataclass
class SectionParametrization:
    potential_inapplicabilities: List[PotentialInapplicability] = field(default_factory=list)
    potential_modifications: List[PotentialModification] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        dict_ = asdict(self)
        dict_['potential_inapplicabilities'] = [p.to_dict() for p in self.potential_inapplicabilities]
        dict_['potential_modifications'] = [p.to_dict() for p in self.potential_modifications]
        return dict_

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'SectionParametrization':
        dict_ = dict_.copy()
        dict_['potential_inapplicabilities'] = [
            PotentialInapplicability.from_dict(p) for p in dict_['potential_inapplicabilities']
        ]
        dict_['potential_modifications'] = [
            PotentialModification.from_dict(p) for p in dict_['potential_modifications']
        ]
        return cls(**dict_)


@dataclass
class Reference:
    nb: str
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'nb': self.nb,
            'name': self.name,
        }

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Reference':
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
        reference (Optional[Reference] = None):
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
    reference: Optional[Reference] = None
    annotations: Optional[Annotations] = None
    id: str = field(default_factory=random_id)
    parametrization: SectionParametrization = field(default_factory=SectionParametrization)

    def __post_init__(self):
        if not isinstance(self.title, EnrichedString):
            raise TypeError

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['title'] = self.title.to_dict()
        res['outer_alineas'] = [al.to_dict() for al in self.outer_alineas]
        res['sections'] = [se.to_dict() for se in self.sections]
        res['applicability'] = self.applicability.to_dict() if self.applicability else None
        res['annotations'] = self.annotations.to_dict() if self.annotations else None
        res['parametrization'] = self.parametrization.to_dict()
        res['reference'] = self.reference.to_dict() if self.reference else None
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'StructuredText':
        return cls(
            title=EnrichedString.from_dict(dict_['title']),
            outer_alineas=[EnrichedString.from_dict(al) for al in dict_['outer_alineas']],
            sections=[StructuredText.from_dict(sec) for sec in dict_['sections']],
            applicability=Applicability.from_dict(dict_['applicability']) if dict_.get('applicability') else None,
            reference=Reference.from_dict(dict_['reference']) if dict_.get('reference') else None,
            annotations=Annotations.from_dict(dict_['annotations']) if dict_.get('annotations') else None,
            id=dict_['id'] if 'id' in dict_ else random_id(),
            parametrization=SectionParametrization.from_dict(dict_['parametrization'])
            if dict_.get('parametrization')
            else SectionParametrization(),
        )

    def text_lines(self, level: int = 0) -> List[str]:
        title_lines = ['#' * level + (' ' if level else '') + self.title.text.strip()]
        alinea_lines = [line.strip() for al in self.outer_alineas for line in al.text_lines()]
        section_lines = [line for sec in self.sections for line in sec.text_lines(level + 1)]
        return title_lines + alinea_lines + section_lines

    def descendent_sections(self) -> List['StructuredText']:
        descendent_sections = self.sections.copy()
        for section in self.sections:
            descendent_sections.extend(section.descendent_sections())
        return descendent_sections

    def titles_sequences(self) -> Dict[str, List[str]]:
        result = {
            section_id: [self.title.text] + titles_sequence
            for section in self.sections
            for section_id, titles_sequence in section.titles_sequences().items()
        }
        result[self.id] = [self.title.text]
        return result

    def parametrization_elements_are_compatible(self) -> bool:
        elts: List[InapplicabilityOrModification] = [
            *self.parametrization.potential_inapplicabilities,
            *self.parametrization.potential_modifications,
        ]
        return all([elts[i].is_compatible_with(elts[j]) for i in range(len(elts) - 1) for j in range(i + 1, len(elts))])
