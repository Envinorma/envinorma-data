import traceback
from dataclasses import replace
from typing import List, Optional, Tuple
from urllib.parse import unquote

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from bs4 import BeautifulSoup
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from lib.am_structure_extraction import extract_short_title
from lib.data import AMMetadata, ArreteMinisteriel, EnrichedString, StructuredText, Table, am_to_text, table_to_html
from lib.legifrance_API import LegifranceRequestError
from lib.parse_html import extract_text_elements
from lib.structure_extraction import TextElement, Title, build_structured_text, structured_text_to_text_elements

from back_office.app_init import app
from back_office.components import error_component, success_component
from back_office.fetch_data import load_initial_am, upsert_initial_am
from back_office.routing import build_am_page
from back_office.utils import ID_TO_AM_MD, AMOperation, RouteParsingError, extract_aida_am, extract_legifrance_am

_AM_TITLE = 'am-init-am-title'
_AM_CONTENT = 'am-init-am-content'
_FORM = 'am-init-form'
_AM_ID = 'am-init-am-id'
_AIDA_DOC = 'am-init-aida-doc'
_AIDA_SUBMIT = 'am-init-aida-submit'
_AIDA_FORM_OUTPUT = 'am-init-aida-form-output'
_LEGIFRANCE_ID = 'am-init-legifrance-doc'
_LEGIFRANCE_SUBMIT = 'am-init-legifrance-submit'
_LEGIFRANCE_FORM_OUTPUT = 'am-init-legifrance-form-output'
_SAVE_BUTTON = 'am-init-save-button'
_SAVE_OUTPUT = 'am-init-save-output'


def _parse_route(route: str) -> str:
    pieces = route.split('/')[1:]
    if len(pieces) != 2:
        raise RouteParsingError(f'Error parsing route {route}')
    am_id = pieces[0]
    try:
        operation = AMOperation(pieces[1])
    except ValueError:
        raise RouteParsingError(f'Error parsing route {route}')
    if operation != AMOperation.INIT:
        raise RouteParsingError(f'Error parsing route {route}')
    return am_id


def _legifrance_form(am_id: str) -> Component:
    return html.Div(
        [
            dcc.Input(
                id=_LEGIFRANCE_ID, value=am_id, className='form-control', style={'display': 'flex'}, disabled=True
            ),
            html.Button('Valider', id=_LEGIFRANCE_SUBMIT, className='btn btn-outline-secondary', n_clicks=0),
        ],
        className='input-group mb-3',
    )


def _aida_form(am_metadata: AMMetadata) -> Component:
    fetch_from_aida = html.Div(
        [
            dcc.Input(id=_AIDA_DOC, value=am_metadata.aida_page, className='form-control', style={'display': 'flex'}),
            html.Button('Valider', id=_AIDA_SUBMIT, className='btn btn-outline-secondary', n_clicks=0),
        ],
        className='input-group mb-3',
    )
    return fetch_from_aida


def _am_loaders(am_id: str) -> Component:
    return html.Div(
        [
            html.Div('Pas d\'arrêté pour le moment.', className='alert alert-primary'),
            html.H5('Charger depuis AIDA'),
            _aida_form(ID_TO_AM_MD[am_id]),
            dbc.Spinner(html.Div(), id=_AIDA_FORM_OUTPUT),
            html.H5('Charger depuis Légifrance'),
            _legifrance_form(am_id),
            dbc.Spinner(html.Div(), id=_LEGIFRANCE_FORM_OUTPUT),
        ],
        style={'margin-top': '80px'},
    )


def _text_to_elements(text: StructuredText) -> List[TextElement]:
    return structured_text_to_text_elements(text, 0)


def _element_to_str(element: TextElement) -> str:
    if isinstance(element, Title):
        return '#' * element.level + ' ' + element.text
    if isinstance(element, str):
        return element
    if isinstance(element, Table):
        return table_to_html(element)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _prepare_text_area_value(elements: List[TextElement]) -> str:
    return '\n'.join([_element_to_str(el) for el in elements])


def _extract_default_form_values(am: ArreteMinisteriel) -> Tuple[str, str]:
    return am.title.text, _prepare_text_area_value(_text_to_elements(am_to_text(replace(am, title=EnrichedString('')))))


def _save_button() -> Component:
    style = {
        'position': 'fixed',
        'bottom': '0px',
        'left': '0px',
        'width': '100%',
        'background-color': 'white',
        'padding-bottom': '10px',
        'padding-top': '10px',
        'text-align': 'center',
    }
    return html.Div(
        [
            html.Div(id=_SAVE_OUTPUT, className='container'),
            html.Button('Enregistrer', className='btn btn-primary', id=_SAVE_BUTTON),
        ],
        style=style,
    )


def _get_form(am: ArreteMinisteriel) -> Component:
    default_title, default_content = _extract_default_form_values(am)
    form_elements = [
        html.Label('Titre', htmlFor=_AM_TITLE, className='form-label'),
        html.Div(dcc.Textarea(id=_AM_TITLE, value=default_title, className='form-control')),
        html.Label('Contenu', htmlFor=_AM_CONTENT, className='form-label'),
        html.Div(
            dcc.Textarea(id=_AM_CONTENT, className='form-control', value=default_content, style={'min-height': '60vh'})
        ),
        _save_button(),
    ]
    return html.Div(form_elements, id=_FORM)


