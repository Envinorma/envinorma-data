from typing import Dict, List

import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from lib.data import AMMetadata, Classement
from lib.config import AM_DATA_FOLDER

from back_office import am_page
from back_office.utils import AMState, ID_TO_AM_MD, div, load_am_state


def _prepare_archive_if_no_data():
    import os, shutil

    if not os.path.exists(AM_DATA_FOLDER):
        os.mkdir(AM_DATA_FOLDER)

    if not os.listdir(AM_DATA_FOLDER):
        print('No AM data. Unzipping default archive.')
        path_to_archive = __file__.replace('back_office/app.py', 'data/AM.zip')
        shutil.unpack_archive(path_to_archive, AM_DATA_FOLDER)
    else:
        print(f'AM data folder not empty: contains {os.listdir(AM_DATA_FOLDER)}')


_prepare_archive_if_no_data()

app = dash.Dash(
    __name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True, title='Envinorma'
)


def _get_page_heading() -> Component:
    src = '/assets/logo-envinorma.png'
    return html.Header(
        dcc.Link(
            html.Div(
                html.Div(html.Img(src=src, style={'width': '30px'}), className='container'),
                style={
                    'padding': '.5em',
                    'border-bottom': '1px solid rgba(0,0,0,.1)',
                    'position': 'sticky',
                    'top': 0,
                    'background-color': '#fff',
                    'z-index': '1',
                    'margin-bottom': '10px',
                },
            ),
            href='/',
        )
    )


app.layout = html.Div(
    [dcc.Location(id='url', refresh=False), _get_page_heading(), html.Div(id='page-content', className='container')],
    id='layout',
)


def _class_name_from_bool(bool_: bool) -> str:
    return 'table-success' if bool_ else 'table-danger'


def _get_str_classement(classement: Classement) -> str:
    if classement.alinea:
        return f'{classement.rubrique}-{classement.regime.value}-al.{classement.alinea}'
    return f'{classement.rubrique}-{classement.regime.value}'


def _get_str_classements(classements: List[Classement]) -> str:
    return ', '.join([_get_str_classement(classement) for classement in classements])


def _get_row(rank: int, am_state: AMState, am_metadata: AMMetadata) -> Component:
    rows = [
        html.Td(rank),
        html.Td(dcc.Link(am_metadata.cid, href=f'/arrete_ministeriel/{am_metadata.cid}')),
        html.Td(str(am_metadata.nor)),
        html.Td(am_metadata.short_title),
        html.Td(_get_str_classements(am_metadata.classements)),
        html.Td('', className=_class_name_from_bool(am_state.state != am_state.state.PENDING_STRUCTURE_VALIDATION)),
        html.Td('', className=_class_name_from_bool(am_state.state == am_state.state.VALIDATED)),
    ]
    return html.Tr(rows)


def _get_header() -> Component:
    return html.Tr(
        [
            html.Th('#'),
            html.Th('N° CID'),
            html.Th('N° NOR'),
            html.Th('Nom'),
            html.Th('Classements'),
            html.Th('Structuré'),
            html.Th('Enrichi'),
        ]
    )


def _build_am_table(id_to_state: Dict[str, AMState], id_to_am_metadata: Dict[str, AMMetadata]) -> Component:
    header = _get_header()
    return html.Table(
        [
            html.Thead(header),
            html.Tbody(
                [_get_row(rank, id_to_state[am_id], am) for rank, (am_id, am) in enumerate(id_to_am_metadata.items())]
            ),
        ],
        className='table table-hover',
    )


def _make_index_component(id_to_state: Dict[str, AMState], id_to_am_metadata: Dict[str, AMMetadata]) -> Component:
    return div([html.H3('Arrêtés ministériels.'), _build_am_table(id_to_state, id_to_am_metadata)])


_CHILD_PAGES = {'/arrete_ministeriel': am_page.page}


def _load_am_states(ids: List[str]) -> Dict[str, AMState]:
    return {id_: load_am_state(id_) for id_ in ids}


def router(pathname: str) -> Component:
    if pathname == '/':
        id_to_state = _load_am_states(list(ID_TO_AM_MD.keys()))
        return _make_index_component(id_to_state, ID_TO_AM_MD)
    for key, page in _CHILD_PAGES.items():
        if pathname[: len(key)] == key:
            return page.router(pathname[len(key) :], key)
    return html.H3('404 error: Unknown path {}'.format(pathname))


@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname: str):
    return router(pathname)


for _PAGE in _CHILD_PAGES.values():
    _PAGE.add_callbacks(app)

APP = app.server  # for gunicorn deployment

if __name__ == '__main__':
    app.run_server(debug=True)
