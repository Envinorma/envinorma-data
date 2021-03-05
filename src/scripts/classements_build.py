'''
Script for generating csv of classements
'''

import os
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import pandas
from pydantic import BaseModel
from tqdm import tqdm

from envinorma.data import Regime
from envinorma.data_build.georisques_data import load_idf_installation_ids
from scripts.s3ic import ClassementType, fetch_records


class State(Enum):
    EN_PROJET = 'En projet'
    EN_FONCTIONNEMENT = 'En fonctionnement'
    A_L_ARRET = 'A l\'arrêt'
    REPRISE = 'Reprise'


_UNKNOWN_REGIME = 'unknown'


class DetailedRegime(Enum):
    NC = 'NC'
    D = 'D'
    DC = 'DC'
    A = 'A'
    S = 'S'
    _1 = '1'
    _2 = '2'
    _3 = '3'
    E = 'E'
    UNKNOWN = _UNKNOWN_REGIME

    def to_regime(self) -> Optional[Regime]:
        try:
            return Regime(self.value)
        except ValueError:
            return None


class DetailedClassement(BaseModel):
    s3ic_id: str
    rubrique: str
    regime: DetailedRegime
    alinea: Optional[str]
    date_autorisation: Optional[date]
    state: Optional[State]
    regime_acte: Optional[DetailedRegime]
    alinea_acte: Optional[str]
    rubrique_acte: Optional[str]
    activite: Optional[str]
    volume: str
    unit: Optional[str]


def _build_s3ic_id(row) -> str:
    return '.'.join([('0' * 5 + str(row.code_base))[-4:], ('0' * 5 + str(row.code_etablissement))[-5:]])


def _build_alinea(row) -> str:
    return row.alinea_gidic or row.alinea_libre


def _build_alinea_acte(row) -> str:
    return row.alinea_gidic_acte or row.alinea_libre_acte


def _get_classements_dataframe() -> pandas.DataFrame:
    records_0 = fetch_records(ClassementType.VIGUEUR)
    records_1 = fetch_records(ClassementType.ACTE)
    merge = pandas.merge(records_0, records_1, on='id')
    merge['s3ic_id'] = merge.apply(_build_s3ic_id, axis=1)
    merge['alinea'] = merge.apply(_build_alinea, axis=1)
    merge['alinea_acte'] = merge.apply(_build_alinea_acte, axis=1)
    return merge.sort_values(by='s3ic_id')


def _build_classement_from_record(record: Dict[str, Any]) -> DetailedClassement:
    return DetailedClassement(**record)


def _get_classements_records(warning: bool = True) -> List[DetailedClassement]:
    if warning:
        print('Beware, using this function also retrieves private classements. Use _get_public_classements instead')
    dataframe = _get_classements_dataframe()
    return [_build_classement_from_record(record) for record in tqdm(dataframe.to_dict('records'), 'init classements')]


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


def _make_safe(classement: DetailedClassement) -> DetailedClassement:
    if _is_47xx(classement.rubrique) or _is_47xx(classement.rubrique_acte):
        return DetailedClassement(
            s3ic_id=classement.s3ic_id,
            rubrique='47xx',
            regime=DetailedRegime.NC,
            alinea=None,
            date_autorisation=None,
            state=classement.state,
            regime_acte=None,
            alinea_acte=None,
            rubrique_acte='47xx',
            activite=None,
            volume='',
            unit='',
        )
    if _is_4xxx(classement.rubrique) or _is_4xxx(classement.rubrique_acte):
        return classement.copy(update={'volume': '', 'unit': ''})
    return classement


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


def load_all_classements() -> List[DetailedClassement]:
    unfiltered_records = _get_classements_records(warning=False)
    return _check_output([_make_safe(record) for record in unfiltered_records])


def _extract_regime(regime: Optional[DetailedRegime]) -> str:
    if not regime:
        return _UNKNOWN_REGIME
    if regime == DetailedRegime.NC:
        return 'NC'
    if regime in (DetailedRegime.D, DetailedRegime.DC):
        return 'D'
    if regime == DetailedRegime.A:
        return 'A'
    if regime == DetailedRegime.E:
        return 'E'
    return _UNKNOWN_REGIME


def _classement_to_row(classement: DetailedClassement) -> Tuple:
    return (
        classement.s3ic_id,
        classement.rubrique,
        _extract_regime(classement.regime),
        classement.alinea,
        classement.date_autorisation,
        classement.state.value if classement.state else None,
        _extract_regime(classement.regime_acte),
        classement.alinea_acte,
        classement.rubrique_acte,
        classement.activite,
        classement.volume,
        classement.unit,
    )


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


def _build_dataframe(classements: List[DetailedClassement]) -> pandas.DataFrame:
    keys = [
        's3ic_id',
        'rubrique',
        'regime',
        'alinea',
        'date_autorisation',
        'state',
        'regime_acte',
        'alinea_acte',
        'rubrique_acte',
        'activite',
        'volume',
        'unit',
    ]
    rows: List[Tuple] = []
    for classement in classements:
        rows.append(_classement_to_row(classement))
    return pandas.DataFrame(rows, columns=keys).drop_duplicates()


def dump_all_active_classements(output_filename: str) -> None:
    classements = load_all_classements()
    idf_ids = load_idf_installation_ids()
    active_classements = [cl for cl in classements if cl.s3ic_id in idf_ids and cl.state == State.EN_FONCTIONNEMENT]
    dataframe = _build_dataframe(active_classements)
    dataframe.to_csv(output_filename)


def check_classement_csv(filename: str) -> None:
    dataframe = pandas.read_csv(
        filename, dtype='str', index_col='Unnamed: 0', na_values=None, parse_dates=['date_autorisation']
    ).fillna('')
    for row in dataframe.to_numpy():
        _row_to_classement(row)


if __name__ == '__main__':
    _OUTPUT_FOLDER = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds'
    _FILENAME = 'classements_idf.csv'
    dump_all_active_classements(os.path.join(_OUTPUT_FOLDER, _FILENAME))
    check_classement_csv(os.path.join(_OUTPUT_FOLDER, _FILENAME))
