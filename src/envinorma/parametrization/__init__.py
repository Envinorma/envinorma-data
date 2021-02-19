import math
import sys
import warnings
from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, TypeVar, Union

from envinorma.data import ArreteMinisteriel, StructuredText, StructuredTextSignature
from envinorma.parametrization.conditions import (
    Condition,
    Equal,
    Greater,
    LeafCondition,
    Littler,
    Parameter,
    ParameterEnum,
    ParameterType,
    Range,
    check_condition,
    condition_to_str,
    extract_leaf_conditions,
    extract_parameters_from_condition,
    load_condition,
)

Ints = Tuple[int, ...]


@dataclass
class SectionReference:
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


def extract_conditions_from_parametrization(
    parameter: Parameter, parametrization: 'Parametrization'
) -> List[LeafCondition]:
    return [
        cd for ap in parametrization.application_conditions for cd in extract_leaf_conditions(ap.condition, parameter)
    ] + [cd for as_ in parametrization.alternative_sections for cd in extract_leaf_conditions(as_.condition, parameter)]


class ParametrizationError(Exception):
    pass


def _check_parametrization(parametrization: 'Parametrization') -> None:
    for app in parametrization.application_conditions:
        check_condition(app.condition)
    for sec in parametrization.alternative_sections:
        check_condition(sec.condition)


def _extract_all_paths(parametrization: 'Parametrization') -> Set[Ints]:
    return set(parametrization.path_to_alternative_sections.keys()).union(
        set(parametrization.path_to_conditions.keys())
    )


_DateRange = Tuple[Optional[datetime], Optional[datetime]]


def _extract_date_range(condition: LeafCondition) -> _DateRange:
    if isinstance(condition, Range):
        return (condition.left, condition.right)
    if isinstance(condition, Equal):
        return (condition.target, condition.target)
    if isinstance(condition, Littler):
        return (None, condition.target)
    if isinstance(condition, Greater):
        return (condition.target, None)
    raise NotImplementedError(type(condition))


def _ranges_strictly_overlap(ranges: List[Tuple[float, float]]) -> bool:
    sorted_ranges = sorted(ranges)
    for ((x, y), (z, t)) in zip(sorted_ranges, sorted_ranges[1:]):
        assert x <= y
        assert z <= t
        if y > z:
            return True
    return False


def _date_ranges_strictly_overlap(ranges: List[_DateRange]) -> bool:
    timestamp_ranges = [
        (dt_left.timestamp() if dt_left else -math.inf, dt_right.timestamp() if dt_right else math.inf)
        for dt_left, dt_right in ranges
    ]
    return _ranges_strictly_overlap(timestamp_ranges)


def _check_date_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    leaf_conditions = [leaf for cd in all_conditions for leaf in extract_leaf_conditions(cd, parameter)]
    ranges: List[_DateRange] = []
    for condition in leaf_conditions:
        ranges.append(_extract_date_range(condition))
    if _date_ranges_strictly_overlap(ranges):
        raise ParametrizationError(
            f'Date ranges overlap, they can be satisfied simultaneously, which can lead to'
            f' ambiguities: {all_conditions}'
        )


_Range = Tuple[float, float]


def _extract_range(condition: LeafCondition) -> _Range:
    if isinstance(condition, Range):
        return (condition.left, condition.right)
    if isinstance(condition, Equal):
        return (condition.target, condition.target)
    if isinstance(condition, Littler):
        return (-math.inf, condition.target)
    if isinstance(condition, Greater):
        return (condition.target, math.inf)
    raise NotImplementedError(type(condition))


def _check_real_number_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    leaf_conditions = [leaf for cd in all_conditions for leaf in extract_leaf_conditions(cd, parameter)]
    ranges = [_extract_range(condition) for condition in leaf_conditions]
    if _ranges_strictly_overlap(ranges):
        raise ParametrizationError(
            f'Ranges overlap, they can be satisfied simultaneously, which can lead to' f' ambiguities: {all_conditions}'
        )


def _check_discrete_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    leaf_conditions = [leaf for cd in all_conditions for leaf in extract_leaf_conditions(cd, parameter)]
    targets: Set = set()
    for condition in leaf_conditions:
        if not isinstance(condition, Equal):
            raise ParametrizationError(f'{parameter.id} conditions must be "=" conditions, got {condition.type}')
        if condition.target in targets:
            raise ParametrizationError(f'Several conditions are simultaneously satisfiable : {all_conditions}')
        targets.add(condition.target)


