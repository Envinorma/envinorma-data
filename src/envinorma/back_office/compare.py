import traceback
from datetime import datetime
from typing import List, Optional, Set, Tuple

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate

from envinorma.back_office.components import error_component
from envinorma.back_office.components.diff import diff_component
from envinorma.back_office.routing import Page
from envinorma.back_office.utils import compute_am_diff, extract_legifrance_am
from legifrance.legifrance_API import LegifranceRequestError

_PREFIX = __file__.split('/')[-1].replace('.py', '').replace('_', '-')
_DATE_BEFORE = f'{_PREFIX}-before-date'
_DATE_AFTER = f'{_PREFIX}-after-date'
_AM_ID = f'{_PREFIX}-am-id'
_FORM_OUTPUT = f'{_PREFIX}-form-output'
_SUBMIT = f'{_PREFIX}-submit'
_DIFF = f'{_PREFIX}-diff'


class _FormError(Exception):
    pass


def _extract_date(date_: str) -> datetime:
    return datetime.strptime(date_, '%Y-%m-%d')


def _date_to_str(date_: datetime) -> str:
    return date_.strftime('%Y-%m-%d')


def _date_picker(id_: str, initial_date: Optional[datetime]) -> Component:
    initial_value = _date_to_str(initial_date) if initial_date else None
    return dcc.DatePickerSingle(
        style={'padding': '0px', 'width': '100%'},
        id=id_,
        date=initial_value,
        display_format='DD/MM/YYYY',
        placeholder=None,
    )


def _before_date(date: Optional[datetime]) -> Component:
    return html.Div(
        [html.Label('Date de la version de référence', htmlFor=_DATE_BEFORE), _date_picker(_DATE_BEFORE, date)],
        className='col-md-12',
    )


def _after_date(date: Optional[datetime]) -> Component:
    return html.Div(
        [html.Label('Date de la version à comparer', htmlFor=_DATE_AFTER), _date_picker(_DATE_AFTER, date)],
        className='col-md-12',
    )


def _am_id(am_id: Optional[str]) -> Component:
    return html.Div(
        [
            html.Label('CID de l\'arrêté ministériel', htmlFor=_AM_ID),
            dcc.Input(value=am_id, id=_AM_ID, className='form-control'),
        ],
        className='col-md-12',
    )


def _diff(am_id: str, date_before: datetime, date_after: datetime) -> Component:
    am_before = extract_legifrance_am(am_id, date_before)
    am_after = extract_legifrance_am(am_id, date_after)
    diff = compute_am_diff(am_before, am_after)
    return diff_component(diff, 'Version de référence', 'Version comparée')


def _form(am_id: Optional[str], date_before_str: Optional[str], date_after_str: Optional[str]) -> Component:
    date_before = _extract_date(date_before_str) if date_before_str else None
    date_after = _extract_date(date_after_str) if date_after_str else None
    margin = {'margin-top': '10px', 'margin-bottom': '10px'}
    return html.Div(
        [
            _am_id(am_id),
            _before_date(date_before),
            _after_date(date_after),
            html.Div(id=_FORM_OUTPUT, style=margin, className='col-md-12'),
            html.Div(html.Button('Valider', className='btn btn-primary', id=_SUBMIT), className='col-12', style=margin),
        ],
        className='row g-3',
    )


def _safe_handle_submit(am_id: Optional[str], date_before: Optional[str], date_after: Optional[str]) -> Component:
    if not date_before or not date_after:
        raise _FormError('Les deux dates doivent être définies.')
    if not am_id:
        raise _FormError('Le CID de l\'arrêté doit être renseigné.')
    return _diff(am_id, _extract_date(date_before), _extract_date(date_after))


def _callbacks(app: Dash) -> None:
    @app.callback(
        Output(_FORM_OUTPUT, 'children'),
        Output(_DIFF, 'children'),
        Input(_SUBMIT, 'n_clicks'),
        State(_AM_ID, 'value'),
        State(_DATE_BEFORE, 'date'),
        State(_DATE_AFTER, 'date'),
    )
    def _handle_sumbit(n_clicks, am_id, date_before, date_after) -> Tuple[Component, Component]:
        if not n_clicks:
            if not (am_id and date_before and date_after):  # parameters defined in URL
                raise PreventUpdate
        try:
            return html.Div(), _safe_handle_submit(am_id, date_before, date_after)
        except _FormError as exc:
            return error_component(f'Erreur dans le formulaire: {str(exc)}'), html.Div()
        except LegifranceRequestError as exc:
            return error_component(f'Erreur dans l\'API Légifrance: {str(exc)}'), html.Div()
        except Exception:
            return error_component(f'Erreur inattendue:\n{traceback.format_exc()}'), html.Div()


def layout(
    am_id: Optional[str] = None, date_before: Optional[str] = None, date_after: Optional[str] = None
) -> Component:
    return html.Div(
        [
            html.H3(f'Comparer deux versions d\'un arrêté.'),
            _form(am_id, date_before, date_after),
            dbc.Spinner(html.Div(id=_DIFF)),
        ]
    )


PAGE = Page(layout, _callbacks)
