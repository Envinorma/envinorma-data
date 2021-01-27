from typing import Dict, List

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from lib.config import AM_DATA_FOLDER
from lib.data import AMMetadata, Classement

# from back_office.ap_parsing import page as ap_parsing_page
from back_office.am_page import router as am_page_router
from back_office.app_init import app
from back_office.fetch_data import load_am_status
from back_office.utils import ID_TO_AM_MD, AMStatus, split_route


def _prepare_archive_if_no_data():
    import os
    import shutil

    if not os.path.exists(AM_DATA_FOLDER):
        os.mkdir(AM_DATA_FOLDER)

    if not os.listdir(AM_DATA_FOLDER):
        print('No AM data. Unzipping default archive.')
        path_to_archive = __file__.replace('back_office/app.py', 'data/AM.zip')
        shutil.unpack_archive(path_to_archive, AM_DATA_FOLDER)
    else:
        print(f'AM data folder not empty: contains {os.listdir(AM_DATA_FOLDER)}')


_prepare_archive_if_no_data()


def _get_page_heading() -> Component:
    src = '/assets/logo-envinorma.png'
    sticky_style = {
        'padding': '.5em',
        'border-bottom': '1px solid rgba(0,0,0,.1)',
        'position': 'sticky',
        'top': 0,
        'background-color': '#fff',
        'z-index': '1',
        'margin-bottom': '10px',
    }
    return dcc.Link(
        html.Div(html.Div(html.Img(src=src, style={'width': '30px'}), className='container'), style=sticky_style),
        href='/',
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


def _get_row(rank: int, am_state: AMStatus, am_metadata: AMMetadata) -> Component:
    rows = [
        html.Td(rank),
        html.Td(dcc.Link(am_metadata.cid, href=f'/arrete_ministeriel/{am_metadata.cid}')),
        html.Td(str(am_metadata.nor)),
        html.Td(am_metadata.short_title),
        html.Td(_get_str_classements(am_metadata.classements)),
        html.Td('', className=_class_name_from_bool(am_state != AMStatus.PENDING_STRUCTURE_VALIDATION)),
        html.Td('', className=_class_name_from_bool(am_state == AMStatus.VALIDATED)),
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


def _build_am_table(id_to_state: Dict[str, AMStatus], id_to_am_metadata: Dict[str, AMMetadata]) -> Component:
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


def _make_index_component(id_to_state: Dict[str, AMStatus], id_to_am_metadata: Dict[str, AMMetadata]) -> Component:
    return html.Div([html.H3('Arrêtés ministériels.'), _build_am_table(id_to_state, id_to_am_metadata)])


def _load_am_states(ids: List[str]) -> Dict[str, AMStatus]:
    return {id_: load_am_status(id_) for id_ in ids}


def router(pathname: str) -> Component:
    if not pathname.startswith('/'):
        raise ValueError(f'Expecting pathname to start with /, received {pathname}')
    if pathname == '/':
        id_to_state = _load_am_states(list(ID_TO_AM_MD.keys()))
        return _make_index_component(id_to_state, ID_TO_AM_MD)
    prefix, suffix = split_route(pathname)
    if prefix == '/arrete_ministeriel':
        return am_page_router(prefix, suffix)
    # if pathname == '/ap_parsing':
    #     return ap_parsing_page()
    return html.H3('404 error: Unknown path {}'.format(pathname))


@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname: str):
    return router(pathname)


APP = app.server  # for gunicorn deployment

if __name__ == '__main__':
    app.run_server(debug=True)
