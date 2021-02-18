import difflib
import json
import os
import traceback
import warnings
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import MATCH, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from envinorma.back_office.am_init_edition import router as am_init_router
from envinorma.back_office.am_init_tab import am_init_tab
from envinorma.back_office.app_init import app
from envinorma.back_office.components import ButtonState, button, error_component, link_button, surline_text
from envinorma.back_office.components.am_component import am_component
from envinorma.back_office.components.parametric_am_list import (
    parametric_am_list_callbacks,
    parametric_am_list_component,
)
from envinorma.back_office.components.summary_component import summary_component
from envinorma.back_office.components.table import ExtendedComponent, table_component
from envinorma.back_office.fetch_data import (
    delete_structured_am,
    load_am_status,
    load_initial_am,
    load_parametrization,
    load_structured_am,
    upsert_am_status,
    upsert_new_parametrization,
)
from envinorma.back_office.generate_final_am import AMVersions, generate_final_am
from envinorma.back_office.parametrization_edition import router as parametrization_router
from envinorma.back_office.structure_edition import router as structure_router
from envinorma.back_office.utils import ID_TO_AM_MD, AMOperation, AMStatus, get_traversed_titles, safe_get_section
from envinorma.config import (
    EnvironmentType,
    config,
    create_folder_and_generate_parametric_filename,
    get_parametric_ams_folder,
)
from envinorma.data import AMMetadata, ArreteMinisteriel, Ints, StructuredText, Table, am_to_text, extract_text_lines
from envinorma.io.markdown import extract_markdown_text
from envinorma.parametrization import (
    AlternativeSection,
    NonApplicationCondition,
    Parametrization,
    UndefinedTitlesSequencesError,
    add_titles_sequences,
    condition_to_str,
    regenerate_paths,
)
from envinorma.utils import SlackChannel, send_slack_notification, write_json

_PREFIX = __file__.split('/')[-1].replace('.py', '').replace('_', '-')
_VALIDATE_INITIALIZATION = f'{_PREFIX}-validate-init'
_VALIDATE_STRUCTURE = f'{_PREFIX}-validate-structure'
_VALIDATE_PARAMETRIZATION = f'{_PREFIX}-validate-parametrization'
_LOADER = f'{_PREFIX}-loading-output'
_STRUCTURE_TABS_AM_TAB = _PREFIX + '-structure-tabs-am-tab'
_STRUCTURE_TABS_DIFF_TAB = _PREFIX + '-structure-tabs-diff-tab'
_STRUCTURE_TABS_AM = _PREFIX + '-structure-tabs-am'
_STRUCTURE_TABS_DIFF = _PREFIX + '-structure-tabs-diff'
_STRUCTURE_TABS_AM_TAB = _PREFIX + '-structure-tabs-am-tab'
_STRUCTURE_TABS_DIFF_TAB = _PREFIX + '-structure-tabs-diff-tab'


def _modal_confirm_button_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': f'{_PREFIX}-modal-confirm-button', 'step': step or MATCH}


def _close_modal_button_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': f'{_PREFIX}-close-modal-button', 'step': step or MATCH}


def _modal_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': f'{_PREFIX}-modal', 'step': step or MATCH}


def _modal_button_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': f'{_PREFIX}-modal-button', 'step': step or MATCH}


def _extract_am_id_and_operation(pathname: str) -> Tuple[str, Optional[AMOperation], str]:
    pieces = pathname.split('/')[1:]
    if len(pieces) == 0:
        raise ValueError('Unexpected')
    if len(pieces) == 1:
        return pieces[0], None, ''
    return pieces[0], AMOperation(pieces[1]), '/'.join(pieces[2:])


def _get_edit_structure_button(parent_page: str) -> Component:
    href = f'{parent_page}/{AMOperation.EDIT_STRUCTURE.value}'
    return link_button('Éditer la structure', href, state=ButtonState.NORMAL_LINK)


def _get_am_initialization_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    return (None, button('Valider le texte initial', id_=_VALIDATE_INITIALIZATION, state=ButtonState.NORMAL))


