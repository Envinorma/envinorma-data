from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
from back_office.components.am_component import table_to_component
from back_office.components.summary_component import summary_component
from dash.dependencies import MATCH, Input, Output, State
from dash.development.base_component import Component
from lib.data import Applicability, ArreteMinisteriel, EnrichedString, StructuredText

_Warning = Tuple[Applicability, str]


def _get_collapse_id(page_id: str, key: Optional[str]) -> Dict[str, Any]:
    return {'type': f'{page_id}-param-am-collapse', 'key': key or MATCH}


def _get_button_id(page_id: str, key: Optional[str]) -> Dict[str, Any]:
    return {'type': f'{page_id}-param-am-previous-text', 'key': key or MATCH}


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


def _previous_text_component(text: StructuredText, page_id: str) -> Component:
    component = html.Div([html.P(line, className='previous_version_alinea') for line in _extract_lines(text)])
    collapse = dbc.Collapse(component, id=_get_collapse_id(page_id, text.id), is_open=True)
    return html.Div(
        [
            html.Button('Version précédente', id=_get_button_id(page_id, text.id), className='btn btn-link'),
            collapse,
        ]
    )


def _text_component(
    text: StructuredText, depth: int, previous_version: Optional[StructuredText], page_id: str
) -> Component:
    previous_version_component = _previous_text_component(previous_version, page_id) if previous_version else html.Div()
    applicability = text.applicability or Applicability()
    return html.Div(
        [
            _title_component(text.title.text, text.id, depth, applicability.active),
            *_warnings_to_components(applicability.warnings),
            *_alineas_to_components(text.outer_alineas),
            *[_get_text_component(sec, depth + 1, page_id) for sec in text.sections],
            previous_version_component,
        ]
    )


def _get_text_component(text: StructuredText, depth: int, page_id: str) -> Component:
    applicability = text.applicability or Applicability()
    if applicability.modified:
        if not applicability.previous_version:
            raise ValueError('Should not happen. Must have a previous_version when modified is True.')
        return _text_component(text, depth, applicability.previous_version, page_id)
    return _text_component(text, depth, None, page_id)


def _li(app: Applicability, id_: str) -> Component:
    badge = (
        html.Span('modification', className='badge bg-secondary', style={'color': 'white'})
        if app.modified
        else html.Span()
    )
    return html.Li([html.A(', '.join(app.warnings) + ' ', href=f'#{id_}'), badge])


def _warnings_component(apps: List[_Warning]) -> Component:
    list_ = html.Ul([_li(app, id_) for app, id_ in apps]) if apps else 'Aucune modifications.'
    return html.Div([html.H4('Modifications', style={'margin-top': '30px'}), html.Hr(), list_])


def _external_links(am: ArreteMinisteriel) -> Component:
    if am.aida_url and am.legifrance_url:
        return html.P(
            [
                html.A('Consulter sur AIDA', href=am.aida_url, target='_blank'),
                html.A('Consulter sur Légifrance', href=am.legifrance_url, target='_blank', className='ml-3'),
            ],
            className='mb-5',
        )
    return html.Div()


def _main_component(am: ArreteMinisteriel, text: StructuredText, warnings: List[_Warning], page_id: str) -> Component:
    if not am.active:
        return html.P('L\'arrêté n\'est pas applicable.')
    return html.Div(
        [
            html.P(html.I(am.title.text)),
            _external_links(am),
            _warnings_component(warnings),
            _get_text_component(text, 0, page_id),
        ]
    )


def _component(am: ArreteMinisteriel, text: StructuredText, warnings: List[_Warning], page_id) -> Component:
    summary = summary_component(text, True)
    return html.Div(
        [
            html.Div(summary, className='col-3'),
            html.Div(_main_component(am, text, warnings, page_id), className='col-9'),
        ],
        style={'margin': '0px'},
        className='row',
    )


def _extract_text_warnings(text: StructuredText) -> List[_Warning]:
    applicability = text.applicability or Applicability()
    if applicability.warnings:
        return [(applicability, text.id)]
    return [inap for sec in text.sections for inap in _extract_text_warnings(sec)]


def _extract_warnings(am: Optional[ArreteMinisteriel]) -> List[_Warning]:
    if not am:
        return []
    return [el for sec in am.sections for el in _extract_text_warnings(sec)]


@dataclass
class _ComponentData:
    am: ArreteMinisteriel
    text: StructuredText = field(init=False)
    warnings: List[_Warning] = field(init=False)

    def __post_init__(self):
        self.text = StructuredText(EnrichedString(self.am.short_title), [], self.am.sections, Applicability())
        self.warnings = _extract_warnings(self.am)


def parametric_am_callbacks(app: dash.Dash, page_id: str) -> None:
    @app.callback(
        Output(_get_collapse_id(page_id, None), 'is_open'),
        Input(_get_button_id(page_id, None), 'n_clicks'),
        State(_get_collapse_id(page_id, None), 'is_open'),
        prevent_initial_call=True,
    )
    def _(n_clicks, is_open):
        if n_clicks:
            return not is_open
        return False


def parametric_am_component(am: ArreteMinisteriel, page_id: str) -> Component:
    data = _ComponentData(am)
    return _component(data.am, data.text, data.warnings, page_id)
