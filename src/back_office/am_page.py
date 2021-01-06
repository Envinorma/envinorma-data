from enum import Enum
from typing import List, Optional, Tuple

import dash_core_components as dcc
import dash_html_components as html
from dash.dash import Dash
from dash.development.base_component import Component

from back_office.parametrization_edition import (
    add_parametrization_edition_callbacks,
    make_am_parametrization_edition_component,
)
from back_office.structure_edition import add_structure_edition_callbacks, make_am_structure_edition_component
from back_office.utils import Page


class AMOperation(Enum):
    EDIT_STRUCTURE = 'edit_structure'
    EDIT_ANNOTATIONS = 'edit_annotations'
    EDIT_PARAMETRIZATION = 'edit_parametrization'


def _extract_am_id_and_operation(pathname: str) -> Tuple[str, Optional[AMOperation], str]:
    pieces = pathname.split('/')[1:]
    if len(pieces) == 0:
        raise ValueError('Unexpected')
    if len(pieces) == 1:
        return pieces[0], None, ''
    return pieces[0], AMOperation(pieces[1]), '/'.join(pieces[2:])


class _Status(Enum):
    PENDING_STRUCTURE_VALIDATION = 'pending-structure-validation'
    PENDING_ENRICHMENT = 'pending-enrichment'
    VALIDATED = 'validated'


def _get_am_status(am_id: str) -> _Status:
    if am_id == '0':
        return _Status.PENDING_STRUCTURE_VALIDATION
    if am_id == '1':
        return _Status.PENDING_ENRICHMENT
    if am_id == '2':
        return _Status.VALIDATED
    return _Status.PENDING_STRUCTURE_VALIDATION


def _get_buttons(am_id: str, operation: AMOperation, enabled: bool, button_text: str) -> Component:
    style = {'margin': '5px'}
    edit_button = html.Button('Éditer', disabled=not enabled, style=style, className='btn btn-primary')
    if enabled:
        edit_button = dcc.Link(
            edit_button,
            href=f'/arrete_ministeriel/{am_id}/{operation.value}',
        )
    validate_button = html.Button(button_text, disabled=not enabled, style=style, className='btn btn-primary')
    return html.P([edit_button, validate_button], style=dict(display='flex'))


def _build_component_based_on_status(am_id: str, am_status: _Status) -> Component:
    children: List[Component] = []
    children.append(html.H3('Edition de structure.'))
    children.append(
        _get_buttons(
            am_id,
            AMOperation.EDIT_STRUCTURE,
            am_status == am_status.PENDING_STRUCTURE_VALIDATION,
            'Valider la structure',
        )
    )
    children.append(html.H3('Edition de l\'enrichissement.'))
    children.append(
        _get_buttons(
            am_id,
            AMOperation.EDIT_PARAMETRIZATION,
            am_status == am_status.PENDING_ENRICHMENT,
            'Valider l\'enrichissement',
        )
    )
    return html.Div(children)


def _make_am_index_component(am_id: str) -> Component:
    am_status = _get_am_status(am_id)
    return _build_component_based_on_status(am_id, am_status)


def _router(pathname: str, parent_page: str) -> Component:
    print(pathname)
    am_id, operation_id, rest_of_path = _extract_am_id_and_operation(pathname)
    parent_page = parent_page + '/' + am_id
    if not operation_id:
        return _make_am_index_component(am_id)
    if operation_id == operation_id.EDIT_STRUCTURE:
        return make_am_structure_edition_component(am_id, parent_page)
    if operation_id == operation_id.EDIT_PARAMETRIZATION:
        return make_am_parametrization_edition_component(am_id)
    # if operation == operation.EDIT_PARAMETRIZATION_TODEL:
    #     return make_am_parametrization_edition_component_todel(am_id)
    raise NotImplementedError()


def _add_callbacks(app: Dash) -> None:
    add_structure_edition_callbacks(app)
    add_parametrization_edition_callbacks(app)


page = Page(_router, _add_callbacks)
