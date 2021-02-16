from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from ap_exploration.data import Acte, ActeState, ActeType, Etablissement
from ap_exploration.db import fetch_etablissement, fetch_etablissement_actes, fetch_etablissement_to_actes
from ap_exploration.routing import Endpoint
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from envinorma.back_office.components.table import ExtendedComponent, table_component


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
    rows = [_text_row(etablissement, len(actes)) for etablissement, actes in etab_to_actes.items()]
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


def _etablissement(etablissement_id: str) -> Component:
    etablissement = fetch_etablissement(etablissement_id)
    actes = fetch_etablissement_actes(etablissement_id)
    return html.Div([html.H1(etablissement.nom_usuel), html.P(etablissement.code_s3ic), _etablissement_actes(actes)])


def _layout(etablissement_id: Optional[str] = None) -> Component:
    if etablissement_id is None:
        return _etablissement_list()
    return _etablissement(etablissement_id)


page = (_layout, None)
