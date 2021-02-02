import difflib
import os
import traceback
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import MATCH, Input, Output, State
from dash.development.base_component import Component
from dash.exceptions import PreventUpdate
from lib.am_to_markdown import extract_markdown_text
from lib.config import EnvironmentType, config
from lib.data import AMMetadata, ArreteMinisteriel, Ints, StructuredText, Table, am_to_text
from lib.generate_final_am import AMVersions, generate_final_am
from lib.parametrization import AlternativeSection, NonApplicationCondition, Parametrization, condition_to_str
from lib.paths import create_folder_and_generate_parametric_filename, get_parametric_ams_folder
from lib.utils import SlackChannel, send_slack_notification, write_json

from back_office.am_init_edition import router as am_init_router
from back_office.am_init_tab import am_init_tab
from back_office.app_init import app
from back_office.components import ButtonState, button, error_component, link_button
from back_office.components.am_component import am_component
from back_office.components.summary_component import summary_component
from back_office.display_am import router as display_am_router
from back_office.fetch_data import (
    load_am_status,
    load_initial_am,
    load_parametrization,
    load_structured_am,
    upsert_am_status,
)
from back_office.parametrization_edition import router as parametrization_router
from back_office.structure_edition import router as structure_router
from back_office.utils import ID_TO_AM_MD, AMOperation, AMStatus, get_traversed_titles, safe_get_section

_VALIDATE_INITIALIZATION = 'am-page-validate-init'
_INVALIDATE_INITIALIZATION = 'am-page-invalidate-initialization'
_VALIDATE_STRUCTURE = 'am-page-validate-structure'
_INVALIDATE_STRUCTURE = 'am-page-invalidate-structure'
_VALIDATE_PARAMETRIZATION = 'am-page-validate-parametrization'
_INVALIDATE_PARAMETRIZATION = 'am-page-invalidate-parametrization'
_LOADER = 'am-page-loading-output'


def _modal_confirm_button_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': 'am-page-modal-confirm-button', 'text_id': step or MATCH}


def _modal_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': 'am-page-modal', 'text_id': step or MATCH}


def _modal_button_id(step: Optional[str] = None) -> Dict[str, Any]:
    return {'type': 'am-page-modal-button', 'text_id': step or MATCH}


def _extract_am_id_and_operation(pathname: str) -> Tuple[str, Optional[AMOperation], str]:
    pieces = pathname.split('/')[1:]
    if len(pieces) == 0:
        raise ValueError('Unexpected')
    if len(pieces) == 1:
        return pieces[0], None, ''
    return pieces[0], AMOperation(pieces[1]), '/'.join(pieces[2:])


def _get_edit_structure_button(parent_page: str, am_status: AMStatus) -> Component:
    href = f'{parent_page}/{AMOperation.EDIT_STRUCTURE.value}'
    state = ButtonState.NORMAL_LINK if am_status == am_status.PENDING_STRUCTURE_VALIDATION else ButtonState.HIDDEN
    return link_button('Éditer', href, state)


def _get_am_initialization_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    return (None, button('Valider le texte initial', id_=_VALIDATE_INITIALIZATION, state=ButtonState.NORMAL))


def _get_confirmation_modal(modal_body: Union[str, Component], step: str) -> Component:
    modal = dbc.Modal(
        [
            dbc.ModalHeader('Confirmation'),
            dbc.ModalBody(modal_body),
            dbc.ModalFooter(
                html.Button('Confirmer', id=_modal_confirm_button_id(step), className='ml-auto btn btn-danger')
            ),
        ],
        id=_modal_id(step),
    )
    return html.Div(
        [button('Étape précédente', id_=_modal_button_id(step), state=ButtonState.NORMAL_LIGHT), modal],
        style={'display': 'inline-block'},
    )


def _get_structure_validation_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    modal_content = (
        'Êtes-vous sûr de vouloir retourner à la phase d\'initialisation du texte ? Ceci est '
        'déconseillé lorsque l\'AM provient de Légifrance ou que la structure a déjà été modifiée.'
    )
    return (
        _get_confirmation_modal(modal_content, 'structure'),
        button('Valider la structure', id_=_VALIDATE_STRUCTURE, state=ButtonState.NORMAL),
    )


