import os
from typing import Tuple

from envinorma.config import AM_DATA_FOLDER


def get_legifrance_filename(am_id: str) -> str:
    return f'{AM_DATA_FOLDER}/legifrance_texts/{am_id}.json'


def get_structured_am_filename(am_id: str) -> str:
    return f'{AM_DATA_FOLDER}/structured_texts/{am_id}.json'


def get_parametrization_filename(am_id: str) -> str:
    return os.path.join(AM_DATA_FOLDER, 'parametrizations', am_id + '.json')


def get_enriched_am_filename(am_id: str) -> str:
    return f'{AM_DATA_FOLDER}/enriched_texts/{am_id}.json'


def get_parametric_ams_folder(am_id: str) -> str:
    return f'{AM_DATA_FOLDER}/parametric_texts/{am_id}'


def generate_parametric_descriptor(version_descriptor: Tuple[str, ...]) -> str:
    if not version_descriptor:
        return 'no_date_version'
    return '_AND_'.join(version_descriptor).replace(' ', '_')


def create_folder_and_generate_parametric_filename(am_id: str, version_descriptor: Tuple[str, ...]) -> str:
    folder_name = get_parametric_ams_folder(am_id)
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return get_parametric_ams_folder(am_id) + '/' + generate_parametric_descriptor(version_descriptor) + '.json'
