from enum import Enum
from typing import List, Optional, Tuple

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component

from back_office.structure_edition import (
    add_structure_edition_callbacks,
    make_am_structure_edition_component,
)

from back_office.parametrization_edition import (
    add_parametrization_edition_callbacks,
    make_am_parametrization_edition_component,
)
from back_office.utils import ID_TO_AM_MD

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets, suppress_callback_exceptions=True)


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


class AMOperation(Enum):
    EDIT_STRUCTURE = 'edit_structure'
    EDIT_ANNOTATIONS = 'edit_annotations'
    EDIT_PARAMETRIZATION = 'edit_parametrization'


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


def _extract_am_id_and_operation(pathname: str) -> Tuple[str, Optional[AMOperation], str]:
    pieces = pathname.split('/')[1:]
    if len(pieces) == 0:
        raise ValueError('Unexpected')
    if len(pieces) == 1:
        return pieces[0], None, ''
    return pieces[0], AMOperation(pieces[1]), '/'.join(pieces[2:])


def _make_am_index_component(am_id: str) -> Component:
    children: List[Component] = []
    children.append(html.H3('Edition de structure.'))
    children.append(
        html.P(dcc.Link(f'brouillon_0', href=f'/arrete_ministeriel/{am_id}/{AMOperation.EDIT_STRUCTURE.value}'))
    )
    children.append(html.H3('Edition de paramètres d\'application.'))
    children.append(
        html.P(dcc.Link(f'brouillon_0', href=f'/arrete_ministeriel/{am_id}/{AMOperation.EDIT_PARAMETRIZATION.value}'))
    )
    return html.Div(children)


def _am_routing(pathname: str) -> Component:
    print(pathname)
    am_id, operation_id, rest_of_path = _extract_am_id_and_operation(pathname)
    if not operation_id:
        return _make_am_index_component(am_id)
    if operation_id == operation_id.EDIT_STRUCTURE:
        return make_am_structure_edition_component(am_id)
    if operation_id == operation_id.EDIT_PARAMETRIZATION:
        return make_am_parametrization_edition_component(am_id)
    # if operation == operation.EDIT_PARAMETRIZATION_TODEL:
    #     return make_am_parametrization_edition_component_todel(am_id)
    raise NotImplementedError()


def _router(pathname: str) -> Component:
    if pathname == '/':
        return _make_index_component()
    key = '/arrete_ministeriel'
    if pathname[: len(key)] == key:
        return _am_routing(pathname[len(key) :])
    return html.H3('404 error {}'.format(pathname))


@app.callback(dash.dependencies.Output('page-content', 'children'), [dash.dependencies.Input('url', 'pathname')])
def display_page(pathname: str):
    return _router(pathname)


add_structure_edition_callbacks(app)
add_parametrization_edition_callbacks(app)

if __name__ == '__main__':
    app.run_server(debug=True)
