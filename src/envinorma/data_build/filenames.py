import os
from typing import Literal

_ENVINORMA_WEB_SEED_FOLDER = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds'

ENRICHED_OUTPUT_FOLDER = os.path.join(_ENVINORMA_WEB_SEED_FOLDER, 'enriched_arretes')
AM_LIST_FILENAME = os.path.join(_ENVINORMA_WEB_SEED_FOLDER, 'am_list.json')
UNIQUE_CLASSEMENTS_FILENAME = os.path.join(_ENVINORMA_WEB_SEED_FOLDER, 'unique_classements.csv')
Dataset = Literal['all', 'idf', 'sample']
DataType = Literal['classements', 'installations', 'documents', 'aps']


def dataset_filename(dataset: Dataset, datatype: DataType) -> str:
    return os.path.join(_ENVINORMA_WEB_SEED_FOLDER, f'{datatype}_{dataset}.csv')


GEORISQUES_URL = 'https://www.georisques.gouv.fr/webappReport/ws'
CQUEST_URL = 'http://data.cquest.org/icpe/commun'
GEORISQUES_DOWNLOAD_URL = 'http://documents.installationsclassees.developpement-durable.gouv.fr/commun'


_NOT_COMMITED_DATA_FOLDER = '/Users/remidelbouys/EnviNorma/brouillons/data'
GEORISQUES_DOCUMENTS_FILENAME = f'{_NOT_COMMITED_DATA_FOLDER}/georisques_documents.json'
GEORISQUES_CLASSEMENTS_FILENAME = f'{_NOT_COMMITED_DATA_FOLDER}/icpe_admin_data.json'
INSTALLATIONS_OPEN_DATA_FILENAME = f'{_NOT_COMMITED_DATA_FOLDER}/icpe.geojson'
DOCUMENTS_FOLDER = f'{_NOT_COMMITED_DATA_FOLDER}/icpe_documents'
DGPR_INSTALLATIONS_FILENAME = f'{_NOT_COMMITED_DATA_FOLDER}/AP svelte/s3ic-liste-etablissements.csv'
DGPR_RUBRIQUES_FILENAME = f'{_NOT_COMMITED_DATA_FOLDER}/AP svelte/sic-liste-rubriques.csv'
