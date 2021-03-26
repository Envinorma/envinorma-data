from datetime import date
from typing import Any, List, Set, cast

import pandas as pd
from tqdm import tqdm

from envinorma.data.classement import DetailedClassement, DetailedRegime, State
from envinorma.data.load import load_classements, load_installation_ids
from envinorma.data_build.filenames import DGPR_RUBRIQUES_FILENAME, Dataset, dataset_filename
from envinorma.utils import write_json


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


def _simplify_regime(regime: str) -> str:
    return DetailedRegime(regime).to_simple_regime()


def _modify_and_keep_final_classements_cols(classements: pd.DataFrame) -> pd.DataFrame:
    classements = classements.copy()
    date_keys = ['date_autorisation', 'date_mise_en_service', 'last_substantial_modif_date']
    for key in date_keys:
        classements[key] = classements[key].apply(lambda x: date.fromisoformat(x) if not isinstance(x, float) else None)
    classements['regime'] = classements['regime'].apply(_simplify_regime)
    classements['regime_acte'] = classements['regime_acte'].apply(_simplify_regime)
    active_classements = classements[classements.state == State.EN_FONCTIONNEMENT.value]
    return cast(pd.DataFrame, active_classements)


def _check_classements(classements: pd.DataFrame) -> None:
    records = classements.to_dict(orient='records')
    for rubrique in tqdm(records, 'Checking classements'):
        DetailedClassement(**rubrique)


def _filter_47xx(dataframe: pd.DataFrame) -> pd.DataFrame:
    dataframe = dataframe.copy()
    loc = dataframe.rubrique == '47xx'
    dataframe.loc[loc, 'regime'] = DetailedRegime.NC.value  # type: ignore
    dataframe.loc[loc, 'alinea'] = None  # type: ignore
    dataframe.loc[loc, 'date_autorisation'] = None  # type: ignore
    dataframe.loc[loc, 'regime_acte'] = DetailedRegime.NC.value  # type: ignore
    dataframe.loc[loc, 'alinea_acte'] = None  # type: ignore
    dataframe.loc[loc, 'rubrique_acte'] = '47xx'  # type: ignore
    dataframe.loc[loc, 'activite'] = None  # type: ignore
    dataframe.loc[loc, 'volume'] = ''  # type: ignore
    dataframe.loc[loc, 'unit'] = ''  # type: ignore
    return dataframe


def _build_csv() -> pd.DataFrame:
    unique_classements = _load_unique_classements()
    classements_in = _keep_classements_having_installation(unique_classements, load_installation_ids())
    classements_with_renamed_columns = _rename_classements_columns(classements_in)
    final_classements = _modify_and_keep_final_classements_cols(classements_with_renamed_columns)
    return _filter_47xx(final_classements)


def build_classements_csv() -> None:
    classements = _build_csv()
    _check_classements(classements)
    classements.to_csv(dataset_filename('all', 'classements'))
    print(f'classements dataset all has {classements.shape[0]} rows')


def load_classements_csv(dataset: Dataset) -> pd.DataFrame:
    return pd.read_csv(dataset_filename(dataset, 'classements'), dtype='str')


def _filter_and_dump(all_classements: pd.DataFrame, dataset: Dataset) -> None:
    installation_ids = load_installation_ids(dataset)
    filtered_df = all_classements[all_classements.s3ic_id.apply(lambda x: x in installation_ids)]
    nb_rows = filtered_df.shape[0]
    assert nb_rows >= 1000, f'Expecting >= 1000 classements, got {nb_rows}'
    filtered_df.to_csv(dataset_filename(dataset, 'classements'))
    print(f'classements dataset {dataset} has {nb_rows} rows')


def build_all_classement_datasets() -> None:
    all_classements = load_classements_csv('all')
    _filter_and_dump(all_classements, 'sample')
    _filter_and_dump(all_classements, 'idf')