def _get_confirmation_modal(
    button_text: str, modal_body: Union[str, Component], step: str, className: str
) -> Component:
    modal = dbc.Modal(
        [
            dbc.ModalHeader('Confirmation'),
            dbc.ModalBody(modal_body),
            dbc.ModalFooter(
                [
                    html.Button('Annuler', id=_close_modal_button_id(step), className='btn btn-light'),
                    html.Button('Confirmer', id=_modal_confirm_button_id(step), className='ml-auto btn btn-danger'),
                ]
            ),
        ],
        id=_modal_id(step),
    )
    return html.Div(
        [html.Button(button_text, id=_modal_button_id(step), className=className), modal],
        style={'display': 'inline-block'},
    )


def _get_reset_structure_button() -> Component:
    modal_content = 'Êtes-vous sûr de vouloir réinitialiser le texte ? Cette opération est irréversible.'
    return _get_confirmation_modal('Réinitialiser le texte', modal_content, 'reset-structure', 'btn btn-danger')


def _get_structure_validation_buttons(parent_page: str) -> Tuple[Optional[Component], Optional[Component]]:
    modal_content = (
        'Êtes-vous sûr de vouloir retourner à la phase d\'initialisation du texte ? Ceci est '
        'déconseillé lorsque l\'AM provient de Légifrance ou que la structure a déjà été modifiée.'
    )
    validate_button = button('Valider la structure', id_=_VALIDATE_STRUCTURE, state=ButtonState.NORMAL)
    right_buttons = html.Div(
        [_get_reset_structure_button(), ' ', _get_edit_structure_button(parent_page), ' ', validate_button],
        style={'display': 'inline-block'},
    )
    return (
        _get_confirmation_modal('Étape précédente', modal_content, 'structure', 'btn btn-light'),
        right_buttons,
    )


def _get_parametrization_edition_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    modal_content = (
        'Êtes-vous sûr de vouloir retourner à la phase de structuration du texte ? Si des paramètres '
        'ont déjà été renseignés, cela peut désaligner certains paramétrages.'
    )
    return (
        _get_confirmation_modal('Étape précédente', modal_content, 'parametrization', 'btn btn-light'),
        button('Valider le paramétrage', id_=_VALIDATE_PARAMETRIZATION, state=ButtonState.NORMAL),
    )


def _get_validated_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    modal_content = 'Retourner au paramétrage ?'
    return (_get_confirmation_modal('Étape précédente', modal_content, 'validated', 'btn btn-light'), None)


def _inline_buttons(button_left: Optional[Component], button_right: Optional[Component]) -> List[Component]:
    left = html.Div(button_left, style={'display': 'inline-block', 'float': 'left'})
    right = html.Div(button_right, style={'display': 'inline-block', 'float': 'right'})
    return [left, right]


def _get_buttons(am_status: AMStatus, parent_page: str) -> Component:
    successive_buttons = [
        _get_am_initialization_buttons(),
        _get_structure_validation_buttons(parent_page),
        _get_parametrization_edition_buttons(),
        _get_validated_buttons(),
    ]
    style = {
        'position': 'fixed',
        'bottom': '0px',
        'left': '0px',
        'width': '100%',
        'background-color': 'white',
        'padding-bottom': '10px',
        'padding-top': '10px',
    }
    return html.Div(
        [
            html.Div(
                html.Div(_inline_buttons(*buttons), className='container'), hidden=i != am_status.step(), style=style
            )
            for i, buttons in enumerate(successive_buttons)
        ]
    )


def _human_alinea_tuple(ints: Optional[List[int]]) -> str:
    if not ints:
        return 'Tous'
    return ', '.join(map(str, sorted(ints)))


