'''Build file data/am_id_to_nb_classements_idf.json containing the number of occurrences 
of each AM among IDF installations.
'''

from collections import Counter
from typing import Dict, List

import pandas
from envinorma.back_office.utils import ID_TO_AM_MD


def _load_classement_to_am() -> Dict[str, List[str]]:
    classement_to_ams: Dict[str, List[str]] = {}
    for am_id, am in ID_TO_AM_MD.items():
        for cl in am.classements:
            cl_str = f'{cl.rubrique}-{cl.regime.value}'
            if cl_str not in classement_to_ams:
                classement_to_ams[cl_str] = []
            classement_to_ams[cl_str].append(am_id)
    return classement_to_ams


def run():
    classement_to_ams = _load_classement_to_am()
    dataframe = pandas.read_csv('backups/classements.csv', dtype=str)  # type: ignore
    rubriques = dataframe.rubrique
    regimes = dataframe.regime

    classements = [f'{rub}-{reg}' for rub, reg in zip(rubriques, regimes)]
    return Counter([am_id for cl in classements for am_id in classement_to_ams.get(cl) or [None]])


if __name__ == '__main__':
    run()
