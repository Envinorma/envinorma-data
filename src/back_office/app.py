from typing import List

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component
from dash.dependencies import Input, Output
from back_office import am_page

from back_office.utils import ID_TO_AM_MD

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, suppress_callback_exceptions=True)


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


def _build_list() -> List[html.P]:
    return [
        html.P(dcc.Link(f'{am.cid} | {am.nor} | {am.short_title}', href=f'/arrete_ministeriel/{am.cid}'))
        for am in ID_TO_AM_MD.values()
    ]


def _make_index_component() -> Component:
    children: List[Component] = []
    children.append(html.H3('Edition d\'un arrêté ministériel.'))
    children.extend(_build_list())
    return html.Div(children)


_CHILD_PAGES = {'/arrete_ministeriel': am_page.page}


def router(pathname: str) -> Component:
    if pathname == '/':
        return _make_index_component()
    for key, page in _CHILD_PAGES.items():
        if pathname[: len(key)] == key:
            return page.router(pathname[len(key) :])
    return html.H3('404 error: Unknown path {}'.format(pathname))


@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname: str):
    return router(pathname)


if __name__ == '__main__':
    for _PAGE in _CHILD_PAGES.values():
        _PAGE.add_callbacks(app)
    app.run_server(debug=True)