def _application_condition_to_row(
    non_application_condition: NonApplicationCondition, am: ArreteMinisteriel, rank: int, current_page: str
) -> List[ExtendedComponent]:
    target_section = non_application_condition.targeted_entity.section
    reference_str = _get_section_title_or_error(target_section.path, am, target_section.titles_sequence)
    alineas = _human_alinea_tuple(non_application_condition.targeted_entity.outer_alinea_indices)
    condition = condition_to_str(non_application_condition.condition)
    source_section = non_application_condition.source.reference.section
    source = _get_section_title_or_error(source_section.path, am, source_section.titles_sequence)
    href = f'{current_page}/{AMOperation.ADD_CONDITION.value}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'{current_page}/{AMOperation.ADD_CONDITION.value}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    return [str(rank), reference_str, alineas, condition, source, edit, copy]


def _get_non_application_table(parametrization: Parametrization, am: ArreteMinisteriel, current_page: str) -> Component:
    header = ['#', 'Paragraphe visé', 'Alineas visés', 'Condition', 'Source', '', '']
    rows = [
        _application_condition_to_row(row, am, rank, current_page)
        for rank, row in enumerate(parametrization.application_conditions)
    ]
    return table_component([header], rows, 'table-sm')


def _get_target_section_id(path: Ints, am: ArreteMinisteriel) -> Optional[str]:
    if not path:
        return None
    section = safe_get_section(path, am)
    if section:
        return section.id
    return None


def _remove_last_word(sentence: str) -> str:
    return ' '.join(sentence.split(' ')[:-1])


def _shorten_text(title: str, max_len: int = 32) -> str:
    if len(title) > max_len:
        return _remove_last_word(title[:max_len]) + ' [...]'
    return title


def _get_section_title_or_error(path: Ints, am: ArreteMinisteriel, titles_sequence: Optional[List[str]]) -> Component:
    titles = get_traversed_titles(path, am)
    section_id = _get_target_section_id(path, am)
    style = {}
    if titles is None:
        style = {'color': 'red'}
        title = f'Introuvable, ce paramètre doit être modifié. (Titres précédents: {titles_sequence})'
    else:
        shortened_titles = [_shorten_text(title) for title in titles]
        joined_titles = ' / '.join(shortened_titles)
        title = html.A(joined_titles, href=f'#{section_id}') if section_id else joined_titles
    return html.Div(html.Span(title, style={**style, 'font-size': '0.8em'}), style={'width': '250px'})


def _wrap_in_paragraphs(strs: List[str]) -> Component:
    return html.Div([html.P(str_) for str_ in strs])


def _constrain(component: Component) -> Component:
    style = {
        'display': 'inline-block',
        'max-height': '100px',
        'min-width': '250px',
        'max-width': '250px',
        'font-size': '0.8em',
        'overflow-x': 'auto',
        'overflow-y': 'auto',
    }
    return html.Div(component, style=style)


def _alternative_section_to_row(
    alternative_section: AlternativeSection, am: ArreteMinisteriel, rank: int, current_page: str
) -> List[ExtendedComponent]:
    target_section = alternative_section.targeted_section
    reference_str = _get_section_title_or_error(target_section.path, am, target_section.titles_sequence)
    condition = condition_to_str(alternative_section.condition)
    source_section = alternative_section.source.reference.section
    source = _get_section_title_or_error(source_section.path, am, source_section.titles_sequence)
    new_version = _constrain(_wrap_in_paragraphs(extract_markdown_text(alternative_section.new_text, level=1)))
    href = f'{current_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'{current_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    return [str(rank), reference_str, condition, source, new_version, edit, copy]


def _get_alternative_section_table(
    parametrization: Parametrization, am: ArreteMinisteriel, current_page: str
) -> Component:
    header = ['#', 'Paragraphe visé', 'Condition', 'Source', 'Nouvelle version', '', '']
    rows = [
        _alternative_section_to_row(row, am, rank, current_page)
        for rank, row in enumerate(parametrization.alternative_sections)
    ]
    return table_component([header], rows, class_name='table-sm')


def _get_add_condition_button(parent_page: str, status: AMStatus) -> Component:
    state = ButtonState.NORMAL_LINK if status == status.PENDING_PARAMETRIZATION else ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_CONDITION.value}'
    return html.Div(link_button('+ Nouveau', href, state), style={'margin-bottom': '35px'})


