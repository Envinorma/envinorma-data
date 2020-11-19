from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Union, Tuple, Optional

from lib.data import Regime, StructuredText


class ParameterType(Enum):
    DATE = 'DATE'
    REGIME = 'REGIME'
    BOOLEAN = 'BOOLEAN'


@dataclass(eq=True, frozen=True)
class Parameter:
    id: str
    type: ParameterType

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Parameter':
        return Parameter(dict_['id'], ParameterType(dict_['type']))


class ParameterEnum(Enum):
    DATE_AUTORISATION = Parameter('date-d-autorisation', ParameterType.DATE)
    DATE_INSTALLATION = Parameter('date-d-installation', ParameterType.DATE)
    REGIME = Parameter('regime', ParameterType.REGIME)


class ConditionType(Enum):
    EQUAL = 'EQUAL'
    AND = 'AND'
    OR = 'OR'
    RANGE = 'RANGE'
    GREATER = 'GREATER'
    LITTLER = 'LITTLER'


def load_condition(dict_: Dict[str, Any]) -> 'Condition':
    type_ = ConditionType(dict_['type'])
    if type_ == ConditionType.AND:
        return AndCondition.from_dict(dict_)
    if type_ == ConditionType.OR:
        return OrCondition.from_dict(dict_)
    if type_ == ConditionType.EQUAL:
        return Equal.from_dict(dict_)
    if type_ == ConditionType.GREATER:
        return Greater.from_dict(dict_)
    if type_ == ConditionType.LITTLER:
        return Littler.from_dict(dict_)
    if type_ == ConditionType.RANGE:
        return Range.from_dict(dict_)
    raise ValueError(f'Unknown condition type {type_}')


@dataclass
class AndCondition:
    conditions: List['Condition']
    type: ConditionType = ConditionType.AND

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['conditions'] = [cd.to_dict() for cd in self.conditions]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AndCondition':
        return AndCondition([load_condition(cd) for cd in dict_['conditions']])


@dataclass
class OrCondition:
    conditions: List['Condition']
    type: ConditionType = ConditionType.OR

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['conditions'] = [cd.to_dict() for cd in self.conditions]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'OrCondition':
        return OrCondition([load_condition(cd) for cd in dict_['conditions']])


def parameter_value_to_dict(value: Any, type_: ParameterType) -> Any:
    if type_ == ParameterType.DATE:
        return int(value.timestamp())
    if type_ == ParameterType.REGIME:
        return value.value
    return value


def load_target(json_value: Any, type_: ParameterType) -> Any:
    if type_ == ParameterType.DATE:
        return datetime.fromtimestamp(json_value)
    if type_ == ParameterType.REGIME:
        return Regime(json_value)
    return json_value


@dataclass
class Littler:
    parameter: Parameter
    target: Any
    strict: bool = True
    type: ConditionType = ConditionType.LITTLER

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Littler':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Littler(parameter, load_target(dict_['target'], parameter.type), dict_['strict'])


@dataclass
class Greater:
    parameter: Parameter
    target: Any
    strict: bool = False
    type: ConditionType = ConditionType.GREATER

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Greater':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Greater(parameter, load_target(dict_['target'], parameter.type), dict_['strict'])


@dataclass
class Equal:
    parameter: Parameter
    target: Any
    type: ConditionType = ConditionType.EQUAL

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Equal':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Equal(parameter, load_target(dict_['target'], parameter.type))


@dataclass
class Range:
    parameter: Parameter
    left: Any
    right: Any
    left_strict: bool = False
    right_strict: bool = True
    type: ConditionType = ConditionType.RANGE

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['left'] = parameter_value_to_dict(self.left, self.parameter.type)
        res['right'] = parameter_value_to_dict(self.right, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Range':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Range(
            Parameter.from_dict(dict_['parameter']),
            load_target(dict_['left'], parameter.type),
            load_target(dict_['right'], parameter.type),
            dict_['left_strict'],
            dict_['right_strict'],
        )


LeafCondition = Union[Equal, Range, Greater, Littler]

Condition = Union[LeafCondition, AndCondition, OrCondition]


