from typing import List

from envinorma.models import ArreteMinisteriel
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
        PotentialInapplicability(inapplicable_section.condition, inapplicable_section.alineas)
        for inapplicable_section in inapplicable_sections
    ]


def _modifications(alternative_sections: List[AlternativeSection]) -> List[PotentialModification]:
    return [
        PotentialModification(alternative_section.condition, alternative_section.new_text)
        for alternative_section in alternative_sections
    ]


def _warnings(warnings: List[AMWarning]) -> List[str]:
    return [warning.text for warning in warnings]


def _init_section_parametrization(parametrization: Parametrization, section_id: str) -> SectionParametrization:
    return SectionParametrization(
        _inapplicabilities(parametrization.id_to_conditions.get(section_id, [])),
        _modifications(parametrization.id_to_alternative_sections.get(section_id, [])),
        _warnings(parametrization.id_to_warnings.get(section_id, [])),
    )


def _add_parametrization_in_section(text: StructuredText, parametrization: Parametrization) -> None:
    text.parametrization = _init_section_parametrization(parametrization, text.id)


def add_parametrization(am: ArreteMinisteriel, parametrization: Parametrization) -> None:
    """Ties each section to associated parametrization elements.

    Args:
        am (ArreteMinisteriel): ArreteMinisteriel to which parametrization is tied.
        parametrization (Parametrization): parametrization to be tied.
    """
    for section in am.descendent_sections():
        _add_parametrization_in_section(section, parametrization)