def _get_parametrization_edition_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    modal_content = (
        'Êtes-vous sûr de vouloir retourner à la phase de structuration du texte ? Si des paramètres '
        'ont déjà été renseignés, cela peut désaligner certains paramétrages.'
    )
    return (
        _get_confirmation_modal(modal_content, 'parametrization'),
        button('Valider la paramétrisation', id_=_VALIDATE_PARAMETRIZATION, state=ButtonState.NORMAL),
    )


def _get_validated_buttons() -> Tuple[Optional[Component], Optional[Component]]:
    modal_content = 'Retourner à la paramétrisation ?'
    return (_get_confirmation_modal(modal_content, 'validated'), None)


def _inline_buttons(button_left: Optional[Component], button_right: Optional[Component]) -> List[Component]:
    left = html.Div(button_left, style={'display': 'inline-block', 'float': 'left'})
    right = html.Div(button_right, style={'display': 'inline-block', 'float': 'right'})
    return [left, right]


def _get_buttons(am_status: AMStatus) -> Component:
    successive_buttons = [
        _get_am_initialization_buttons(),
        _get_structure_validation_buttons(),
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


def _deduce_step_classname(rank: int, status: AMStatus) -> str:
    return (
        'list-group-item text-center flex-fill '
        + (' list-group-item-secondary' if rank == status.step() else '')
        + (' ' if rank < status.step() else '')
    )


def _get_nav(status: AMStatus) -> Component:
    texts = ['Initilisation', 'Structuration', 'Paramétrisation', 'Relecture']
    lis = [html.Li(text, className=_deduce_step_classname(i, status)) for i, text in enumerate(texts)]
    return html.Ul(className='list-group list-group-horizontal', children=lis, style={'margin-bottom': '30px'})


def _human_alinea_tuple(ints: Optional[List[int]]) -> str:
    if not ints:
        return 'Tous'
    return ', '.join(map(str, sorted(ints)))


def _application_condition_to_row(
    non_application_condition: NonApplicationCondition, am: ArreteMinisteriel, rank: int, current_page: str
) -> Component:
    reference_str = _get_section_title_or_error(non_application_condition.targeted_entity.section.path, am)
    alineas = _human_alinea_tuple(non_application_condition.targeted_entity.outer_alinea_indices)
    condition = condition_to_str(non_application_condition.condition)
    source = _get_section_title_or_error(non_application_condition.source.reference.section.path, am)
    href = f'{current_page}/{AMOperation.ADD_CONDITION.value}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'{current_page}/{AMOperation.ADD_CONDITION.value}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    cells = [rank, reference_str, alineas, condition, source, edit, copy]
    return html.Tr([html.Td(cell) for cell in cells])


def _get_non_application_table(parametrization: Parametrization, am: ArreteMinisteriel, current_page: str) -> Component:
    header_names = ['#', 'Paragraphe visé', 'Alineas visés', 'Condition', 'Source', '', '']
    header = html.Thead(html.Tr([html.Th(name) for name in header_names]))
    body = html.Tbody(
        [
            _application_condition_to_row(row, am, rank, current_page)
            for rank, row in enumerate(parametrization.application_conditions)
        ]
    )
    return html.Table([header, body], className='table table-hover')


def _wrap_in_paragraphs(strs: List[str]) -> Component:
    return html.Div([html.P(str_) for str_ in strs])


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


def _get_section_title_or_error(path: Ints, am: ArreteMinisteriel) -> Component:
    titles = get_traversed_titles(path, am)
    section_id = _get_target_section_id(path, am)
    style = {}
    if titles is None:
        style = {'color': 'red'}
        title = 'Introuvable, ce paramètre doit être modifié.'
    else:
        shortened_titles = [_shorten_text(title) for title in titles]
        joined_titles = ' / '.join(shortened_titles)
        title = html.A(joined_titles, href=f'#{section_id}') if section_id else joined_titles
    return html.Span(title, style=style)


def _alternative_section_to_row(
    alternative_section: AlternativeSection, am: ArreteMinisteriel, rank: int, current_page: str
) -> Component:
    reference_str = _get_section_title_or_error(alternative_section.targeted_section.path, am)
    condition = condition_to_str(alternative_section.condition)
    source = _get_section_title_or_error(alternative_section.source.reference.section.path, am)
    new_version = _wrap_in_paragraphs(extract_markdown_text(alternative_section.new_text, level=1))
    href = f'{current_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}/{rank}'
    edit = link_button('Éditer', href=href, state=ButtonState.NORMAL_LINK)
    href_copy = f'{current_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}/{rank}/copy'
    copy = link_button('Copier', href=href_copy, state=ButtonState.NORMAL_LINK)
    cells = [rank, reference_str, condition, source, new_version, edit, copy]
    return html.Tr([html.Td(cell) for cell in cells])


def _get_alternative_section_table(
    parametrization: Parametrization, am: ArreteMinisteriel, current_page: str
) -> Component:
    header_names = ['#', 'Paragraphe visé', 'Condition', 'Source', 'Nouvelle version', '', '']
    header = html.Thead(html.Tr([html.Th(name) for name in header_names]))
    body = html.Tbody(
        [
            _alternative_section_to_row(row, am, rank, current_page)
            for rank, row in enumerate(parametrization.alternative_sections)
        ]
    )
    return html.Table([header, body], className='table table-hover')


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
            html.Div([summary_component(am_to_text(am), False)], className='col-3'),
            html.Div(am_component(am, [], 5), className='col-9'),
        ],
        className='row',
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
        ]
    )


