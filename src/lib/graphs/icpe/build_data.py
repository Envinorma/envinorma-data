from collections import Counter
from typing import Dict, List
from lib.graphs.utils import build_data_file_name
from lib.graphs.icpe.data import ICPEDataset, ICPESStat
from lib.georisques_data import (
    DocumentType,
    GRClassement,
    GRClassementActivite,
    GRDocument,
    GeorisquesInstallation,
    load_all_classements,
    load_all_installations,
    load_all_documents,
)


def _count_document_types(documents: List[GRDocument]) -> Dict[DocumentType, int]:
    return Counter([doc.type_doc for doc in documents])


def _build_stat(
    installation: GeorisquesInstallation, classements: List[GRClassement], documents: List[GRDocument]
) -> ICPESStat:
    nb_active_classements = len(
        [clt for clt in classements if clt.etat_activite and clt.etat_activite == GRClassementActivite.ACTIVE]
    )
    nb_inactive_classements = len(
        [clt for clt in classements if clt.etat_activite and clt.etat_activite == GRClassementActivite.INACTIVE]
    )
    doc_types = _count_document_types(documents)
    rubriques = [classement.code_nomenclature for classement in classements]
    return ICPESStat(
        num_dep=installation.num_dep,
        region=installation.region or 'unknown',
        city=installation.city,
        last_inspection=installation.last_inspection,
        regime=installation.regime.value,
        seveso=installation.seveso.value,
        family=installation.family.value,
        active=installation.active.value,
        code_postal=installation.code_postal,
        code_naf=installation.code_naf,
        nb_documents=len(documents),
        nb_ap=doc_types[DocumentType.AP],
        nb_reports=doc_types[DocumentType.RAPPORT],
        nb_sanctions=doc_types[DocumentType.SANCTION],
        nb_med=doc_types[DocumentType.APMED],
        nb_active_classements=nb_active_classements,
        nb_inactive_classements=nb_inactive_classements,
        rubriques=rubriques,
    )


def build():
    all_documents = load_all_documents()
    all_installations = load_all_installations()
    all_classements = load_all_classements()
    rows = [
        _build_stat(
            installation, all_classements[installation.s3ic_id], all_documents[installation.s3ic_id.replace('.', '-')]
        )
        for installation in all_installations
        if installation.s3ic_id in all_classements
        if installation.s3ic_id.replace('.', '-') in all_documents
    ]
    ICPEDataset(rows).to_csv(build_data_file_name(__file__))


if __name__ == '__main__':
    build()
