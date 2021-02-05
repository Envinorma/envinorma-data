import os
from collections import Counter
from typing import Any, Dict, List

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from lib.config import config
from lib.data import AMMetadata, Classement

# from back_office.ap_parsing import page as ap_parsing_page
from back_office.am_page import router as edit_am_page_router
from back_office.display_am import router as diplay_am_router
from back_office.app_init import app
from back_office.components import replace_line_breaks
from back_office.fetch_data import load_all_am_statuses
from back_office.utils import AM_ID_TO_NB_CLASSEMENTS_IDF, ID_TO_AM_MD, AMStatus, split_route


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
        'z-index': '10',
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


def _get_row(rank: int, am_state: AMStatus, am_metadata: AMMetadata, occurrences: int) -> Component:
    rows = [
        html.Td(rank),
        html.Td(dcc.Link(am_metadata.cid, href=f'/am/{am_metadata.cid}')),
        html.Td(dcc.Link(html.Button('Éditer', className='btn btn-light btn-sm'), href=f'/edit_am/{am_metadata.cid}')),
        html.Td(str(am_metadata.nor)),
        html.Td(am_metadata.short_title),
        html.Td(_get_str_classements(am_metadata.classements)),
        html.Td(occurrences),
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
            html.Th(''),
            html.Th('N° NOR'),
            html.Th('Nom'),
            html.Th('Classements'),
            html.Th('Nb classements IDF'),
            html.Th('Initialisé'),
            html.Th('Structuré'),
            html.Th('Paramétré'),
        ]
    )


def _build_am_table(
    id_to_state: Dict[str, AMStatus], id_to_am_metadata: Dict[str, AMMetadata], id_to_occurrences: Dict[str, int]
) -> Component:
    header = _get_header()
    sorted_ids = sorted(id_to_am_metadata, key=lambda x: id_to_occurrences.get(x, 0), reverse=True)
    rows = [
        _get_row(rank, id_to_state[am_id], id_to_am_metadata[am_id], id_to_occurrences.get(am_id, 0))
        for rank, am_id in enumerate(sorted_ids)
    ]
    return html.Table([html.Thead(header), html.Tbody(rows)], className='table')


def _cumsum(values: List[int]) -> List[int]:
    res: List[int] = [0] * len(values)
    for i, value in enumerate(values):
        if i == 0:
            res[i] == value
        res[i] = res[i - 1] + value
    return res


def _count_step_cumulated_advancement(
    id_to_state: Dict[str, AMStatus], id_to_occurrences: Dict[str, Any]
) -> List[float]:
    id_to_step = {id_: state.step() for id_, state in id_to_state.items()}
    step_to_nb_occurrences = {}
    for id_, step in id_to_step.items():
        step_to_nb_occurrences[step] = step_to_nb_occurrences.get(step, 0) + id_to_occurrences.get(id_, 0)
    cumsum = _cumsum([step_to_nb_occurrences.get(i, 0) for i in range(4)][::-1])[::-1]
    total = sum(step_to_nb_occurrences.values())
    return [x / total for x in cumsum]


def _count_step_cumulated_nb_am(id_to_state: Dict[str, AMStatus]) -> List[int]:
    counter = Counter([status.step() for status in id_to_state.values()])
    return [sum(counter.values()), counter[1] + counter[2] + counter[3], counter[2] + counter[3], counter[3]]


def _build_recap(id_to_state: Dict[str, AMStatus], id_to_occurrences: Dict[str, Any]) -> Component:
    step_cumulated_advancement = _count_step_cumulated_advancement(id_to_state, id_to_occurrences)
    step_cumulated_nb_am = _count_step_cumulated_nb_am(id_to_state)

    txts = [
        f'{step_cumulated_nb_am[0]} arrêtés\n',
        f'{step_cumulated_nb_am[1]} arrêtés initialisés\n({int(100*step_cumulated_advancement[1])}% des classements)',
        f'{step_cumulated_nb_am[2]} arrêtés structurés\n({int(100*step_cumulated_advancement[2])}% des classements)',
        f'{step_cumulated_nb_am[3]} arrêtés paramétrés\n({int(100*step_cumulated_advancement[3])}% des classements)',
    ]
    cols = [
        html.Div(
            html.Div(html.Div(replace_line_breaks(txt), className='card-body'), className='card text-center'),
            className='col-3',
        )
        for txt in txts
    ]
    return html.Div(cols, className='row', style={'margin-top': '20px', 'margin-bottom': '40px'})


def _make_index_component(
    id_to_state: Dict[str, AMStatus], id_to_am_metadata: Dict[str, AMMetadata], id_to_occurrences: Dict[str, int]
) -> Component:
    return html.Div(
        [
            html.H2('Arrêtés ministériels.'),
            _build_recap(id_to_state, id_to_occurrences),
            _build_am_table(id_to_state, id_to_am_metadata, id_to_occurrences),
        ]
    )


def router(pathname: str) -> Component:
    if not pathname.startswith('/'):
        raise ValueError(f'Expecting pathname to start with /, received {pathname}')
    if pathname == '/':
        id_to_state = load_all_am_statuses()
        return _make_index_component(id_to_state, ID_TO_AM_MD, AM_ID_TO_NB_CLASSEMENTS_IDF)
    prefix, suffix = split_route(pathname)
    if prefix == '/edit_am':
        return edit_am_page_router(prefix, suffix)
    if prefix == '/am':
        return diplay_am_router(prefix, suffix.split('/')[-1])
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
