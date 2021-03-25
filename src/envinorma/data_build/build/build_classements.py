from datetime import date
from typing import Any, Set, cast

import pandas as pd
from tqdm import tqdm

from envinorma.data.classement import DetailedClassement
from envinorma.data.load import load_installation_ids
from envinorma.data_build.filenames import DGPR_RUBRIQUES_FILENAME, dataset_filename


def _load_unique_classements() -> pd.DataFrame:
    all_rubriques = pd.read_csv(DGPR_RUBRIQUES_FILENAME, sep=';', dtype='str')
    return all_rubriques.drop_duplicates()


def _keep_classements_having_installation(classements: pd.DataFrame, installation_ids: Set[str]) -> pd.DataFrame:
    return cast(pd.DataFrame, classements[classements.code_s3ic.apply(lambda x: x in installation_ids)])


def _rename_classements_columns(classements: pd.DataFrame) -> pd.DataFrame:
    column_mapping = {
        'code_s3ic': 's3ic_id',
        'rubrique_envigueur': 'rubrique',
        'alinéa_envigueur': 'alinea',
        'régime_envigueur': 'regime',
        'libellé_court_envigueur': 'activite',
        'date_acte_rub_en_vigueur': 'date_autorisation',
        'date_début_exploitation_rub': 'date_mise_en_service',
        'date_dernière_modification_notable_rub': 'last_substantial_modif_date',
        'état_technique': 'state',
        'rubrique_autorisé': 'rubrique_acte',
        'alinéa_autorisé': 'alinea_acte',
        'régime_autorisé': 'regime_acte',
        'quantité': 'volume',
        'unité': 'unit',
    }
    return classements.rename(columns=cast(Any, column_mapping))


def _modify_and_keep_final_classements_cols(classements: pd.DataFrame) -> pd.DataFrame:
    classements = classements.copy()
    date_keys = ['date_autorisation', 'date_mise_en_service', 'last_substantial_modif_date']
    for key in date_keys:
        classements[key] = classements[key].apply(lambda x: date.fromisoformat(x) if not isinstance(x, float) else None)
    return classements


def _check_classements(classements: pd.DataFrame) -> None:
    records = classements.to_dict(orient='records')
    for rubrique in tqdm(records):
        DetailedClassement(**rubrique)


def build_classements_csv() -> None:
    unique_classements = _load_unique_classements()
    classements_in = _keep_classements_having_installation(unique_classements, load_installation_ids())
    classements_with_renamed_columns = _rename_classements_columns(classements_in)
    final_classements = _modify_and_keep_final_classements_cols(classements_with_renamed_columns)
    _check_classements(final_classements)
    final_classements.to_csv(dataset_filename('all', 'classements'))
