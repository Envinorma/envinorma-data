import os
from collections import Counter
from typing import Dict, List

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from lib.config import config
from lib.data import AMMetadata, Classement

# from back_office.ap_parsing import page as ap_parsing_page
from back_office.am_page import router as am_page_router
from back_office.app_init import app
from back_office.fetch_data import load_all_am_statuses
from back_office.utils import ID_TO_AM_MD, AMStatus, split_route


def _create_tmp_am_folder():
    if not os.path.exists(config.storage.am_data_folder):
        os.mkdir(config.storage.am_data_folder)
    parametric_folder = f'{config.storage.am_data_folder}/parametric_texts'
    if not os.path.exists(parametric_folder):
        os.mkdir(parametric_folder)


_create_tmp_am_folder()


def _get_page_heading() -> Component:
    src = '/assets/logo-envinorma.png'
    sticky_style = {
        'padding': '.2em',
        'border-bottom': '1px solid rgba(0,0,0,.1)',
        'position': 'sticky',
        'top': 0,
        'background-color': '#fff',
        'z-index': '1',
        'margin-bottom': '10px',
    }
    nav = html.Span(
        [
            html.Span(
                html.A('Arrêtés', href='/', className='nav-link', style={'color': 'grey', 'display': 'inline-block'})
            ),
            html.Span(
                html.A(
                    'Guide d\'enrichissement',
                    href='https://www.notion.so/Guide-d-enrichissement-3874408245dc474ca8181a3d1d50f78e',
                    className='nav-link',
                    target="_blank",
                    style={'color': 'grey', 'display': 'inline-block'},
                )
            ),
        ],
        style={'display': 'inline-block'},
    )
    img = html.Img(src=src, style={'width': '30px', 'display': 'inline-block'})
    return html.Div(html.Div([dcc.Link(img, href='/'), nav], className='container'), style=sticky_style)


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
        html.Td('', className=_class_name_from_bool(am_state.step() >= 1)),
        html.Td('', className=_class_name_from_bool(am_state.step() >= 2)),
        html.Td('', className=_class_name_from_bool(am_state.step() >= 3)),
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
            html.Th('Initialisé'),
            html.Th('Structuré'),
            html.Th('Paramétré'),
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


def _build_recap(id_to_state: Dict[str, AMStatus]) -> Component:
    counter = Counter([status.step() for status in id_to_state.values()])
    txts = [
        f'{len(id_to_state)} arrêtés',
        f'{counter[1] + counter[2] + counter[3]} arrêtés initialisés',
        f'{counter[2] + counter[3]} arrêtés structurés',
        f'{counter[3]} arrêtés paramétrés',
    ]
    cols = [
        html.Div(html.Div(html.Div(txt, className='card-body'), className='card text-center'), className='col-3')
        for txt in txts
    ]
    return html.Div(cols, className='row', style={'margin-top': '20px', 'margin-bottom': '40px'})


def _make_index_component(id_to_state: Dict[str, AMStatus], id_to_am_metadata: Dict[str, AMMetadata]) -> Component:
    return html.Div(
        [html.H2('Arrêtés ministériels.'), _build_recap(id_to_state), _build_am_table(id_to_state, id_to_am_metadata)]
    )


def router(pathname: str) -> Component:
    if not pathname.startswith('/'):
        raise ValueError(f'Expecting pathname to start with /, received {pathname}')
    if pathname == '/':
        id_to_state = load_all_am_statuses()
        return _make_index_component(id_to_state, ID_TO_AM_MD)
    prefix, suffix = split_route(pathname)
    if prefix == '/arrete_ministeriel':
        return am_page_router(prefix, suffix)
    # if pathname == '/ap_parsing':
    #     return ap_parsing_page()
    return html.H3('404 error: Unknown path {}'.format(pathname))


app.layout = html.Div(
    [dcc.Location(id='url', refresh=False), _get_page_heading(), html.Div(id='page-content', className='container')],
    id='layout',
)


@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname: str):
    return router(pathname)


APP = app.server  # for gunicorn deployment

if __name__ == '__main__':
    app.run_server(debug=True)