def condition_to_str(condition: Condition) -> str:
    if isinstance(condition, Equal):
        return f'{condition.parameter.id} == {condition.target}'
    if isinstance(condition, Littler):
        comp = '<' if condition.strict else '<='
        return f'{condition.parameter.id} {comp} {condition.target}'
    if isinstance(condition, Greater):
        comp = '>' if condition.strict else '>='
        return f'{condition.parameter.id} {comp} {condition.target}'
    if isinstance(condition, Range):
        left_comp = '<' if condition.left_strict else '<='
        right_comp = '<' if condition.right_strict else '<='
        return f'{condition.left} {left_comp} {condition.parameter.id} {right_comp} {condition.right_strict}'
    if isinstance(condition, AndCondition):
        return '(' + ') and ('.join([condition_to_str(cd) for cd in condition.conditions]) + ')'
    if isinstance(condition, OrCondition):
        return '(' + ') and ('.join([condition_to_str(cd) for cd in condition.conditions]) + ')'
    raise NotImplementedError(f'stringifying condition {condition} is not implemented yet.')


Ints = Tuple[int, ...]


@dataclass
class SectionReference:
    path: Ints

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'SectionReference':
        return SectionReference(tuple(dict_['path']))


@dataclass
class EntityReference:
    section: SectionReference
    outer_alinea_indices: Optional[List[int]]
    whole_arrete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'EntityReference':
        whole_arrete = dict_['whole_arrete'] if 'whole_arrete' in dict_ else False
        return EntityReference(
            SectionReference.from_dict(dict_['section']), dict_['outer_alinea_indices'], whole_arrete
        )


@dataclass
class ConditionSource:
    explanation: str
    reference: EntityReference

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'ConditionSource':
        return ConditionSource(dict_['explanation'], EntityReference.from_dict(dict_['reference']))


@dataclass
class NonApplicationCondition:
    targeted_entity: EntityReference
    condition: Condition
    source: ConditionSource
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_entity': self.targeted_entity.to_dict(),
            'condition': self.condition.to_dict(),
            'source': self.source.to_dict(),
            'description': self.description,
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'NonApplicationCondition':
        return NonApplicationCondition(
            EntityReference.from_dict(dict_['targeted_entity']),
            load_condition(dict_['condition']),
            ConditionSource.from_dict(dict_['source']),
            dict_.get('description'),
        )


@dataclass
class AlternativeSection:
    targeted_section: SectionReference
    new_text: StructuredText
    condition: Condition
    source: ConditionSource
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'targeted_section': self.targeted_section.to_dict(),
            'new_text': self.new_text.to_dict(),
            'condition': self.condition.to_dict(),
            'source': self.source.to_dict(),
            'description': self.description,
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AlternativeSection':
        return AlternativeSection(
            SectionReference.from_dict(dict_['targeted_section']),
            StructuredText.from_dict(dict_['new_text']),
            load_condition(dict_['condition']),
            ConditionSource.from_dict(dict_['source']),
            dict_.get('description'),
        )


@dataclass
class Parametrization:
    application_conditions: List[NonApplicationCondition]
    alternative_sections: List[AlternativeSection]
    path_to_conditions: Dict[Ints, List[NonApplicationCondition]] = field(init=False)
    path_to_alternative_sections: Dict[Ints, List[AlternativeSection]] = field(init=False)

    def __post_init__(self):
        self.path_to_conditions = {}
        for cd in self.application_conditions:
            path = cd.targeted_entity.section.path
            if path not in self.path_to_conditions:
                self.path_to_conditions[path] = []
            self.path_to_conditions[path].append(cd)

        self.path_to_alternative_sections = {}
        for sec in self.alternative_sections:
            path = sec.targeted_section.path
            if path not in self.path_to_alternative_sections:
                self.path_to_alternative_sections[path] = []
            self.path_to_alternative_sections[path].append(sec)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'application_conditions': [app.to_dict() for app in self.application_conditions],
            'alternative_sections': [sec.to_dict() for sec in self.alternative_sections],
        }

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Parametrization':
        return Parametrization(
            [NonApplicationCondition.from_dict(app) for app in dict_['application_conditions']],
            [AlternativeSection.from_dict(sec) for sec in dict_['alternative_sections']],
        )


