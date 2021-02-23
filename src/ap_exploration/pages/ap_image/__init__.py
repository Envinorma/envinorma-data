import base64
import os
import random
import shutil
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import requests
from ap_exploration.db import load_ap_georisques_url
from ap_exploration.pages.ap_image.alto_to_html import (
    alto_page_to_grouped_lines,
    alto_page_to_grouped_paragraphs,
    alto_page_to_html,
    alto_pages_to_paragraphs,
    alto_pages_to_structured_text,
)
from ap_exploration.pages.ap_image.process import extract_alto_pages, load_step, start_process
from ap_exploration.routing import Page
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.back_office.components import error_component
from envinorma.back_office.utils import generate_id
from envinorma.config import config
from envinorma.data_build.georisques_data import GR_DOC_BASE_URL
from envinorma.io.alto import AltoPage

_UPLOAD = generate_id(__file__, 'upload-data')
_FILENAME_DONE = generate_id(__file__, 'filename-alto')
_INTERVAL = generate_id(__file__, 'interval')
_FILENAME_PDF = generate_id(__file__, 'filename-pdf')
_PROGRESS_BAR = generate_id(__file__, 'progress-bar')
_PROGRESS_BAR_WRAPPER = generate_id(__file__, 'progress-bar-wrapper')
_LOADER = generate_id(__file__, 'loader')
_DROPDOWN = generate_id(__file__, 'dropdown')
_BUTTON = generate_id(__file__, 'button')
_OCR_OUTPUT = generate_id(__file__, 'ocr-output')
_DOC_IDS = load_ap_georisques_url()
_PDF_AP_FOLDER = config.storage.ap_data_folder


def _page_tab_id(page_number: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'page-tab-number'), 'key': page_number}


def _page_id(page_number: Any) -> Dict[str, Any]:
    return {'type': generate_id(__file__, 'page-number'), 'key': page_number}


def _upload_component() -> Component:
    style = {
        'width': '100%',
        'height': '35px',
        'lineHeight': '35px',
        'borderWidth': '1px',
        'borderStyle': 'dashed',
        'borderRadius': '5px',
        'textAlign': 'center',
        'margin-bottom': '10px',
        'cursor': 'pointer',
    }
    return dcc.Upload(
        id=_UPLOAD, children=html.Div(['Glissez-déposez ou sélectionnez un fichier']), style=style, multiple=False
    )


def _options() -> List[Dict[str, Any]]:
    return [{'value': file_, 'label': file_} for file_ in os.listdir(_PDF_AP_FOLDER) if file_.endswith('.pdf')]


def _dropdown() -> Component:
    return dcc.Dropdown(options=_options(), id=_DROPDOWN)


def _button() -> Component:
    return html.Button('Tirer au hasard', id=_BUTTON, className='btn btn-primary', style={'width': '100%'})


def _progress() -> Component:
    progress = dbc.Progress(value=5, id=_PROGRESS_BAR, striped=True, animated=True, style={'height': '25px'})
    return html.Div(progress, hidden=True, id=_PROGRESS_BAR_WRAPPER, className='mt-3 mb-3')


def _card(content: Component, title: str) -> Component:
    return html.Div(
        html.Div([html.H5(title, className='card-title'), content], className='card-body'), className='card'
    )


def _upload_row() -> Component:
    col1 = html.Div([html.P('Uploadez un document'), _upload_component()])
    col2 = html.Div([html.P('Ou choisissez un fichier existant'), _dropdown()])
    col3 = html.Div([html.P('Ou choisir un document géorisques aléatoire'), _button()])
    cols = [html.Div(col1, className='col-4'), html.Div(col2, className='col-4'), html.Div(col3, className='col-4')]
    return _card(html.Div(cols, className='row'), 'Choisissez un fichier')


def _page() -> Component:
    return html.Div(
        [
            html.H1('PDF parsing'),
            _upload_row(),
            _progress(),
            dcc.Store(id=_FILENAME_PDF),
            dcc.Store(id=_FILENAME_DONE),
            dcc.Interval(id=_INTERVAL, interval=2000),
            html.Div('', id=_OCR_OUTPUT),
            html.Div(dbc.Spinner(html.Div(), id=_LOADER)),
        ]
    )


def _handle_uploaded_file(contents: str, filename: str) -> str:
    _, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    new_filename = os.path.join(_PDF_AP_FOLDER, filename)

    open(new_filename, 'wb').write(decoded)
    return new_filename


def _save_file(contents: str, filename: str) -> str:
    filename = _handle_uploaded_file(contents, filename)
    return filename


def _explain_word_confidence() -> Component:
    return html.P('L\'intensité de surlignage des mots est inversement proportionnelle à la confiance de détection.')


def _word_confidence_tab(pages: List[AltoPage]) -> Component:
    return html.Div(
        [_explain_word_confidence(), *[html.Div(alto_page_to_html(page, False), className='mb-3') for page in pages]]
    )


def _explain_grouping() -> Component:
    return html.P(
        'Les lignes sont surlignées en bleu, les textes (groupes de lig'
        'nes) en vert et les blocs composés (groupes de textes) en rouge.'
    )


def _paginate(pages: List[AltoPage]) -> Component:
    children = html.Ul(
        [
            html.Li(html.A(i, className='page-link', id=_page_tab_id(i - 1)), className='page-item')
            for i in range(1, len(pages) + 1)
        ],
        className='pagination pagination-sm',
    )
    return html.Div(
        [html.Nav(children, **{'aria-label': '...'})]
        + [html.Div(alto_page_to_grouped_lines(page), id=_page_id(i), hidden=i != 0) for i, page in enumerate(pages)]
    )


