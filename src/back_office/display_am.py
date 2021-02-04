import json
import os
from dataclasses import dataclass
from typing import Optional, Tuple
from urllib.parse import unquote

import dash_html_components as html
from dash.development.base_component import Component
from lib.data import ArreteMinisteriel
from lib.paths import get_parametric_ams_folder

from back_office.app_init import app
from back_office.components.parametric_am import parametric_am_component
from back_office.utils import AMOperation, RouteParsingError


def _parse_route(route: str) -> Tuple[str, str]:
    pieces = route.split('/')[1:]
    if len(pieces) != 3:
        raise RouteParsingError(f'Error parsing route {route}')
    am_id = pieces[0]
    try:
        operation = AMOperation(pieces[1])
    except ValueError:
        raise RouteParsingError(f'Error parsing route {route}')
    if operation != AMOperation.DISPLAY_AM:
        raise RouteParsingError(f'Error parsing route {route}')
    filename = pieces[2]
    return am_id, filename


@dataclass
class _PageData:
    path: str
    file_found: bool
    am: Optional[ArreteMinisteriel]


def _fetch_data(am_id: str, filename: str) -> _PageData:
    folder = get_parametric_ams_folder(am_id)
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        return _PageData(path=path, file_found=False, am=None)
    return _PageData(path=path, file_found=True, am=ArreteMinisteriel.from_dict(json.load(open(path))))


def _not_found_component(path: str) -> Component:
    return html.P(f'404 - file {path} does not exist.')


def _build_component(page_data: _PageData) -> Component:
    if not page_data.file_found or not page_data.am:
        return _not_found_component(page_data.path)
    return parametric_am_component(page_data.am, app)


def _make_page(am_id: str, filename: str) -> Component:
    page_data = _fetch_data(am_id, filename)
    return _build_component(page_data)


def router(pathname: str) -> Component:
    pathname = unquote(pathname)
    try:
        am_id, filename = _parse_route(pathname)
    except RouteParsingError as exc:
        return html.P(f'404 - Page introuvable - {str(exc)}')
    return _make_page(am_id, filename)