def _get_add_alternative_section_button(parent_page: str, status: AMStatus) -> Component:
    state = ButtonState.NORMAL_LINK if status == status.PENDING_PARAMETRIZATION else ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}'
    return html.Div(link_button('+ Nouveau', href, state), style={'margin-bottom': '35px'})


def _get_am_component_with_toc(am: ArreteMinisteriel) -> Component:
    return html.Div(
        [
            html.Div([summary_component(am_to_text(am), True)], className='col-3'),
            html.Div(am_component(am, [], 5), className='col-9'),
        ],
        className='row',
        style={'margin': '0px'},
    )


def _get_parametrization_summary(
    parent_page: str, status: AMStatus, parametrization: Parametrization, am: Optional[ArreteMinisteriel]
) -> Component:
    if status != AMStatus.PENDING_PARAMETRIZATION:
        return html.Div([])
    if not am:
        return error_component('AM introuvable, impossible d\'afficher les paramètres.')
    return html.Div(
        [
            html.H4('Conditions de non-application'),
            _get_non_application_table(parametrization, am, parent_page),
            _get_add_condition_button(parent_page, status),
            html.H4('Paragraphes alternatifs'),
            _get_alternative_section_table(parametrization, am, parent_page),
            _get_add_alternative_section_button(parent_page, status),
            html.H4('Texte'),
            _get_am_component_with_toc(am),
        ],
        style={
            'position': 'sticky',
            'top': '0px',
            'bottom': '0',
            'height': '75vh',
            'overflow-y': 'auto',
        },
    )


def _keep_defined_and_join(elements: List[Optional[Union[str, Component]]]) -> List[Union[str, Component]]:
    return [el_lb for el in elements if el is not None for el_lb in (el, html.Br())]


def _extract_char_positions(str_: str, char: str) -> Set[int]:
    return {i for i, ch in enumerate(str_) if ch == char}


def _diffline_is_special(line: Optional[str]) -> bool:
    return bool(line and line[:1] in ('-', '+', '?'))


def _extract_diff_component(diff: str, next_diff: Optional[str]) -> Optional[Union[Component, str]]:
    if diff[:1] == '+':
        symbol = '+'
        strong_color = '#acf2bd'
        light_color = '#e6ffec'
    elif diff[:1] == '-':
        symbol = '-'
        strong_color = '#fdb8c0'
        light_color = '#feeef0'
    else:
        raise ValueError(f'Expecting diff to start with "+" or "-", received {diff[:1]}')
    to_surline = _extract_char_positions(next_diff, symbol) if next_diff and next_diff[0] == '?' else set()
    rich_diff = surline_text(diff, to_surline, {'background-color': strong_color})
    return html.Span(rich_diff, style={'background-color': light_color})


def _ellipse() -> Component:
    return html.Span('[...]', style={'color': 'grey'})


def _diff_to_component(
    diff: str, previous_diff: Optional[str], next_diff: Optional[str]
) -> Optional[Union[Component, str]]:
    if not _diffline_is_special(diff):
        if _diffline_is_special(previous_diff):
            if _diffline_is_special(next_diff):
                return diff
            return html.Span([diff, html.Br(), _ellipse()])
        if _diffline_is_special(next_diff):
            return diff
        return None
    if diff[:1] in ('+', '-'):
        return _extract_diff_component(diff, next_diff)
    if diff[:1] == '?':
        return None
    raise ValueError(f'Unexpected diff format "{diff}"')


def _build_diff_component(text_1: List[str], text_2: List[str]) -> Component:
    diffs = list(difflib.Differ().compare(text_1, text_2))
    components = _keep_defined_and_join(
        [
            _diff_to_component(diff, previous, next_)
            for diff, previous, next_ in zip(diffs, [None, *diffs[:-1]], [*diffs[1:], None])
        ]
    )
    if not components:
        return html.P('Pas de différences.')
    return html.Div(components)


