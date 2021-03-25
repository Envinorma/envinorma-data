'''
Script for generating csv of classements
'''

from typing import Any, Dict, List, Optional, Tuple

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
    assert classement.rubrique == '47xx', classement
    assert classement.regime == DetailedRegime.NC, classement
    assert not classement.alinea, classement
    assert not classement.date_autorisation, classement
    assert classement.regime_acte == DetailedRegime.NC, classement
    assert not classement.alinea_acte, classement
    assert classement.rubrique_acte == '47xx', classement
    assert not classement.activite, classement
    assert classement.volume == '', classement
    assert classement.unit == '', classement


def _check_classement_is_safe(classement: DetailedClassement) -> None:
    if _is_47xx(classement.rubrique):
        _check_void(classement)
    if _is_47xx(classement.rubrique_acte):
        _check_void(classement)


def _check_output(classements: List[DetailedClassement]) -> List[DetailedClassement]:
    for classement in classements:
        _check_classement_is_safe(classement)
    return classements


def _row_to_classement(record: Dict[str, Any]) -> DetailedClassement:
    key_dates = ['date_autorisation', 'date_mise_en_service', 'last_substantial_modif_date']
    for key in key_dates:
        record[key] = record[key] or None
    return DetailedClassement(**record)


def check_classements_csv(filename: str) -> None:
    dataframe = pandas.read_csv(
        filename, dtype='str', index_col='Unnamed: 0', na_values=None, parse_dates=['date_autorisation']
    ).fillna('')
    classements = [_row_to_classement(record) for record in dataframe.to_dict(orient='records')]
    _check_output(classements)
