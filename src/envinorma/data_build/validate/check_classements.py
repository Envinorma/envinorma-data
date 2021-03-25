'''
Script for generating csv of classements
'''

from typing import List, Optional, Tuple

import pandas

from envinorma.data.classement import DetailedClassement, DetailedRegime, State


def _is_47xx(rubrique: Optional[str]) -> bool:
    if not rubrique:
        return False
    if rubrique[:2] == '47':
        return True
    return False


def _is_4xxx(rubrique: Optional[str]) -> bool:
    if not rubrique:
        return False
    if len(rubrique) == 4 and rubrique[:1] == '4':
        return True
    return False


def _check_void(classement: DetailedClassement) -> None:
    assert classement.rubrique == '47xx'
    assert classement.regime == DetailedRegime.NC
    assert classement.alinea is None
    assert classement.date_autorisation is None
    assert classement.regime_acte is None
    assert classement.alinea_acte is None
    assert classement.rubrique_acte == '47xx'
    assert classement.activite is None
    assert classement.volume == ''
    assert classement.unit == ''


def _check_no_volume(classement: DetailedClassement) -> None:
    assert classement.unit == ''
    assert classement.volume == ''


def _check_classement_is_safe(classement: DetailedClassement) -> None:
    if _is_47xx(classement.rubrique):
        _check_void(classement)
    if _is_47xx(classement.rubrique_acte):
        _check_void(classement)
    if _is_4xxx(classement.rubrique):
        _check_no_volume(classement)
    if _is_4xxx(classement.rubrique_acte):
        _check_no_volume(classement)


def _check_output(classements: List[DetailedClassement]) -> List[DetailedClassement]:
    for classement in classements:
        _check_classement_is_safe(classement)
    return classements


def _row_to_classement(classement: Tuple) -> DetailedClassement:
    (
        s3ic_id,
        rubrique,
        regime,
        alinea,
        date_autorisation,
        state,
        regime_acte,
        alinea_acte,
        rubrique_acte,
        activite,
        volume,
        unit,
    ) = classement
    return DetailedClassement(
        s3ic_id=s3ic_id,
        rubrique=rubrique,
        regime=DetailedRegime(regime) if regime else DetailedRegime.UNKNOWN,
        alinea=alinea,
        date_autorisation=date_autorisation or None,
        state=State(state) if state else None,
        regime_acte=DetailedRegime(regime_acte) if regime_acte else DetailedRegime.UNKNOWN,
        alinea_acte=alinea_acte,
        rubrique_acte=rubrique_acte,
        activite=activite,
        volume=volume,
        unit=unit,
    )


def check_classements_csv(filename: str) -> None:
    dataframe = pandas.read_csv(
        filename, dtype='str', index_col='Unnamed: 0', na_values=None, parse_dates=['date_autorisation']
    ).fillna('')
    classements = [_row_to_classement(row) for row in dataframe.to_numpy()]
    _check_output(classements)
