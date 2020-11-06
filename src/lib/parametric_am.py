from copy import copy
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, KeysView, List, Optional, Set, Tuple, Union
from lib.am_structure_extraction import ArreteMinisteriel, EnrichedString, LegifranceArticle, StructuredText
from lib.texts_properties import extract_am_structure


class ParameterType(Enum):
    DATE = 'DATE'
    BOOLEAN = 'BOOLEAN'


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
    section_path: List[int]
    outer_alinea_indices: Optional[List[int]]


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
    short_title: str


def _generate_bool_condition(parameter_str: str) -> Equal:
    return Equal(Parameter(parameter_str, ParameterType.BOOLEAN), True)


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
    return ParametricAM(
        am.title, am.visa, [structured_text_to_parametric_text(section) for section in am.sections], am.short_title
    )


def _extract_section_titles(am: Union[ParametricAM, ParametricText], path: List[int]) -> Dict[int, str]:
    sections = am.sections if isinstance(am, ParametricAM) else am.default.sections
    if not path:
        titles = {i: section.default.title.text for i, section in enumerate(sections)}
        return titles
    return _extract_section_titles(sections[path[0]], path[1:])


def _extract_section(am: Union[ParametricAM, ParametricText], path: List[int]) -> ParametricText:
    if not path:
        if isinstance(am, ParametricAM):
            raise ValueError()
        return am
    sections = am.sections if isinstance(am, ParametricAM) else am.default.sections
    return _extract_section(sections[0], path[1:])


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
    return ParametricAM(am.title, am.visa, sections, am.short_title)


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
    return ParametricAM(am.title, am.visa, sections, am.short_title)


def condition_to_str(condition: ApplicationCondition) -> str:
    if isinstance(condition, Equal):
        return f'Si {condition.parameter.id} == {condition.target}:'
    if isinstance(condition, Littler):
        comp = '<' if condition.strict else '<='
        return f'Si {condition.parameter.id} {comp} {condition.target}:'
    if isinstance(condition, Greater):
        comp = '>' if condition.strict else '>='
        return f'Si {condition.parameter.id} {comp} {condition.target}:'
    raise NotImplementedError(f'stringifying condition {condition.type} is not implemented yet.')


def _extract_conditional_text_structure(
    text: ConditionalText, depth: int, with_paths: bool, path: List[int]
) -> List[str]:
    prefix = '|--' * depth
    return [
        prefix + condition_to_str(text.condition) + ' ' + (str(path) if with_paths else ''),
        prefix + '|--' + text.text.title.text,
        *extract_am_structure(text.text, '|--' * (depth + 2)),
    ]


def _extract_parametrized_text_structure(
    text: ParametricText, depth: int, with_paths: bool, path_prefix: List[int]
) -> List[str]:
    prefix = '|--' * depth
    if not text.parametric_versions:
        return [
            f'{prefix}{text.default.title.text}' + ' ' + (str(path_prefix) if with_paths else ''),
            *[
                str_
                for i, section in enumerate(text.default.sections)
                for str_ in _extract_parametrized_text_structure(section, depth + 1, with_paths, path_prefix + [i])
            ],
        ]
    return [
        str_
        for i, text in enumerate(text.parametric_versions)
        for str_ in _extract_conditional_text_structure(text, depth, with_paths, path_prefix + [i])
    ]


def _extract_parametric_am_structure(am: ParametricAM, with_paths: bool) -> List[str]:
    return [
        am.title.text,
        *[
            str_
            for i, section in enumerate(am.sections)
            for str_ in _extract_parametrized_text_structure(section, 1, with_paths, [i])
        ],
    ]


def _extract_parameters_from_condition(condition: ApplicationCondition) -> List[Parameter]:
    if isinstance(condition, (OrCondition, AndCondition)):
        return [param for cd in condition.conditions for param in _extract_parameters_from_condition(cd)]
    return [condition.parameter]


def _extract_parameters_from_text(text: ParametricText) -> Set[Parameter]:
    if not text.parametric_versions:
        return {str_ for section in text.default.sections for str_ in _extract_parameters_from_text(section)}
    return {cd for txt in text.parametric_versions for cd in _extract_parameters_from_condition(txt.condition)}


def _extract_parameters(am: ParametricAM) -> Set[Parameter]:
    return {str_ for section in am.sections for str_ in _extract_parameters_from_text(section)}


def _any_parameter_is_undefined(
    conditional_texts: List[ConditionalText], defined_parameters: KeysView[Parameter]
) -> bool:
    parameters = {cd for text in conditional_texts for cd in _extract_parameters_from_condition(text.condition)}
    return any([parameter not in defined_parameters for parameter in parameters])


def _condition_is_fulfilled(condition: ApplicationCondition, parameter_values: Dict[Parameter, Any]) -> bool:
    if isinstance(condition, AndCondition):
        return all([_condition_is_fulfilled(cd, parameter_values) for cd in condition.conditions])
    if isinstance(condition, OrCondition):
        return any([_condition_is_fulfilled(cd, parameter_values) for cd in condition.conditions])
    value = parameter_values[condition.parameter]
    if isinstance(condition, Littler):
        if condition.strict:
            return value < condition.target
        return value <= condition.target
    if isinstance(condition, Greater):
        if condition.strict:
            return value > condition.target
        return value >= condition.target
    raise NotImplementedError('Condition {condition.type} not implemented yet.')


def _generate_inactive_section(title: EnrichedString) -> StructuredText:
    return StructuredText(title, [], [], None, False)


def _apply_parameter_values_in_text(text: ParametricText, parameter_values: Dict[Parameter, Any]) -> StructuredText:
    if not text.parametric_versions or _any_parameter_is_undefined(text.parametric_versions, parameter_values.keys()):
        sections = [_apply_parameter_values_in_text(sec, parameter_values) for sec in text.default.sections]
        return StructuredText(text.default.title, text.default.outer_alineas, sections, text.default.legifrance_article)
    for parametric_version in text.parametric_versions:
        if _condition_is_fulfilled(parametric_version.condition, parameter_values):
            return parametric_version.text
    return _generate_inactive_section(text.default.title)


def _apply_parameter_values_in_am(am: ParametricAM, parameter_values: Dict[Parameter, Any]) -> ArreteMinisteriel:
    sections = [_apply_parameter_values_in_text(section, parameter_values) for section in am.sections]
    return ArreteMinisteriel(am.title, sections, am.visa, am.short_title)

