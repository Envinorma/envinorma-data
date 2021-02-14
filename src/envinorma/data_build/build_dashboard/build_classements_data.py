from envinorma.dashboard.classements.data import RubriquesDataset, RubriqueStat
from envinorma.data_build.georisques_data import (
    GeorisquesInstallation,
    GRClassement,
    load_all_classements,
    load_all_installations,
)


def _build_stat(classement: GRClassement, installation: GeorisquesInstallation) -> RubriqueStat:
    return RubriqueStat(
        rubrique=classement.code_nomenclature,
        year=classement.date_autorisation.year if classement.date_autorisation else -1,
        s3ic_base=installation.s3ic_id.split('.')[0],
        department=installation.num_dep,
        active=classement.etat_activite.value if classement.etat_activite else 'not-specified',
        famille_nomenclature=classement.famille_nomenclature.value
        if classement.famille_nomenclature
        else 'not-specified',
    )


def build(output_filename: str):
    all_classements = load_all_classements()
    all_installations = load_all_installations()
    rows = [
        _build_stat(classement, installation)
        for installation in all_installations
        for classement in all_classements[installation.s3ic_id]
        if classement.date_autorisation
    ]
    RubriquesDataset(rows).to_csv(output_filename)
