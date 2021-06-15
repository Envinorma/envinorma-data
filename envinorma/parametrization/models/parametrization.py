from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union

from envinorma.models import Ints
from envinorma.models.structured_text import StructuredText

from ..consistency import check_conditions_are_incompatible
from ..exceptions import ParametrizationError
from .condition import Condition, LeafCondition, extract_leaf_conditions, load_condition
from .parameter import Parameter


@dataclass
class SectionReference:
    """Reference of a section in an ArreteMinisteriel

    Args:
        path (Tuple[int, ...]):
            path to the section in the tree structure of the ArreteMinisteriel
            e.g. (0, 1, 0) matches section: arrete_ministeriel.sections[0].sections[1].sections[0]
        titles_sequence (Optional[List[str]]):
            path to the section in the tree structure of the ArreteMinisteriel following
            section titles, useful when modifications are made in the AM that break the
            path search.
    """

    path: Ints
    titles_sequence: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'SectionReference':
        return cls(tuple(dict_['path']), dict_.get('titles_sequence'))


@dataclass
class EntityReference:
    section: SectionReference
    outer_alinea_indices: Optional[List[int]]

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'EntityReference':
        return EntityReference(SectionReference.from_dict(dict_['section']), dict_['outer_alinea_indices'])


@dataclass
class ConditionSource:
    reference: EntityReference

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'ConditionSource':
        return ConditionSource(EntityReference.from_dict(dict_['reference']))


@dataclass
class InapplicableSection:
    """Description of a potential inapplicable section in a ArreteMinisteriel under some condition.

    Args:
        targeted_entity (EntityReference):
            Section and alineas potentially inapplicable
        condition (Condition):
            Condition to which the targeted section is modified
        source (ConditionSource):
            Description of where the condition was found in the arrete
    """

    targeted_entity: EntityReference
    condition: Condition
    source: ConditionSource

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_entity': self.targeted_entity.to_dict(),
            'condition': self.condition.to_dict(),
            'source': self.source.to_dict(),
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'InapplicableSection':
        return InapplicableSection(
            EntityReference.from_dict(dict_['targeted_entity']),
            load_condition(dict_['condition']),
            ConditionSource.from_dict(dict_['source']),
        )


@dataclass
class AlternativeSection:
    """Description of a potential modification in a ArreteMinisteriel, applied at some condition.

    Args:
        targeted_section (SectionReference):
            Section potentially modified
        new_text (StructuredText):
            New version of the section when condition is met
        condition (Condition):
            Condition to which the targeted section is modified
        source (ConditionSource):
            Description of where the condition was found in the arrete

    """

    targeted_section: SectionReference
    new_text: StructuredText
    condition: Condition
    source: ConditionSource

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_section': self.targeted_section.to_dict(),
            'new_text': self.new_text.to_dict(),
            'condition': self.condition.to_dict(),
            'source': self.source.to_dict(),
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AlternativeSection':
        return AlternativeSection(
            SectionReference.from_dict(dict_['targeted_section']),
            StructuredText.from_dict(dict_['new_text']),
            load_condition(dict_['condition']),
            ConditionSource.from_dict(dict_['source']),
        )


@dataclass
class AMWarning:
    """Warning attached to a section of an arrete_ministeriel

    Args:
        targeted_section (SectionReference):
            Section to which the warning is attached
        text (str):
            Content of the warning

    """

    targeted_section: SectionReference
    text: str

    def to_dict(self) -> Dict[str, Any]:
        return {'targeted_section': self.targeted_section.to_dict(), 'text': self.text}

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AMWarning':
        return AMWarning(SectionReference.from_dict(dict_['targeted_section']), dict_['text'])


def extract_conditions_from_parametrization(
    parameter: Parameter, parametrization: 'Parametrization'
) -> List[LeafCondition]:
    return [leaf for cd in parametrization.extract_conditions() for leaf in extract_leaf_conditions(cd, parameter)]