def _check_bool_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    leaf_conditions = [leaf for cd in all_conditions for leaf in extract_leaf_conditions(cd, parameter)]
    targets: Set[bool] = set()
    for condition in leaf_conditions:
        if not isinstance(condition, Equal):
            raise ParametrizationError(f'bool conditions must be "=" conditions, got {condition.type}')
        if condition.target in targets:
            raise ParametrizationError(f'Several conditions are simultaneously satisfiable : {all_conditions}')
        targets.add(condition.target)


def _check_conditions_are_incompatible(all_conditions: List[Condition], parameter: Parameter) -> None:
    if parameter.type == ParameterType.DATE:
        _check_date_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.REAL_NUMBER:
        _check_real_number_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.REGIME:
        _check_discrete_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.RUBRIQUE:
        _check_discrete_conditions_are_incompatible(all_conditions, parameter)
    elif parameter.type == ParameterType.BOOLEAN:
        _check_bool_conditions_are_incompatible(all_conditions, parameter)
    else:
        raise NotImplementedError(parameter.type)


def _check_consistency(
    non_application_conditions: List[NonApplicationCondition], alternative_sections: List[AlternativeSection]
) -> None:
    all_conditions = [nac.condition for nac in non_application_conditions] + [
        als.condition for als in alternative_sections
    ]
    if not all_conditions:
        return None
    all_parameters = {param for condition in all_conditions for param in extract_parameters_from_condition(condition)}
    if len(all_parameters) >= 2:
        return  # complicated and infrequent, not checked for now
    if len(all_parameters) == 0:
        raise ParametrizationError('There should be at least one parameter in conditions.')
    _check_conditions_are_incompatible(all_conditions, list(all_parameters)[0])


def check_parametrization_consistency(parametrization: 'Parametrization') -> None:
    all_paths = _extract_all_paths(parametrization)
    for path in all_paths:
        _check_consistency(
            parametrization.path_to_conditions.get(path, []), parametrization.path_to_alternative_sections.get(path, [])
        )


@dataclass
class Parametrization:
    application_conditions: List[NonApplicationCondition]
    alternative_sections: List[AlternativeSection]
    signatures: Optional[Dict[Ints, StructuredTextSignature]] = None
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
        _check_parametrization(self)
        try:
            check_parametrization_consistency(self)
        except ParametrizationError as exc:
            warnings.warn(f'Parametrization error, will raise an exception in the future : {str(exc)}')

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        del res['path_to_conditions']
        del res['path_to_alternative_sections']
        res['application_conditions'] = [app.to_dict() for app in self.application_conditions]
        res['alternative_sections'] = [sec.to_dict() for sec in self.alternative_sections]
        if self.signatures:
            res['signatures'] = [[path, signature.to_dict()] for path, signature in self.signatures.items()]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Parametrization':
        signatures: Optional[Dict[Ints, StructuredTextSignature]]
        if dict_.get('signatures'):
            signatures = {tuple(key): StructuredTextSignature.from_dict(value) for key, value in dict_['signatures']}
        else:
            signatures = None
        return Parametrization(
            [NonApplicationCondition.from_dict(app) for app in dict_['application_conditions']],
            [AlternativeSection.from_dict(sec) for sec in dict_['alternative_sections']],
            signatures,
        )


ParameterObject = Union[NonApplicationCondition, AlternativeSection]
Combinations = Dict[Tuple[str, ...], Dict[Parameter, Any]]


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
    elts: List[str] = []
    elts.append(f'{source.reference.section.path} {tuple(source.reference.outer_alinea_indices or [])}')
    elts.append(f' ({source.explanation})')
    return ''.join(elts)


def _count_alineas(section: StructuredText) -> int:
    return 1 + len(section.outer_alineas) + sum([_count_alineas(sec) for sec in section.sections])


def alternative_section_to_row(section: AlternativeSection) -> str:
    cells: List[str] = []
    cells.append(str(section.targeted_section.path))
    cells.append('AS')
    cells.append('-')
    cells.append(f'`{condition_to_str(section.condition)}`')
    cells.append(f'{section.description}')
    cells.append(_condition_source_to_markdown(section.source))
    cells.append(f'{_count_alineas(section.new_text)} alineas')

    return '|'.join(cells)


def non_application_condition_to_row(condition: NonApplicationCondition) -> str:
    cells: List[str] = []
    cells.append(str(condition.targeted_entity.section.path))
    cells.append('NAC')
    cells.append(str(tuple(condition.targeted_entity.outer_alinea_indices or ())))
    cells.append(f'`{condition_to_str(condition.condition)}`')
    cells.append(f'{condition.description}')
    cells.append(_condition_source_to_markdown(condition.source))
    cells.append('-')
    return '|'.join(cells)


