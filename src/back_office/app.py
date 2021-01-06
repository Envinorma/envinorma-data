from typing import Dict, List

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from lib.data import AMMetadata

from back_office import am_page
from back_office.utils import ID_TO_AM_MD, div

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(
    __name__,
    external_stylesheets=['https://cdn.jsdelivr.net/npm/bootstrap@5.0.0-beta1/dist/css/bootstrap.min.css'],
    suppress_callback_exceptions=True,
)


app.layout = html.Div(
    [
        dcc.Location(id='url', refresh=False),
        html.Div(
            id='title',
            style={'width': '80%', 'margin': 'auto'},
            children=[dcc.Link(html.H1('Envinorma'), href='/')],
        ),
        html.Div(id='page-content', style={'width': '80%', 'margin': 'auto'}),
    ]
)


def _get_row(am: AMMetadata) -> Component:
    rows = [
        html.Td(dcc.Link(am.cid, href=f'/arrete_ministeriel/{am.cid}')),
        html.Td(str(am.nor)),
        html.Td(am.short_title),
        html.Td('', className='table-success'),
        html.Td('', className='table-danger'),
    ]
    return html.Tr(rows)


def _get_header() -> Component:
    return html.Tr([html.Th('N° CID'), html.Th('N° NOR'), html.Th('Nom'), html.Th('Structuré'), html.Th('Enrichi')])


def _build_am_table(id_to_am_metadata: Dict[str, AMMetadata]) -> Component:
    header = _get_header()
    return html.Table(
        [html.Thead(header), html.Tbody([_get_row(am) for am in id_to_am_metadata.values()])],
        className='table table-hover',
    )


def _make_index_component(id_to_am_metadata: Dict[str, AMMetadata]) -> Component:
    return div([html.H3('Arrêtés ministériels.'), _build_am_table(id_to_am_metadata)])


_CHILD_PAGES = {'/arrete_ministeriel': am_page.page}


def router(pathname: str) -> Component:
    if pathname == '/':
        return _make_index_component(ID_TO_AM_MD)
    for key, page in _CHILD_PAGES.items():
        if pathname[: len(key)] == key:
            return page.router(pathname[len(key) :], key)
    return html.H3('404 error: Unknown path {}'.format(pathname))


@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname: str):
    return router(pathname)


if __name__ == '__main__':
    for _PAGE in _CHILD_PAGES.values():
        _PAGE.add_callbacks(app)
    app.run_server(debug=True)
