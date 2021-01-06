from typing import Any, Callable, Dict, List, Optional, Union

import dash
import dash_html_components as html
from dash.development.base_component import Component
from lib.data import load_am_data

_AM = load_am_data()
ID_TO_AM_MD = {am.cid: am for am in _AM.metadata if am.cid == 'JORFTEXT000026251890'}


class Page:
    def __init__(self, router: Callable[[str, str], Component], add_callbacks: Callable[[dash.Dash], None]) -> None:
        self.router: Callable[[str, str], Component] = router
        self.add_callbacks: Callable[[dash.Dash], None] = add_callbacks


def div(children: Union[List[Component], Component], style: Optional[Dict[str, Any]] = None) -> Component:
    return html.Div(children, style=style)
