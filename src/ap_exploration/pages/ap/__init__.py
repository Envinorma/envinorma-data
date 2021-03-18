from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component

from ap_exploration.data import Acte, ActeState, Etablissement, Prescription, PrescriptionStatus
from ap_exploration.db import fetch_acte, fetch_ap_prescriptions
from ap_exploration.pages.ap.add_prescriptions import page as add_prescriptions_page
from ap_exploration.routing import APOperation, Endpoint
from envinorma.back_office.components.am_component import table_to_component
from envinorma.back_office.components.table import ExtendedComponent, table_component
from envinorma.data.text_elements import Table, TextElement


def _href(acte_id: str) -> str:
    return f'/{Endpoint.AP}/id/{acte_id}/{APOperation.EDIT_PRESCRIPTIONS}'


def _element_to_component(element: TextElement) -> ExtendedComponent:
    if isinstance(element, Table):
        return table_to_component(element, None)
    if isinstance(element, str):
        return html.P(element)
    raise NotImplementedError(type(element))


def _prescription_status(status: PrescriptionStatus) -> Component:
    return html.P(html.Span(status.value, className='badge badge-success'))


def _buttons() -> Component:
    return html.Div(
        [html.Button('Éditer', className='btn btn-primary'), ' ', html.Button('Supprimer', className='btn btn-danger')],
        style={'text-align': 'right'},
    )


def _prescription(prescription: Prescription) -> Component:
    return html.Div(
        [
            html.H4(prescription.title),
            _prescription_status(prescription.status),
            *[_element_to_component(element) for element in prescription.content],
            _buttons(),
        ],
        style={
            'padding': '10px',
            'border': '1px solid rgba(0,0,0,.1)',
            'border-radius': '5px',
            'margin-bottom': '10px',
        },
    )


def _prescriptions_list(prescriptions: List[Prescription]) -> Component:
    return html.Div([_prescription(prescription) for prescription in prescriptions])


def _prescriptions(prescriptions: List[Prescription]) -> Component:
    table = _prescriptions_list(prescriptions) if prescriptions else html.P('Pas de prescriptions.')
    return html.Div([html.H3('Liste des prescriptions'), table])


def _acte_state(state: ActeState) -> Component:
    if state == ActeState.EN_VIGUEUR:
        return html.Span(state.value, className='badge bg-success', style={'color': 'white'})
    if state == ActeState.EN_PROJET:
        return html.Span(state.value, className='badge bg-warning')
    return html.Span(state.value, className='badge bg-danger', style={'color': 'white'})


def _table(ap: Acte) -> Component:
    raw_rows = [
        [html.Strong('Date de publication'), ap.date_acte],
        [html.Strong('Type'), ap.type.value],
        [html.Strong('État'), _acte_state(ap.state)],
        [html.Strong('Date d\'abgrogation'), ap.date_abrogation] if ap.date_abrogation else [],
        [html.Strong('Date d\'annulation'), ap.date_annulation] if ap.date_annulation else [],
        [html.Strong('Date d\'application'), ap.date_application] if ap.date_application else [],
        [html.Strong('Date de fin de validité'), ap.date_fin_validite] if ap.date_fin_validite else [],
        [html.Strong('Date de modification'), ap.date_modification] if ap.date_modification else [],
    ]
    rows = [row for row in raw_rows if row]
    return table_component([], rows)


def _etablissement_href(etablissement_id: str) -> str:
    return f'/{Endpoint.ETABLISSEMENT}/id/{etablissement_id}'


def _back_to_etablissement(etablissement: Etablissement) -> Component:
    return dcc.Link(
        f'< retour à l\'établissement {etablissement.nom_usuel}', href=_etablissement_href(etablissement.id)
    )


def _ap_layout(ap_id: str) -> Component:
    ap = fetch_acte(ap_id)
    return html.Div(
        [
            html.H1([ap.reference_acte or ap.type.value]),
            _back_to_etablissement(ap.etablissement),
            _table(ap),
            _prescriptions(fetch_ap_prescriptions(ap_id)),
            dcc.Link(html.Button('Éditer les prescriptions', className='btn btn-primary'), href=_href(ap_id)),
        ]
    )


def _callbacks(app: dash.Dash) -> None:
    add_prescriptions_page[1](app)


def _layout(ap_id: str, operation: Optional[str] = None) -> Component:
    if not operation:
        return _ap_layout(ap_id)
    operation_ = APOperation(operation)
    if operation_ == APOperation.EDIT_PRESCRIPTIONS:
        return add_prescriptions_page[0](ap_id)
    return html.P('Page inexistente.')


page = (_layout, _callbacks)
