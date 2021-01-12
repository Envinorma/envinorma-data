from enum import Enum
import difflib
import os
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import dash_core_components as dcc
import dash_html_components as html
from dash.dash import Dash
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from lib.am_to_markdown import extract_markdown_text
from lib.data import ArreteMinisteriel, StructuredText, am_to_text
from lib.parametrization import AlternativeSection, NonApplicationCondition, Parametrization, condition_to_str
from lib.utils import get_structured_text_wip_folder

from back_office.parametrization_edition import add_parametrization_edition_callbacks, router as parametrization_router
from back_office.structure_edition import add_structure_edition_callbacks, make_am_structure_edition_component
from back_office.utils import (
    ID_TO_AM_MD,
    AMOperation,
    AMState,
    AMWorkflowState,
    Page,
    div,
    dump_am_state,
    get_default_structure_filename,
    get_section_title,
    load_am,
    load_am_from_file,
    load_am_state,
    load_parametrization,
)

_VALIDATE_STRUCTURE_BUTTON_ID = 'am-page-validate-structure'
_INVALIDATE_STRUCTURE_BUTTON_ID = 'am-page-invalidate-structure'
_VALIDATE_PARAMETRIZATION_BUTTON_ID = 'am-page-validate-parametrization'
_INVALIDATE_PARAMETRIZATION_BUTTON_ID = 'am-page-invalidate-parametrization'


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
    text: str,
    state: _ButtonState,
    id_: Optional[str] = None,
    className: str = 'btn btn-primary',
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


def _get_edit_structure_button(parent_page: str, am_status: AMWorkflowState) -> Component:
    href = f'{parent_page}/{AMOperation.EDIT_STRUCTURE.value}'
    state = _ButtonState.NORMAL if am_status == am_status.PENDING_STRUCTURE_VALIDATION else _ButtonState.HIDDEN
    return _link_button('Éditer', href, state, 'btn btn-link')


def _get_validate_structure_button_(state_0: _ButtonState, state_1: _ButtonState) -> Component:
    return div(
        [
            _button_with_id('Valider la structure', id_=_VALIDATE_STRUCTURE_BUTTON_ID, state=state_0),
            _button_with_id('Invalider la structure', id_=_INVALIDATE_STRUCTURE_BUTTON_ID, state=state_1),
        ]
    )


def _get_validate_structure_button(am_status: AMWorkflowState) -> Component:
    if am_status == am_status.PENDING_STRUCTURE_VALIDATION:
        return _get_validate_structure_button_(_ButtonState.NORMAL, _ButtonState.HIDDEN)
    if am_status == am_status.PENDING_PARAMETRIZATION:
        return _get_validate_structure_button_(_ButtonState.HIDDEN, _ButtonState.NORMAL)
    return _get_validate_structure_button_(_ButtonState.HIDDEN, _ButtonState.DISABLED)


def _get_structure_validation_buttons(parent_page: str, am_status: AMWorkflowState) -> Component:
    edit_button = _get_edit_structure_button(parent_page, am_status)
    validate_button = _get_validate_structure_button(am_status)
    return div(_inline_buttons([edit_button, validate_button]), {'margin-bottom': '35px'})


def _get_validate_parametrization_button_(state: _ButtonState) -> Component:
    return _button_with_id('Valider la paramétrisation', id_=_VALIDATE_PARAMETRIZATION_BUTTON_ID, state=state)


def _get_invalidate_parametrization_button(state: _ButtonState) -> Component:
    return _button_with_id('Invalider la paramétrisation', id_=_INVALIDATE_PARAMETRIZATION_BUTTON_ID, state=state)


def _get_validate_parametrization_button(am_status: AMWorkflowState) -> Component:
    if am_status == am_status.PENDING_STRUCTURE_VALIDATION:
        return div(
            [
                _get_validate_parametrization_button_(_ButtonState.HIDDEN),
                _get_invalidate_parametrization_button(_ButtonState.HIDDEN),
            ]
        )
    if am_status == am_status.PENDING_PARAMETRIZATION:
        return div(
            [
                _get_validate_parametrization_button_(_ButtonState.NORMAL),
                _get_invalidate_parametrization_button(_ButtonState.HIDDEN),
            ]
        )
    return div(
        [
            _get_validate_parametrization_button_(_ButtonState.HIDDEN),
            _get_invalidate_parametrization_button(_ButtonState.NORMAL),
        ]
    )


