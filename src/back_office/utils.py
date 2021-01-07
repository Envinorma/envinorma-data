import os
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import dash
import dash_html_components as html
from dash.development.base_component import Component
from lib.config import STORAGE
from lib.data import ArreteMinisteriel, load_am_data
from lib.parametrization import Parametrization
from lib.utils import (
    get_parametrization_wip_folder,
    get_state_file,
    get_structured_text_wip_folder,
    write_json,
)

_AM = load_am_data()
ID_TO_AM_MD = {am.cid: am for am in _AM.metadata if am.state != am.state.ABROGE}
# ID_TO_AM_MD = {am.cid: am for am in ID_TO_AM_MD.values() if am.cid == 'JORFTEXT000026251890'}
# ID_TO_AM_MD = {am.cid: am for am in ID_TO_AM_MD.values() if '26' in am.cid}


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


def load_parametrization(am_id: str, am_state: AMState) -> Parametrization:
    folder = get_parametrization_wip_folder(am_id)
    if len(am_state.parametrization_draft_filenames) == 0:
        full_filename = os.path.join(folder, 'default.json')
        if not os.path.exists(full_filename):
            return Parametrization([], [])
    else:
        last_filename = am_state.parametrization_draft_filenames[-1]
        full_filename = os.path.join(folder, last_filename)
    return Parametrization.from_dict(json.load(open(full_filename)))


def _load_am_from_file(path: str) -> ArreteMinisteriel:
    return ArreteMinisteriel.from_dict(json.load(open(path)))


def load_am(am_id: str, am_state: AMState) -> ArreteMinisteriel:
    if len(am_state.structure_draft_filenames) == 0:
        last_filename = 'default.json'
    else:
        last_filename = am_state.structure_draft_filenames[-1]
    full_filename = os.path.join(get_structured_text_wip_folder(am_id), last_filename)
    return _load_am_from_file(full_filename)
