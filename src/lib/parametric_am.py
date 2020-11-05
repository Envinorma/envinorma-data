from copy import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from lib.am_structure_extraction import ArreteMinisteriel, EnrichedString, LegifranceArticle, StructuredText
from lib.texts_properties import extract_am_structure


class ParameterType(Enum):
    DATE = 'DATE'


@dataclass
class Parameter:
    id: str
    type: ParameterType


class ParameterEnum(Enum):
    DATE_D_AUTORISATION = Parameter('date-d-autorisation', ParameterType.DATE)


class ConditionType(Enum):
    EQUAL = 'EQUAL'
    AND = 'AND'
    OR = 'OR'
    RANGE = 'RANGE'
    GREATER = 'GREATER'
    LITTLER = 'LITTLER'


@dataclass
class AndCondition:
    conditions: List['ApplicationCondition']
    type: ConditionType = ConditionType.AND


@dataclass
class OrCondition:
    conditions: List['ApplicationCondition']
    type: ConditionType = ConditionType.OR


@dataclass
class Littler:
    parameter: Parameter
    target: Any
    strict: bool
    type: ConditionType = ConditionType.LITTLER


@dataclass
class Greater:
    parameter: Parameter
    target: Any
    strict: bool
    type: ConditionType = ConditionType.GREATER


@dataclass
class Equal:
    parameter: Parameter
    target: Any
    type: ConditionType = ConditionType.EQUAL


@dataclass
class Range:
    parameter: Parameter
    left: Any
    right: Any
    left_strict: bool
    right_strict: bool
    type: ConditionType = ConditionType.RANGE


ApplicationCondition = Union[Equal, Range, Greater, Littler, AndCondition, OrCondition]


@dataclass
class ConditionalText:
    text: StructuredText
    condition: ApplicationCondition


@dataclass
class AlineaReference:
    section_index: Optional[int]
    outer_alinea_indices: List[int]
    reference_in_subsection: Optional['AlineaReference']


@dataclass
class ParametrizationSource:
    explanation: str
    reference: AlineaReference


@dataclass
class TextWithParametricSections:
    title: EnrichedString
    outer_alineas: List[EnrichedString]
    sections: List['ParametricText']
    legifrance_article: Optional[LegifranceArticle]


@dataclass
class ParametricText:
    default: TextWithParametricSections
    parametric_versions: List[ConditionalText]
    parametrization_sources: List[ParametrizationSource]


@dataclass
class ParametricAM:
    title: EnrichedString
    visa: List[EnrichedString]
    sections: List[ParametricText]


def structured_text_to_parametric_text(text: StructuredText) -> ParametricText:
    return ParametricText(
        TextWithParametricSections(
            text.title,
            text.outer_alineas,
            [structured_text_to_parametric_text(section) for section in text.sections],
            text.legifrance_article,
        ),
        [],
        [],
    )


def am_to_parametric_am(am: ArreteMinisteriel) -> ParametricAM:
    return ParametricAM(am.title, am.visa, [structured_text_to_parametric_text(section) for section in am.sections])


def _extract_sections(am: Union[ParametricAM, ParametricText], path: List[str]) -> Dict[str, ParametricText]:
    sections = am.sections if isinstance(am, ParametricAM) else am.default.sections
    res = {section.default.title.text: section for section in sections}
    if not path:
        return res
    return _extract_sections(res[path[0]], path[1:])


def _extract_section(am: Union[ParametricAM, ParametricText], path: List[str]) -> ParametricText:
    if not path:
        raise ValueError()
    return _extract_sections(am, path[:-1])[path[-1]]


def _parametric_text_to_structured_text(text: TextWithParametricSections) -> StructuredText:
    return StructuredText(
        text.title,
        text.outer_alineas,
        [_parametric_text_to_structured_text(section.default) for section in text.sections],
        text.legifrance_article,
    )


def _condition_text(
    text: ParametricText, condition: ApplicationCondition, source: ParametrizationSource
) -> ParametricText:
    if text.parametric_versions:
        raise ValueError('Can only add new parametric version.')
    if text.parametrization_sources:
        raise ValueError('Can only add new parametrization source.')
    parametric_version = ConditionalText(_parametric_text_to_structured_text(text.default), condition)
    return ParametricText(text.default, [parametric_version], [source])


