import re
from datetime import date
from typing import List, Optional

from envinorma.utils import ensure_not_none

from . import ArreteMinisteriel, Reference, StructuredText


def _extract_all_references(sections: List[StructuredText]) -> List[Reference]:
    return [ensure_not_none(section.reference) for section in sections] + [
        ref for section in sections for ref in _extract_all_references(section.sections)
    ]


def _check_references(am: ArreteMinisteriel) -> None:
    references = _extract_all_references(am.sections)
    nb_refs = len(references)
    if None in references:
        nb_none = len([x for x in references if x is None])
        raise ValueError(f'References cannot be None, found {nb_none}/{nb_refs} None')
    nb_empty_refs = len([x for x in references if not x])
    if nb_empty_refs / (nb_refs or 1) >= 0.95:
        raise ValueError(f'More than 95% of references are empty, found {nb_empty_refs}/{nb_refs} empty')


def _print_input_id(func):
    def _func(am: ArreteMinisteriel):
        try:
            func(am)
        except Exception:  # noqa: E722
            print(am.id)
            raise

    return _func


def _check_date_of_signature(date_of_signature: Optional[date]):
    if not date_of_signature:
        raise ValueError('Expecting date_of_signature to be defined')


def _check_regimes(am: ArreteMinisteriel) -> None:
    # Regime must be A, E or D
    for classement in am.classements:
        if classement.regime.value not in 'AED':
            raise ValueError(f'Invalid regime {classement.regime.value}')


def _check_non_none_fields(am: ArreteMinisteriel) -> None:
    if am.legifrance_url is None:
        raise ValueError('Expecting legifrance_url to be defined')

    if am.aida_url is None:
        raise ValueError('Expecting aida_url to be defined')


_REGEXP = re.compile(r'^(JORFTEXT|LEGITEXT)[0-9]{12}$')


def _check_am_id_format(am_id: str) -> None:
    if _REGEXP.match(am_id) is None:
        raise ValueError(f'Invalid AM ID format: {am_id}')


@_print_input_id
def check_am(am: ArreteMinisteriel) -> None:
    _check_am_id_format(am.id or '')
    _check_regimes(am)
    _check_references(am)
    _check_non_none_fields(am)
    _check_date_of_signature(am.date_of_signature)
