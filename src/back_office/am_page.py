import difflib
import os
import traceback
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from lib.am_to_markdown import extract_markdown_text
from lib.data import AMMetadata, ArreteMinisteriel, Ints, StructuredText, am_to_text
from lib.generate_final_am import AMVersions, generate_final_am
from lib.parametrization import AlternativeSection, NonApplicationCondition, Parametrization, condition_to_str
from lib.paths import create_folder_and_generate_parametric_filename, get_parametric_ams_folder
from lib.utils import write_json

from back_office.components import error_component
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
from back_office.utils import ID_TO_AM_MD, AMOperation, AMStatus, get_section_title
from back_office.app_init import app

_VALIDATE_STRUCTURE_BUTTON_ID = 'am-page-validate-structure'
_INVALIDATE_STRUCTURE_BUTTON_ID = 'am-page-invalidate-structure'
_VALIDATE_PARAMETRIZATION_BUTTON_ID = 'am-page-validate-parametrization'
_INVALIDATE_PARAMETRIZATION_BUTTON_ID = 'am-page-invalidate-parametrization'
_LOADER = 'am-page-loading-output'


def _extract_am_id_and_operation(pathname: str) -> Tuple[str, Optional[AMOperation], str]:
    pieces = pathname.split('/')[1:]
    if len(pieces) == 0:
        raise ValueError('Unexpected')
    if len(pieces) == 1:
        return pieces[0], None, ''
    return pieces[0], AMOperation(pieces[1]), '/'.join(pieces[2:])


def _inline_buttons(buttons: List[Component]) -> Component:
    return html.P(buttons, style=dict(display='flex'))


class _ButtonState(Enum):
    NORMAL = 0
    DISABLED = 1
    HIDDEN = 2


def _button_with_id(
    text: str, state: _ButtonState, id_: Optional[str] = None, className: str = 'btn btn-primary'
) -> html.Button:
    disabled = state != _ButtonState.NORMAL
    hidden = state == _ButtonState.HIDDEN
    if id_:
        return html.Button(
            text,
            id=id_,
            disabled=disabled,
            style={'margin': '5px'},
            className=className,
            n_clicks=0,
            hidden=hidden,
        )
    return html.Button(text, disabled=disabled, style={'margin': '5px'}, className=className, n_clicks=0, hidden=hidden)


def _link_button(
    text: str,
    href: str,
    state: _ButtonState,
    className: str = 'btn btn-primary',
) -> html.Button:
    if state != _ButtonState.NORMAL:
        return _button_with_id(text, state, className=className)
    return dcc.Link(_button_with_id(text, state, className=className), href=href)


def _get_edit_structure_button(parent_page: str, am_status: AMStatus) -> Component:
    href = f'{parent_page}/{AMOperation.EDIT_STRUCTURE.value}'
    state = _ButtonState.NORMAL if am_status == am_status.PENDING_STRUCTURE_VALIDATION else _ButtonState.HIDDEN
    return _link_button('Éditer', href, state, 'btn btn-link')


def _get_validate_structure_button_(state_0: _ButtonState, state_1: _ButtonState) -> Component:
    return html.Div(
        [
            _button_with_id('Valider la structure', id_=_VALIDATE_STRUCTURE_BUTTON_ID, state=state_0),
            _button_with_id('Invalider la structure', id_=_INVALIDATE_STRUCTURE_BUTTON_ID, state=state_1),
        ]
    )


def _get_validate_structure_button(am_status: AMStatus) -> Component:
    if am_status == am_status.PENDING_STRUCTURE_VALIDATION:
        return _get_validate_structure_button_(_ButtonState.NORMAL, _ButtonState.HIDDEN)
    if am_status == am_status.PENDING_PARAMETRIZATION:
        return _get_validate_structure_button_(_ButtonState.HIDDEN, _ButtonState.NORMAL)
    return _get_validate_structure_button_(_ButtonState.HIDDEN, _ButtonState.DISABLED)


