from enum import Enum
from typing import Any, List, Optional, Tuple

from lib.config import STORAGE
from lib.data import ArreteMinisteriel, Ints, StructuredText, load_am_data

_AM = load_am_data()
ID_TO_AM_MD = {am.cid: am for am in _AM.metadata if am.state != am.state.ABROGE}


def assert_int(value: Any) -> int:
    if not isinstance(value, int):
        raise ValueError(f'Expecting type int, received type {type(value)}')
    return value


def assert_str(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError(f'Expecting type str, received type {type(value)}')
    return value


def assert_list(value: Any) -> List:
    if not isinstance(value, list):
        raise ValueError(f'Expecting type list, received type {type(value)}')
    return value


class AMOperation(Enum):
    EDIT_STRUCTURE = 'edit_structure'
    ADD_CONDITION = 'add_condition'
    ADD_ALTERNATIVE_SECTION = 'add_alternative_section'
    DISPLAY_AM = 'display_am'


class AMStatus(Enum):
    PENDING_STRUCTURE_VALIDATION = 'pending-structure-validation'
    PENDING_PARAMETRIZATION = 'pending-enrichment'
    VALIDATED = 'validated'


def write_file(content: str, filename: str):
    if STORAGE != 'local':
        raise ValueError(f'Unhandled storage value {STORAGE}')
    with open(filename, 'w') as file_:
        file_.write(content)


def get_subsection(path: Ints, text: StructuredText) -> StructuredText:
    if not path:
        return text
    return get_subsection(path[1:], text.sections[path[0]])


def get_section(path: Ints, am: ArreteMinisteriel) -> StructuredText:
    return get_subsection(path[1:], am.sections[path[0]])


def safe_get_subsection(path: Ints, text: StructuredText) -> Optional[StructuredText]:
    if not path:
        return text
    if path[0] >= len(text.sections):
        return None
    return safe_get_subsection(path[1:], text.sections[path[0]])


def safe_get_section(path: Ints, am: ArreteMinisteriel) -> Optional[StructuredText]:
    return safe_get_subsection(path[1:], am.sections[path[0]])


def get_section_title(path: Ints, am: ArreteMinisteriel) -> Optional[str]:
    if not path:
        return 'Arrêté complet.'
    if path[0] >= len(am.sections):
        return None
    section = safe_get_subsection(path[1:], am.sections[path[0]])
    if not section:
        return None
    return section.title.text


def get_truncated_str(str_: str, _max_len: int = 80) -> str:
    truncated_str = str_[:_max_len]
    if len(str_) > _max_len:
        return truncated_str[:-5] + '[...]'
    return truncated_str


def split_route(route: str) -> Tuple[str, str]:
    assert route.startswith('/')
    pieces = route[1:].split('/')
    return '/' + pieces[0], ('/' + '/'.join(pieces[1:])) if pieces[1:] else ''


class RouteParsingError(Exception):
    pass


# from tqdm import tqdm
# import shutil

# for AM in tqdm(_AM.metadata):
#     AM_ID = AM.cid

#     if not os.path.exists(get_parametrization_wip_folder(AM_ID)):
#         os.mkdir(get_parametrization_wip_folder(AM_ID))
#     default_param = get_parametrization_filename(AM.nor or AM.cid)
#     if os.path.exists(default_param):
#         shutil.copy(default_param, get_parametrization_wip_folder(AM_ID) + '/default.json')

#     if not os.path.exists(get_structured_text_wip_folder(AM_ID)):
#         os.mkdir(get_structured_text_wip_folder(AM_ID))
#     default_text = get_structured_text_filename(AM.nor or AM.cid)
#     if os.path.exists(default_text):
#         shutil.copy(default_text, get_structured_text_wip_folder(AM_ID) + '/default.json')

#     new_state = AMState(AMStatus.PENDING_STRUCTURE_VALIDATION, [], [])
#     dump_am_state(AM_ID, new_state)
