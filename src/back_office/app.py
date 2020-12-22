from typing import List
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component

from back_office.structure_edition import add_callbacks, make_am_component
from back_office.utils import ID_TO_AM_MD

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)


app.layout = html.Div(
    [
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content', style={'width': '80%', 'margin': 'auto'}),
    ]
)


def _make_index_component() -> Component:
    children: List[Component] = []
    children.append(html.H3('Structure edition.'))
    children.extend(
        [
            html.P([dcc.Link(f'{am.cid} | {am.nor} | {am.short_title}', href=f'/arrete_ministeriel/{am.cid}')])
            for am in ID_TO_AM_MD.values()
        ]
    )
    return html.Div(children)


@app.callback(dash.dependencies.Output('page-content', 'children'), [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname: str):
    if pathname == '/':
        return _make_index_component()
    if 'arrete_ministeriel' in pathname:
        am_id = pathname.split('arrete_ministeriel/')[-1]
        return make_am_component(am_id)
    return html.H3('You are on page {}'.format(pathname))


add_callbacks(app)

if __name__ == '__main__':
    app.run_server(debug=True)