def _get_structure_validation_buttons(parent_page: str, am_status: AMStatus) -> Component:
    edit_button = _get_edit_structure_button(parent_page, am_status)
    validate_button = _get_validate_structure_button(am_status)
    return html.Div(_inline_buttons([edit_button, validate_button]), {'margin-bottom': '35px'})


def _get_validate_parametrization_button_(state: _ButtonState) -> Component:
    return _button_with_id('Valider la paramétrisation', id_=_VALIDATE_PARAMETRIZATION_BUTTON_ID, state=state)


def _get_invalidate_parametrization_button(state: _ButtonState) -> Component:
    return _button_with_id('Invalider la paramétrisation', id_=_INVALIDATE_PARAMETRIZATION_BUTTON_ID, state=state)


def _get_validate_parametrization_button(am_status: AMStatus) -> Component:
    if am_status == am_status.PENDING_STRUCTURE_VALIDATION:
        return html.Div(
            [
                _get_validate_parametrization_button_(_ButtonState.HIDDEN),
                _get_invalidate_parametrization_button(_ButtonState.HIDDEN),
            ]
        )
    if am_status == am_status.PENDING_PARAMETRIZATION:
        return html.Div(
            [
                _get_validate_parametrization_button_(_ButtonState.NORMAL),
                _get_invalidate_parametrization_button(_ButtonState.HIDDEN),
            ]
        )
    return html.Div(
        [
            _get_validate_parametrization_button_(_ButtonState.HIDDEN),
            _get_invalidate_parametrization_button(_ButtonState.NORMAL),
        ]
    )


def _get_parametrization_edition_buttons(am_status: AMStatus) -> Component:
    validate_button = _get_validate_parametrization_button(am_status)
    return _inline_buttons([validate_button])


def _get_structure_validation_title(status: AMStatus) -> Component:
    title = 'Edition de structure '
    if status == status.PENDING_STRUCTURE_VALIDATION:
        return html.H3(title)
    return html.H3([title, html.Span('ok', className='badge bg-success', style={'color': 'white'})])


def _get_parametrization_edition_title(status: AMStatus) -> Component:
    title = 'Edition de la paramétrisation '
    if status != status.VALIDATED:
        return html.H3(title)
    return html.H3([title, html.Span('ok', className='badge bg-success', style={'color': 'white'})])


def _human_alinea_tuple(ints: Optional[List[int]]) -> str:
    if not ints:
        return 'Tous'
    return ', '.join(map(str, sorted(ints)))


def _application_condition_to_row(
    non_application_condition: NonApplicationCondition, am: ArreteMinisteriel, rank: int, current_page: str
) -> Component:
    reference_str = _get_section_title_or_error(non_application_condition.targeted_entity.section.path, am)
    alineas = _human_alinea_tuple(non_application_condition.targeted_entity.outer_alinea_indices)
    description = non_application_condition.description
    condition = condition_to_str(non_application_condition.condition)
    source = _get_section_title_or_error(non_application_condition.source.reference.section.path, am)
    href = f'{current_page}/{AMOperation.ADD_CONDITION.value}/{rank}'
    edit = _link_button('Éditer', href=href, className='btn btn-link', state=_ButtonState.NORMAL)
    href_copy = f'{current_page}/{AMOperation.ADD_CONDITION.value}/{rank}/copy'
    copy = _link_button('Copier', href=href_copy, className='btn btn-link', state=_ButtonState.NORMAL)
    cells = [rank, reference_str, alineas, description, condition, source, edit, copy]
    return html.Tr([html.Td(cell) for cell in cells])


def _get_non_application_table(parametrization: Parametrization, am: ArreteMinisteriel, current_page: str) -> Component:
    header_names = ['#', 'Paragraphe visé', 'Alineas visés', 'Description', 'Condition', 'Source', '', '']
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


def _get_section_title_or_error(path: Ints, am: ArreteMinisteriel) -> Component:
    title = get_section_title(path, am)
    style = {}
    if title is None:
        style = {'color': 'red'}
        title = 'Introuvable, ce paramètre doit être modifié.'
    return html.Span(title, style=style)


