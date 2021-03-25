from envinorma.dashboard.classements.data import RubriquesDataset, RubriqueStat
from envinorma.data.classement import DetailedClassement
from envinorma.data.installation import Installation
from envinorma.data.load import load_classements, load_installations


def _build_stat(classement: DetailedClassement, installation: Installation) -> RubriqueStat:
    return RubriqueStat(
        rubrique=classement.rubrique,
        year=classement.date_autorisation.year if classement.date_autorisation else -1,
        s3ic_base=installation.s3ic_id.split('.')[0],
        department=installation.num_dep,
        active=classement.state.value if classement.state else 'not-specified',
        famille_nomenclature=classement.activite if classement.activite else 'not-specified',
    )


def build(output_filename: str):
    all_classements = load_classements('all')
    all_installations = {inst.s3ic_id: inst for inst in load_installations('all')}
    rows = [
        _build_stat(classement, all_installations[classement.s3ic_id])
        for classement in all_classements
        if classement.date_autorisation
    ]
    RubriquesDataset(rows).to_csv(output_filename)
