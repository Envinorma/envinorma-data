import base64
import os
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate

from ap_exploration.routing import Page
from envinorma.back_office.components import replace_line_breaks
from envinorma.back_office.components.am_component import structured_text_component
from envinorma.back_office.components.summary_component import summary_component
from envinorma.back_office.utils import generate_id
from envinorma.data import StructuredText, add_title_default_numbering
from envinorma.io.docx import DocxNoTextError
from envinorma.io.docx import extract_text_from_file as parse_docx
from envinorma.io.docx import get_docx_xml_soup
from envinorma.io.open_document import load_and_transform as parse_odt
from envinorma.pdf import pdf_to_docx
from envinorma.utils import random_string

_UPLOAD = generate_id(__file__, 'upload-data')
_FILENAME_PDF = generate_id(__file__, 'filename-pdf')
_FILENAME_NOT_PDF = generate_id(__file__, 'filename-not-pdf')
_LOADER = generate_id(__file__, 'loader')
_DROPDOWN = generate_id(__file__, 'dropdown')
_PDF_PARSE_OUTPUT = generate_id(__file__, 'pdf-parse-output')
_PARSE_OUTPUT = generate_id(__file__, 'parse-output')
_PDF_AP_FOLDER = '/Users/remidelbouys/EnviNorma/ap_sample/pdf_workspace'


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


def _step_outputs() -> Component:

    return html.Div(
        [
            html.Div(dbc.Spinner(html.Div(), id=_PDF_PARSE_OUTPUT), className='col-6'),
            html.Div(dbc.Spinner(html.Div(), id=_PARSE_OUTPUT), className='col-6'),
        ],
        className='row',
    )


def _dropdown_pdf() -> Component:
    return dcc.Dropdown(options=_options(), id=_DROPDOWN)


def _page() -> Component:
    return html.Div(
        [
            html.H1('AP .pdf parser'),
            _upload_component(),
            html.P('Ou choisissez un fichier existant'),
            _dropdown_pdf(),
            dcc.Store(id=_FILENAME_PDF),
            dcc.Store(id=_FILENAME_NOT_PDF),
            _step_outputs(),
            html.Div(dbc.Spinner(html.Div(), id=_LOADER)),
        ]
    )


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
    return f'{_PDF_AP_FOLDER}/{_generate_new_filename(filename)}'


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
    except DocxNoTextError:
        return _FileData(filename=filename, error=f'Pas de texte dans le docx issu du pdf.')
    except Exception:
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


def _alert_component(text: str, extra_class_name: str) -> Component:
    return html.Div(
        replace_line_breaks(text),
        style={'height': '190px', 'margin-top': '10px', 'overflow-y': 'auto'},
        className='alert ' + extra_class_name,
    )


def _success_component(text: str) -> Component:
    return _alert_component(text, 'alert-success')


def _error_component(text: str) -> Component:
    return _alert_component(text, 'alert-danger')


def _parse_ok() -> Component:
    return _success_component('Parse ok')


def _pdf_parse_ok() -> Component:
    return _success_component('PDF-Parsing ok')


def _pdf_parse_already_done() -> Component:
    return _success_component('PDF-Parsing déjà effectué.')


def _save_file(contents: str, filename: str) -> str:
    filename = _handle_uploaded_file(contents, filename)
    return filename


def _transformation_is_necessary(filename: str) -> bool:
    return filename.endswith('.pdf')


args = dict(
    multi_processing=False,
    connected_border_tolerance=0.5,
    max_border_width=6.0,
    min_border_clearance=2.0,
    float_image_ignorable_gap=5.0,
    float_layout_tolerance=0.1,
    page_margin_factor_top=0.5,
    page_margin_factor_bottom=0.5,
    shape_merging_threshold=0.5,
    shape_min_dimension=2.0,
    line_overlap_threshold=0.9,
    line_merging_threshold=2.0,
    line_separate_threshold=5.0,
    lines_left_aligned_threshold=1.0,
    lines_right_aligned_threshold=1.0,
    lines_center_aligned_threshold=2.0,
    clip_image_res_ratio=3.0,
    curve_path_ratio=0.2,
)


def _transform_pdf(filename: str) -> str:
    new_filename = _change_extension_pdf_to_docx(filename)
    pdf_to_docx(filename, new_filename, start_page=0, end_page=1)
    return new_filename


def _parse_contents(filename: str) -> Tuple[Component, Component]:
    file_data = _parse_file(filename)
    if file_data.error:
        return html.Div(), _error_component(file_data.error)
    return _build_parsed_content_component(file_data), _parse_ok()


def _change_extension_pdf_to_docx(filename: str) -> str:
    if not filename.endswith('.pdf'):
        raise ValueError(f'{filename} does not have a pdf extension')
    return filename[:-4] + '.docx'


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
        print(upload_timestamp, dropdown_timestamp)
        upload_timestamp = upload_timestamp or 0
        dropdown_timestamp = dropdown_timestamp or 0
        if upload_timestamp > dropdown_timestamp:
            if contents:
                return _save_file(contents, name)
        else:
            candidate_file = os.path.join(_PDF_AP_FOLDER, dropdown_value)
            docx_file = _change_extension_pdf_to_docx(candidate_file)
            if os.path.exists(docx_file):  # PDF parsing already done
                return docx_file
            return candidate_file
        return None

    @app.callback(
        Output(_FILENAME_NOT_PDF, 'data'), Output(_PDF_PARSE_OUTPUT, 'children'), Input(_FILENAME_PDF, 'data')
    )
    def handle_new_pdf_filename(filename) -> Tuple[Union[str, Exception], Component]:
        if filename:
            if _transformation_is_necessary(filename):
                try:
                    return _transform_pdf(filename), _pdf_parse_ok()
                except Exception:
                    return PreventUpdate(), _error_component(traceback.format_exc())
            else:
                return filename, _pdf_parse_already_done()
        raise PreventUpdate

    @app.callback(Output(_LOADER, 'children'), Output(_PARSE_OUTPUT, 'children'), Input(_FILENAME_NOT_PDF, 'data'))
    def handle_new_not_pdf_filename(filename) -> Tuple[Component, Component]:
        if filename:
            return _parse_contents(filename)
        raise PreventUpdate


page: Page = (_page, _add_callbacks)
