import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import Input, MATCH, Output, State
from dash.development.base_component import Component
from lib.data import Applicability, ArreteMinisteriel, EnrichedString, StructuredText
from lib.paths import get_parametric_ams_folder

from back_office.app_init import app
from back_office.components.am_component import table_to_component
from back_office.components.summary_component import summary_component
from back_office.utils import AMOperation, RouteParsingError


def _get_collapse_id(text_id: Optional[str] = None) -> Dict[str, Any]:
    return {'type': 'display-am-collapse', 'text_id': text_id or MATCH}


def _get_button_id(text_id: Optional[str] = None) -> Dict[str, Any]:
    return {'type': 'display-am-previous-text', 'text_id': text_id or MATCH}


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


def _extract_text_warnings(text: StructuredText) -> List[Tuple[Applicability, str]]:
    applicability = _ensure_applicability(text.applicability)
    if applicability.warnings:
        return [(applicability, text.id)]
    return [inap for sec in text.sections for inap in _extract_text_warnings(sec)]


def _extract_warnings(am: Optional[ArreteMinisteriel]) -> List[Tuple[Applicability, str]]:
    if not am:
        return []
    return [el for sec in am.sections for el in _extract_text_warnings(sec)]


@dataclass
class _PageData:
    path: str
    file_found: bool
    am: Optional[ArreteMinisteriel]
    text: Optional[StructuredText] = field(init=False)
    warnings: List[Tuple[Applicability, str]] = field(init=False)

    def __post_init__(self):
        self.text = (
            StructuredText(EnrichedString(self.am.short_title), [], self.am.sections, Applicability())
            if self.am
            else None
        )
        self.warnings = _extract_warnings(self.am)


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


def _ensure_text(text: Optional[StructuredText]) -> StructuredText:
    if not text:
        raise ValueError('Text expected to exist')
    return text


def _ensure_applicability(applicability: Optional[Applicability]) -> Applicability:
    if not applicability:
        raise ValueError('applicability expected to exist')
    return applicability


def _alinea_to_component(alinea: EnrichedString) -> Component:
    if alinea.text:
        return html.P(alinea.text, className='' if alinea.active else 'inactive')
    if alinea.table:
        return table_to_component(alinea.table, None)
    return html.Span()


def _alineas_to_components(alineas: List[EnrichedString]) -> List[Component]:
    return [_alinea_to_component(alinea) for alinea in alineas]


def _warning_to_component(warning: str) -> Component:
    return html.Div(warning, className='alert alert-secondary')


def _warnings_to_components(warnings: List[str]) -> List[Component]:
    return [_warning_to_component(warning) for warning in warnings]


def _title_component(title: str, text_id: str, depth: int, active: bool) -> Component:
    className = 'inactive' if not active else ''
    if depth == 0:
        return html.Div([html.H4(title, id=text_id, className=className), html.Hr()], style={'margin-top': '30px'})
    return html.H5(title, id=text_id, className=className)


def _extract_lines(text: StructuredText) -> List[str]:
    alinea_lines = [al.text if not al.table else '*tableau*' for al in text.outer_alineas]
    section_lines = [li for sec in text.sections for li in _extract_lines(sec)]
    return [text.title.text] + alinea_lines + section_lines


def _previous_text_component(text: StructuredText) -> Component:
    component = html.Div([html.P(line, className='previous_version_alinea') for line in _extract_lines(text)])
    collapse = dbc.Collapse(component, id=_get_collapse_id(text.id), is_open=True)
    return html.Div(
        [
            html.Button('Version précédente', id=_get_button_id(text.id), className='btn btn-link'),
            collapse,
        ]
    )


def _text_component(text: StructuredText, depth: int, previous_version: Optional[StructuredText] = None) -> Component:
    previous_version_component = _previous_text_component(previous_version) if previous_version else html.Div()

    return html.Div(
        [
            _title_component(text.title.text, text.id, depth, text.applicability.active),
            *_warnings_to_components(text.applicability.warnings),
            *_alineas_to_components(text.outer_alineas),
            *[_get_text_component(sec, depth + 1) for sec in text.sections],
            previous_version_component,
        ]
    )


def _get_text_component(text: StructuredText, depth: int) -> Component:
    applicability = _ensure_applicability(text.applicability)
    if applicability.modified:
        if not applicability.previous_version:
            raise ValueError('Should not happen. Must have a previous_version when modified is True.')
        return _text_component(text, depth, applicability.previous_version)
    return _text_component(text, depth)


def _li(app: Applicability, id_: str) -> Component:
    badge = (
        html.Span('modification', className='badge bg-secondary', style={'color': 'white'})
        if app.modified
        else html.Span()
    )
    return html.Li([html.A(', '.join(app.warnings) + ' ', href=f'#{id_}'), badge])


def _warnings_component(apps: List[Tuple[Applicability, str]]) -> Component:
    list_ = html.Ul([_li(app, id_) for app, id_ in apps]) if apps else 'Aucune modifications.'
    return html.Div([html.H4('Modifications', style={'margin-top': '30px'}), html.Hr(), list_])


def _main_component(page_data: _PageData) -> Component:
    am = _ensure_am(page_data.am)
    text = _ensure_text(page_data.text)
    if not am.active:
        return html.P('L\'arrêté n\'est pas applicable.')
    return html.Div(
        [
            html.I(am.title.text),
            _warnings_component(page_data.warnings),
            _get_text_component(text, 0),
        ],
        style={'margin-top': '60px'},
    )


def _build_component(page_data: _PageData) -> Component:
    if not page_data.file_found:
        return _not_found_component(page_data.path)
    summary = summary_component(page_data.text, False) if page_data.text else html.Div()
    return html.Div(
        [html.Div(summary, className='col-3'), html.Div(_main_component(page_data), className='col-9')], className='row'
    )


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


@app.callback(
    Output(_get_collapse_id(), 'is_open'), Input(_get_button_id(), 'n_clicks'), State(_get_collapse_id(), 'is_open')
)
def _(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return False
