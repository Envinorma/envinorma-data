import json
from lib.config import AM_DATA_FOLDER
from typing import List, Optional, Tuple
from shutil import copyfile

from lib.data import ArreteMinisteriel


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


def _handle_filename(filename: str, rubrique: str, installation_id: int) -> str:
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


if __name__ == '__main__':
    all_args: List[Tuple[str, str, int]] = [
        ('TREP1900331A/date-d-installation_<_2019-04-09.json', '2521', 1),
        ('TREP1900331A/date-d-installation_>=_2019-04-09.json', '2521', 1),
        ('TREP1900331A/no_date_version.json', '2521', 1),
        ('ATEP9760292A/no_date_version.json', '2517', 1),
        ('ATEP9760290A/no_date_version.json', '2515', 1),
        ('DEVP1706393A/reg_E_AND_date_after_2017.json', '1510', 2),
        ('DEVP1706393A/reg_E_AND_date_before_2003.json', '1510', 2),
        ('DEVP1706393A/reg_E_AND_date_between_2003_and_2010.json', '1510', 2),
        ('DEVP1706393A/reg_E_AND_date_between_2010_and_2017.json', '1510', 2),
        ('DEVP1706393A/reg_E_no_date.json', '1510', 2),
    ]
    file_ = open('tmp.txt', 'w')
    for args in all_args:
        file_.write(_handle_filename(*args))