def _alternative_section_to_row(
    alternative_section: AlternativeSection, am: ArreteMinisteriel, rank: int, current_page: str
) -> Component:
    reference_str = _get_section_title_or_error(alternative_section.targeted_section.path, am)
    description = alternative_section.description
    condition = condition_to_str(alternative_section.condition)
    source = _get_section_title_or_error(alternative_section.source.reference.section.path, am)
    new_version = _wrap_in_paragraphs(extract_markdown_text(alternative_section.new_text, level=1))
    href = f'{current_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}/{rank}'
    edit = _link_button('Éditer', href=href, className='btn btn-link', state=_ButtonState.NORMAL)
    href_copy = f'{current_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}/{rank}/copy'
    copy = _link_button('Copier', href=href_copy, className='btn btn-link', state=_ButtonState.NORMAL)
    cells = [rank, reference_str, description, condition, source, new_version, edit, copy]
    return html.Tr([html.Td(cell) for cell in cells])


def _get_alternative_section_table(
    parametrization: Parametrization, am: ArreteMinisteriel, current_page: str
) -> Component:
    header_names = ['#', 'Paragraphe visé', 'Description', 'Condition', 'Source', 'Nouvelle version', '', '']
    header = html.Thead(html.Tr([html.Th(name) for name in header_names]))
    body = html.Tbody(
        [
            _alternative_section_to_row(row, am, rank, current_page)
            for rank, row in enumerate(parametrization.alternative_sections)
        ]
    )
    return html.Table([header, body], className='table table-hover')


def _get_add_condition_button(parent_page: str, status: AMStatus) -> Component:
    state = _ButtonState.NORMAL if status == status.PENDING_PARAMETRIZATION else _ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_CONDITION.value}'
    return html.Div(_link_button('+ Nouveau', href, state, 'btn btn-link'), {'margin-bottom': '35px'})


def _get_add_alternative_section_button(parent_page: str, status: AMStatus) -> Component:
    state = _ButtonState.NORMAL if status == status.PENDING_PARAMETRIZATION else _ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}'
    return html.Div(_link_button('+ Nouveau', href, state, 'btn btn-link'), {'margin-bottom': '35px'})


