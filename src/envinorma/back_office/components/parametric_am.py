from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Set, Tuple

import dash
import dash_bootstrap_components as dbc
import dash_html_components as html
from dash.dependencies import MATCH, Input, Output, State
from dash.development.base_component import Component

from envinorma.back_office.components.am_component import table_to_component
from envinorma.back_office.components.diff import diff_component
from envinorma.back_office.components.summary_component import summary_component
from envinorma.back_office.utils import assert_str, compute_text_diff
from envinorma.data import Applicability, ArreteMinisteriel, EnrichedString, StructuredText
from envinorma.topics.patterns import TopicName

_Warning = Tuple[Applicability, str]


def _get_collapse_id(page_id: str, key: Optional[str]) -> Dict[str, Any]:
    return {'type': f'{page_id}-param-am-collapse', 'key': key or MATCH}


def _get_button_id(page_id: str, key: Optional[str]) -> Dict[str, Any]:
    return {'type': f'{page_id}-param-am-previous-text', 'key': key or MATCH}


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


def _diff(text: StructuredText, previous_text: StructuredText) -> Component:
    differences = compute_text_diff(previous_text, text)
    return diff_component(differences, 'Version initiale', 'Version modifiée')


def _previous_text_component(text: StructuredText, previous_text: StructuredText, page_id: str) -> Component:
    diff = html.Div(_diff(text, previous_text))
    collapse = dbc.Collapse(diff, id=_get_collapse_id(page_id, assert_str(previous_text.id)), is_open=True)
    return html.Div(
        [
            html.Button(
                'Version précédente', id=_get_button_id(page_id, assert_str(previous_text.id)), className='btn btn-link'
            ),
            collapse,
        ]
    )


def _text_component(text: StructuredText, depth: int, page_id: str) -> Component:
    applicability = text.applicability or Applicability()
    previous_version_component = html.Div()
    if applicability.modified:
        if not applicability.previous_version:
            raise ValueError('Should not happen. Must have a previous_version when modified is True.')
        previous_version_component = _previous_text_component(text, applicability.previous_version, page_id)
    return html.Div(
        [
            _title_component(text.title.text, text.id, depth, applicability.active),
            *_warnings_to_components(applicability.warnings),
            *_alineas_to_components(text.outer_alineas),
            *[_text_component(sec, depth + 1, page_id) for sec in text.sections],
            previous_version_component,
        ]
    )


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
            _text_component(text, 0, page_id),
        ]
    )


def _component(am: ArreteMinisteriel, text: StructuredText, warnings: List[_Warning], page_id: str) -> Component:
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


def _extract_topic(text: StructuredText) -> Optional[TopicName]:
    if not text.annotations:
        return None
    return text.annotations.topic


def _filter_text(text: StructuredText, topics_to_keep: Set[TopicName]) -> Optional[StructuredText]:
    if not text.sections:
        return text if _extract_topic(text) in topics_to_keep else None
    optional_sections = [_filter_text(sec, topics_to_keep) for sec in text.sections]
    sections = [sec for sec in optional_sections if sec]
    if not sections:
        return None
    return replace(text, sections=sections)


def _filter_am(am: ArreteMinisteriel, topics_to_keep: Set[TopicName]) -> ArreteMinisteriel:
    optional_sections = [_filter_text(sec, topics_to_keep) for sec in am.sections]
    sections = [sec for sec in optional_sections if sec]
    return replace(am, sections=sections)


def _build_component_data(am: ArreteMinisteriel, topics_to_keep: Optional[Set[TopicName]]) -> _ComponentData:
    if topics_to_keep is not None:
        return _ComponentData(_filter_am(am, topics_to_keep))
    return _ComponentData(am)


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


def parametric_am_component(
    am: ArreteMinisteriel, page_id: str, topics_to_keep: Optional[Set[TopicName]] = None
) -> Component:

    data = _build_component_data(am, topics_to_keep)
    return _component(data.am, data.text, data.warnings, page_id)