def _groups_tab(pages: List[AltoPage]) -> Component:
    return html.Div(
        [_explain_grouping()] + [html.Div(alto_page_to_html(page, True), className='mb-3') for page in pages]
    )


def _grouped_by_lines(pages: List[AltoPage]) -> Component:
    return html.Div([html.Div(alto_page_to_grouped_lines(page), className='mb-3') for page in pages])


def _grouped_by_paragraphs(pages: List[AltoPage]) -> Component:
    return html.Div([html.Div(alto_page_to_grouped_paragraphs(page), className='mb-3') for page in pages])


def _raw_text(pages: List[AltoPage]) -> Component:
    return alto_pages_to_paragraphs(pages)


def _structured_text(pages: List[AltoPage]) -> Component:
    return alto_pages_to_structured_text(pages)


def _top_margin(component: Component) -> Component:
    return html.Div(component, style={'margin-top': '15px'})


def _tabs(pages: List[AltoPage]) -> Component:
    return dbc.Tabs(
        [
            dbc.Tab(_top_margin(_word_confidence_tab(pages)), label='Output 1'),
            dbc.Tab(_top_margin(_groups_tab(pages)), label='Output 2'),
            dbc.Tab(_top_margin(_grouped_by_lines(pages)), label='Regroupement par lignes'),
            dbc.Tab(_top_margin(_grouped_by_paragraphs(pages)), label='Regroupement par paragraphes'),
            dbc.Tab(_top_margin(_raw_text(pages)), label='Texte extrait'),
            dbc.Tab(_top_margin(_structured_text(pages)), label='Texte structuré'),
        ],
        style={'margin-top': '5px'},
    )


def _seems_georisques_document_id(filename: str) -> bool:
    if not filename.endswith('.pdf'):
        return False
    without_extension = filename[:-4]
    if len(without_extension) != 36:
        return False
    if set(without_extension[4:]) - set('abcdef0123456789'):
        return False
    if without_extension[1] != '_' or without_extension[3] != '_':
        return False
    return True


def _load_and_display_alto(path: str) -> Component:
    pages = extract_alto_pages(path)
    children = []
    filename = path.split('/')[-1]
    if _seems_georisques_document_id(filename):
        link = html.A(
            'Lien vers le document géorisques', href=GR_DOC_BASE_URL + '/' + filename.replace('_', '/'), target='_blank'
        )
        children.append(html.Button(link, className='btn btn-link mb-3 mt-3'))
    children.append(_tabs(pages))
    return html.Div(children)


def download_document(url: str, output_filename: str) -> None:
    req = requests.get(url, stream=True)
    if req.status_code == 200:
        with open(output_filename, 'wb') as f:
            req.raw.decode_content = True
            shutil.copyfileobj(req.raw, f)


def _generate_output_filename(georisques_doc_id: str) -> str:
    return '_'.join(georisques_doc_id.split('/')[-3:])


def _download_random_document() -> str:
    random_doc = random.choice(_DOC_IDS)
    output_filename = os.path.join(_PDF_AP_FOLDER, _generate_output_filename(random_doc))
    input_url = GR_DOC_BASE_URL + '/' + random_doc
    download_document(input_url, output_filename)
    return output_filename


def _add_callbacks(app: dash.Dash):
    @app.callback(
        Output(_FILENAME_PDF, 'data'),
        Input(_UPLOAD, 'contents'),
        Input(_DROPDOWN, 'value'),
        Input(_BUTTON, 'n_clicks'),
        State(_UPLOAD, 'filename'),
        prevent_initial_call=True,
    )
    def save_file(contents, dropdown_value, _, name) -> Optional[str]:
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if trigger_id == _UPLOAD:
            if contents:
                return _save_file(contents, name)
        elif trigger_id == _DROPDOWN:
            return os.path.join(_PDF_AP_FOLDER, dropdown_value)
        elif trigger_id == _BUTTON:
            return _download_random_document()
        raise ValueError(f'Unknown trigger {trigger_id}')

    def _filename_trigger(triggered: List[Dict[str, Any]]) -> bool:
        if len(triggered) != 1:
            raise ValueError(f'Expecting one trigger, got {len(triggered)}')
        return _FILENAME_PDF in (triggered[0].get('prop_id') or '')

    @app.callback(
        Output(_FILENAME_DONE, 'data'),
        Output(_PROGRESS_BAR, 'children'),
        Output(_PROGRESS_BAR, 'value'),
        Output(_PROGRESS_BAR_WRAPPER, 'hidden'),
        Input(_INTERVAL, 'n_intervals'),
        Input(_FILENAME_PDF, 'data'),
        State(_PROGRESS_BAR_WRAPPER, 'hidden'),
        prevent_initial_call=True,
    )
    def _process_file(_, filename, progress_is_hidden):
        ctx = dash.callback_context
        filename_trigger = _filename_trigger(ctx.triggered)
        if filename_trigger and progress_is_hidden:
            start_process(filename)
            return dash.no_update, 'OCR en cours.', 5, False
        if not filename_trigger and not progress_is_hidden:
            step = load_step(filename)
            if step.done:
                return filename, 'Done.', 100, True
            return dash.no_update, step.messsage, int(step.advancement * 100), False
        raise PreventUpdate

    @app.callback(Output(_LOADER, 'children'), Output(_OCR_OUTPUT, 'children'), Input(_FILENAME_DONE, 'data'))
    def handle_new_pdf_filename(filename):
        if filename:
            try:
                return _load_and_display_alto(filename), html.Div()
            except Exception:
                print(traceback.format_exc())
                return html.Div(), error_component(traceback.format_exc())
        raise PreventUpdate


page: Page = (_page, _add_callbacks)
