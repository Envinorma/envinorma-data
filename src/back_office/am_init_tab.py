from typing import Any, Dict, List, Optional

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from lib.data import ArreteMinisteriel, am_to_text

from back_office.app_init import app
from back_office.components import ButtonState, link_button
from back_office.components.am_component import am_component
from back_office.components.summary_component import summary_component
from back_office.fetch_data import delete_initial_am
from back_office.routing import build_am_page
from back_office.utils import AMOperation

_DELETE_BUTTON = 'am-init-tab-delete-button'
_DELETE_OUTPUT = 'am-init-tab-delete-output'
_REDIRECT = 'am-init-tab-redirect'
_MODAL = 'am-init-tab-modal'
_CONFIRM_DELETE = 'am-init-tab-confirm-delete'
_AM_ID = 'am-init-tab-am-id'


def _delete_modal() -> Component:
    modal = dbc.Modal(
        [
            dbc.ModalHeader('Confirmation'),
            dbc.ModalBody('Êtes-vous sûr de vouloir supprimer le contenu de cet AM ? Cette action est irréversible.'),
            dbc.ModalFooter(html.Button('Supprimer', id=_CONFIRM_DELETE, className='ml-auto btn btn-danger')),
        ],
        id=_MODAL,
    )
    return html.Div(
        [html.Button('Supprimer', id=_DELETE_BUTTON, className='btn btn-danger'), modal],
        style={'display': 'inline-block'},
    )


def _buttons(am_page: str) -> Component:
    href = f'{am_page}/{AMOperation.INIT.value}'
    delete = _delete_modal()
    edit = link_button('Éditer', href, ButtonState.NORMAL_LINK)
    style = {
        'display': 'inline-block',
        'position': 'fixed',
        'bottom': '0px',
        'left': '25%',
        'z-index': '10',
        'width': '50%',
        'text-align': 'center',
        'padding-bottom': '10px',
        'padding-top': '10px',
        'margin': 'auto',
    }
    return html.Div([edit, delete], style=style)


def _initial_am_component(am: ArreteMinisteriel, am_page: str) -> Component:
    am_row = html.Div(
        [
            html.Div([summary_component(am_to_text(am), False)], className='col-3'),
            html.Div(am_component(am, [], 3), className='col-9'),
        ],
        className='row',
    )
    return html.Div([html.Div(id=_DELETE_OUTPUT), html.Div(id=_REDIRECT), am_row, _buttons(am_page)])


def am_init_tab(am_id: str, am: Optional[ArreteMinisteriel], am_page: str) -> Component:
    am_id_store = dcc.Store(id=_AM_ID, data=am_id)
    if not am:
        return dcc.Location(
            pathname=build_am_page(am_id) + '/' + AMOperation.INIT.value, id='am-init-tab-redir', refresh=True
        )
    component = _initial_am_component(am, am_page)
    return html.Div([component, am_id_store])


@app.callback(
    Output(_MODAL, 'is_open'),
    [Input(_DELETE_BUTTON, 'n_clicks'), Input(_CONFIRM_DELETE, 'n_clicks')],
    [State(_MODAL, 'is_open')],
    prevent_initial_call=True,
)
def _toggle_modal(n1, n2, is_open):
    if n1 or n2:
        return not is_open
    return is_open


def _delete_initial_am(am_id: str) -> None:
    delete_initial_am(am_id)


@app.callback(
    Output(_DELETE_OUTPUT, 'children'),
    [Input(_CONFIRM_DELETE, 'n_clicks')],
    State(_AM_ID, 'data'),
    prevent_initial_call=True,
)
def _confirm_deletion(nb_clicks: Optional[int], am_id: str) -> Component:
    if nb_clicks:
        _delete_initial_am(am_id)
        return dcc.Location(href=build_am_page(am_id) + '/' + AMOperation.INIT.value, id='am-init-tab-delete-redirect')
    return html.Div()
