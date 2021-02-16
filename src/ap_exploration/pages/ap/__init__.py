from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from ap_exploration.data import Prescription
from ap_exploration.db import fetch_acte, fetch_ap_prescriptions
from ap_exploration.pages.ap.add_prescriptions import page as add_prescriptions_page
from ap_exploration.routing import APOperation, Endpoint
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from envinorma.back_office.components.am_component import table_to_component
from envinorma.back_office.components.table import ExtendedComponent
from envinorma.data import Table
from envinorma.structure import TextElement


def _href(acte_id: str) -> str:
    return f'/{Endpoint.AP}/id/{acte_id}/{APOperation.EDIT_PRESCRIPTIONS}'


def _element_to_component(element: TextElement) -> ExtendedComponent:
    if isinstance(element, Table):
        return table_to_component(element, None)
    if isinstance(element, str):
        return html.P(element)
    raise NotImplementedError(type(element))


def _prescription(prescription: Prescription) -> Component:
    return html.Div(
        [html.H4(prescription.title), *[_element_to_component(element) for element in prescription.content]]
    )


def _prescriptions(prescriptions: List[Prescription]) -> Component:
    return (
        html.Div([_prescription(pres) for pres in prescriptions]) if prescriptions else html.P('Pas de prescriptions.')
    )


def _ap_layout(ap_id: str) -> Component:
    ap = fetch_acte(ap_id)
    return html.Div(
        [
            html.H1(ap.reference_acte or ap.type.value),
            html.P(ap.date_acte),
            dcc.Link(html.Button('Editer les prescriptions', className='btn btn-primary'), href=_href(ap_id)),
            _prescriptions(fetch_ap_prescriptions(ap_id)),
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