def _get_parametrization_summary(
    parent_page: str, status: AMStatus, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    if status != AMStatus.PENDING_PARAMETRIZATION:
        return html.Div([])
    return html.Div(
        [
            html.H4('Conditions de non-application'),
            _get_non_application_table(parametrization, am, parent_page),
            _get_add_condition_button(parent_page, status),
            html.H4('Paragraphes alternatifs'),
            _get_alternative_section_table(parametrization, am, parent_page),
            _get_add_alternative_section_button(parent_page, status),
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
    return html.Div([html.H4('Liste des différences avec le texte d\'origine.'), *components], className='col-10')


def _extract_text_lines(text: StructuredText, level: int = 0) -> List[str]:
    title_lines = ['#' * level + (' ' if level else '') + text.title.text.strip()]
    alinena_lines = [al.text.strip() for al in text.outer_alineas]
    section_lines = [line for sec in text.sections for line in _extract_text_lines(sec, level + 1)]
    return title_lines + alinena_lines + section_lines


def _build_am_diff_component(initial_am: ArreteMinisteriel, current_am: ArreteMinisteriel) -> Component:
    return _build_diff_component(
        _extract_text_lines(am_to_text(initial_am)), _extract_text_lines(am_to_text(current_am))
    )


def _get_structure_validation_diff(am_id: str, status: AMStatus) -> Component:
    if status != status.PENDING_STRUCTURE_VALIDATION:
        return html.Div()
    initial_am = load_initial_am(am_id)
    if not initial_am:
        return html.Div('AM introuvable.')
    current_am = load_structured_am(am_id)
    if not current_am:
        return html.Div('Pas de modifications de structuration.')
    return _build_am_diff_component(initial_am, current_am)


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


def _build_component_based_on_status(
    am_id: str, parent_page: str, am_status: AMStatus, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    children = [
        _get_structure_validation_title(am_status),
        _get_structure_validation_diff(am_id, am_status),
        _get_structure_validation_buttons(parent_page, am_status),
        _get_parametrization_edition_title(am_status),
        _get_parametrization_summary(parent_page, am_status, parametrization, am),
        _get_parametrization_edition_buttons(am_status),
        _get_final_parametric_texts_component(am_id, am_status, parent_page),
    ]
    return html.Div(children)


def _make_am_index_component(
    am_id: str, am_status: AMStatus, parent_page: str, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    return _build_component_based_on_status(am_id, parent_page, am_status, parametrization, am)


def _get_title_component(am_metadata: AMMetadata, parent_page: str) -> Component:
    am_id = am_metadata.nor or am_metadata.cid
    return html.Div(dcc.Link(html.H2(f'Arrêté ministériel {am_id}'), href=parent_page), className='am_title')


def _get_body_component(
    am_id: str, parent_page: str, am: ArreteMinisteriel, am_status: AMStatus, parametrization: Parametrization
) -> Component:
    return _make_am_index_component(am_id, am_status, parent_page, parametrization, am)


def _get_subpage_content(route: str, operation_id: AMOperation) -> Component:
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
    if not am or not am_metadata:
        return html.P('Arrêté introuvable.')
    body = html.Div(
        _get_body_component(am_id, current_page, am, am_status, parametrization), className='am_page_content'
    )
    return html.Div(
        [
            _get_title_component(am_metadata, current_page),
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
    if clicked_button == _VALIDATE_STRUCTURE_BUTTON_ID:
        new_status = AMStatus.PENDING_PARAMETRIZATION
    elif clicked_button == _INVALIDATE_STRUCTURE_BUTTON_ID:
        new_status = AMStatus.PENDING_STRUCTURE_VALIDATION
    elif clicked_button == _VALIDATE_PARAMETRIZATION_BUTTON_ID:
        new_status = AMStatus.VALIDATED
    elif clicked_button == _INVALIDATE_PARAMETRIZATION_BUTTON_ID:
        new_status = AMStatus.PENDING_PARAMETRIZATION
    else:
        raise NotImplementedError(f'Unknown button id {clicked_button}')
    upsert_am_status(am_id, new_status)
    if clicked_button == _VALIDATE_PARAMETRIZATION_BUTTON_ID:
        _generate_and_dump_am_version(am_id)


_BUTTON_IDS = [
    _VALIDATE_STRUCTURE_BUTTON_ID,
    _INVALIDATE_STRUCTURE_BUTTON_ID,
    _VALIDATE_PARAMETRIZATION_BUTTON_ID,
    _INVALIDATE_PARAMETRIZATION_BUTTON_ID,
]
_INPUTS = [Input(id_, 'n_clicks') for id_ in _BUTTON_IDS] + [
    Input('am-page-am-id', 'children'),
    Input('am-page-current-page', 'children'),
]


@app.callback(Output(_LOADER, 'children'), _INPUTS)
def _handle_click(n_clicks_0, n_clicks_1, n_clicks_2, n_clicks_3, am_id, current_page):
    all_n_clicks = n_clicks_0, n_clicks_1, n_clicks_2, n_clicks_3
    for id_, n_clicks in zip(_BUTTON_IDS, all_n_clicks):
        if n_clicks >= 1:
            try:
                _update_am_status(id_, am_id)
            except Exception:  # pylint: disable = broad-except
                return error_component(traceback.format_exc())
    return _page_with_spinner(am_id, current_page)


def router(parent_page: str, route: str) -> Component:
    am_id, operation_id, _ = _extract_am_id_and_operation(route)
    if am_id not in ID_TO_AM_MD:
        return html.P(f'404 - Arrêté {am_id} inconnu')
    am_metadata = ID_TO_AM_MD[am_id]
    current_page = parent_page + '/' + am_id
    if operation_id:
        subpage_component = _get_subpage_content(route, operation_id)
        return html.Div([_get_title_component(am_metadata, current_page), subpage_component])
    return _page_with_spinner(am_id, current_page)