def _condition_text_subsection(
    text: ParametricText, condition: ApplicationCondition, source: ParametrizationSource, path: List[int]
) -> ParametricText:
    if not path:
        return _condition_text(text, condition, source)
    default = copy(text.default)
    default.sections = [
        _condition_text_subsection(section, condition, source, path[1:]) if i == path[0] else section
        for i, section in enumerate(default.sections)
    ]
    return ParametricText(default, text.parametric_versions, text.parametrization_sources)


def _condition_am_subsection(
    am: ParametricAM, condition: ApplicationCondition, source: ParametrizationSource, path: List[int]
) -> ParametricAM:
    if not path:
        raise ValueError('Path can\'t be empty.')
    sections = [
        _condition_text_subsection(section, condition, source, path[1:]) if i == path[0] else section
        for i, section in enumerate(am.sections)
    ]
    return ParametricAM(am.title, am.visa, sections)


def _add_conditional_version(
    text: ParametricText, new_section: ConditionalText, source: Optional[ParametrizationSource]
) -> ParametricText:
    final_text = copy(text)
    text.parametric_versions.append(new_section)
    if source:
        text.parametrization_sources.append(source)
    return final_text


def _add_conditional_version_subsection(
    text: ParametricText, new_section: ConditionalText, source: Optional[ParametrizationSource], path: List[int]
) -> ParametricText:
    if not path:
        return _add_conditional_version(text, new_section, source)
    default = copy(text.default)
    default.sections = [
        _add_conditional_version_subsection(section, new_section, source, path[1:]) if i == path[0] else section
        for i, section in enumerate(default.sections)
    ]
    return ParametricText(default, text.parametric_versions, text.parametrization_sources)


def _add_conditional_version_in_am(
    am: ParametricAM, new_section: ConditionalText, source: Optional[ParametrizationSource], path: List[int]
) -> ParametricAM:
    sections = [
        _add_conditional_version_subsection(section, new_section, source, path[1:]) if i == path[0] else section
        for i, section in enumerate(am.sections)
    ]
    return ParametricAM(am.title, am.visa, sections)


def condition_to_str(condition: ApplicationCondition, depth: int) -> str:
    prefix = '|--' * depth
    if isinstance(condition, Equal):
        return f'{prefix}Si {condition.parameter.id} == {condition.target}:'
    if isinstance(condition, Littler):
        comp = '<' if condition.strict else '<='
        return f'{prefix}Si {condition.parameter.id} {comp} {condition.target}:'
    if isinstance(condition, Greater):
        comp = '>' if condition.strict else '>='
        return f'{prefix}Si {condition.parameter.id} {comp} {condition.target}:'
    raise NotImplementedError(f'stringifying condition {condition.type} is not implemented yet.')


def _extract_conditional_text_structure(text: ConditionalText, depth: int) -> List[str]:
    return [condition_to_str(text.condition, depth), *extract_am_structure(text.text, '|--' * (depth + 1))]


def _extract_parametrized_text_structure(text: ParametricText, depth: int) -> List[str]:
    prefix = '|--' * depth
    if not text.parametric_versions:
        return [
            f'{prefix}{text.default.title.text}',
            *[
                str_
                for section in text.default.sections
                for str_ in _extract_parametrized_text_structure(section, depth + 1)
            ],
        ]
    return [str_ for text in text.parametric_versions for str_ in _extract_conditional_text_structure(text, depth)]


def _extract_parametrized_am_structure(am: ParametricAM) -> List[str]:
    return [
        am.title.text,
        *[str_ for section in am.sections for str_ in _extract_parametrized_text_structure(section, 1)],
    ]


def _extract_parameters(am: ParametricAM) -> List[Parameter]:
    pass  # TODO


def _apply_parameter_values(am: ParametricAM, parameter_values: Dict[Parameter, Any]) -> ArreteMinisteriel:
    pass  # TODO