def _keep_defined_and_join(elements: List[Optional[Union[str, Component]]]) -> List[Union[str, Component]]:
    return [el_lb for el in elements if el is not None for el_lb in (el, html.Br())]


def _extract_char_positions(str_: str, char: str) -> Set[int]:
    return {i for i, ch in enumerate(str_) if ch == char}


def _surline_text(str_: str, positions_to_surline: Set[int], style: Dict[str, Any]) -> Union[Component, str]:
    if not positions_to_surline:
        return str_
    surline = False
    current_word = ''
    components: List[Union[Component, str]] = []
    for position, char in enumerate(str_):
        if position in positions_to_surline:
            if not surline:
                components.append(current_word)
                current_word = char
                surline = True
            else:
                current_word += char
        else:
            if surline:
                components.append(html.Span(current_word, style=style))
                surline = False
                current_word = char
            else:
                current_word += char
    if surline:
        components.append(html.Span(current_word, style=style))
    else:
        components.append(current_word)
    return html.Span(components)


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
    rich_diff = _surline_text(diff, to_surline, {'background-color': strong_color})
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
    return html.Div([html.H4('Liste des différences avec le texte d\'origine'), *components])


def _extract_text_lines(text: StructuredText, level: int = 0) -> List[str]:
    title_lines = ['#' * level + (' ' if level else '') + text.title.text.strip()]
    alinena_lines = [line.strip() for al in text.outer_alineas for line in al.text.split('\n')]
    section_lines = [line for sec in text.sections for line in _extract_text_lines(sec, level + 1)]
    return title_lines + alinena_lines + section_lines


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
        _extract_text_lines(am_to_text(initial_am)), _extract_text_lines(am_to_text(current_am))
    )
    return html.Div([diff_tables, diff_lines])


def _get_structure_validation_diff(am_id: str, status: AMStatus, parent_page: str) -> Component:
    if status != status.PENDING_STRUCTURE_VALIDATION:
        return html.Div()
    initial_am = load_initial_am(am_id)
    if not initial_am:
        return html.Div('AM introuvable.')
    current_am = load_structured_am(am_id)
    button = _get_edit_structure_button(parent_page, status)
    edit_button = html.Div(
        _get_edit_structure_button(parent_page, status),
        style={
            'display': 'inline-block',
            'position': 'fixed',
            'bottom': '0px',
            'left': '25%',
            'z-index': '10',
            'width': '50%',
            'text-align': 'center',
            'padding-bottom': '10px',
            'padding-top': '10px',
            'margin': 'auto',
        },
    )
    if not current_am:
        diff = html.Div(
            ['Pas de modifications de structuration par rapport à l\'arrêté d\'origine.', html.Br(), button]
        )
    else:
        diff = html.Div([_build_am_diff_component(initial_am, current_am)])
    am_to_display = current_am or initial_am

    am_component = html.Div(
        [html.Br(), html.H4('Version actuelle de l\'AM'), _get_am_component_with_toc(am_to_display)]
    )
    return html.Div([diff, am_component, edit_button])


def _create_if_inexistent(folder: str) -> None:
    if not os.path.exists(folder):
        os.mkdir(folder)


def _generate_versions_if_empty(am_id: str, folder: str) -> None:
    if os.listdir(folder):
        return
    _generate_and_dump_am_version(am_id)


