from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import MATCH, Input, Output, State
from dash.development.base_component import Component

from envinorma.back_office.app_init import app
from envinorma.back_office.fetch_data import load_most_advanced_am
from envinorma.back_office.pages.parametrization_edition import page_ids
from envinorma.back_office.utils import AMOperation, get_section, safe_get_section, safe_get_subsection
from envinorma.data import Ints, StructuredText, dump_path, load_path
from envinorma.parametrization import AlternativeSection, NonApplicationCondition, ParameterObject

DropdownOptions = List[Dict[str, Any]]


def _get_target_entity(parameter: ParameterObject) -> Ints:
    if isinstance(parameter, NonApplicationCondition):
        return parameter.targeted_entity.section.path
    if isinstance(parameter, AlternativeSection):
        return parameter.targeted_section.path
    raise NotImplementedError(f'{type(parameter)}')


def _target_section_form(options: DropdownOptions, loaded_parameter: Optional[ParameterObject], rank: int) -> Component:
    default_value = dump_path(_get_target_entity(loaded_parameter)) if loaded_parameter else None
    dropdown_target = html.Div(
        [
            dcc.Dropdown(
                options=options, id=page_ids.target_section(rank), value=default_value, style={'font-size': '0.8em'}
            )
        ]
    )
    return html.Div([html.H6('Titre'), dropdown_target])


def _ensure_optional_condition(parameter: Optional[ParameterObject]) -> Optional[NonApplicationCondition]:
    if not parameter:
        return None
    if not isinstance(parameter, NonApplicationCondition):
        raise ValueError(f'Expection NonApplicationCondition, not {type(parameter)}')
    return parameter


def _target_alineas_form(
    operation: AMOperation, loaded_parameter: Optional[ParameterObject], text: Optional[StructuredText], rank: int
) -> Component:
    title = html.H6('Alineas visés')
    if not _is_condition(operation):
        return html.Div(
            [title, dbc.Checklist(options=[], id=page_ids.target_alineas(rank))],
            hidden=True,
        )
    condition = _ensure_optional_condition(loaded_parameter)

    if not condition:
        value = []
        options = []
    else:
        assert text is not None
        path = condition.targeted_entity.section.path
        alineas = condition.targeted_entity.outer_alinea_indices
        target_section_alineas = section.outer_alineas if (section := safe_get_subsection(path, text)) else []
        if target_section_alineas:
            options = [{'label': al.text, 'value': i} for i, al in enumerate(target_section_alineas)]
            value = alineas if alineas else list(range(len(target_section_alineas)))
        else:
            options = []
            value = []
    return html.Div(
        [
            title,
            dbc.Checklist(options=options, value=value, id=page_ids.target_alineas(rank)),
        ]
    )


def _is_condition(operation: AMOperation) -> bool:
    return operation == operation.ADD_CONDITION


def _ensure_alternative_section(parameter: ParameterObject) -> AlternativeSection:
    if not isinstance(parameter, AlternativeSection):
        raise ValueError(f'Expection AlternativeSection, not {type(parameter)}')
    return parameter


def _extract_title_and_content(text: StructuredText, level: int = 0) -> Tuple[str, str]:
    title = text.title.text
    contents: List[str] = []
    for alinea in text.outer_alineas:
        contents.append(alinea.text)
    for section in text.sections:
        section_title, section_content = _extract_title_and_content(section, level + 1)
        contents.append('#' * (level + 1) + ' ' + section_title)
        contents.append(section_content)
    return title, '\n'.join(contents)


def _new_section_form(default_title: str, default_content: str, rank: int, operation: AMOperation) -> Component:
    text_area = dcc.Textarea(
        id=page_ids.new_text_content(rank),
        className='form-control',
        value=default_content,
        style={'min-height': '300px'},
    )
    content = [
        html.H5('Nouvelle version'),
        html.Div(dcc.Input(id=page_ids.new_text_title(rank), value=default_title), hidden=True),
        html.Label('Contenu du paragraphe', className='form-label'),
        html.Div(text_area),
    ]
    return html.Div(content, hidden=operation != AMOperation.ADD_ALTERNATIVE_SECTION)


def _new_section_form_from_default(
    operation: AMOperation, loaded_parameter: Optional[ParameterObject], rank: int
) -> Component:
    if not loaded_parameter or operation == AMOperation.ADD_CONDITION:
        default_title, default_content = '', ''
    else:
        parameter = _ensure_alternative_section(loaded_parameter)
        default_title, default_content = _extract_title_and_content(parameter.new_text)
    return _new_section_form(default_title, default_content, rank, operation)


