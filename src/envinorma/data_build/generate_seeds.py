'''
Download last versions of AM and send them to envinorma-web
'''

from envinorma.data_build.build.build_ams import generate_ams
from envinorma.data_build.build.build_classements import build_classements_csv
from envinorma.data_build.build.build_documents import build_all_document_datasets, download_georisques_documents
from envinorma.data_build.build.build_installations import build_installations_csv
from envinorma.data_build.filenames import (
    AM_LIST_FILENAME,
    ENRICHED_OUTPUT_FOLDER,
    UNIQUE_CLASSEMENTS_FILENAME,
    dataset_filename,
)
from envinorma.data_build.validate.check_am import check_ams
from envinorma.data_build.validate.check_classements import check_classements_csv
from envinorma.data_build.validate.check_installations import check_installations_csv
from envinorma.data_build.validate.check_unique_classements import check_unique_classements_csv


def _check_seeds() -> None:
    check_unique_classements_csv(UNIQUE_CLASSEMENTS_FILENAME)
    check_classements_csv(dataset_filename('all', 'classements'))
    check_installations_csv(dataset_filename('all', 'installations'))
    check_ams(AM_LIST_FILENAME, ENRICHED_OUTPUT_FOLDER)


def run():
    generate_ams()
    build_classements_csv()
    build_installations_csv()
    download_georisques_documents()
    build_all_document_datasets()
    _check_seeds()


if __name__ == '__main__':
    run()
