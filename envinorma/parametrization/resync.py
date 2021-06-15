import sys
import warnings
from copy import deepcopy
from dataclasses import replace
from typing import List, Union

from envinorma.models import ArreteMinisteriel, Ints, StructuredText

from .models.parametrization import AlternativeSection, InapplicableSection, Parametrization, SectionReference


def _extract_titles_sequence(text: Union[ArreteMinisteriel, StructuredText], path: Ints) -> List[str]:
    if not path:
        return []
    if path[0] >= len(text.sections):
        raise ValueError('Path is not compatible with this text.')
    return [text.sections[path[0]].title.text] + _extract_titles_sequence(text.sections[path[0]], path[1:])


def _add_titles_sequences_section(obj: SectionReference, am: ArreteMinisteriel) -> SectionReference:
    return replace(obj, titles_sequence=_extract_titles_sequence(am, obj.path))


def _add_titles_sequences_inapplicable_section(obj: InapplicableSection, am: ArreteMinisteriel) -> InapplicableSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = _add_titles_sequences_section(new_source.source.reference.section, am)
    new_source.targeted_entity.section = _add_titles_sequences_section(new_source.targeted_entity.section, am)
    return new_source


def _add_titles_sequences_alternative_section(obj: AlternativeSection, am: ArreteMinisteriel) -> AlternativeSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = _add_titles_sequences_section(new_source.source.reference.section, am)
    new_source.targeted_section = _add_titles_sequences_section(new_source.targeted_section, am)
    return new_source


def add_titles_sequences(parametrization: Parametrization, am: ArreteMinisteriel) -> Parametrization:
    return replace(
        parametrization,
        inapplicable_sections=[
            _add_titles_sequences_inapplicable_section(x, am) for x in parametrization.inapplicable_sections
        ],
        alternative_sections=[
            _add_titles_sequences_alternative_section(x, am) for x in parametrization.alternative_sections
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


def _regenerate_paths_section(obj: SectionReference, am: ArreteMinisteriel) -> SectionReference:
    if obj.titles_sequence is None:
        raise UndefinedTitlesSequencesError('Titles sequences need to be defined')
    return replace(obj, path=_extract_paths(am, obj.titles_sequence))


def _regenerate_paths_inapplicable_section(obj: InapplicableSection, am: ArreteMinisteriel) -> InapplicableSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = _regenerate_paths_section(new_source.source.reference.section, am)
    new_source.targeted_entity.section = _regenerate_paths_section(new_source.targeted_entity.section, am)
    return new_source


def _regenerate_paths_alternative_section(obj: AlternativeSection, am: ArreteMinisteriel) -> AlternativeSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = _regenerate_paths_section(new_source.source.reference.section, am)
    new_source.targeted_section = _regenerate_paths_section(new_source.targeted_section, am)
    return new_source


def regenerate_paths(parametrization: Parametrization, am: ArreteMinisteriel) -> Parametrization:
    return replace(
        parametrization,
        inapplicable_sections=[
            _regenerate_paths_inapplicable_section(x, am) for x in parametrization.inapplicable_sections
        ],
        alternative_sections=[
            _regenerate_paths_alternative_section(x, am) for x in parametrization.alternative_sections
        ],
    )