def _extract_tables(text: Union[ArreteMinisteriel, StructuredText]) -> List[Table]:
    in_sections = [tb for sec in text.sections for tb in _extract_tables(sec)]
    if isinstance(text, ArreteMinisteriel):
        return in_sections
    return [al.table for al in text.outer_alineas if al.table] + in_sections


def _extract_nb_cells(table: Table) -> int:
    return sum([len(row.cells) for row in table.rows])


def _build_difference_in_tables_component(initial_am: ArreteMinisteriel, current_am: ArreteMinisteriel) -> Component:
    initial_tables_nb_cells = list(map(_extract_nb_cells, _extract_tables(initial_am)))
    current_tables_nb_cells = list(map(_extract_nb_cells, _extract_tables(current_am)))
    if initial_tables_nb_cells == current_tables_nb_cells:
        return html.Div()
    return html.Div(
        [
            html.H4('Différences liées aux tableaux'),
            error_component(
                'Les tableaux du texte transformé sont différents des tableaux d\'origine.'
                f'\nNombre de cellules par tableau dans le texte d\'origine: {initial_tables_nb_cells}'
                f'\nNombre de cellules par tableau dans le texte transformé: {current_tables_nb_cells}'
            ),
        ]
    )


def _build_am_diff_component(initial_am: ArreteMinisteriel, current_am: ArreteMinisteriel) -> Component:
    diff_tables = _build_difference_in_tables_component(initial_am, current_am)
    diff_lines = _build_diff_component(
        extract_text_lines(am_to_text(initial_am)), extract_text_lines(am_to_text(current_am))
    )
    return html.Div([diff_tables, diff_lines])


def _structure_am_component(am: ArreteMinisteriel) -> Component:
    style = {
        'position': 'sticky',
        'top': '0px',
        'bottom': '0',
        'height': '70vh',
        'overflow-y': 'auto',
    }
    return html.Div(
        [html.H4('Version actuelle de l\'AM'), html.Div([_get_am_component_with_toc(am)], style=style)],
        hidden=False,
        id=_STRUCTURE_TABS_AM,
    )


def _diff_tab_content(initial_am: ArreteMinisteriel, current_am: Optional[ArreteMinisteriel]) -> Component:
    if not current_am:
        child = 'Pas de modifications de structuration par rapport à l\'arrêté d\'origine.'
    else:
        child = _build_am_diff_component(initial_am, current_am)
    return html.Div(
        [html.H4('Liste des différences avec le texte d\'origine'), child], hidden=True, id=_STRUCTURE_TABS_DIFF
    )


def _nav(tab_title_and_ids: List[Tuple[str, str]]) -> Component:
    tabs = [
        html.A(title, href='#', id=id_, className='nav-link' + (' active' if i == 0 else ''))
        for i, (title, id_) in enumerate(tab_title_and_ids)
    ]
    return html.Div([html.Div(tabs, className='nav flex-column nav-pills me-3')], className='d-flex align-items-start')


def _structure_tabs(initial_am: ArreteMinisteriel, current_am: Optional[ArreteMinisteriel]) -> Component:
    am_to_display = current_am or initial_am
    tabs = [('AM', _STRUCTURE_TABS_AM_TAB), ('Diff', _STRUCTURE_TABS_DIFF_TAB)]
    nav = _nav(tabs)
    return html.Div(
        [
            html.Div(nav, className='col-1'),
            html.Div(
                [_diff_tab_content(initial_am, current_am), _structure_am_component(am_to_display)], className='col-11'
            ),
        ],
        className='row',
    )


def _get_structure_validation_diff(am_id: str, status: AMStatus) -> Component:
    if status != status.PENDING_STRUCTURE_VALIDATION:
        return html.Div()
    initial_am = load_initial_am(am_id)
    if not initial_am:
        return html.Div('AM introuvable.')
    return _structure_tabs(initial_am, load_structured_am(am_id))


def _create_if_inexistent(folder: str) -> None:
    if not os.path.exists(folder):
        os.mkdir(folder)


