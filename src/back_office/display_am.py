import json
import os
from urllib.parse import unquote
from dataclasses import dataclass
from typing import List, Optional, Tuple

import dash_html_components as html
from dash.development.base_component import Component
from lib.data import Applicability, ArreteMinisteriel, EnrichedString, StructuredText
from lib.paths import get_parametric_ams_folder

from back_office.components.am_component import table_to_component
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


def _ensure_am(am: Optional[ArreteMinisteriel]) -> ArreteMinisteriel:
    if not am:
        raise ValueError('AM expected to exist')
    return am


def _ensure_applicability(applicability: Optional[Applicability]) -> Applicability:
    if not applicability:
        raise ValueError('applicability expected to exist')
    return applicability


def _inactive_text_component(text: StructuredText) -> Component:
    return html.Div(
        [
            html.P(html.B(text.title.text)),
            html.Div(
                f'Paragraphe non applicable : {text.applicability.reason_inactive}', className='alert alert-primary'
            ),
        ]
    )


def _alinea_to_component(alinea: EnrichedString) -> Component:
    if alinea.text:
        return html.P(alinea.text)
    if alinea.table:
        return table_to_component(alinea.table, None)
    return html.Span()


def _alineas_to_components(alineas: List[EnrichedString]) -> List[Component]:
    return [_alinea_to_component(alinea) for alinea in alineas]


def _raw_text_component(text: StructuredText, alert: Optional[Component]) -> Component:
    subsections = [_raw_text_component(section, None) for section in text.sections]
    components: List[Component] = []
    components.append(html.P(html.B(text.title.text)))
    if alert:
        components.append(alert)
    components.extend(_alineas_to_components(text.outer_alineas))
    components.extend(subsections)
    return html.Div(components)


def _modified_text_component(text: StructuredText) -> Component:
    return _raw_text_component(
        text, html.Div(f'Paragraphe modifié : {text.applicability.reason_modified}', className='alert alert-primary')
    )


def _active_text_component(text: StructuredText) -> Component:
    return html.Div(
        [
            html.P(html.B(text.title.text)),
            *_alineas_to_components(text.outer_alineas),
            _get_sections_components(text.sections),
        ]
    )


def _get_text_component(text: StructuredText) -> Component:
    applicability = _ensure_applicability(text.applicability)
    if not applicability.active:
        return _inactive_text_component(text)
    if applicability.modified:
        return _modified_text_component(text)
    return _active_text_component(text)


def _get_sections_components(sections: List[StructuredText]) -> Component:
    return html.Div([_get_text_component(section) for section in sections])


def _main_component(page_data: _PageData) -> Component:
    am = _ensure_am(page_data.am)
    if not am.applicability.active:
        return html.P('AM is not applicable')
    return html.Div([html.H4(am.title.text), _get_sections_components(am.sections)])


def _build_component(page_data: _PageData) -> Component:
    if not page_data.file_found:
        return _not_found_component(page_data.path)
    return _main_component(page_data)


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
