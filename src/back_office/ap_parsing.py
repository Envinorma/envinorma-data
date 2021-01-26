import base64
import traceback
from dataclasses import dataclass
from typing import Optional

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from lib.data import StructuredText, add_title_default_numbering
from lib.docx import extract_text_from_file as parse_docx, get_docx_xml, get_docx_xml_soup
from lib.open_document import load_and_transform as parse_odt
from lib.pdf import pdf_to_docx
from lib.utils import random_string

from back_office.app_init import app
from back_office.components.am_component import structured_text_component
from back_office.components.summary_component import summary_component
from back_office.utils import error_component

_UPLOAD = 'ap-parsing-upload-data'
_FILENAME_PDF = 'ap-parsing-filename-pdf'
_FILENAME_NOT_PDF = 'ap-parsing-filename-not-pdf'
_LOADER = 'ap-parsing-loader'


def page() -> Component:
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
    upload = dcc.Upload(
        id=_UPLOAD, children=html.Div(['Drag and Drop or ', html.A('Select Files')]), style=style, multiple=False
    )
    return html.Div([upload, dcc.Store(id=_FILENAME_PDF), dcc.Store(id=_FILENAME_NOT_PDF), dbc.Spinner(id=_LOADER)])


@dataclass
class _FileData:
    filename: str
    error: Optional[str] = None
    extracted_text: Optional[StructuredText] = None


def _generate_new_filename(filename: str) -> str:
    if '.' not in filename:
        filename = f'{filename}.unknown'  # Ensure at least one '.'
    extension = '.' + filename.split('.')[-1]
    return filename.replace(extension, random_string() + extension)


def _generate_tmp_path(filename: str) -> str:
    return f'/tmp/{_generate_new_filename(filename)}'


def _handle_uploaded_file(contents: str, filename: str) -> str:
    _, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    new_filename = _generate_tmp_path(filename)

    open(new_filename, 'wb').write(decoded)
    return new_filename


def _docx_seems_empty(filename: str) -> bool:
    return len(''.join(list(get_docx_xml_soup(filename).stripped_strings))) <= 100


def _parse_file(filename: str) -> _FileData:
    file_extension = filename.split('.')[-1]
    try:
        if file_extension in ('docx',):
            if _docx_seems_empty(filename):
                return _FileData(filename, error='Fichier vide.')
            text = parse_docx(filename)
        elif file_extension == 'odt':
            text = parse_odt(filename)
        else:
            return _FileData(filename=filename, error=f'Format {file_extension} non supporté.')
    except Exception:  # pylint: disable=broad-except
        return _FileData(filename=filename, error=f'Erreur inattendue :\n{traceback.format_exc()}')
    text_with_numbering = add_title_default_numbering(text)
    return _FileData(filename=filename, extracted_text=text_with_numbering)


def _text_with_summary(text: StructuredText) -> Component:
    summary = summary_component(text)
    text_ = structured_text_component(text, ['abroge'])
    return html.Div([html.Div(summary, className='col-3'), html.Div(text_, className='col-9')], className='row')


def _build_parsed_content_component(file_data: _FileData) -> Component:
    if not file_data.extracted_text:
        raise ValueError('Expecting text to be defined if no error occurred.')
    return html.Div(
        [
            html.H5(file_data.filename),
            html.Hr(),
            _text_with_summary(file_data.extracted_text),
        ]
    )


def _save_file(contents: str, filename: str) -> str:
    filename = _handle_uploaded_file(contents, filename)
    return filename


def _extension(filename: str) -> str:
    return filename.split('.')[-1]


def _transform_pdf_if_necessary(filename: str) -> str:
    if _extension(filename) != 'pdf':
        return filename
    new_filename = filename.replace('.pdf', '.docx')
    pdf_to_docx(filename, new_filename)
    return new_filename


def _parse_contents(filename: str) -> Component:
    file_data = _parse_file(filename)
    if file_data.error:
        return error_component(file_data.error)
    return _build_parsed_content_component(file_data)


@app.callback(Output(_FILENAME_PDF, 'data'), Input(_UPLOAD, 'contents'), State(_UPLOAD, 'filename'))
def save_file(contents, name):
    if contents:
        return _save_file(contents, name)
    return None


@app.callback(Output(_FILENAME_NOT_PDF, 'data'), Input(_FILENAME_PDF, 'data'))
def handle_new_pdf_filename(filename):
    if filename:
        return _transform_pdf_if_necessary(filename)
    return None


@app.callback(Output(_LOADER, 'children'), Input(_FILENAME_NOT_PDF, 'data'))
def handle_new_not_pdf_filename(filename):
    if filename:
        return _parse_contents(filename)
    return html.Div()
