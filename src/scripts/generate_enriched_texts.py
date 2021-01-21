from typing import Optional

from lib.data import AMMetadata, load_am_data
from lib.paths import create_folder_and_generate_parametric_filename
from lib.utils import write_json
from lib.generate_final_am import AMVersions, generate_final_am

TEST_ID = 'JORFTEXT000023081678'


def _dump(am_id: str, versions: Optional[AMVersions]) -> None:
    if not versions:
        return
    for version_desc, version in versions.items():
        filename = create_folder_and_generate_parametric_filename(am_id, version_desc)
        write_json(version.to_dict(), filename)


def _get_am_metadata(am_id: str) -> AMMetadata:
    ams = load_am_data()
    for metadata in ams.metadata:
        if metadata.cid == am_id:
            return metadata
    raise ValueError(f'AM {am_id} not found.')


def handle_am(am_id: str) -> None:
    metadata = _get_am_metadata(am_id)
    final_am = generate_final_am(metadata)
    _dump(am_id, final_am.am_versions)


if __name__ == '__main__':
    handle_am(TEST_ID)
