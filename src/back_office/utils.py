import os
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Tuple

from lib.config import EnvironmentType, config
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
    INIT = 'init'
    EDIT_STRUCTURE = 'edit_structure'
    ADD_CONDITION = 'add_condition'
    ADD_ALTERNATIVE_SECTION = 'add_alternative_section'


class AMStatus(Enum):
    PENDING_INITIALIZATION = 'pending-initialization'
    PENDING_STRUCTURE_VALIDATION = 'pending-structure-validation'
    PENDING_PARAMETRIZATION = 'pending-enrichment'
    VALIDATED = 'validated'

    def step(self) -> int:
        if self == AMStatus.PENDING_INITIALIZATION:
            return 0
        if self == AMStatus.PENDING_STRUCTURE_VALIDATION:
            return 1
        if self == AMStatus.PENDING_PARAMETRIZATION:
            return 2
        if self == AMStatus.VALIDATED:
            return 3
        raise NotImplementedError()


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


def get_traversed_titles_rec(path: Ints, text: StructuredText) -> Optional[List[str]]:
    if not path:
        return [text.title.text]
    if path[0] >= len(text.sections):
        return None
    titles = get_traversed_titles_rec(path[1:], text.sections[path[0]])
    if titles is None:
        return None
    return [text.title.text] + titles


def get_traversed_titles(path: Ints, am: ArreteMinisteriel) -> Optional[List[str]]:
    if not path:
        return ['Arrêté complet.']
    if path[0] >= len(am.sections):
        return None
    return get_traversed_titles_rec(path[1:], am.sections[path[0]])


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


def check_backups():
    if config.environment.type == EnvironmentType.PROD:
        return
    files = os.listdir(__file__.replace('back_office/utils.py', 'backups'))
    max_date: Optional[datetime] = max(
        [datetime.strptime(file_.split('.')[0], '%Y-%m-%d-%H-%M') for file_ in files], default=None
    )
    if not max_date:
        raise ValueError('No back_office db backups found : run one.')
    if (datetime.now() - max_date).total_seconds() >= 20 * 3600:
        raise ValueError(f'Last backup is too old, run one. (date: {max_date})')