def _load_am(path: str) -> ArreteMinisteriel:
    return ArreteMinisteriel.from_dict(json.load(open(path)))


def _load_parametric_ams(folder: str) -> Dict[str, ArreteMinisteriel]:
    return {file_: _load_am(os.path.join(folder, file_)) for file_ in os.listdir(folder)}


def _generate_versions_if_empty(am_id: str, folder: str) -> None:
    if os.listdir(folder):
        return
    _generate_and_dump_am_version(am_id)


def _list_parametric_texts(am_id: str, am_status: AMStatus) -> Component:
    if am_status != AMStatus.VALIDATED:
        return html.Div()
    folder = get_parametric_ams_folder(am_id)
    _create_if_inexistent(folder)
    _generate_versions_if_empty(am_id, folder)
    filename_to_am = _load_parametric_ams(folder)
    return parametric_am_list_component(filename_to_am, _PREFIX)


def _final_parametric_texts_component(am_id: str, am_status: AMStatus) -> Component:
    return html.Div([html.H3('Versions finales'), _list_parametric_texts(am_id, am_status)])


def _get_final_parametric_texts_component(am_id: str, am_status: AMStatus) -> Component:
    return html.Div([_final_parametric_texts_component(am_id, am_status)], hidden=am_status != AMStatus.VALIDATED)


def _get_initial_am_component(
    am_id: str, am_status: AMStatus, am: Optional[ArreteMinisteriel], am_page: str
) -> Component:
    if am_status != AMStatus.PENDING_INITIALIZATION:
        return html.Div()
    return am_init_tab(am_id, am, am_page)


def _deduce_step_classname(rank: int, status: AMStatus) -> str:
    return 'breadcrumb-item' + (' ' if rank == status.step() else ' active') + (' ' if rank < status.step() else '')


def _build_component_based_on_status(
    am_id: str, parent_page: str, am_status: AMStatus, parametrization: Parametrization, am: Optional[ArreteMinisteriel]
) -> Component:
    children = [
        html.Div(
            [
                _get_initial_am_component(am_id, am_status, am, parent_page),
                _get_structure_validation_diff(am_id, am_status),
                _get_parametrization_summary(parent_page, am_status, parametrization, am),
                _get_final_parametric_texts_component(am_id, am_status),
            ],
            style={'margin-bottom': '100px'},
        ),
        _get_buttons(am_status, parent_page),
    ]
    return html.Div(children)


def _make_am_index_component(
    am_id: str, am_status: AMStatus, parent_page: str, parametrization: Parametrization, am: Optional[ArreteMinisteriel]
) -> Component:
    return _build_component_based_on_status(am_id, parent_page, am_status, parametrization, am)


def _get_nav(status: AMStatus) -> Component:
    texts = ['1. Initilisation', '2. Structuration', '3. Paramétrage', '4. Relecture']
    lis = [html.Li(text, className=_deduce_step_classname(i, status)) for i, text in enumerate(texts)]
    return html.Ol(
        className='breadcrumb',
        children=lis,
        style={'padding': '7px', 'padding-left': '15px', 'padding-right': '15px', 'font-weight': '300'},
    )


def _get_title_component(
    am_id: str, am_metadata: Optional[AMMetadata], parent_page: str, am_status: AMStatus
) -> Component:
    nav = html.Div(_get_nav(am_status), className='col-6')
    am_id = (am_metadata.nor or am_metadata.cid) if am_metadata else am_id
    am_backlink = html.Div(dcc.Link(html.H2(f'Arrêté ministériel {am_id}'), href=parent_page), className='col-6')
    row = html.Div(html.Div([am_backlink, nav], className='row'), className='container')
    return html.Div(row, className='am_title')


def _get_body_component(
    am_id: str, parent_page: str, am: Optional[ArreteMinisteriel], am_status: AMStatus, parametrization: Parametrization
) -> Component:
    if not am and am_status != AMStatus.PENDING_INITIALIZATION:
        return html.P('Arrêté introuvable.')
    return _make_am_index_component(am_id, am_status, parent_page, parametrization, am)