def _build_new_text_component(str_path: Optional[str], am_id: str, operation: AMOperation, rank: int) -> Component:
    if operation != AMOperation.ADD_ALTERNATIVE_SECTION or not str_path:
        return _new_section_form('', '', rank, operation)
    am = load_most_advanced_am(am_id)
    if not am:
        return _new_section_form('', '', rank, operation)
    path = load_path(str_path)
    section = safe_get_section(path, am)
    if not section:
        return _new_section_form('', '', rank, operation)
    title, content = _extract_title_and_content(section)
    return _new_section_form(title, content, rank, operation)


def _build_targeted_alineas_options(section_dict: Dict[str, Any], operation: AMOperation) -> List[Dict[str, Any]]:
    if operation != AMOperation.ADD_CONDITION or not section_dict:
        return []
    section = StructuredText.from_dict(section_dict)
    alineas_str = [al.text for al in section.outer_alineas]
    return [{'label': al, 'value': i} for i, al in enumerate(alineas_str)]


def _store_target_section(str_path: Optional[str], am_id: str) -> Dict[str, Any]:
    if not str_path:
        return {}
    am = load_most_advanced_am(am_id)
    if not am:
        return {}
    path = load_path(str_path)
    section = get_section(path, am)
    return section.to_dict()


def _build_targeted_alineas_value(section_dict: Dict[str, Any], operation: AMOperation) -> List[int]:
    if operation != AMOperation.ADD_CONDITION or not section_dict:
        return []
    section = StructuredText.from_dict(section_dict)
    return list(range(len(section.outer_alineas)))


def _delete_button(rank: int, is_edition: bool) -> Component:
    return html.Span(
        dbc.Button('X', color='danger', id=page_ids.delete_block_button(rank), size='sm'),
        hidden=is_edition,
        style={'float': 'right'},
        className='mb-1',
    )


def target_section_form(
    operation: AMOperation,
    text_title_options: DropdownOptions,
    loaded_parameter: Optional[ParameterObject],
    text: Optional[StructuredText],
    rank: int,
    is_edition: bool,
) -> Component:
    block = html.Div(
        [
            _delete_button(rank, is_edition),
            _target_section_form(text_title_options, loaded_parameter, rank),
            _target_alineas_form(operation, loaded_parameter, text, rank),
            html.Div(_new_section_form_from_default(operation, loaded_parameter, rank), id=page_ids.new_text(rank)),
            dcc.Store(id=page_ids.target_section_store(rank)),
        ],
        style={
            'padding': '10px',
            'border': '1px solid rgba(0,0,0,.1)',
            'border-radius': '5px',
            'background-color': '#EEE',
        },
        className='mt-3 mb-3',
    )
    return html.Div(block, id=page_ids.target_section_block(rank))


@dataclass
class TargetSectionFormValues:
    new_texts_titles: List[str]
    new_texts_contents: List[str]
    target_sections: List[str]
    target_alineas: List[List[int]]


def _add_callbacks(app: dash.Dash):
    @app.callback(
        Output(page_ids.new_text(cast(int, MATCH)), 'children'),
        Input(page_ids.target_section(cast(int, MATCH)), 'value'),
        State(page_ids.AM_ID, 'children'),
        State(page_ids.AM_OPERATION, 'children'),
        State(page_ids.target_section(cast(int, MATCH)), 'id'),
        prevent_initial_call=True,
    )
    def build_new_text(path, am_id, operation, trigger_id):
        rank = trigger_id['rank']
        return _build_new_text_component(path, am_id, AMOperation(operation), rank)

    @app.callback(
        Output(page_ids.target_section_store(cast(int, MATCH)), 'data'),
        Input(page_ids.target_section(cast(int, MATCH)), 'value'),
        State(page_ids.AM_ID, 'children'),
        prevent_initial_call=True,
    )
    def store_target_section(path, am_id):
        return _store_target_section(path, am_id)

    @app.callback(
        Output(page_ids.target_alineas(cast(int, MATCH)), 'options'),
        Input(page_ids.target_section_store(cast(int, MATCH)), 'data'),
        State(page_ids.AM_OPERATION, 'children'),
        prevent_initial_call=True,
    )
    def build_targeted_alinea_options(target_section, operation):
        return _build_targeted_alineas_options(target_section, AMOperation(operation))

    @app.callback(
        Output(page_ids.target_alineas(cast(int, MATCH)), 'value'),
        Input(page_ids.target_section_store(cast(int, MATCH)), 'data'),
        State(page_ids.AM_OPERATION, 'children'),
        prevent_initial_call=True,
    )
    def build_targeted_alinea_value(target_section, operation):
        return _build_targeted_alineas_value(target_section, AMOperation(operation))

    @app.callback(
        Output(page_ids.target_section_block(cast(int, MATCH)), 'children'),
        Input(page_ids.delete_block_button(cast(int, MATCH)), 'n_clicks'),
        prevent_initial_call=True,
    )
    def delete_section(_):
        return html.Div()


_add_callbacks(app)
