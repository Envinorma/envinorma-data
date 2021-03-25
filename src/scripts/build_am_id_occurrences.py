'''Build file data/am_id_to_nb_classements.json containing the number of occurrences 
of each AM among all active installations.
'''

from collections import Counter
from typing import Dict, List

from envinorma.back_office.utils import ID_TO_AM_MD
from envinorma.data.load import load_classements


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
    classements = load_classements('all')
    keys = [f'{cl.rubrique}-{cl.regime.value}' for cl in classements]
    return Counter([am_id for cl in keys for am_id in classement_to_ams.get(cl) or [None]])


if __name__ == '__main__':
    run()
