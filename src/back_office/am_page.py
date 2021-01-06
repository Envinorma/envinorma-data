from datetime import datetime
from enum import Enum
from typing import List, Optional, Tuple

import dash_core_components as dcc
import dash_html_components as html
from dash.dash import Dash
from dash.development.base_component import Component
from lib.am_to_markdown import extract_markdown_text
from lib.data import ArreteMinisteriel, EnrichedString, StructuredText
from lib.parametrization import (
    AlternativeSection,
    ConditionSource,
    EntityReference,
    Greater,
    Littler,
    NonApplicationCondition,
    ParameterEnum,
    Parametrization,
    Range,
    SectionReference,
    condition_to_str,
)

from back_office.parametrization_edition import (
    add_parametrization_edition_callbacks,
    make_am_parametrization_edition_component,
)
from back_office.structure_edition import add_structure_edition_callbacks, make_am_structure_edition_component
from back_office.utils import AMOperation, ID_TO_AM_MD, Page, div, load_am


def _extract_am_id_and_operation(pathname: str) -> Tuple[str, Optional[AMOperation], str]:
    pieces = pathname.split('/')[1:]
    if len(pieces) == 0:
        raise ValueError('Unexpected')
    if len(pieces) == 1:
        return pieces[0], None, ''
    return pieces[0], AMOperation(pieces[1]), '/'.join(pieces[2:])


def _fake_parametrization() -> Parametrization:
    parameter = ParameterEnum.DATE_INSTALLATION.value
    date_1 = datetime(2018, 1, 1)
    date_2 = datetime(2019, 1, 1)
    condition_1 = Greater(parameter, date_1, False)
    condition_2 = Range(parameter, date_1, date_2, left_strict=False, right_strict=True)
    condition_3 = Littler(parameter, date_2, True)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None, False))
    new_text = StructuredText(EnrichedString('Art. 2', []), [EnrichedString('version modifiée')], [], None, None)
    parametrization = Parametrization(
        [
            NonApplicationCondition(EntityReference(SectionReference((0,)), None), condition_1, source),
            NonApplicationCondition(EntityReference(SectionReference((0,)), None), condition_3, source),
        ],
        [AlternativeSection(SectionReference((1,)), new_text, condition_2, source)],
    )
    return parametrization


def _load_parametrization(am_id: str) -> Optional[Parametrization]:
    am_md = ID_TO_AM_MD.get(am_id)
    if not am_md:
        return None
    return _fake_parametrization()  # TODO


class _Status(Enum):
    PENDING_STRUCTURE_VALIDATION = 'pending-structure-validation'
    PENDING_PARAMETRIZATION = 'pending-enrichment'
    VALIDATED = 'validated'


def _get_am_status(am_id: str) -> _Status:  # TODO
    if am_id == 'JORFTEXT000026251890':
        return _Status.PENDING_STRUCTURE_VALIDATION
    if am_id == 'JORFTEXT000018622600':
        return _Status.PENDING_PARAMETRIZATION
    if am_id == 'JORFTEXT000022673160':
        return _Status.VALIDATED
    return _Status.PENDING_STRUCTURE_VALIDATION


def _inline_buttons(buttons: List[Component]) -> Component:
    return html.P(buttons, style=dict(display='flex'))


def _primary_button(text: str, disabled: bool = False) -> html.Button:
    return html.Button(text, disabled=disabled, style={'margin': '5px'}, className='btn btn-primary')


def _primary_link_button(text: str, href: str, disabled: bool = False) -> html.Button:
    if disabled:
        return _primary_button(text, disabled)
    return dcc.Link(_primary_button(text, disabled), href=href)


def _get_edit_button(href: str, enabled: bool) -> Component:
    return _primary_link_button('Éditer', href, not enabled)


def _get_edit_structure_button(parent_page: str, am_status: _Status) -> Component:
    return _get_edit_button(
        f'{parent_page}/{AMOperation.EDIT_STRUCTURE}', am_status == am_status.PENDING_STRUCTURE_VALIDATION
    )


def _get_validate_structure_button(am_status: _Status) -> Component:
    if am_status == am_status.PENDING_STRUCTURE_VALIDATION:
        return _primary_button('Valider la structure')
    return _primary_button('Invalider la structure')


def _get_structure_validation_buttons(parent_page: str, am_status: _Status) -> Component:
    edit_button = _get_edit_structure_button(parent_page, am_status)
    validate_button = _get_validate_structure_button(am_status)
    return _inline_buttons([edit_button, validate_button])


def _get_validate_parametrization_button(am_status: _Status) -> Component:
    if am_status == am_status.PENDING_STRUCTURE_VALIDATION:
        return _primary_button('Valider la paramétrisation', True)
    if am_status == am_status.PENDING_PARAMETRIZATION:
        return _primary_button('Valider la paramétrisation')
    return _primary_button('Invalider la paramétrisation')


def _get_parametrization_edition_buttons(am_status: _Status) -> Component:
    validate_button = _get_validate_parametrization_button(am_status)
    return _inline_buttons([validate_button])


def _get_structure_validation_title(status: _Status) -> Component:
    title = 'Edition de structure '
    if status == status.PENDING_STRUCTURE_VALIDATION:
        return html.H3(title)
    return html.H3([title, html.Span('ok', className='badge rounded-pill bg-success')])


def _get_parametrization_edition_title(status: _Status) -> Component:
    title = 'Edition de la paramétrisation '
    if status != status.VALIDATED:
        return html.H3(title)
    return html.H3([title, html.Span('ok', className='badge rounded-pill bg-success')])