def _get_subpage_content(route: str, operation_id: AMOperation) -> Component:
    if operation_id == AMOperation.INIT:
        return am_init_router(route)
    if operation_id in (AMOperation.ADD_ALTERNATIVE_SECTION, AMOperation.ADD_CONDITION):
        return parametrization_router(route)
    if operation_id == AMOperation.EDIT_STRUCTURE:
        return structure_router(route)
    raise NotImplementedError(f'Operation {operation_id} not handled')


def _page(am_id: str, current_page: str) -> Component:
    am_metadata = ID_TO_AM_MD.get(am_id)
    am_status = load_am_status(am_id)
    am = load_structured_am(am_id) or load_initial_am(am_id)  # Fetch initial AM if no parametrization ever done.
    parametrization = load_parametrization(am_id) or Parametrization([], [])
    body = html.Div(
        _get_body_component(am_id, current_page, am, am_status, parametrization), className='am_page_content'
    )
    return html.Div(
        [
            _get_title_component(am_id, am_metadata, current_page, am_status),
            body,
            html.P(am_id, hidden=True, id=f'{_PREFIX}-am-id'),
            html.P(current_page, hidden=True, id=f'{_PREFIX}-current-page'),
        ]
    )


def _page_with_spinner(am_id: str, current_page: str) -> Component:
    return dbc.Spinner(html.Div(_page(am_id, current_page), id=_LOADER))


def _flush_folder(am_id: str) -> None:
    folder = get_parametric_ams_folder(am_id)
    if os.path.exists(folder):
        for file_ in os.listdir(folder):
            os.remove(os.path.join(folder, file_))


def _dump_am_versions(am_id: str, versions: Optional[AMVersions]) -> None:
    if not versions:
        return
    _flush_folder(am_id)
    for version_desc, version in versions.items():
        filename = create_folder_and_generate_parametric_filename(am_id, version_desc)
        write_json(version.to_dict(), filename)


def _generate_and_dump_am_version(am_id: str) -> None:
    final_am = generate_final_am(ID_TO_AM_MD[am_id])
    _dump_am_versions(am_id, final_am.am_versions)


def _add_titles_sequences(am_id: str) -> None:
    try:
        parametrization = load_parametrization(am_id)
        am = load_structured_am(am_id) or load_initial_am(am_id)
        if am and parametrization:
            new_parametrization = add_titles_sequences(parametrization, am)
            upsert_new_parametrization(am_id, new_parametrization)
    except Exception:
        warnings.warn(f'Error during titles sequence addition:\n{traceback.format_exc()}')


def _handle_validate_parametrization(am_id: str) -> None:
    _generate_and_dump_am_version(am_id)
    _add_titles_sequences(am_id)


def _handle_validate_structure(am_id: str) -> None:
    parametrization = load_parametrization(am_id)
    if not parametrization:
        return  # parametrization has no risk to be deprecated in this case
    am = load_structured_am(am_id) or load_initial_am(am_id)
    if not am:
        warnings.warn('Should not happen, structure can be validated only for existing texts.')
        return
    try:
        new_parametrization = regenerate_paths(parametrization, am)
    except UndefinedTitlesSequencesError:
        return
    upsert_new_parametrization(am_id, new_parametrization)