def _check_consistency_on_section(
    inapplicable_sections: List[InapplicableSection], alternative_sections: List[AlternativeSection]
) -> None:
    all_conditions = [nac.condition for nac in inapplicable_sections] + [als.condition for als in alternative_sections]
    if not all_conditions:
        return None
    all_parameters = {param for condition in all_conditions for param in condition.parameters()}
    if len(all_parameters) >= 2:
        return  # complicated and infrequent, not checked for now
    if len(all_parameters) == 0:
        raise ParametrizationError('There should be at least one parameter in conditions.')
    check_conditions_are_incompatible(all_conditions, list(all_parameters)[0])


T = TypeVar('T')
K = TypeVar('K')


def _group(elements: List[T], groupper: Callable[[T], K]) -> Dict[K, List[T]]:
    groups: Dict[K, List[T]] = {}
    for element in elements:
        key = groupper(element)
        if key not in groups:
            groups[key] = []
        groups[key].append(element)
    return groups


@dataclass
class Parametrization:
    """Data class for describing parametrization of an arrete ministeriel.

    Args:
        inapplicable_sections (List[InapplicableSection]):
            list of potentially inapplicable sections of an ArreteMinisteriel
        alternative_sections (List[AlternativeSection])
            list of potentially inapplicable modified sections of an ArreteMinisteriel
        warnings (List[AMWarning])
            list of non conditionned warnings associated with an ArreteMinisteriel

    """

    inapplicable_sections: List[InapplicableSection]
    alternative_sections: List[AlternativeSection]
    warnings: List[AMWarning]
    path_to_conditions: Dict[Ints, List[InapplicableSection]] = field(init=False)
    path_to_alternative_sections: Dict[Ints, List[AlternativeSection]] = field(init=False)
    path_to_warnings: Dict[Ints, List[AMWarning]] = field(init=False)

    def __post_init__(self):
        self.path_to_conditions = _group(self.inapplicable_sections, lambda x: x.targeted_entity.section.path)
        self.path_to_alternative_sections = _group(self.alternative_sections, lambda x: x.targeted_section.path)
        self.path_to_warnings = _group(self.warnings, lambda x: x.targeted_section.path)
        self.check()
        self.check_consistency()

    def to_dict(self) -> Dict[str, Any]:
        res = {}
        res['inapplicable_sections'] = [app.to_dict() for app in self.inapplicable_sections]
        res['alternative_sections'] = [sec.to_dict() for sec in self.alternative_sections]
        res['warnings'] = [warning.to_dict() for warning in self.warnings]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Parametrization':
        # field renaming
        if 'inapplicable_sections' in dict_:
            inapplicable_sections_raw = dict_['inapplicable_sections']
        else:
            inapplicable_sections_raw = dict_['application_conditions']
        return Parametrization(
            [InapplicableSection.from_dict(app) for app in inapplicable_sections_raw],
            [AlternativeSection.from_dict(sec) for sec in dict_['alternative_sections']],
            [AMWarning.from_dict(sec) for sec in dict_.get('warnings', [])],
        )

    def extract_conditions(self) -> List[Condition]:
        return [ap.condition for ap in self.inapplicable_sections] + [
            as_.condition for as_ in self.alternative_sections
        ]

    def extract_parameters(self) -> Set[Parameter]:
        return {parameter for condition in self.extract_conditions() for parameter in condition.parameters()}

    def check(self) -> None:
        for app in self.inapplicable_sections:
            app.condition.check()
        for sec in self.alternative_sections:
            sec.condition.check()

    def _extract_all_paths(self) -> Set[Ints]:
        return set(self.path_to_alternative_sections.keys()).union(set(self.path_to_conditions.keys()))

    def check_consistency(self) -> None:
        all_paths = self._extract_all_paths()
        for path in all_paths:
            _check_consistency_on_section(
                self.path_to_conditions.get(path, []), self.path_to_alternative_sections.get(path, [])
            )


ParameterObjectWithCondition = Union[InapplicableSection, AlternativeSection]
ParameterObject = Union[ParameterObjectWithCondition, AMWarning]
Combinations = Dict[Tuple[str, ...], Dict[Parameter, Any]]