def _get_parametrization_edition_buttons(am_status: AMWorkflowState) -> Component:
    validate_button = _get_validate_parametrization_button(am_status)
    return _inline_buttons([validate_button])


def _get_structure_validation_title(status: AMWorkflowState) -> Component:
    title = 'Edition de structure '
    if status == status.PENDING_STRUCTURE_VALIDATION:
        return html.H3(title)
    return html.H3([title, html.Span('ok', className='badge bg-success', style={'color': 'white'})])


def _get_parametrization_edition_title(status: AMWorkflowState) -> Component:
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
    reference_str = get_section_title(non_application_condition.targeted_entity.section.path, am)
    alineas = _human_alinea_tuple(non_application_condition.targeted_entity.outer_alinea_indices)
    description = non_application_condition.description
    condition = condition_to_str(non_application_condition.condition)
    source = get_section_title(non_application_condition.source.reference.section.path, am)
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
    return div([html.P(str_) for str_ in strs])


def _alternative_section_to_row(
    alternative_section: AlternativeSection, am: ArreteMinisteriel, rank: int, current_page: str
) -> Component:
    reference_str = get_section_title(alternative_section.targeted_section.path, am)
    description = alternative_section.description
    condition = condition_to_str(alternative_section.condition)
    source = get_section_title(alternative_section.source.reference.section.path, am)
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


def _get_add_condition_button(parent_page: str, status: AMWorkflowState) -> Component:
    state = _ButtonState.NORMAL if status == status.PENDING_PARAMETRIZATION else _ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_CONDITION.value}'
    return div(_link_button('+ Nouveau', href, state, 'btn btn-link'), {'margin-bottom': '35px'})


def _get_add_alternative_section_button(parent_page: str, status: AMWorkflowState) -> Component:
    state = _ButtonState.NORMAL if status == status.PENDING_PARAMETRIZATION else _ButtonState.HIDDEN
    href = f'{parent_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}'
    return div(_link_button('+ Nouveau', href, state, 'btn btn-link'), {'margin-bottom': '35px'})


