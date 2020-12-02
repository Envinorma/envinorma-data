from lib.graphs.utils import build_data_file_name
from lib.graphs.rubriques_over_time.data import RubriquesDataset, RubriqueStat
from lib.georisques_data import GRClassement, GeorisquesInstallation, load_all_classements, load_all_installations


def _build_stat(classement: GRClassement, installation: GeorisquesInstallation) -> RubriqueStat:
    return RubriqueStat(
        rubrique=classement.code_nomenclature,
        year=classement.date_autorisation.year,
        s3ic_base=installation.code_s3ic.split('.')[0],
        department=installation.num_dep,
        active=classement.etat_activite.value if classement.etat_activite else 'not-specified',
        famille_nomenclature=classement.famille_nomenclature.value
        if classement.famille_nomenclature
        else 'not-specified',
    )


def build():
    all_classements = load_all_classements()
    all_installations = load_all_installations()
    rows = [
        _build_stat(classement, installation)
        for installation in all_installations
        for classement in all_classements[installation.code_s3ic]
        if classement.date_autorisation
    ]
    RubriquesDataset(rows).to_csv(build_data_file_name(__file__))


if __name__ == '__main__':
    build()
