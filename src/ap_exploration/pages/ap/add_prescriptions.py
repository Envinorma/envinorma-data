import os
import traceback
from dataclasses import dataclass
from typing import Any, Counter, List, Union

import bs4
import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_editable_div as ded
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate

from ap_exploration.data import Acte, Prescription, PrescriptionStatus
from ap_exploration.db import add_prescriptions, fetch_acte
from ap_exploration.db.ap_sample import AP_FOLDER, APS
from ap_exploration.routing import APOperation, Endpoint
from envinorma.back_office.components import error_component
from envinorma.back_office.components.am_component import table_to_component
from envinorma.back_office.components.table import ExtendedComponent
from envinorma.back_office.utils import generate_id
from envinorma.data import StructuredText
from envinorma.data.text_elements import Linebreak, Table, TextElement, Title
from envinorma.io.open_document import extract_text_and_metadata
from envinorma.io.parse_html import extract_table_from_soup, merge_between_linebreaks
from envinorma.structure import structured_text_to_text_elements

_FILE_DROPDOWN = generate_id(__file__, 'file-dropdown')
_TEXT_AREA = generate_id(__file__, 'text-area')
_EDITABLE_DIV = generate_id(__file__, 'editable-div')
_SAVE_BUTTON = generate_id(__file__, 'save-button')
_SAVE_OUTPUT = generate_id(__file__, 'save-output')
_REDIRECT = generate_id(__file__, 'redirect')
_AP_ID = generate_id(__file__, 'ap_id')


def _href(acte_id: str) -> str:
    return f'/{Endpoint.AP}/id/{acte_id}/{APOperation.EDIT_PRESCRIPTIONS}'


def _dropdown() -> Component:
    options = [{'label': x, 'value': x} for x in APS]
    return dcc.Dropdown(id=_FILE_DROPDOWN, options=options)


def _save_button() -> Component:
    return html.Button('Enregistrer', id=_SAVE_BUTTON, className='btn btn-primary', style={'margin-top': '5px'})


def _acte_href(acte_id: str) -> str:
    return f'/{Endpoint.AP}/id/{acte_id}'


def _back_to_actes(ap: Acte) -> Component:
    return dcc.Link(f'< retour', href=_acte_href(ap.id))


def _layout(ap_id: str) -> Component:
    ap = fetch_acte(ap_id)
    return html.Div(
        [
            html.H1(ap.reference_acte or ap.type.value),
            _back_to_actes(ap),
            html.H4('Charger un document'),
            _dropdown(),
            html.Div(id=_TEXT_AREA),
            html.Div(id=_SAVE_OUTPUT),
            dcc.Store(id=_AP_ID, data=ap_id),
        ]
    )


def _new_prescription() -> ExtendedComponent:
    return html.Span('prescription', className='badge bg-primary', style={'color': 'white'})


def _element_to_component(element: TextElement) -> ExtendedComponent:
    if isinstance(element, Table):
        return table_to_component(element, None)
    if isinstance(element, str):
        return html.P(element)
    if isinstance(element, Title):
        return html.Div([_new_prescription(), html.H4(element.text)])
    if isinstance(element, Linebreak):
        return html.Br()
    raise NotImplementedError(type(element))


def _prebuild_prescriptions(text: StructuredText) -> List[ExtendedComponent]:
    text_elements = structured_text_to_text_elements(text)
    return [_element_to_component(element) for element in text_elements]


def _create_editable_text(text: StructuredText) -> Component:
    return html.Div(
        [
            ded.EditableDiv(
                _prebuild_prescriptions(text),
                id=_EDITABLE_DIV,
                style={'padding': '10px', 'border': '1px solid rgba(0,0,0,.1)', 'border-radius': '5px'},
            ),
            _save_button(),
        ]
    )


def _extract_from_odt(filename: str) -> Component:
    full_filename = os.path.join(AP_FOLDER, filename)
    try:
        extracted = extract_text_and_metadata(full_filename)
        if not extracted.text:
            return error_component(f'Erreur pendant l\'extraction: {extracted.error}')
        return _create_editable_text(extracted.text)
    except Exception:
        return error_component(traceback.format_exc())


