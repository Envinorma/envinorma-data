import json
import base64
import os
import traceback
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
import pdf2image
import pytesseract
from ap_exploration.pages.ap_image.alto_to_html import alto_page_to_html
from ap_exploration.routing import Page
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.back_office.components import error_component
from envinorma.back_office.utils import generate_id
from envinorma.io.alto import AltoFile, AltoPage
from tqdm import tqdm

_UPLOAD = generate_id(__file__, 'upload-data')
_FILENAME_PDF = generate_id(__file__, 'filename-pdf')
_LOADER = generate_id(__file__, 'loader')
_DROPDOWN = generate_id(__file__, 'dropdown')
_OCR_OUTPUT = generate_id(__file__, 'ocr-output')
_PDF_AP_FOLDER = '/Users/remidelbouys/EnviNorma/ap_sample/pdf_image_workspace'


def _ensure_one_page_and_get_it(alto: AltoFile) -> AltoPage:
    if len(alto.layout.pages) != 1:
        raise ValueError(f'Expecting exactly one page, got {len(alto.layout.pages)}')
    return alto.layout.pages[0]


def _change_extension_pdf_to_alto(filename: str) -> str:
    if not filename.endswith('.pdf'):
        raise ValueError(f'{filename} does not have a pdf extension')
    return filename[:-4] + '.alto'


def _decode(content: Union[str, bytes]) -> str:
    return content.decode() if isinstance(content, bytes) else content


def _tesseract(page: Any) -> str:
    return _decode(pytesseract.image_to_alto_xml(page, lang='fra'))  # config='user_words_file words'


def _ocr_with_memo(filename: str) -> List[AltoFile]:
    alto_filename = _change_extension_pdf_to_alto(filename)
    if os.path.exists(alto_filename):
        return [AltoFile.from_xml(xml) for xml in json.load(open(alto_filename))]
    print('Converting to image.')
    pages = pdf2image.convert_from_path(filename)
    print('OCRing.')
    xmls = [_tesseract(page) for page in tqdm(pages)]
    json.dump(xmls, open(alto_filename, 'w'))
    files = [AltoFile.from_xml(xml) for xml in xmls]
    return files


def _extract_alto_pages(filename: str) -> List[AltoPage]:
    pages = _ocr_with_memo(filename)
    return [_ensure_one_page_and_get_it(page) for page in pages]


def _upload_component() -> Component:
    style = {
        'width': '100%',
        'height': '60px',
        'lineHeight': '60px',
        'borderWidth': '1px',
        'borderStyle': 'dashed',
        'borderRadius': '5px',
        'textAlign': 'center',
        'margin-bottom': '10px',
        'cursor': 'pointer',
    }
    return dcc.Upload(id=_UPLOAD, children=html.Div(['Drag and Drop or Select Files']), style=style, multiple=False)


def _options() -> List[Dict[str, Any]]:
    return [{'value': file_, 'label': file_} for file_ in os.listdir(_PDF_AP_FOLDER) if file_.endswith('.pdf')]


def _dropdown() -> Component:
    return dcc.Dropdown(options=_options(), id=_DROPDOWN)


def _page() -> Component:
    return html.Div(
        [
            html.H1('AP .pdf parser'),
            _upload_component(),
            html.P('Ou choisissez un fichier existant'),
            _dropdown(),
            dcc.Store(id=_FILENAME_PDF),
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


def _transform_pdf(filename: str) -> Component:
    pages = _extract_alto_pages(filename)
    return html.Div([html.Div(alto_page_to_html(page)) for page in pages])


def _add_callbacks(app: dash.Dash):
    @app.callback(
        Output(_FILENAME_PDF, 'data'),
        Input(_UPLOAD, 'contents'),
        Input(_DROPDOWN, 'value'),
        State(_UPLOAD, 'filename'),
        State(_UPLOAD, 'last_modified'),
        State(_DROPDOWN, 'n_clicks_timestamp'),
        prevent_initial_call=True,
    )
    def save_file(contents, dropdown_value, name, upload_timestamp, dropdown_timestamp):
        upload_timestamp = upload_timestamp or 0
        dropdown_timestamp = dropdown_timestamp or 0
        if upload_timestamp > dropdown_timestamp:
            if contents:
                return _save_file(contents, name)
        else:
            return os.path.join(_PDF_AP_FOLDER, dropdown_value)
        return None

    @app.callback(Output(_LOADER, 'children'), Output(_OCR_OUTPUT, 'children'), Input(_FILENAME_PDF, 'data'))
    def handle_new_pdf_filename(filename):
        if filename:
            try:
                return _transform_pdf(filename), html.Div()
            except Exception:
                print(traceback.format_exc())
                return html.Div(), error_component(traceback.format_exc())
        raise PreventUpdate


page: Page = (_page, _add_callbacks)
