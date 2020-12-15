from typing import List


def _extract_python_file_vars(filename: str) -> List[str]:
    return [x.split(' = ')[0] for x in open(filename).readlines()]


def test_config():
    assert set(_extract_python_file_vars('lib/config.py')) == set(_extract_python_file_vars('lib/config.template.py'))