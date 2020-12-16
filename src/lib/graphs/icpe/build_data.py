from collections import Counter
from lib.data import Nomenclature, Regime
from typing import Dict, List, Optional, Set, Tuple
from lib.graphs.utils import build_data_file_name
from lib.graphs.icpe.data import ICPEDataset, ICPESStat
from lib.georisques_data import (
    DocumentType,
    GRClassement,
    GRClassementActivite,
    GRDocument,
    GRRegime,
    GeorisquesInstallation,
    load_installations_with_classements_and_docs,
)


def _count_document_types(documents: List[GRDocument]) -> Dict[DocumentType, int]:
    return Counter([doc.type_doc for doc in documents])


def _gr_regime_to_regime(regime: Optional[GRRegime]) -> Optional[Regime]:
    if not regime:
        return None
    if regime == regime.AUTORISATION:
        return Regime.A
    if regime == regime.ENREGISTREMENT:
        return Regime.E
    return None


def _compute_rubrique_and_regime(classement: GRClassement) -> Tuple[str, Regime]:
    regime = classement.theoretical_regime or _gr_regime_to_regime(classement.regime) or Regime.DC  # Bold assumption
    return (classement.code_nomenclature, regime)


def _compute_nb_am(classements: List[GRClassement], nomenclature: Nomenclature) -> int:
    am_ids: Set[str] = set()
    for classement in classements:
        if classement.code_nomenclature:
            rubrique_regime = _compute_rubrique_and_regime(classement)
            for am in nomenclature.rubrique_and_regime_to_am.get(rubrique_regime) or []:
                am_ids.add(am.cid)
    return len(am_ids)


def _build_stat(
    installation: GeorisquesInstallation,
    nomenclature: Nomenclature,
) -> ICPESStat:
    classements = installation.classements
    documents = installation.documents
    nb_active_classements = len(
        [clt for clt in classements if clt.etat_activite and clt.etat_activite == GRClassementActivite.ACTIVE]
    )
    nb_inactive_classements = len(
        [clt for clt in classements if clt.etat_activite and clt.etat_activite == GRClassementActivite.INACTIVE]
    )
    doc_types = _count_document_types(documents or [])
    rubriques = [classement.code_nomenclature for classement in classements]
    nb_am = _compute_nb_am(classements or [], nomenclature)
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


def build():
    all_installations = load_installations_with_classements_and_docs()
    nomenclature = Nomenclature.load_default()
    rows = [_build_stat(installation, nomenclature) for installation in all_installations]
    ICPEDataset(rows).to_csv(build_data_file_name(__file__))


if __name__ == '__main__':
    build()
