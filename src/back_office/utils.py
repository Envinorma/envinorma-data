import json
import os
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import dash
import dash_html_components as html
from dash.development.base_component import Component
from lib.config import STORAGE
from lib.data import ArreteMinisteriel, Ints, StructuredText, load_am_data
from lib.parametrization import Parametrization
from lib.utils import get_parametrization_wip_folder, get_state_file, get_structured_text_wip_folder, write_json

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


class Page:
    def __init__(self, router: Callable[[str, str], Component], add_callbacks: Callable[[dash.Dash], None]) -> None:
        self.router: Callable[[str, str], Component] = router
        self.add_callbacks: Callable[[dash.Dash], None] = add_callbacks


def div(children: Union[List[Component], Component], style: Optional[Dict[str, Any]] = None) -> Component:
    return html.Div(children, style=style)


class AMOperation(Enum):
    EDIT_STRUCTURE = 'edit_structure'
    ADD_CONDITION = 'add_condition'
    ADD_ALTERNATIVE_SECTION = 'add_alternative_section'


class AMWorkflowState(Enum):
    PENDING_STRUCTURE_VALIDATION = 'pending-structure-validation'
    PENDING_PARAMETRIZATION = 'pending-enrichment'
    VALIDATED = 'validated'


@dataclass
class AMState:
    state: AMWorkflowState
    structure_draft_filenames: List[str]
    parametrization_draft_filenames: List[str]

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'AMState':
        dict_ = dict_.copy()
        dict_['state'] = AMWorkflowState(dict_['state'])
        return AMState(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        dict_ = asdict(self)
        dict_['state'] = self.state.value
        return dict_


def load_am_state(am_id: str) -> AMState:
    state_file = get_state_file(am_id)
    return AMState.from_dict(json.load(open(state_file)))


def dump_am_state(am_id: str, am_state: AMState) -> None:
    state_file = get_state_file(am_id)
    write_json(am_state.to_dict(), state_file)


def write_file(content: str, filename: str):
    if STORAGE != 'local':
        raise ValueError(f'Unhandled storage value {STORAGE}')
    with open(filename, 'w') as file_:
        file_.write(content)


def get_default_structure_filename(am_id: str) -> str:
    return os.path.join(get_structured_text_wip_folder(am_id), 'default.json')


def get_default_parametrization_filename(am_id: str) -> str:
    return os.path.join(get_parametrization_wip_folder(am_id), 'default.json')


def load_parametrization(am_id: str, am_state: AMState) -> Parametrization:
    folder = get_parametrization_wip_folder(am_id)
    if len(am_state.parametrization_draft_filenames) == 0:
        full_filename = get_default_parametrization_filename(am_id)
        if not os.path.exists(full_filename):
            return Parametrization([], [])
    else:
        last_filename = am_state.parametrization_draft_filenames[-1]
        full_filename = os.path.join(folder, last_filename)
    return Parametrization.from_dict(json.load(open(full_filename)))


def load_am_from_file(path: str) -> ArreteMinisteriel:
    return ArreteMinisteriel.from_dict(json.load(open(path)))


def load_am(am_id: str, am_state: AMState) -> Optional[ArreteMinisteriel]:
    if len(am_state.structure_draft_filenames) == 0:
        last_filename = 'default.json'
    else:
        last_filename = am_state.structure_draft_filenames[-1]
    full_filename = os.path.join(get_structured_text_wip_folder(am_id), last_filename)
    if not os.path.exists(full_filename):
        return None
    return load_am_from_file(full_filename)


def get_subsection(path: Ints, text: StructuredText) -> StructuredText:
    if not path:
        return text
    return get_subsection(path[1:], text.sections[path[0]])


def get_section(path: Ints, am: ArreteMinisteriel) -> StructuredText:
    return get_subsection(path[1:], am.sections[path[0]])


def get_section_title(path: Ints, am: ArreteMinisteriel) -> str:
    if not path:
        return 'Arrêté complet.'
    return get_subsection(path[1:], am.sections[path[0]]).title.text


def get_truncated_str(str_: str, _max_len: int = 80) -> str:
    truncated_str = str_[:_max_len]
    if len(str_) > _max_len:
        return truncated_str[:-5] + '[...]'
    return truncated_str


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

#     new_state = AMState(AMWorkflowState.PENDING_STRUCTURE_VALIDATION, [], [])
#     dump_am_state(AM_ID, new_state)
