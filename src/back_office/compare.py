import random
import traceback
from datetime import datetime
from typing import List, Optional, Set, Tuple

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from lib.am_structure_extraction import transform_arrete_ministeriel
from lib.data import AMSource, ArreteMinisteriel, extract_text_lines, load_legifrance_text
from lib.diff import (
    AddedLine,
    DiffLine,
    Mask,
    ModifiedLine,
    RemovedLine,
    TextDifferences,
    UnchangedLine,
    build_text_differences,
)
from lib.legifrance_API import LegifranceRequestError, get_legifrance_client, get_loda_via_cid

from back_office.app_init import app
from back_office.components import error_component, surline_text

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
    return dcc.DatePickerSingle(style={'padding': '0px', 'width': '100%'}, id=id_, date=initial_value)


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


def _load_legifrance_version(am_id: str, date: datetime) -> ArreteMinisteriel:
    client = get_legifrance_client()
    legifrance_current_version = load_legifrance_text(get_loda_via_cid(am_id, date, client))
    random.seed(legifrance_current_version.title)
    return transform_arrete_ministeriel(legifrance_current_version, am_id=am_id)


def _extract_lines(am: ArreteMinisteriel) -> List[str]:
    return [line for section in am.sections for line in extract_text_lines(section, 0)]


def _compute_am_diff(am_before: ArreteMinisteriel, am_after: ArreteMinisteriel) -> TextDifferences:
    lines_before = _extract_lines(am_before)
    lines_after = _extract_lines(am_after)
    return build_text_differences(lines_before, lines_after)


def _positions_to_surline(mask: Mask) -> Set[int]:
    return {i for i, el in enumerate(mask.elements) if el != el.UNCHANGED}


def _diff_rows(diff_line: DiffLine) -> List[html.Tr]:
    if isinstance(diff_line, UnchangedLine):
        return [html.Tr([html.Td(diff_line.content)] * 2)]
    if isinstance(diff_line, AddedLine):
        return [html.Tr([html.Td(''), html.Td(diff_line.content, className='table-success')])]
    if isinstance(diff_line, RemovedLine):
        return [html.Tr([html.Td(diff_line.content, className='table-danger'), html.Td('')])]
    if isinstance(diff_line, ModifiedLine):
        green = {'background-color': '#ff95a2'}
        text_before = surline_text(diff_line.content_before, _positions_to_surline(diff_line.mask_before), green)
        red = {'background-color': '#80da96'}
        text_after = surline_text(diff_line.content_after, _positions_to_surline(diff_line.mask_after), red)
        row_1 = html.Tr(
            [html.Td(text_before, className='table-danger'), html.Td(text_after, className='table-success')]
        )
        return [row_1]
    raise NotImplementedError(f'Unhandled type {diff_line}')


def _diff_component(diff: TextDifferences) -> Component:
    header: List[Component] = [html.Thead([html.Tr([html.Th('Version de référence'), html.Th('Version comparée')])])]
    rows: List[Component] = [row for line in diff.diff_lines for row in _diff_rows(line)]
    return html.Table(header + rows, className='table table-sm table-borderless diff')


def _diff(am_id: str, date_before: datetime, date_after: datetime) -> Component:
    am_before = _load_legifrance_version(am_id, date_before)
    am_after = _load_legifrance_version(am_id, date_after)
    diff = _compute_am_diff(am_before, am_after)
    return _diff_component(diff)


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
        [html.H3(f'Comparer deux versions d\'un arrêté.'), _form(am_id, date_before, date_after), html.Div(id=_DIFF)]
    )
