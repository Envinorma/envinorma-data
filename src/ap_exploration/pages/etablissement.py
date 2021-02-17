from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from ap_exploration.data import Acte, ActeState, ActeType, Etablissement, Prescription, PrescriptionStatus
from ap_exploration.db import (
    fetch_aps_prescriptions,
    fetch_etablissement,
    fetch_etablissement_actes,
    fetch_etablissement_to_actes,
)
from ap_exploration.routing import Endpoint
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from envinorma.back_office.components.am_component import table_to_component
from envinorma.back_office.components.table import ExtendedComponent, table_component
from envinorma.data import Table
from envinorma.structure import TextElement


def _href(etablissement_id: str) -> str:
    return f'{Endpoint.ETABLISSEMENT}/id/{etablissement_id}'


def _text_row(etablissement: Etablissement, nb_actes: int) -> List[Union[str, Component]]:
    return [
        dcc.Link(etablissement.code_s3ic, href=_href(str(etablissement.id))),
        etablissement.nom_usuel,
        str(nb_actes),
    ]


def _etablissement_list() -> Component:
    headers = [['ID', 'Nom', 'Nb actes']]
    etab_to_actes = fetch_etablissement_to_actes()
    tuples = sorted(etab_to_actes.items(), key=lambda x: x[0].code_s3ic != '0065.06689')
    rows = [_text_row(etablissement, len(actes)) for etablissement, actes in tuples]
    return table_component(headers, rows)


def _acte_type(type_: ActeType) -> Component:
    return html.Span(type_.short(), className='badge bg-primary', style={'color': 'white'})


def _acte_state(state: ActeState) -> Component:
    if state == ActeState.EN_VIGUEUR:
        return html.Span(state.value, className='badge bg-success', style={'color': 'white'})
    if state == ActeState.EN_PROJET:
        return html.Span(state.value, className='badge bg-warning')
    return html.Span(state.value, className='badge bg-danger', style={'color': 'white'})


def _small(text: str) -> Component:
    return html.Span(text, style={'font-size': '0.8em'})


def _acte_href(acte_id: str) -> str:
    return f'/{Endpoint.AP}/id/{acte_id}'


def _acte_row(acte: Acte) -> List[Any]:
    return [
        dcc.Link(_small(acte.reference_acte or acte.type.value), href=_acte_href(str(acte.id))),
        _acte_type(acte.type),
        _acte_state(acte.state),
        _small(str(acte.date_acte) if acte.date_acte else ''),
        _small(str(acte.date_application) if acte.date_application else ''),
        _small(str(acte.date_modification) if acte.date_modification else ''),
        _small(str(acte.date_fin_validite) if acte.date_fin_validite else ''),
        _small(str(acte.date_annulation) if acte.date_annulation else ''),
        _small(str(acte.date_abrogation) if acte.date_abrogation else ''),
    ]


def _sort_acts(actes: List[Acte]) -> List[Acte]:
    return sorted(actes, key=lambda x: x.date_acte if x.date_acte else -1)


def _etablissement_actes(actes: List[Acte]) -> Component:
    rows = [_acte_row(acte) for acte in _sort_acts(actes)]
    headers: List[List[ExtendedComponent]] = [
        [
            _small('Nom'),
            _small('Type'),
            _small('Statut'),
            _small('Date acte'),
            _small('Application'),
            _small('Modification'),
            _small('Fin de validité'),
            _small('Annulation'),
            _small('Abrogation'),
        ]
    ]
    return table_component(headers, rows, 'table-sm')


def _prescription_status(status: PrescriptionStatus) -> Component:
    return html.Span(status.value, className='badge badge-success')


def _ap_date(ap: Acte) -> Component:
    name = f'{ap.type.short()} du {ap.date_acte}' if ap.date_acte else ap.type.short()
    return html.Span(name, className='badge badge-primary')


def _element_to_component(element: TextElement) -> ExtendedComponent:
    if isinstance(element, Table):
        return table_to_component(element, None)
    if isinstance(element, str):
        return html.P(element)
    raise NotImplementedError(type(element))


def _prescription(prescription: Prescription, ap: Optional[Acte]) -> Component:
    return html.Div(
        [
            html.P([_ap_date(ap) if ap else html.Div(), ' ', _prescription_status(prescription.status)]),
            html.H4(prescription.title),
            *[_element_to_component(element) for element in prescription.content],
        ],
        style={
            'padding': '10px',
            'border': '1px solid rgba(0,0,0,.1)',
            'border-radius': '5px',
            'margin-bottom': '10px',
        },
    )


def _prescriptions_list(prescriptions: List[Prescription], actes: Dict[str, Acte]) -> Component:
    return html.Div([_prescription(prescription, actes.get(prescription.ap_id)) for prescription in prescriptions])


def _prescriptions(prescriptions: List[Prescription], actes: Dict[str, Acte]) -> Component:
    table = _prescriptions_list(prescriptions, actes) if prescriptions else html.P('Pas de prescriptions.')
    return html.Div([html.H3('Liste des prescriptions'), table])


def _etablissement(etablissement_id: str) -> Component:
    etablissement = fetch_etablissement(etablissement_id)
    actes = fetch_etablissement_actes(etablissement_id)
    acte_id_to_acte = {acte.id: acte for acte in actes}
    prescriptions = fetch_aps_prescriptions(list(acte_id_to_acte))
    return html.Div(
        [
            html.H1([etablissement.nom_usuel, ' - ', etablissement.code_s3ic]),
            _etablissement_actes(actes),
            _prescriptions(prescriptions, acte_id_to_acte),
        ]
    )


def _layout(etablissement_id: Optional[str] = None) -> Component:
    if etablissement_id is None:
        return _etablissement_list()
    return _etablissement(etablissement_id)


page = (_layout, None)
