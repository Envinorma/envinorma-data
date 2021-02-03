import json
import os
from shutil import copyfile
import shutil
from typing import List, Optional, Tuple

from lib.config import AM_DATA_FOLDER
from lib.data import ArreteMinisteriel
from lib.scrap_scructure_and_enrich_all_am import load_data
from lib.utils import write_json
from tqdm import tqdm


def _get_input_path(filename: str) -> str:
    return f'{AM_DATA_FOLDER}/parametric_texts/{filename}'


def _get_output_path(filename: str) -> str:
    return f'/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds/{filename}'


def _ruby_bool(bool_: bool) -> str:
    return 'true' if bool_ else 'false'


def _ruby_optional_str(str_: Optional[str]) -> str:
    if str_ is None:
        return 'nil'
    return f'"{str_}"'


def _exists(folder: str) -> bool:
    if os.path.exists(folder):
        return True
    print(f'Warning: folder {folder} does not exist.')
    return False


def _concatenate_and_dump_all_am():
    parametric_texts_folder = AM_DATA_FOLDER + '/parametric_texts'
    data = load_data()
    all_folders = [md.nor or md.cid for md in data.arretes_ministeriels.metadata if md.state == md.state.VIGUEUR]
    folders_to_copy = [fd for fd in all_folders if _exists(parametric_texts_folder + '/' + fd)]
    res = [
        json.load(open(os.path.join(parametric_texts_folder, folder, file)))
        for folder in tqdm(folders_to_copy)
        for file in os.listdir(parametric_texts_folder + '/' + folder)
        if 'no_date' in file
    ]
    print(len(res))
    write_json(res, 'am_list.json', pretty=False)


def _handle_filename(filename: str, rubrique: str) -> str:
    arrete = ArreteMinisteriel.from_dict(json.load(open(_get_input_path(filename))))

    copyfile(_get_input_path(filename), _get_output_path(filename))
    left_date = arrete.installation_date_criterion.left_date if arrete.installation_date_criterion else None
    right_date = arrete.installation_date_criterion.right_date if arrete.installation_date_criterion else None
    summary = json.dumps(arrete.summary.to_dict(), ensure_ascii=False) if arrete.summary else 'nil'
    return f'''
path = File.join(File.dirname(__FILE__), "./seeds/{filename}")
arrete_{rubrique} = JSON.parse(File.read(path))
Arrete.create(
    name: "AM - {rubrique}",
    data: arrete_{rubrique},
    short_title: "{arrete.short_title}",
    title: "{arrete.title.text}",
    unique_version: {_ruby_bool(arrete.unique_version)},
    installation_date_criterion_left: {_ruby_optional_str(left_date)},
    installation_date_criterion_right: {_ruby_optional_str(right_date)},
    aida_url: {_ruby_optional_str(arrete.aida_url)},
    legifrance_url: {_ruby_optional_str(arrete.legifrance_url)},
    summary: {summary}
)

'''


def _move_file(filename: str) -> None:
    source = f'{AM_DATA_FOLDER}/parametric_texts/{filename}'
    destination = '/Users/remidelbouys/EnviNorma/envinorma-web/db/seeds/enriched_arretes/{}'.format(
        filename.replace('/', '_')
    )
    shutil.copyfile(source, destination)


def _copy_all_files():
    files_to_move = [
        'TREP1900331A/date-d-installation_<_2019-04-09.json',
        'TREP1900331A/date-d-installation_>=_2019-04-09.json',
        'TREP1900331A/no_date_version.json',
        'ATEP9760292A/no_date_version.json',
        'ATEP9760290A/no_date_version.json',
        'DEVP1706393A/reg_E_AND_date_after_2017.json',
        'DEVP1706393A/reg_E_AND_date_before_2003.json',
        'DEVP1706393A/reg_E_AND_date_between_2003_and_2010.json',
        'DEVP1706393A/reg_E_AND_date_between_2010_and_2017.json',
        'DEVP1706393A/reg_E_no_date.json',
        # 'JORFTEXT000023081678/date-d-installation_>=_2010-10-03.json',
        # 'JORFTEXT000023081678/date-d-installation_<_2010-10-03.json',
        # 'JORFTEXT000023081678/no_date_version.json',
    ]
    for file_ in files_to_move:
        _move_file(file_)


if __name__ == '__main__':
    # _concatenate_and_dump_all_am()
    _copy_all_files()