from datetime import date
from typing import Any, cast

import pandas as pd
from tqdm import tqdm

from envinorma.data.installation import Installation
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


def _modify_and_keep_final_installations_cols(installations: pd.DataFrame) -> pd.DataFrame:
    installations = installations.copy()
    installations['num_dep'] = installations.code_postal.apply(lambda x: (x or '')[:2])
    installations['last_inspection'] = installations.last_inspection.apply(
        lambda x: date.fromisoformat(x) if not isinstance(x, float) else None
    )
    expected_keys = [x for x in Installation.__dataclass_fields__ if x not in ('documents', 'classements')]  # type: ignore
    return installations[expected_keys]


def _check_installations(installations: pd.DataFrame) -> None:
    for record in tqdm(installations.to_dict(orient='records')):
        Installation(**record)


def build_installations_csv() -> None:
    A_E_installations = _load_A_E_installations()
    installations_with_renamed_columns = _rename_installations_columns(A_E_installations)
    final_installations = _modify_and_keep_final_installations_cols(installations_with_renamed_columns)
    _check_installations(final_installations)
    final_installations.to_csv(dataset_filename('all', 'installations'))


def load_installations_csv(dataset: Dataset) -> pd.DataFrame:
    return pd.read_csv(dataset_filename(dataset, 'installations'), dtype='str')
