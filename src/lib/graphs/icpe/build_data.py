from collections import Counter
from lib.graphs.icpe.data import RubriquePerDepartments
from lib.graphs.utils import build_data_file_name
from lib.georisques_data import load_all_classements, load_all_installations


def build():
    all_classements = load_all_classements()
    all_installations = load_all_installations()

    tuples_occurrences = Counter(
        [
            (classement.code_nomenclature, classement.regime.value if classement.regime else None, installation.num_dep)
            for installation in all_installations
            for classement in all_classements[installation.code_s3ic]
            if classement.date_autorisation
        ]
    )
    codes = []
    regimes = []
    departments = []
    occurrences = []
    for (code, regime, dep), occs in tuples_occurrences.items():
        codes.append(code)
        regimes.append(regime)
        departments.append(dep)
        occurrences.append(occs)

    RubriquePerDepartments(codes, regimes, departments, occurrences).to_csv(build_data_file_name(__file__))


if __name__ == '__main__':
    build()
