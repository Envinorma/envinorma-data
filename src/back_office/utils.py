import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import dash
import dash_html_components as html
from dash.development.base_component import Component
from lib.data import ArreteMinisteriel, load_am_data
from lib.utils import get_state_file, get_structured_text_filename, write_json

_AM = load_am_data()
ID_TO_AM_MD = {am.cid: am for am in _AM.metadata if am.cid == 'JORFTEXT000026251890'}
ID_TO_AM_MD = {am.cid: am for am in _AM.metadata if '26' in am.cid}


class Page:
    def __init__(self, router: Callable[[str, str], Component], add_callbacks: Callable[[dash.Dash], None]) -> None:
        self.router: Callable[[str, str], Component] = router
        self.add_callbacks: Callable[[dash.Dash], None] = add_callbacks


def div(children: Union[List[Component], Component], style: Optional[Dict[str, Any]] = None) -> Component:
    return html.Div(children, style=style)


def _load_am_from_file(am_id: str) -> ArreteMinisteriel:
    path = get_structured_text_filename(am_id)
    return ArreteMinisteriel.from_dict(json.load(open(path)))


def load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    am_md = ID_TO_AM_MD.get(am_id)
    if not am_md:
        return None
    return _load_am_from_file(am_md.nor or am_md.cid)


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
