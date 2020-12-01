from collections import Counter
from lib.graphs.utils import build_data_file_name
from lib.graphs.rubriques_over_time.data import RubriqueOverTimeDataset
from lib.georisques_data import load_all_classements, load_all_installations


def build():
    all_classements = load_all_classements()
    all_installations = load_all_installations()

    tuples_occurrences = Counter(
        [
            (classement.code_nomenclature, classement.date_autorisation.year, installation.num_dep)
            for installation in all_installations
            for classement in all_classements[installation.code_s3ic]
            if classement.date_autorisation
        ]
    )
    codes = []
    years = []
    departments = []
    occurrences = []
    for (code, year, dep), occs in tuples_occurrences.items():
        codes.append(code)
        years.append(year)
        departments.append(dep)
        occurrences.append(occs)

    RubriqueOverTimeDataset(codes, years, departments, occurrences).to_csv(build_data_file_name(__file__))


if __name__ == '__main__':
    build()
