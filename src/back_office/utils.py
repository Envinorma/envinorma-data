import dash
from typing import Callable

from dash.development.base_component import Component
from lib.data import load_am_data

_AM = load_am_data()
ID_TO_AM_MD = {am.cid: am for am in _AM.metadata if am.cid == 'JORFTEXT000026251890'}


class Page:
    def __init__(self, router: Callable[[str], Component], add_callbacks: Callable[[dash.Dash], None]) -> None:
        self.router: Callable[[str], Component] = router
        self.add_callbacks: Callable[[dash.Dash], None] = add_callbacks