def _extract_text(text: StructuredText, depth: int) -> List[str]:
    lines: List[str] = []
    lines.append('#' * depth + f' {text.title.text}')
    lines.extend([al.text for al in text.outer_alineas])
    lines.extend([line for section in text.sections for line in _extract_text(section, depth + 1)])
    return lines


def _text_to_raw_text_markdown(text: StructuredText) -> str:
    lines: List[str] = []
    lines.append('```')
    lines.extend(_extract_text(text, 1) or ['(texte vide)'])
    lines.append('```')
    return '\n\n'.join(lines)


def _condition_source_to_markdown(source: ConditionSource) -> str:
    lines: List[str] = []
    lines.append(f'\tSection: {list(source.reference.section.path)}')
    lines.append(f'\tAlineas: {source.reference.outer_alinea_indices or "tous"}')
    lines.append(f'\tExplication: {source.explanation}')
    return '\n\n'.join(lines)


def alternative_section_to_markdown(section: AlternativeSection) -> str:
    markdown: List[str] = []
    markdown.append(f'Description : {section.description}')
    markdown.append('Condition de modification :')
    markdown.append(f'\t {condition_to_str(section.condition)}')
    markdown.append('Nouveau texte :')
    markdown.append(_text_to_raw_text_markdown(section.new_text))
    markdown.append('Source :')
    markdown.append(_condition_source_to_markdown(section.source))
    return '\n\n'.join(markdown)


def non_application_condition_to_markdown(condition: NonApplicationCondition) -> str:
    markdown: List[str] = []
    markdown.append(f'Description : {condition.description}')
    markdown.append('Non applicable si :')
    markdown.append(f'\t {condition_to_str(condition.condition)}')
    markdown.append('Alinéas abrogés :' + ('tous' if condition.targeted_entity.outer_alinea_indices else ''))
    markdown.append('Source :')
    markdown.append(_condition_source_to_markdown(condition.source))
    return '\n\n'.join(markdown)


def sections_and_conditions_to_markdown(
    path: Ints,
    alternative_sections: List[AlternativeSection],
    non_application_conditions: List[NonApplicationCondition],
) -> str:
    lines: List[str] = []
    lines.append(f'## Section {list(path)}')
    lines.append('### Sections alternatives')
    lines.extend([f'#### {i}' + alternative_section_to_markdown(alt) for i, alt in enumerate(alternative_sections)])
    lines.append('### Applications conditionnées')
    lines.extend(
        [f'#### {i}\n\n' + non_application_condition_to_markdown(na) for i, na in enumerate(non_application_conditions)]
    )
    return '\n\n'.join(lines)


def parametrization_to_markdown(parametrization: Parametrization) -> str:
    all_paths = list(parametrization.path_to_alternative_sections) + list(parametrization.path_to_conditions)
    markdown_lines: List[str] = []
    for path in sorted(all_paths):
        markdown_lines.append(
            sections_and_conditions_to_markdown(
                path,
                parametrization.path_to_alternative_sections.get(path, []),
                parametrization.path_to_conditions.get(path, []),
            )
        )
    return '\n\n'.join(markdown_lines)


def build_simple_parametrization(
    non_applicable_section_references: List[Ints],
    modified_articles: Dict[Ints, StructuredText],
    source_section: Ints,
    date: datetime,
) -> Parametrization:
    source = ConditionSource(
        'Paragraphe décrivant ce qui s\'applique aux installations existantes',
        EntityReference(SectionReference(source_section), None),
    )
    date_str = date.strftime('%d-%m-%Y')
    description = (
        f'''Le paragraphe ne s'applique qu'aux sites dont la date d'installation est postérieure au {date_str}.'''
    )
    is_old_installation = Littler(ParameterEnum.DATE_INSTALLATION.value, date)
    is_new_installation = Greater(ParameterEnum.DATE_INSTALLATION.value, date)
    application_conditions = [
        NonApplicationCondition(
            EntityReference(SectionReference(tuple(ref)), None), is_old_installation, source, description
        )
        for ref in non_applicable_section_references
    ]
    description = (
        f'''Le paragraphe est modifié pour les sites dont la date d'installation est postérieure au {date_str}.'''
    )
    alternative_sections = [
        AlternativeSection(SectionReference(ref), value, is_new_installation, source, description)
        for ref, value in modified_articles.items()
    ]
    return Parametrization(application_conditions, alternative_sections)