def _update_am_status(clicked_button: str, am_id: str) -> None:
    new_status = None
    if clicked_button == _VALIDATE_INITIALIZATION:
        new_status = AMStatus.PENDING_STRUCTURE_VALIDATION
    elif clicked_button == _modal_confirm_button_id('structure'):
        new_status = AMStatus.PENDING_INITIALIZATION
    elif clicked_button == _VALIDATE_STRUCTURE:
        new_status = AMStatus.PENDING_PARAMETRIZATION
    elif clicked_button == _modal_confirm_button_id('parametrization'):
        new_status = AMStatus.PENDING_STRUCTURE_VALIDATION
    elif clicked_button == _VALIDATE_PARAMETRIZATION:
        new_status = AMStatus.VALIDATED
    elif clicked_button == _modal_confirm_button_id('validated'):
        new_status = AMStatus.PENDING_PARAMETRIZATION
    elif clicked_button == _modal_confirm_button_id('reset-structure'):
        delete_structured_am(am_id)
    else:
        raise NotImplementedError(f'Unknown button id {clicked_button}')
    if new_status:
        upsert_am_status(am_id, new_status)
        if config.environment.type == EnvironmentType.PROD:
            send_slack_notification(
                f'AM {am_id} a désormais le statut {new_status.value}', SlackChannel.ENRICHMENT_NOTIFICATIONS
            )
    if clicked_button == _VALIDATE_PARAMETRIZATION:
        _handle_validate_parametrization(am_id)
    if clicked_button == _VALIDATE_STRUCTURE:
        _handle_validate_structure(am_id)
    if clicked_button == _modal_confirm_button_id('parametrization'):
        _add_titles_sequences(am_id)


_BUTTON_IDS = [
    _VALIDATE_INITIALIZATION,
    _modal_confirm_button_id('structure'),
    _VALIDATE_STRUCTURE,
    _modal_confirm_button_id('parametrization'),
    _modal_confirm_button_id('reset-structure'),
    _VALIDATE_PARAMETRIZATION,
    _modal_confirm_button_id('validated'),
]
_INPUTS = [Input(id_, 'n_clicks') for id_ in _BUTTON_IDS] + [
    Input(f'{_PREFIX}-am-id', 'children'),
    Input(f'{_PREFIX}-current-page', 'children'),
]


@app.callback(Output(_LOADER, 'children'), _INPUTS, prevent_initial_call=True)
def _handle_click(*args):
    all_n_clicks = args[: len(_BUTTON_IDS)]
    am_id, current_page = args[len(_BUTTON_IDS) :]
    for id_, n_clicks in zip(_BUTTON_IDS, all_n_clicks):
        if (n_clicks or 0) >= 1:
            try:
                _update_am_status(id_, am_id)
            except Exception:  # pylint: disable = broad-except
                return error_component(traceback.format_exc())
            return _page_with_spinner(am_id, current_page)
    raise PreventUpdate


@app.callback(
    Output(_modal_id(), 'is_open'),
    Input(_modal_button_id(), 'n_clicks'),
    Input(_close_modal_button_id(), 'n_clicks'),
    State(_modal_id(), 'is_open'),
    prevent_initial_call=True,
)
def _toggle_modal(n_clicks, n_clicks_close, is_open):
    if n_clicks or n_clicks_close:
        return not is_open
    return False


@app.callback(
    Output(_STRUCTURE_TABS_AM, 'hidden'),
    Output(_STRUCTURE_TABS_DIFF, 'hidden'),
    Output(_STRUCTURE_TABS_AM_TAB, 'className'),
    Output(_STRUCTURE_TABS_DIFF_TAB, 'className'),
    Input(_STRUCTURE_TABS_AM_TAB, 'n_clicks_timestamp'),
    Input(_STRUCTURE_TABS_DIFF_TAB, 'n_clicks_timestamp'),
    prevent_initial_call=True,
)
def _structure_tabs_click_handler(click_timestamp_am_tab, click_timestamp_diff_tab):
    if (click_timestamp_am_tab or 0) > (click_timestamp_diff_tab or 0):
        return False, True, 'nav-link active', 'nav-link'
    else:
        return True, False, 'nav-link', 'nav-link active'


parametric_am_list_callbacks(app, _PREFIX)


def router(parent_page: str, route: str) -> Component:
    am_id, operation_id, _ = _extract_am_id_and_operation(route)
    if am_id not in ID_TO_AM_MD:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    am_metadata = ID_TO_AM_MD[am_id]
    current_page = parent_page + '/' + am_id
    if operation_id:
        am_status = load_am_status(am_id)
        subpage_component = _get_subpage_content(route, operation_id)
        return html.Div([_get_title_component(am_id, am_metadata, current_page, am_status), subpage_component])
    return _page_with_spinner(am_id, current_page)
