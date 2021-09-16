from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TypeVar, Union
from envinorma.models.condition import Condition, LeafCondition, extract_leaf_conditions, load_condition
from envinorma.models.parameter import Parameter
from envinorma.models.structured_text import StructuredText

from ..consistency import check_conditions_not_compatible
from ..exceptions import ParametrizationError

from envinorma.utils import random_id


@dataclass
class InapplicableSection:
    """Description of a potential inapplicable section in a ArreteMinisteriel under some condition."""

    section_id: str
    alineas: Optional[List[int]]
    condition: Condition
    id: str = field(default_factory=random_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'section_id': self.section_id,
            'alineas': self.alineas,
            'condition': self.condition.to_dict(),
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'InapplicableSection':
        return InapplicableSection(
            dict_['section_id'],
            dict_['alineas'],
            load_condition(dict_['condition']),
            dict_['id'],
        )


@dataclass
class AlternativeSection:
    """Description of a potential modification in a ArreteMinisteriel, applied at some condition."""

    section_id: str
    new_text: StructuredText
    condition: Condition
    id: str = field(default_factory=random_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'section_id': self.section_id,
            'new_text': self.new_text.to_dict(),
            'condition': self.condition.to_dict(),
            'id': self.id,
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AlternativeSection':
        return AlternativeSection(
            dict_['section_id'],
            StructuredText.from_dict(dict_['new_text']),
            load_condition(dict_['condition']),
            dict_['id'],
        )


@dataclass
class AMWarning:
    """Warning attached to a section of an arrete_ministeriel."""

    section_id: str
    text: str
    id: str = field(default_factory=random_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'section_id': self.section_id,
            'text': self.text,
            'id': self.id,
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AMWarning':
        return AMWarning(
            dict_['section_id'],
            dict_['text'],
            dict_['id'],
        )


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
    check_conditions_not_compatible(all_conditions, list(all_parameters)[0])


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
    id_to_conditions: Dict[str, List[InapplicableSection]] = field(init=False)
    id_to_alternative_sections: Dict[str, List[AlternativeSection]] = field(init=False)
    id_to_warnings: Dict[str, List[AMWarning]] = field(init=False)

    def __post_init__(self):
        self.id_to_conditions = _group(self.inapplicable_sections, lambda x: x.section_id)
        self.id_to_alternative_sections = _group(self.alternative_sections, lambda x: x.section_id)
        self.id_to_warnings = _group(self.warnings, lambda x: x.section_id)
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
        for condition in self.extract_conditions():
            condition.check()

    def _extract_all_ids(self) -> Set[str]:
        return set(self.id_to_alternative_sections.keys()).union(set(self.id_to_conditions.keys()))

    def check_consistency(self) -> None:
        all_ids = self._extract_all_ids()
        for id_ in all_ids:
            _check_consistency_on_section(
                self.id_to_conditions.get(id_, []), self.id_to_alternative_sections.get(id_, [])
            )


ParameterObjectWithCondition = Union[InapplicableSection, AlternativeSection]
ParameterObject = Union[ParameterObjectWithCondition, AMWarning]
Combinations = Dict[Tuple[str, ...], Dict[Parameter, Any]]
