import base64

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from lib.docx import extract_text as parse_docx
from lib.open_document import extract_text as parse_odt
from lib.pdf import extract_text as parse_pdf

from back_office.app_init import app
from back_office.components.am_component import structured_text_component
from back_office.utils import error_component

_UPLOAD = 'ap-parsing-upload-data'
_OUTPUT = 'output-data-upload'


def page() -> Component:
    style = {
        'width': '100%',
        'height': '60px',
        'lineHeight': '60px',
        'borderWidth': '1px',
        'borderStyle': 'dashed',
        'borderRadius': '5px',
        'textAlign': 'center',
        'margin': '10px',
    }
    upload = dcc.Upload(
        id=_UPLOAD, children=html.Div(['Drag and Drop or ', html.A('Select Files')]), style=style, multiple=False
    )
    return html.Div([upload, html.Div(id=_OUTPUT)])


def _parse_contents(contents: str, filename: str) -> Component:
    _, content_string = contents.split(',')
    file_extension = filename.split('.')[-1]
    decoded = base64.b64decode(content_string)
    if file_extension == 'docx':
        text = parse_docx(decoded)
    elif file_extension == 'odt':
        text = parse_odt(decoded)
    elif file_extension == 'pdf':
        text = parse_pdf(decoded)
    else:
        return error_component(f'Format {file_extension} non supporté.')

    return html.Div(
        [
            html.H5(filename),
            html.H6(file_extension),
            html.Hr(),
            html.Div('Raw Content'),
            structured_text_component(text, ['abrogé']),
        ]
    )


@app.callback(Output(_OUTPUT, 'children'), Input(_UPLOAD, 'contents'), State(_UPLOAD, 'filename'))
def update_output(contents, name):
    if contents:
        return _parse_contents(contents, name)
    return html.Div()


if __name__ == '__main__':
    app.run_server(debug=True)