def _get_parametric_texts_list(am_id: str, page_url: str, am_status: AMStatus) -> Component:
    folder = get_parametric_ams_folder(am_id)
    _create_if_inexistent(folder)
    if am_status == AMStatus.VALIDATED:
        _generate_versions_if_empty(am_id, folder)
    prefix_url = f'{page_url}/{AMOperation.DISPLAY_AM.value}'
    lis = [html.Li(dcc.Link(file_, href=f'{prefix_url}/{file_}')) for file_ in sorted(os.listdir(folder))]
    return html.Ul(lis)


def _final_parametric_texts_component(am_id: str, page_url: str, am_status: AMStatus) -> Component:
    return html.Div([html.H3('Versions finales'), _get_parametric_texts_list(am_id, page_url, am_status)])


def _get_final_parametric_texts_component(am_id: str, am_status: AMStatus, page_url: str) -> Component:
    return html.Div(
        [_final_parametric_texts_component(am_id, page_url, am_status)], hidden=am_status != AMStatus.VALIDATED
    )


def _get_initial_am_component(
    am_id: str, am_status: AMStatus, am: Optional[ArreteMinisteriel], am_page: str
) -> Component:
    if am_status != AMStatus.PENDING_INITIALIZATION:
        return html.Div()
    return am_init_tab(am_id, am, am_page)


def _build_component_based_on_status(
    am_id: str, parent_page: str, am_status: AMStatus, parametrization: Parametrization, am: Optional[ArreteMinisteriel]
) -> Component:
    children = [
        _get_nav(am_status),
        html.Div(
            [
                _get_initial_am_component(am_id, am_status, am, parent_page),
                _get_structure_validation_diff(am_id, am_status, parent_page),
                _get_parametrization_summary(parent_page, am_status, parametrization, am),
                _get_final_parametric_texts_component(am_id, am_status, parent_page),
            ],
            style={'margin-bottom': '100px'},
        ),
        _get_buttons(am_status),
    ]
    return html.Div(children)


def _make_am_index_component(
    am_id: str, am_status: AMStatus, parent_page: str, parametrization: Parametrization, am: Optional[ArreteMinisteriel]
) -> Component:
    return _build_component_based_on_status(am_id, parent_page, am_status, parametrization, am)


def _get_title_component(am_id: str, am_metadata: Optional[AMMetadata], parent_page: str) -> Component:
    am_id = (am_metadata.nor or am_metadata.cid) if am_metadata else am_id
    return html.Div(dcc.Link(html.H2(f'Arrêté ministériel {am_id}'), href=parent_page), className='am_title')


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
    if operation_id == AMOperation.DISPLAY_AM:
        return display_am_router(route)
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
            _get_title_component(am_id, am_metadata, current_page),
            body,
            html.P(am_id, hidden=True, id='am-page-am-id'),
            html.P(current_page, hidden=True, id='am-page-current-page'),
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


def _update_am_status(clicked_button: str, am_id: str) -> None:
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
    else:
        raise NotImplementedError(f'Unknown button id {clicked_button}')
    upsert_am_status(am_id, new_status)
    if config.environment.type == EnvironmentType.PROD:
        send_slack_notification(
            f'AM {am_id} a désormais le statut {new_status.value}', SlackChannel.ENRICHMENT_NOTIFICATIONS
        )
    if clicked_button == _VALIDATE_PARAMETRIZATION:
        _generate_and_dump_am_version(am_id)


_BUTTON_IDS = [
    _VALIDATE_INITIALIZATION,
    _modal_confirm_button_id('structure'),
    _VALIDATE_STRUCTURE,
    _modal_confirm_button_id('parametrization'),
    _VALIDATE_PARAMETRIZATION,
    _modal_confirm_button_id('validated'),
]
_INPUTS = [Input(id_, 'n_clicks') for id_ in _BUTTON_IDS] + [
    Input('am-page-am-id', 'children'),
    Input('am-page-current-page', 'children'),
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
    State(_modal_id(), 'is_open'),
    prevent_initial_call=True,
)
def _toggle_modal(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return False


def router(parent_page: str, route: str) -> Component:
    am_id, operation_id, _ = _extract_am_id_and_operation(route)
    if am_id not in ID_TO_AM_MD:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    am_metadata = ID_TO_AM_MD[am_id]
    current_page = parent_page + '/' + am_id
    if operation_id:
        subpage_component = _get_subpage_content(route, operation_id)
        return html.Div([_get_title_component(am_id, am_metadata, current_page), subpage_component])
    return _page_with_spinner(am_id, current_page)