def sections_and_conditions_to_rows(
    alternative_sections: List[AlternativeSection], non_application_conditions: List[NonApplicationCondition]
) -> List[str]:
    return [alternative_section_to_row(alt) for alt in alternative_sections] + [
        non_application_condition_to_row(na) for na in non_application_conditions
    ]


def parametrization_to_markdown(parametrization: Parametrization) -> str:
    all_paths = list(parametrization.path_to_alternative_sections) + list(parametrization.path_to_conditions)
    table_rows = [
        'Section | Type | Alineas | Condition | Description | Source | Alternative text',
        '---|---|---|---|---|---|---',
    ]
    for path in sorted(all_paths):
        table_rows.extend(
            sections_and_conditions_to_rows(
                parametrization.path_to_alternative_sections.get(path, []),
                parametrization.path_to_conditions.get(path, []),
            )
        )
    return '\n'.join(table_rows)


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


def add_am_signatures(
    parametrization: Parametrization, signatures: Dict[Ints, StructuredTextSignature]
) -> Parametrization:
    return replace(parametrization, signatures=signatures)


def extract_titles_sequence(text: Union[ArreteMinisteriel, StructuredText], path: Ints) -> List[str]:
    if not path:
        return []
    if path[0] >= len(text.sections):
        raise ValueError(f'Path is not compatible with this text.')
    return [text.sections[path[0]].title.text] + extract_titles_sequence(text.sections[path[0]], path[1:])


def add_titles_sequences_section(obj: SectionReference, am: ArreteMinisteriel) -> SectionReference:
    return replace(obj, titles_sequence=extract_titles_sequence(am, obj.path))


def add_titles_sequences_non_application_condition(
    obj: NonApplicationCondition, am: ArreteMinisteriel
) -> NonApplicationCondition:
    new_source = deepcopy(obj)
    new_source.source.reference.section = add_titles_sequences_section(new_source.source.reference.section, am)
    new_source.targeted_entity.section = add_titles_sequences_section(new_source.targeted_entity.section, am)
    return new_source


def add_titles_sequences_alternative_section(obj: AlternativeSection, am: ArreteMinisteriel) -> AlternativeSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = add_titles_sequences_section(new_source.source.reference.section, am)
    new_source.targeted_section = add_titles_sequences_section(new_source.targeted_section, am)
    return new_source


def add_titles_sequences(parametrization: Parametrization, am: ArreteMinisteriel) -> Parametrization:
    return replace(
        parametrization,
        application_conditions=[
            add_titles_sequences_non_application_condition(x, am) for x in parametrization.application_conditions
        ],
        alternative_sections=[
            add_titles_sequences_alternative_section(x, am) for x in parametrization.alternative_sections
        ],
    )


class SectionNotFoundWarning(Warning):
    pass


def _extract_paths(text: Union[ArreteMinisteriel, StructuredText], titles_sequence: List[str]) -> Ints:
    if not titles_sequence:
        return ()
    for i, section in enumerate(text.sections):
        if section.title.text == titles_sequence[0]:
            return (i,) + _extract_paths(section, titles_sequence[1:])
    warnings.warn(
        SectionNotFoundWarning(f'Title {titles_sequence[0]} not found among sections, replacing path with (inf,).')
    )
    return (sys.maxsize,)


class UndefinedTitlesSequencesError(Exception):
    pass


def regenerate_paths_section(obj: SectionReference, am: ArreteMinisteriel) -> SectionReference:
    if obj.titles_sequence is None:
        raise UndefinedTitlesSequencesError('Titles sequences need to be defined')
    return replace(obj, path=_extract_paths(am, obj.titles_sequence))


def regenerate_paths_non_application_condition(
    obj: NonApplicationCondition, am: ArreteMinisteriel
) -> NonApplicationCondition:
    new_source = deepcopy(obj)
    new_source.source.reference.section = regenerate_paths_section(new_source.source.reference.section, am)
    new_source.targeted_entity.section = regenerate_paths_section(new_source.targeted_entity.section, am)
    return new_source


def regenerate_paths_alternative_section(obj: AlternativeSection, am: ArreteMinisteriel) -> AlternativeSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = regenerate_paths_section(new_source.source.reference.section, am)
    new_source.targeted_section = regenerate_paths_section(new_source.targeted_section, am)
    return new_source


def regenerate_paths(parametrization: Parametrization, am: ArreteMinisteriel) -> Parametrization:
    return replace(
        parametrization,
        application_conditions=[
            regenerate_paths_non_application_condition(x, am) for x in parametrization.application_conditions
        ],
        alternative_sections=[
            regenerate_paths_alternative_section(x, am) for x in parametrization.alternative_sections
        ],
    )
