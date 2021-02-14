'''
Script for generating all versions of a specific AM using its
structured version and its parametrization.
'''
from typing import Optional

from envinorma.back_office.generate_final_am import AMVersions, generate_final_am
from envinorma.back_office.utils import ID_TO_AM_MD
from envinorma.paths import create_folder_and_generate_parametric_filename
from envinorma.utils import write_json

TEST_ID = 'JORFTEXT000023081678'


def _dump(am_id: str, versions: Optional[AMVersions]) -> None:
    if not versions:
        return
    for version_desc, version in versions.items():
        filename = create_folder_and_generate_parametric_filename(am_id, version_desc)
        write_json(version.to_dict(), filename)


def handle_am(am_id: str) -> None:
    metadata = ID_TO_AM_MD.get(am_id)
    if not metadata:
        raise ValueError(f'AM {am_id} not found.')
    final_am = generate_final_am(metadata)
    _dump(am_id, final_am.am_versions)


if __name__ == '__main__':
    handle_am(TEST_ID)
