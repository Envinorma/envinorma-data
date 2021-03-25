from datetime import date
from envinorma.data import Regime
from typing import Any, Dict, cast

import pandas as pd
from tqdm import tqdm

from envinorma.data.installation import ActivityStatus, Installation, InstallationFamily, Seveso
from envinorma.data_build.filenames import DGPR_INSTALLATIONS_FILENAME, Dataset, dataset_filename


def _load_A_E_installations() -> pd.DataFrame:
    installations_with_duplicates = pd.read_csv(DGPR_INSTALLATIONS_FILENAME, sep=';', dtype='str')
    installations_with_D = installations_with_duplicates.drop_duplicates()
    installations_with_duplicated_ids = installations_with_D[
        installations_with_D['régime_etab_en_vigueur'].apply(lambda x: x in ('A', 'E'))
    ]
    return installations_with_duplicated_ids.groupby('code_s3ic').last().reset_index()


def _rename_installations_columns(input_installations: pd.DataFrame) -> pd.DataFrame:
    column_mapping = {
        'code_s3ic': 's3ic_id',
        'region': 'region',
        'département': 'department',
        'commune_principale': 'city',
        'raison_sociale': 'name',
        'coordonnées_géographiques_x': 'lat',
        'coordonnées_géographiques_y': 'lon',
        'date_inspection': 'last_inspection',
        'régime_etab_en_vigueur': 'regime',
        'statut_seveso': 'seveso',
        'famille': 'family',
        'état_de_l_activité': 'active',
        'code_postal': 'code_postal',
        'code_insee_commune': 'code_insee',
        'code_naf': 'code_naf',
    }
    return input_installations.rename(columns=cast(Any, column_mapping))


def _map_family(family_in: str) -> str:
    if family_in == 'industrie':
        return InstallationFamily.INDUSTRIES.value
    if family_in == 'carriere':
        return InstallationFamily.CARRIERES.value
    if family_in == 'volailles':
        return InstallationFamily.VOLAILLES.value
    if family_in == 'bovins':
        return InstallationFamily.BOVINS.value
    if family_in == 'porcs':
        return InstallationFamily.PORCS.value
    return family_in


def _map_seveso(seveso_in: str) -> str:
    if seveso_in == 'SSH':
        return Seveso.SEUIL_HAUT.value
    if seveso_in == 'SSB':
        return Seveso.SEUIL_BAS.value
    return seveso_in


def _modify_and_keep_final_installations_cols(installations: pd.DataFrame) -> pd.DataFrame:
    installations = installations.copy()
    installations['num_dep'] = installations.code_postal.apply(lambda x: (x or '')[:2])
    installations['last_inspection'] = installations.last_inspection.apply(
        lambda x: date.fromisoformat(x) if not isinstance(x, float) else None
    )
    installations['family'] = installations.family.apply(_map_family)
    installations['active'] = installations['active'].fillna('')  # type: ignore
    installations['seveso'] = installations['seveso'].fillna('').apply(_map_seveso)  # type: ignore
    expected_keys = [x for x in Installation.__dataclass_fields__]  # type: ignore
    return installations[expected_keys]


def _dataframe_record_to_installation(record: Dict[str, Any]) -> Installation:
    record['regime'] = Regime(record['regime'])
    record['seveso'] = Seveso(record['seveso'])
    record['family'] = InstallationFamily(record['family'])
    record['active'] = ActivityStatus(record['active'])
    return Installation(**record)


def _check_installations(installations: pd.DataFrame) -> None:
    for record in tqdm(installations.to_dict(orient='records')):
        _dataframe_record_to_installation(record)


def build_installations_csv() -> None:
    A_E_installations = _load_A_E_installations()
    installations_with_renamed_columns = _rename_installations_columns(A_E_installations)
    final_installations = _modify_and_keep_final_installations_cols(installations_with_renamed_columns)
    _check_installations(final_installations)
    final_active_installations = final_installations[
        final_installations.active == ActivityStatus.EN_FONCTIONNEMENT.value
    ]
    final_active_installations.to_csv(dataset_filename('all', 'installations'))
    print(f'Dumped {final_active_installations.shape[0]} active installations.')


def load_installations_csv(dataset: Dataset) -> pd.DataFrame:
    return pd.read_csv(dataset_filename(dataset, 'installations'), dtype='str')


def _select(s3ic_id: str) -> bool:
    return sum([ord(x) for x in s3ic_id]) % 10 == 0  # proba 1/10


def _filter_and_dump(all_installations: pd.DataFrame, dataset: Dataset) -> None:
    if dataset == 'idf':
        filtered_df = all_installations[all_installations.region == 'ILE DE FRANCE']
    elif dataset == 'sample':
        filtered_df = all_installations[all_installations.s3ic_id.apply(_select)]
    else:
        raise NotImplementedError(dataset)
    nb_rows = filtered_df.shape[0]
    assert nb_rows >= 1000, f'Expecting >= 1000 installations, got {nb_rows}'
    print(f'Installation dataset {dataset} has {nb_rows} rows')
    filtered_df.to_csv(dataset_filename(dataset, 'installations'))


def build_all_installations_datasets() -> None:
    all_installations = load_installations_csv('all')
    _filter_and_dump(all_installations, 'sample')
    _filter_and_dump(all_installations, 'idf')
