import json
import os
import random
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Tuple

from dash_text_components.diff import TextDifferences, build_text_differences
from envinorma.aida import parse_aida_text
from envinorma.config import config
from envinorma.data import (
    ArreteMinisteriel,
    EnrichedString,
    Ints,
    StructuredText,
    extract_text_lines,
    load_am_data,
    load_legifrance_text,
)
from envinorma.structure.am_structure_extraction import extract_short_title, transform_arrete_ministeriel
from flask_login import current_user
from legifrance.legifrance_API import get_legifrance_client, get_loda_via_cid

_AM = load_am_data()
ID_TO_AM_MD = {am.cid: am for am in _AM.metadata if am.state == am.state.VIGUEUR}
AM_ID_TO_NB_CLASSEMENTS_IDF = json.load(
    open(__file__.replace('envinorma/back_office/utils.py', 'data/am_id_to_nb_classements_idf.json'))
)


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
    if not path or len(path) == 0:
        return None
    if path[0] >= len(am.sections):
        return None
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
    files = os.listdir(__file__.replace('envinorma/back_office/utils.py', 'backups'))
    max_date: Optional[datetime] = max(
        [datetime.strptime(file_.split('.')[0], '%Y-%m-%d-%H-%M') for file_ in files], default=None
    )
    if not max_date:
        raise ValueError('No back_office db backups found : run one.')
    if (datetime.now() - max_date).total_seconds() >= 20 * 3600:
        raise ValueError(f'Last backup is too old, run one. (date: {max_date})')


def check_legifrance_diff_computed():
    files = os.listdir(__file__.replace('envinorma/back_office/utils.py', 'data/legifrance_diffs'))
    max_date: Optional[datetime] = max(
        [datetime.strptime(file_.split('.')[0], '%Y-%m-%d-%H-%M') for file_ in files], default=None
    )
    cmd = 'python3 scripts/check_new_texts_were_published.py'
    if not max_date:
        raise ValueError(f'No legifrance_diffs found : run one.\ncmd: {cmd}')
    if (datetime.now() - max_date).total_seconds() >= 12 * 24 * 3600:
        raise ValueError(f'Last legifrance_diffs computation is too old, run one. (date: {max_date})\ncmd: {cmd}')


def extract_aida_am(page_id: str, am_id: str) -> Optional[ArreteMinisteriel]:
    text = parse_aida_text(page_id)
    if not text:
        return None
    if len(text.sections) == 1:
        section = text.sections[0]
        if section.outer_alineas:
            new_sections = [StructuredText(EnrichedString(''), section.outer_alineas, [], None)] + section.sections
        else:
            new_sections = section.sections
        return ArreteMinisteriel(
            title=section.title,
            short_title=extract_short_title(section.title.text),
            sections=new_sections,
            visa=[],
            id=am_id,
        )
    return ArreteMinisteriel(
        title=EnrichedString('title'), short_title='short_tile', sections=[text], visa=[], id=am_id
    )


def extract_legifrance_am(am_id: str, date: Optional[datetime] = None) -> ArreteMinisteriel:
    date = date or datetime.now()
    client = get_legifrance_client(config.legifrance.client_id, config.legifrance.client_secret)
    legifrance_current_version = load_legifrance_text(get_loda_via_cid(am_id, date, client))
    random.seed(legifrance_current_version.title)
    return transform_arrete_ministeriel(legifrance_current_version, am_id=am_id)


def _extract_lines(am: ArreteMinisteriel) -> List[str]:
    return [line for section in am.sections for line in extract_text_lines(section, 0)]


def compute_am_diff(am_before: ArreteMinisteriel, am_after: ArreteMinisteriel) -> TextDifferences:
    lines_before = _extract_lines(am_before)
    lines_after = _extract_lines(am_after)
    return build_text_differences(lines_before, lines_after)


def compute_text_diff(text_before: StructuredText, text_after: StructuredText) -> TextDifferences:
    lines_before = extract_text_lines(text_before)
    lines_after = extract_text_lines(text_after)
    return build_text_differences(lines_before, lines_after)


def generate_id(filename: str, suffix: str) -> str:
    prefix = filename.split('/')[-1].replace('.py', '').replace('_', '-')
    return prefix + '-' + suffix


@dataclass
class User:
    username: str
    password: str
    active: bool = True
    authenticated: bool = True
    anonymous: bool = False

    def get_id(self) -> str:
        return self.username

    @property
    def is_active(self):
        return self.active

    @property
    def is_authenticated(self):
        return self.authenticated

    @property
    def is_anonymous(self):
        return self.anonymous


UNIQUE_USER = User(config.login.username, config.login.password)
ANONYMOUS_USER = User('anonymous', '', False, False, True)


def _assert_user_or_none(candidate: Any) -> Optional[User]:
    return candidate  # hack for typing


def get_current_user() -> User:
    return _assert_user_or_none(current_user) or ANONYMOUS_USER