def _build_component(am_id: str, am: Optional[ArreteMinisteriel]) -> Component:
    if not am:
        return _am_loaders(am_id)
    return html.Div(_get_form(am), style={'margin-top': '60px'})


def _make_page(am_id: str) -> Component:
    return html.Div([_build_component(am_id, load_initial_am(am_id)), dcc.Store(id=_AM_ID, data=am_id)])


def _save_and_get_component(am_id: str, am: ArreteMinisteriel) -> Component:
    try:
        upsert_initial_am(am_id, am)
    except Exception:
        return error_component(f'Erreur inattendue lors de l\'enregristrement de l\'AM: \n{traceback.format_exc()}')
    return html.Div(
        [
            success_component('AM enregistré avec succès'),
            dcc.Location(pathname=build_am_page(am_id), id='am-init-tab-success-redirect'),
        ]
    )


def _parse_aida_page_and_save_am(page_id: str, am_id: str) -> Component:
    try:
        am = extract_aida_am(page_id, am_id)
    except Exception:
        return error_component(f'Erreur inattendue: \n{traceback.format_exc()}')
    if not am:
        return error_component(f'Aucun AM trouvé sur cette page.')
    return _save_and_get_component(am_id, am)


@app.callback(
    Output(_AIDA_FORM_OUTPUT, 'children'),
    Input(_AIDA_SUBMIT, 'n_clicks'),
    State(_AIDA_DOC, 'value'),
    State(_AM_ID, 'data'),
    prevent_initial_call=True,
)
def _build_am_from_aida(n_clicks, page_id, am_id: str) -> Component:
    if n_clicks >= 1:
        return _parse_aida_page_and_save_am(page_id, am_id)
    return html.Div()


def _fetch_parse_and_save_legifrance_text(am_id: str) -> Component:
    try:
        am = extract_legifrance_am(am_id)
    except LegifranceRequestError as exc:
        return error_component(f'Erreur lors de la récupération du text: {exc}')
    except Exception:
        return error_component(f'Erreur inattendue: \n{traceback.format_exc()}')
    return _save_and_get_component(am_id, am)


@app.callback(
    Output(_LEGIFRANCE_FORM_OUTPUT, 'children'),
    Input(_LEGIFRANCE_SUBMIT, 'n_clicks'),
    State(_AM_ID, 'data'),
    prevent_initial_call=True,
)
def _build_am_from_legifrance(n_clicks, am_id: str) -> Component:
    if n_clicks >= 1:
        return _fetch_parse_and_save_legifrance_text(am_id)
    return html.Div()


def _count_prefix_hashtags(line: str) -> int:
    for i, char in enumerate(line):
        if char != '#':
            return i
    return len(line)


def _build_title(str_: str) -> Title:
    level = _count_prefix_hashtags(str_)
    return Title(str_[level:].strip(), level=level)


def _is_empty(element: TextElement) -> bool:
    if isinstance(element, str) and not element.strip():
        return True
    return False


def _add_title(element: TextElement) -> TextElement:
    if isinstance(element, str) and element.startswith('#'):
        return _build_title(element)
    return element


def _extract_elements(am_content: str) -> List[TextElement]:
    soup = BeautifulSoup(am_content, 'html.parser')
    text_elements = extract_text_elements(soup)
    split_lines = [
        line
        for el in text_elements
        for line in (el.split('\n') if isinstance(el, str) else [el])
        if not _is_empty(line)
    ]
    final_elements = [_add_title(el) for el in split_lines]
    return final_elements


def _extract_structured_text(am_content: str) -> StructuredText:
    return build_structured_text(None, _extract_elements(am_content))


def _parse_and_save_new_am(am_id: str, am_title: str, am_content: str) -> Component:
    previous_am = load_initial_am(am_id)
    if not previous_am:
        return error_component('Aucun am existant trouvé. Commencez par charger un AM.')
    try:
        new_structured_text = _extract_structured_text(am_content)
        if new_structured_text.outer_alineas:
            new_sections = [
                StructuredText(EnrichedString(''), new_structured_text.outer_alineas, [], None)
            ] + new_structured_text.sections
        else:
            new_sections = new_structured_text.sections
        new_am = replace(
            previous_am,
            title=EnrichedString(am_title),
            short_title=extract_short_title(am_title),
            sections=new_sections,
        )
        upsert_initial_am(am_id, new_am)
    except Exception:
        return error_component(f'Erreur inattendue:\n{traceback.format_exc()}')
    return html.Div(
        [
            success_component('Enregistrement réussi.'),
            dcc.Location(pathname=build_am_page(am_id), id='am-init-tab-success-redirect-2'),
        ]
    )


@app.callback(
    Output(_SAVE_OUTPUT, 'children'),
    Input(_SAVE_BUTTON, 'n_clicks'),
    State(_AM_ID, 'data'),
    State(_AM_TITLE, 'value'),
    State(_AM_CONTENT, 'value'),
    prevent_initial_call=True,
)
def _save_new_am(n_clicks, am_id: str, am_title: str, am_content: str) -> Component:
    if n_clicks:
        return _parse_and_save_new_am(am_id, am_title, am_content)
    return html.Div()


def router(pathname: str) -> Component:
    pathname = unquote(pathname)
    try:
        am_id = _parse_route(pathname)
    except RouteParsingError as exc:
        return html.P(f'404 - Page introuvable - {str(exc)}')
    return _make_page(am_id)
