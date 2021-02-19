'''
Script for manually changing title sequences for AM 1510.
'''
from copy import deepcopy
from dataclasses import replace
from typing import List, Optional

from envinorma.back_office.fetch_data import load_parametrization, upsert_new_parametrization
from envinorma.parametrization import AlternativeSection, NonApplicationCondition, Parametrization, SectionReference

_TITLE_MAPPING = {
    "Annexe II - PRESCRIPTIONS GÉNÉRALES APPLICABLES AUX INSTALLATIONS CLASSÉES POUR LA PROTECTION DE L'ENVIRONNEMENT SOUMISES À LA RUBRIQUE 1510, Y COMPRIS LORSQU'ELLES RELÈVENT ÉGALEMENT DE L'UNE OU PLUSIEURS DES RUBRIQUES 1530, 1532, 2662 OU 2663 DE LA NOMENCLATURE DES INSTALLATIONS CLASSÉES POUR LA PROTECTION DE L'ENVIRONNEMENT": "Annexe II - PRESCRIPTIONS GÉNÉRALES APPLICABLES AUX INSTALLATIONS CLASSÉES POUR LA PROTECTION DE L'ENVIRONNEMENT SOUMISES À LA RUBRIQUE 1510"
}


def update_titles_sequence(titles: Optional[List[str]]) -> Optional[List[str]]:
    if titles is None:
        return None
    print('changing title sequence')
    return [_TITLE_MAPPING.get(title, title) for title in titles]


def change_titles_sequences_section(obj: SectionReference) -> SectionReference:
    return replace(obj, titles_sequence=update_titles_sequence(obj.titles_sequence))


def change_titles_sequences_non_application_condition(obj: NonApplicationCondition) -> NonApplicationCondition:
    new_source = deepcopy(obj)
    new_source.source.reference.section = change_titles_sequences_section(new_source.source.reference.section)
    new_source.targeted_entity.section = change_titles_sequences_section(new_source.targeted_entity.section)
    return new_source


def change_titles_sequences_alternative_section(obj: AlternativeSection) -> AlternativeSection:
    new_source = deepcopy(obj)
    new_source.source.reference.section = change_titles_sequences_section(new_source.source.reference.section)
    new_source.targeted_section = change_titles_sequences_section(new_source.targeted_section)
    return new_source


def change_titles_sequences(parametrization: Parametrization) -> Parametrization:
    return replace(
        parametrization,
        application_conditions=[
            change_titles_sequences_non_application_condition(x) for x in parametrization.application_conditions
        ],
        alternative_sections=[
            change_titles_sequences_alternative_section(x) for x in parametrization.alternative_sections
        ],
    )


def run():
    am_id = 'JORFTEXT000034429274'
    parametrization = load_parametrization(am_id)
    if not parametrization:
        raise ValueError('Parametrization not found.')
    new_parametrization = change_titles_sequences(parametrization)
    upsert_new_parametrization(am_id, new_parametrization)


if __name__ == '__main__':
    run()