def _back_to_ap_href(ap_id: str) -> str:
    return f'/{Endpoint.AP}/id/{ap_id}'


@dataclass
class _PrescriptionBeginMark:
    pass


_TextElement = Union[TextElement, _PrescriptionBeginMark]


def _extract_elements_from_soup(tag: Any) -> List[_TextElement]:
    if isinstance(tag, str):
        return [str(tag)]
    if isinstance(tag, bs4.Tag):
        if tag.name == 'span':
            if 'badge' in tag.attrs.get('class') or '':
                return [_PrescriptionBeginMark()]
        if tag.name == 'br':
            return [Linebreak()]
        if tag.name == 'table':
            return [extract_table_from_soup(tag)]
        children = [element for tag in tag.children for element in _extract_elements_from_soup(tag)]
        if tag.name in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            children = [Linebreak(), *children, Linebreak()]
        return children
    if tag is None:
        return []
    raise ValueError(f'Unexpected type {type(tag)}')


def _ensure_tables_or_strs(elements: List[TextElement]) -> None:
    res = Counter([type(x) for x in elements])
    for type_ in [Table, str]:
        del res[type_]
    if res:
        raise ValueError(f'Elements should be titles and strings, also found {res}')


def _elements_to_prescription(ap_id: str, elements: List[TextElement]) -> Prescription:
    _ensure_tables_or_strs(elements)
    if not elements:
        return Prescription(ap_id=ap_id, title='', content=[], status=PrescriptionStatus.EN_VIGUEUR)
    first_element = elements[0]
    title = first_element if isinstance(first_element, str) else ''
    content = elements[1:] if isinstance(first_element, str) else elements  # first line is kept if not used as title
    return Prescription(ap_id=ap_id, title=title, content=content, status=PrescriptionStatus.EN_VIGUEUR)


def _split_between_prescription_marks(elements: List[_TextElement]) -> List[List[TextElement]]:
    groups: List[List[TextElement]] = []
    for element in elements:
        if isinstance(element, _PrescriptionBeginMark):
            groups.append([])
            continue
        if groups:  # initial elements are not added
            groups[-1].append(element)
    return groups


def _extract_prescriptions(ap_id: str, inner_html: str) -> List[Prescription]:
    soup = bs4.BeautifulSoup(inner_html, 'html.parser')
    elements = _extract_elements_from_soup(soup)
    element_groups = _split_between_prescription_marks(elements)
    return [_elements_to_prescription(ap_id, merge_between_linebreaks(group)) for group in element_groups if group]


def _extract_and_dump_prescriptions(ap_id: str, inner_html: str) -> Component:
    try:
        prescriptions = _extract_prescriptions(ap_id, inner_html)
        add_prescriptions(ap_id, prescriptions)
    except Exception:
        return error_component(traceback.format_exc())
    return dcc.Location(href=_back_to_ap_href(ap_id), id=_REDIRECT)


def _callbacks(app: dash.Dash) -> None:
    @app.callback(Output(_TEXT_AREA, 'children'), Input(_FILE_DROPDOWN, 'value'), prevent_initial_call=True)
    def _init_text_area(filename: str) -> Component:
        if not filename:
            raise PreventUpdate
        if filename.endswith('.odt'):
            return _extract_from_odt(filename)
        return error_component('Format non supporté.')

    @app.callback(
        Output(_SAVE_OUTPUT, 'children'),
        Input(_SAVE_BUTTON, 'n_clicks'),
        State(_AP_ID, 'data'),
        State(_EDITABLE_DIV, 'value'),
        prevent_initial_call=True,
    )
    def _save_prescriptions(_, ap_id: str, inner_html) -> Component:
        if not inner_html:
            raise PreventUpdate
        return _extract_and_dump_prescriptions(ap_id, inner_html)


page = (_layout, _callbacks)
