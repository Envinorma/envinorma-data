from typing import List

from envinorma.models import ArreteMinisteriel, Ints
from envinorma.models.condition import OrCondition
from envinorma.models.structured_text import (
    PotentialInapplicability,
    PotentialModification,
    SectionParametrization,
    StructuredText,
)
from envinorma.parametrization import Parametrization
from envinorma.parametrization.models.parametrization import AlternativeSection, AMWarning, InapplicableSection


def _inapplicabilities(inapplicable_sections: List[InapplicableSection]) -> List[PotentialInapplicability]:
    return [
        PotentialInapplicability(
            inapplicable_section.condition, inapplicable_section.targeted_entity.outer_alinea_indices
        )
        for inapplicable_section in inapplicable_sections
    ]


def _modifications(alternative_sections: List[AlternativeSection]) -> List[PotentialModification]:
    return [
        PotentialModification(alternative_section.condition, alternative_section.new_text)
        for alternative_section in alternative_sections
    ]


def _warnings(warnings: List[AMWarning]) -> List[str]:
    return [warning.text for warning in warnings]


def _init_section_parametrization(parametrization: Parametrization, path: Ints) -> SectionParametrization:
    return SectionParametrization(
        _inapplicabilities(parametrization.path_to_conditions.get(path, [])),
        _modifications(parametrization.path_to_alternative_sections.get(path, [])),
        _warnings(parametrization.path_to_warnings.get(path, [])),
    )


def _add_parametrization_in_section(text: StructuredText, path: Ints, parametrization: Parametrization) -> None:
    text.parametrization = _init_section_parametrization(parametrization, path)
    for i, section in enumerate(text.sections):
        _add_parametrization_in_section(section, path + (i,), parametrization)


def _am_inapplicabilities(am: ArreteMinisteriel, parametrization: Parametrization) -> None:
    am.applicability.warnings = _warnings(parametrization.path_to_warnings.get((), []))
    conditions = [cd.condition for cd in parametrization.path_to_conditions.get((), [])]
    if len(conditions) >= 2:
        am.applicability.condition_of_inapplicability = OrCondition(frozenset(conditions))
    elif len(conditions) == 1:
        am.applicability.condition_of_inapplicability = conditions[0]
    else:
        am.applicability.condition_of_inapplicability = None


def add_parametrization(am: ArreteMinisteriel, parametrization: Parametrization) -> None:
    """Ties each section to associated parametrization elements.

    Args:
        am (ArreteMinisteriel): ArreteMinisteriel to which parametrization is tied.
        parametrization (Parametrization): parametrization to be tied.
    """
    _am_inapplicabilities(am, parametrization)
    for i, section in enumerate(am.sections):
        _add_parametrization_in_section(section, (i,), parametrization)
