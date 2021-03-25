'''
script for building data necessary for dashboard-envinorma.herokuapp.py
'''
from typing import Callable, Dict

from envinorma.build_dashboard.build_classements_data import build as classements_build
from envinorma.build_dashboard.build_icpe_data import build as icpe_build
from envinorma.build_dashboard.build_tables_in_am_data import build as tables_in_am_build

if __name__ == '__main__':
    output_folder = __file__.replace('data_build/build_dashboard/__init__.py', 'dashboard/{}/data.csv')
    builders: Dict[str, Callable[[str], None]] = {
        'classements': classements_build,
        'icpe': icpe_build,
        'tables_in_am': tables_in_am_build,
    }
    for key, builder in builders.items():
        print(key)
        builder(output_folder.format(key))
