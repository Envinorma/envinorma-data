import os
from typing import Dict, Optional

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from envinorma.config import config

from ap_exploration.db.ap import download_document
from ap_exploration.pages.ap import page as ap_page
from ap_exploration.pages.ap_image import page as ap_image_page
from ap_exploration.pages.ap_image.v2 import page as ap_image_v2_page
from ap_exploration.pages.ap_odt import page as ap_odt_page
from ap_exploration.pages.ap_pdf import page as ap_pdf_page
from ap_exploration.pages.etablissement import page as etablissement_page
from ap_exploration.pages.temp_page import page as temp_page
from ap_exploration.routing import ROUTER, Endpoint, Page

_FRA_TESS_DATA_URL = 'https://github.com/tesseract-ocr/tessdata/raw/master/fra.traineddata'
_TESSDATA_PREFIX = config.storage.tessdata


def _download_fra_tessdata_if_inexistent():
    filename = os.path.join(_TESSDATA_PREFIX, 'fra.traineddata')
    if not os.path.exists(filename):
        print('Downloading fra.traineddata.')
        download_document(_FRA_TESS_DATA_URL, filename)


_download_fra_tessdata_if_inexistent()


def _header_link(content: str, href: str, target: Optional[str] = None) -> Component:
    style = {'color': 'grey', 'display': 'inline-block'}
    return html.Span(html.A(content, href=href, className='nav-link', style=style, target=target))


def _get_nav() -> Component:
    nav = html.Span(
        [
            _header_link('Accueil', href='/'),
            _header_link('AP image', href=f'/{Endpoint.AP_IMAGE}'),
            _header_link('AP image V2', href=f'/{Endpoint.AP_IMAGE_V2}'),
            _header_link('AP pdf', href=f'/{Endpoint.AP_PDF}'),
            _header_link('AP odt', href=f'/{Endpoint.AP_ODT}'),
            _header_link('Etablissements', href=f'/{Endpoint.ETABLISSEMENT}'),
        ],
        style={'display': 'inline-block'},
    )
    return nav


def _get_page_heading() -> Component:
    src = '/assets/logo-envinorma.png'
    sticky_style = {
        'padding': '.2em',
        'border-bottom': '1px solid rgba(0,0,0,.1)',
        'position': 'sticky',
        'top': 0,
        'background-color': '#fff',
        'z-index': '10',
        'margin-bottom': '10px',
    }
    img = html.Img(src=src, style={'width': '30px', 'display': 'inline-block'})
    return html.Div(html.Div([dcc.Link(img, href='/'), _get_nav()], className='container'), style=sticky_style)


app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP, __file__.replace('ap_exploration.py', 'assets/cpstyle.css')],
    suppress_callback_exceptions=True,
    title='AP Exploration - Envinorma',
    update_title=None,
)


app.layout = html.Div(
    [dcc.Location(id='url', refresh=False), _get_page_heading(), html.Div(id='page-content', className='container')],
    id='layout',
)


def _index_layout() -> Component:
    links = html.Ul(
        [
            html.Li(dcc.Link('Liste des établissements', href=f'/{Endpoint.ETABLISSEMENT}')),
            html.Li(dcc.Link('Sample d\'AP .odt', href=f'/{Endpoint.AP_ODT}')),
        ]
    )
    return html.Div(links)


_ENDPOINT_TO_PAGE: Dict[Endpoint, Page] = {
    Endpoint.AP_ODT: ap_odt_page,
    Endpoint.AP_PDF: ap_pdf_page,
    Endpoint.INDEX: (_index_layout, None),
    Endpoint.ETABLISSEMENT: etablissement_page,
    Endpoint.AP: ap_page,
    Endpoint.AP_IMAGE: ap_image_page,
    Endpoint.AP_IMAGE_V2: ap_image_v2_page,
    Endpoint.TMP: temp_page,
}


def _route(pathname: str) -> Component:
    endpoint, kwargs = ROUTER.match(pathname)
    return _ENDPOINT_TO_PAGE[endpoint][0](**kwargs)


@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname: str):
    return _route(pathname)


for _, _add_callbacks in _ENDPOINT_TO_PAGE.values():
    if _add_callbacks:
        _add_callbacks(app)

APP = app.server  # for gunicorn deployment

if __name__ == '__main__':
    app.run_server(debug=True)