def _get_subsection(path: Tuple[int, ...], text: StructuredText) -> StructuredText:
    if not path:
        return text
    return _get_subsection(path[1:], text.sections[path[0]])


def _get_section(path: Tuple[int, ...], am: ArreteMinisteriel) -> StructuredText:
    return _get_subsection(path[1:], am.sections[path[0]])


def _application_condition_to_row(
    non_application_condition: NonApplicationCondition, am: ArreteMinisteriel
) -> Component:
    reference_str = _get_section(non_application_condition.targeted_entity.section.path, am).title.text
    alineas = non_application_condition.targeted_entity.outer_alinea_indices or 'Tous'
    description = non_application_condition.description
    condition = condition_to_str(non_application_condition.condition)
    source = _get_section(non_application_condition.source.reference.section.path, am).title.text
    cells = [reference_str, alineas, description, condition, source]
    return html.Tr([html.Td(cell) for cell in cells])


def _get_non_application_table(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    header_names = ['Paragraphe visé', 'Alineas visés', 'Description', 'Condition', 'Source']
    header = html.Thead(html.Tr([html.Th(name) for name in header_names]))
    body = html.Tbody([_application_condition_to_row(row, am) for row in parametrization.application_conditions])
    return html.Table([header, body], className='table table-hover')


def _wrap_in_paragraphs(strs: List[str]) -> Component:
    return div([html.P(str_) for str_ in strs])


def _alternative_section_to_row(alternative_section: AlternativeSection, am: ArreteMinisteriel) -> Component:
    reference_str = _get_section(alternative_section.targeted_section.path, am).title.text
    description = alternative_section.description
    condition = condition_to_str(alternative_section.condition)
    source = _get_section(alternative_section.source.reference.section.path, am).title.text
    new_version = _wrap_in_paragraphs(extract_markdown_text(alternative_section.new_text, level=1))
    cells = [reference_str, description, condition, source, new_version]
    return html.Tr([html.Td(cell) for cell in cells])


def _get_alternative_section_table(parametrization: Parametrization, am: ArreteMinisteriel) -> Component:
    header_names = ['Paragraphe visé', 'Description', 'Condition', 'Source', 'Nouvelle version']
    header = html.Thead(html.Tr([html.Th(name) for name in header_names]))
    body = html.Tbody([_alternative_section_to_row(row, am) for row in parametrization.alternative_sections])
    return html.Table([header, body], className='table table-hover')


def _get_add_condition_button(parent_page: str, status: _Status) -> Component:
    disabled = status != status.PENDING_PARAMETRIZATION
    href = f'{parent_page}/{AMOperation.ADD_CONDITION.value}'
    return _primary_link_button('Nouveau', href, disabled)


def _get_add_alternative_section_button(parent_page: str, status: _Status) -> Component:
    disabled = status != status.PENDING_PARAMETRIZATION
    href = f'{parent_page}/{AMOperation.ADD_ALTERNATIVE_SECTION.value}'
    return _primary_link_button('Nouveau', href, disabled)


def _get_parametrization_summary(
    parent_page: str, status: _Status, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    if status == status.PENDING_STRUCTURE_VALIDATION:
        return div([])
    return div(
        [
            html.H4(['Conditions de non-application', _get_add_condition_button(parent_page, status)]),
            _get_non_application_table(parametrization, am),
            html.H4(['Paragraphes alternatifs', _get_add_alternative_section_button(parent_page, status)]),
            _get_alternative_section_table(parametrization, am),
        ]
    )


def _build_component_based_on_status(
    parent_page: str, am_status: _Status, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    children = [
        _get_structure_validation_title(am_status),
        _get_structure_validation_buttons(parent_page, am_status),
        _get_parametrization_edition_title(am_status),
        _get_parametrization_summary(parent_page, am_status, parametrization, am),
        _get_parametrization_edition_buttons(am_status),
    ]
    return html.Div(children)


def _make_am_index_component(
    am_id: str, parent_page: str, parametrization: Parametrization, am: ArreteMinisteriel
) -> Component:
    am_status = _get_am_status(am_id)
    return _build_component_based_on_status(parent_page, am_status, parametrization, am)


def _get_subtitle_component(am_id: str, parent_page: str) -> Component:
    return dcc.Link(html.H2(f'Arrêté ministériel {am_id}'), href=parent_page)


def _get_body_component(
    operation_id: Optional[AMOperation],
    am_id: str,
    parent_page: str,
    am: ArreteMinisteriel,
    parametrization: Parametrization,
) -> Component:
    if not operation_id:
        return _make_am_index_component(am_id, parent_page, parametrization, am)
    if operation_id == operation_id.EDIT_STRUCTURE:
        return make_am_structure_edition_component(am_id, parent_page, am)
    if operation_id in (operation_id.ADD_CONDITION, operation_id.ADD_ALTERNATIVE_SECTION):
        return make_am_parametrization_edition_component(am, operation_id, parent_page)
    raise NotImplementedError()


def _router(pathname: str, parent_page: str) -> Component:
    print(pathname)
    am_id, operation_id, _ = _extract_am_id_and_operation(pathname)
    parent_page = parent_page + '/' + am_id
    am = load_am(am_id)
    parametrization = _load_parametrization(am_id)
    if not am or not parametrization:
        body = html.P('Arrêté introuvable.')
    else:
        body = _get_body_component(operation_id, am_id, parent_page, am, parametrization)
    subtitle_component = _get_subtitle_component(am_id, parent_page)
    return div([subtitle_component, body])


def _add_callbacks(app: Dash) -> None:
    add_structure_edition_callbacks(app)
    add_parametrization_edition_callbacks(app)


page = Page(_router, _add_callbacks)
