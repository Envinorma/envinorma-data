import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import unquote

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


def _extract_text_modifications(text: StructuredText) -> List[StructuredText]:
    applicability = _ensure_applicability(text.applicability)
    if applicability.modified:
        return [text]
    if not applicability.active:
        return []
    return [mod for sec in text.sections for mod in _extract_text_modifications(sec)]


def _extract_modifications(am: Optional[ArreteMinisteriel]) -> List[StructuredText]:
    if not am:
        return []
    return [mod for sec in am.sections for mod in _extract_text_modifications(sec)]


def _extract_text_inapplicabilities(text: StructuredText) -> List[StructuredText]:
    applicability = _ensure_applicability(text.applicability)
    if not applicability.active:
        return [text]
    if applicability.modified:
        return []
    return [inap for sec in text.sections for inap in _extract_text_inapplicabilities(sec)]


def _extract_inapplicabilities(am: Optional[ArreteMinisteriel]) -> List[StructuredText]:
    if not am:
        return []
    return [inap for sec in am.sections for inap in _extract_text_inapplicabilities(sec)]


@dataclass
class _PageData:
    path: str
    file_found: bool
    am: Optional[ArreteMinisteriel]
    modifications: List[StructuredText] = field(init=False)
    inapplicabilities: List[StructuredText] = field(init=False)

    def __post_init__(self):
        self.modifications = _extract_modifications(self.am)
        self.inapplicabilities = _extract_inapplicabilities(self.am)


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
            _title_component(text.title.text, text.id),
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


def _title_component(title: str, text_id: str) -> Component:
    style = {'position': 'relative', 'left': '-25px', 'margin-top': '30px'}
    return html.H5([html.A('⬆️ ', href='#'), html.B(title)], id=text_id, style=style)


def _raw_text_component(text: StructuredText, alert: Optional[Component]) -> Component:
    subsections = [_raw_text_component(section, None) for section in text.sections]
    components: List[Component] = []
    components.append(_title_component(text.title.text, text.id))
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
            _title_component(text.title.text, text.id),
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


def _inapplicabilities_component(inapplicabilities: List[StructuredText]) -> Component:
    list_ = (
        html.Ul([html.Li(html.A(ina.applicability.reason_inactive, href=f'#{ina.id}')) for ina in inapplicabilities])
        if inapplicabilities
        else 'Aucun paragraphes inapplicables'
    )
    return html.Div([html.H4('Paragraphes inapplicables'), list_])


def _modifications_component(modifications: List[StructuredText]) -> Component:
    list_ = (
        html.Ul([html.Li(html.A(mod.applicability.reason_modified, href=f'#{mod.id}')) for mod in modifications])
        if modifications
        else 'Aucune modifications.'
    )
    return html.Div([html.H4('Modifications'), list_])


def _main_component(page_data: _PageData) -> Component:
    am = _ensure_am(page_data.am)
    if not am.applicability.active:
        return html.P('AM is not applicable')
    return html.Div(
        [
            html.I(am.title.text),
            _modifications_component(page_data.modifications),
            _inapplicabilities_component(page_data.inapplicabilities),
            _get_sections_components(am.sections),
        ]
    )


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