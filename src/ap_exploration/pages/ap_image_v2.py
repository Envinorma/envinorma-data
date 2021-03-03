import base64
import random
import traceback
from typing import Any, Dict, List, Optional

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from ap_exploration.db.ap import (
    SAMPLE_DOC_IDS,
    APExtractionStep,
    download_georisques_document,
    dump_ap_extraction_step,
    georisques_full_url,
    has_ap_extraction_step,
    load_ap,
    load_ap_extraction_step,
    load_document_ids,
    save_document,
    seems_georisques_document_id,
)
from ap_exploration.pages.ap_image.build_ap import ArretePrefectoral
from ap_exploration.pages.ap_image.components.upload_row import upload_row
from ap_exploration.pages.ap_image.process import start_ap_extraction_process
from ap_exploration.routing import Page
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.back_office.components import error_component
from envinorma.back_office.components.am_component import table_to_component
from envinorma.back_office.utils import generate_id
from envinorma.data import Table
from envinorma.structure import TextElement, Title

_UPLOAD = generate_id(__file__, 'upload-data')
_PROCESSING_DONE = generate_id(__file__, 'processing-done')
_INTERVAL = generate_id(__file__, 'interval')
_DOCUMENT_ID = generate_id(__file__, 'document-id')
_PROGRESS_BAR = generate_id(__file__, 'progress-bar')
_PROGRESS_BAR_WRAPPER = generate_id(__file__, 'progress-bar-wrapper')
_LOADER = generate_id(__file__, 'loader')
_DROPDOWN = generate_id(__file__, 'dropdown')
_BUTTON = generate_id(__file__, 'button')
_OCR_OUTPUT = generate_id(__file__, 'ocr-output')


def _progress() -> Component:
    progress = dbc.Progress(value=5, id=_PROGRESS_BAR, striped=True, animated=True, style={'height': '25px'})
    return html.Div(progress, hidden=True, id=_PROGRESS_BAR_WRAPPER, className='mt-3 mb-3')


def _page() -> Component:
    return html.Div(
        [
            html.H1('PDF parsing'),
            upload_row(_UPLOAD, _BUTTON, _DROPDOWN, load_document_ids()),
            _progress(),
            dcc.Store(id=_DOCUMENT_ID),
            dcc.Store(id=_PROCESSING_DONE),
            dcc.Interval(id=_INTERVAL, interval=2000),
            html.Div('', id=_OCR_OUTPUT),
            html.Div(dbc.Spinner(html.Div(), id=_LOADER)),
        ]
    )


def _handle_uploaded_file(contents: str, filename: str) -> str:
    _, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    document_id = filename.split('.')[0]
    save_document(document_id, decoded)
    return document_id


def _get_html_heading_classname(level: int) -> type:
    if level <= 6:
        return getattr(html, f'H{level}')
    return html.H6


def _title_to_component(title: Title, smallest_level: int) -> Component:
    if title.level == 0:
        return html.P(title.text)
    cls_ = _get_html_heading_classname(title.level + smallest_level - 1)
    if title.id:
        title_component = cls_(title.text, id=title.id)
    else:
        title_component = cls_(title.text)
    return title_component


def _make_component(element: TextElement, smallest_level: int) -> Component:
    if isinstance(element, Table):
        return table_to_component(element, None)
    if isinstance(element, Title):
        return _title_to_component(element, smallest_level)
    if isinstance(element, str):
        return html.P(element)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _ap_component(ap: ArretePrefectoral) -> Component:
    content = [_make_component(elt, 1) for elt in ap.content]
    return html.Div(content)


def _load_and_display_ap(document_id: str) -> Component:
    ap = load_ap(document_id)
    children = []
    if seems_georisques_document_id(document_id):
        link = html.A('Lien vers le document géorisques', href=georisques_full_url(document_id), target='_blank')
        children.append(html.Button(link, className='btn btn-link mb-3 mt-3'))
    children.append(_ap_component(ap))
    return html.Div(children)


def _download_random_document() -> str:
    document_id = random.choice(SAMPLE_DOC_IDS)
    download_georisques_document(document_id)
    return document_id


def _load_or_init_step(document_id: str) -> APExtractionStep:
    if has_ap_extraction_step(document_id):
        return load_ap_extraction_step(document_id)
    step = APExtractionStep('Starting OCR.', 0.05, False)
    dump_ap_extraction_step(step, document_id)
    return step


def _add_callbacks(app: dash.Dash):
    @app.callback(
        Output(_DOCUMENT_ID, 'data'),
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
                return _handle_uploaded_file(contents, name)
        elif trigger_id == _DROPDOWN:
            return dropdown_value
        elif trigger_id == _BUTTON:
            return _download_random_document()
        raise ValueError(f'Unknown trigger {trigger_id}')

    def _filename_trigger(triggered: List[Dict[str, Any]]) -> bool:
        if len(triggered) == 0:
            raise ValueError(f'Expecting at least one trigger, got {len(triggered)}')
        return any([_DOCUMENT_ID in (trig.get('prop_id') or '') for trig in triggered])

    @app.callback(
        Output(_PROCESSING_DONE, 'data'),
        Output(_PROGRESS_BAR, 'children'),
        Output(_PROGRESS_BAR, 'value'),
        Output(_PROGRESS_BAR_WRAPPER, 'hidden'),
        Input(_INTERVAL, 'n_intervals'),
        Input(_DOCUMENT_ID, 'data'),
        State(_PROGRESS_BAR_WRAPPER, 'hidden'),
        prevent_initial_call=True,
    )
    def _process_file(_, document_id, progress_is_hidden):
        ctx = dash.callback_context
        filename_trigger = _filename_trigger(ctx.triggered)
        if filename_trigger and progress_is_hidden:
            start_ap_extraction_process(document_id)
            return dash.no_update, 'OCR en cours.', 5, False
        if not filename_trigger and not progress_is_hidden:
            step = _load_or_init_step(document_id)
            if step.done:
                return document_id, 'Done.', 100, True
            return dash.no_update, step.messsage, int(step.advancement * 100), False
        raise PreventUpdate

    @app.callback(Output(_LOADER, 'children'), Output(_OCR_OUTPUT, 'children'), Input(_PROCESSING_DONE, 'data'))
    def handle_processing_done(document_id):
        if document_id:
            try:
                return _load_and_display_ap(document_id), html.Div()
            except Exception:
                print(traceback.format_exc())
                return html.Div(), error_component(traceback.format_exc())
        raise PreventUpdate


page: Page = (_page, _add_callbacks)
