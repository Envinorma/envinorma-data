from collections import Counter
from typing import Dict, List, Set

from envinorma.dashboard.icpe.data import ICPEDataset, ICPESStat
from envinorma.data import Nomenclature
from envinorma.data.classement import DetailedClassement, State
from envinorma.data.document import Document, DocumentType
from envinorma.data.load import load_installations
from envinorma.data_build.georisques_data import Installation


def _count_document_types(documents: List[Document]) -> Dict[DocumentType, int]:
    return Counter([doc.type for doc in documents])


def _compute_nb_am(classements: List[DetailedClassement], nomenclature: Nomenclature) -> int:
    am_ids: Set[str] = set()
    for classement in classements:
        if classement.rubrique:
            regime = classement.regime.to_regime()
            if not regime:
                continue
            for am in nomenclature.rubrique_and_regime_to_am.get((classement.rubrique, regime)) or []:
                am_ids.add(am.cid)
    return len(am_ids)


def _build_stat(
    installation: Installation,
    classements: List[DetailedClassement],
    documents: List[Document],
    nomenclature: Nomenclature,
) -> ICPESStat:
    nb_active_classements = len([clt for clt in classements if clt.state == State.EN_FONCTIONNEMENT])
    nb_inactive_classements = len([clt for clt in classements if clt.state != State.EN_FONCTIONNEMENT])
    doc_types = _count_document_types(documents or [])
    rubriques = [classement.rubrique for classement in classements]
    nb_am = _compute_nb_am(classements or [], nomenclature)
    return ICPESStat(
        num_dep=installation.num_dep,
        region=installation.region or 'unknown',
        city=installation.city,
        last_inspection=installation.last_inspection,
        regime=installation.regime.value,
        seveso=installation.seveso.value,
        family=installation.family.value,
        active=installation.active.value == installation.active.EN_FONCTIONNEMENT,
        code_postal=installation.code_postal,
        code_naf=installation.code_naf,
        nb_documents=len(documents or []),
        nb_ap=doc_types[DocumentType.AP],
        nb_am=nb_am,
        nb_arretes=nb_am + doc_types[DocumentType.AP],
        nb_reports=doc_types[DocumentType.RAPPORT],
        nb_sanctions=doc_types[DocumentType.SANCTION],
        nb_med=doc_types[DocumentType.APMED],
        nb_active_classements=nb_active_classements,
        nb_inactive_classements=nb_inactive_classements,
        rubriques=rubriques,
    )


def build(output_filename: str):
    all_installations = load_installations('all')
    nomenclature = Nomenclature.load_default()
    rows = [_build_stat(installation, [], [], nomenclature) for installation in all_installations]
    ICPEDataset(rows).to_csv(output_filename)
