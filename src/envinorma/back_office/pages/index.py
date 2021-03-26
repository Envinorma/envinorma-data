from collections import Counter
from typing import Any, Dict, List, Optional, Union

import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component

from envinorma.back_office.components import replace_line_breaks
from envinorma.back_office.fetch_data import load_all_am_statuses
from envinorma.back_office.routing import Page
from envinorma.back_office.utils import AM_ID_TO_NB_CLASSEMENTS, ID_TO_AM_MD, AMStatus
from envinorma.data import AMMetadata, Classement


def _class_name_from_bool(bool_: bool) -> str:
    return 'table-success' if bool_ else 'table-danger'


def _get_str_classement(classement: Classement) -> str:
    if classement.alinea:
        return f'{classement.rubrique}-{classement.regime.value}-al.{classement.alinea}'
    return f'{classement.rubrique}-{classement.regime.value}'


def _get_str_classements(classements: List[Classement]) -> str:
    return ', '.join([_get_str_classement(classement) for classement in classements])


def _normal_td(content: Union[Component, str, int]) -> Component:
    return html.Td(content, className='align-middle', style={'font-size': '0.85em'})


def _get_row(rank: int, am_state: Optional[AMStatus], am_metadata: AMMetadata, occurrences: int) -> Component:
    am_step = am_state.step() if am_state else -1
    rows = [
        _normal_td(rank),
        _normal_td(dcc.Link(am_metadata.cid, href=f'/am/{am_metadata.cid}')),
        _normal_td(str(am_metadata.nor)),
        _normal_td(am_metadata.short_title),
        _normal_td(_get_str_classements(am_metadata.classements)),
        _normal_td(am_metadata.source.value),
        _normal_td(occurrences),
        html.Td('', className=_class_name_from_bool(am_step >= 1)),
        html.Td('', className=_class_name_from_bool(am_step >= 2)),
        html.Td('', className=_class_name_from_bool(am_step >= 3)),
    ]
    return html.Tr(rows, className='table-danger' if not am_state else '')


def _th(str_: str) -> Component:
    return html.Th(str_, style={'font-size': '0.85em'})


def _get_header() -> Component:
    return html.Tr(
        [
            _th('#'),
            _th('N° CID'),
            _th('N° NOR'),
            _th('Nom'),
            _th('Classements'),
            _th('Source'),
            _th('Occs.'),
            _th('Initialisé'),
            _th('Structuré'),
            _th('Paramétré'),
        ]
    )


def _build_am_table(
    id_to_state: Dict[str, AMStatus], id_to_am_metadata: Dict[str, AMMetadata], id_to_occurrences: Dict[str, int]
) -> Component:
    header = _get_header()
    sorted_ids = sorted(id_to_am_metadata, key=lambda x: id_to_occurrences.get(x, 0), reverse=True)
    rows = [
        _get_row(rank, id_to_state.get(am_id), id_to_am_metadata[am_id], id_to_occurrences.get(am_id, 0))
        for rank, am_id in enumerate(sorted_ids)
    ]
    return html.Table([html.Thead(header), html.Tbody(rows)], className='table table-sm')


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
    step_to_nb_occurrences: Dict[int, int] = {}
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
    displayed_ids = set(list(id_to_am_metadata))
    id_to_state = {id_: state for id_, state in id_to_state.items() if id_ in displayed_ids}
    id_to_occurrences = {id_: occ for id_, occ in id_to_occurrences.items() if id_ in displayed_ids}
    return html.Div(
        [
            html.H2('Arrêtés ministériels.'),
            _build_recap(id_to_state, id_to_occurrences),
            _build_am_table(id_to_state, id_to_am_metadata, id_to_occurrences),
        ]
    )


def _layout() -> Component:
    id_to_state = load_all_am_statuses()
    return _make_index_component(id_to_state, ID_TO_AM_MD, AM_ID_TO_NB_CLASSEMENTS)


PAGE = Page(_layout, None)