def _get_parametrization_summary(
    parent_page: str, status: AMWorkflowState, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    if status != AMWorkflowState.PENDING_PARAMETRIZATION:
        return div([])
    return div(
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


def _load_file_and_get_lines(text_file: str) -> List[str]:
    return _extract_text_lines(am_to_text(load_am_from_file(text_file)))


def _build_diff_component_from_files(text_file_1: str, text_file_2: str) -> Component:
    return _build_diff_component(_load_file_and_get_lines(text_file_1), _load_file_and_get_lines(text_file_2))


def _get_structure_validation_diff(am_id: str, status: AMState) -> Component:
    if status.state != status.state.PENDING_STRUCTURE_VALIDATION:
        return html.Div()
    files = status.structure_draft_filenames
    if len(files) == 0:
        return html.Div('Pas de modifications de structuration.')
    initial_file = get_default_structure_filename(am_id)
    final_file = os.path.join(get_structured_text_wip_folder(am_id), files[-1])
    return _build_diff_component_from_files(initial_file, final_file)


def _build_component_based_on_status(
    am_id: str, parent_page: str, am_state: AMState, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    children = [
        _get_structure_validation_title(am_state.state),
        _get_structure_validation_diff(am_id, am_state),
        _get_structure_validation_buttons(parent_page, am_state.state),
        _get_parametrization_edition_title(am_state.state),
        _get_parametrization_summary(parent_page, am_state.state, parametrization, am),
        _get_parametrization_edition_buttons(am_state.state),
    ]
    return html.Div(children)


def _make_am_index_component(
    am_id: str, am_state: AMState, parent_page: str, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    return _build_component_based_on_status(am_id, parent_page, am_state, parametrization, am)


def _get_subtitle_component(am_id: str, parent_page: str) -> Component:
    return dcc.Link(html.H2(f'Arrêté ministériel {am_id}'), href=parent_page)


def _get_body_component(
    operation_id: Optional[AMOperation],
    am_id: str,
    parent_page: str,
    am: ArreteMinisteriel,
    am_state: AMState,
    parametrization: Parametrization,
) -> Component:
    if not operation_id:
        return _make_am_index_component(am_id, am_state, parent_page, parametrization, am)
    if operation_id == operation_id.EDIT_STRUCTURE:
        return make_am_structure_edition_component(am_id, parent_page, am)
    raise NotImplementedError()


def _router(route: str, parent_page: str) -> Component:
    am_id, operation_id, _ = _extract_am_id_and_operation(route)
    if am_id not in ID_TO_AM_MD:
        return html.P('404 - Arrêté inconnu')
    am_metadata = ID_TO_AM_MD.get(am_id)
    page_title = am_metadata.nor or am_metadata.cid if am_metadata else am_id
    current_page = parent_page + '/' + am_id
    subtitle_component = _get_subtitle_component(page_title, current_page)
    if operation_id in (AMOperation.ADD_ALTERNATIVE_SECTION, AMOperation.ADD_CONDITION):
        return html.Div([subtitle_component, parametrization_router(route)])
    am_state = load_am_state(am_id)
    am = load_am(am_id, am_state)
    parametrization = load_parametrization(am_id, am_state)
    if not am or not parametrization or not am_metadata:
        body = html.P('Arrêté introuvable.')
    else:
        body = _get_body_component(operation_id, am_id, current_page, am, am_state, parametrization)
    return html.Div(
        [
            subtitle_component,
            body,
            html.P(am_id, hidden=True, id='am-id-am-page'),
            html.P(current_page, hidden=True, id='parent-page-am-page'),
        ],
        id='am-page',
    )


def _update_am_state(clicked_button: str, am_id: str) -> None:
    if clicked_button == _VALIDATE_STRUCTURE_BUTTON_ID:
        new_state = AMWorkflowState.PENDING_PARAMETRIZATION
    elif clicked_button == _INVALIDATE_STRUCTURE_BUTTON_ID:
        new_state = AMWorkflowState.PENDING_STRUCTURE_VALIDATION
    elif clicked_button == _VALIDATE_PARAMETRIZATION_BUTTON_ID:
        new_state = AMWorkflowState.VALIDATED
    elif clicked_button == _INVALIDATE_PARAMETRIZATION_BUTTON_ID:
        new_state = AMWorkflowState.PENDING_PARAMETRIZATION
    else:
        raise NotImplementedError(f'Unknown button id {clicked_button}')
    am_state = load_am_state(am_id)
    am_state.state = new_state
    dump_am_state(am_id, am_state)


def _add_callbacks(app: Dash) -> None:
    add_structure_edition_callbacks(app)
    add_parametrization_edition_callbacks(app)

    ids = [
        _VALIDATE_STRUCTURE_BUTTON_ID,
        _INVALIDATE_STRUCTURE_BUTTON_ID,
        _VALIDATE_PARAMETRIZATION_BUTTON_ID,
        _INVALIDATE_PARAMETRIZATION_BUTTON_ID,
    ]
    inputs = [Input(id_, 'n_clicks') for id_ in ids] + [
        Input('am-id-am-page', 'children'),
        Input('parent-page-am-page', 'children'),
    ]
    out = Output('am-page', 'children')

    def _handle_click(n_clicks_0, n_clicks_1, n_clicks_2, n_clicks_3, am_id_, parent_page):
        all_n_clicks = n_clicks_0, n_clicks_1, n_clicks_2, n_clicks_3
        for id_, n_clicks in zip(ids, all_n_clicks):
            if n_clicks >= 1:
                _update_am_state(id_, am_id_)
        return _router(f'/{am_id_}', '/'.join(parent_page.split('/')[:-1]))

    app.callback(out, inputs)(_handle_click)


page = Page(_router, _add_callbacks)
