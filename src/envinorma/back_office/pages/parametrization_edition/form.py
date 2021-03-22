import json
import traceback
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import ALL, Input, Output, State
from dash.development.base_component import Component

from envinorma.back_office.app_init import app
from envinorma.back_office.fetch_data import remove_parameter
from envinorma.back_office.routing import build_am_page
from envinorma.back_office.utils import AMOperation, get_truncated_str
from envinorma.data import Ints, StructuredText, dump_path
from envinorma.parametrization import ParameterObject, ParametrizationError

from . import page_ids
from .condition_form import ConditionFormValues, condition_form
from .form_handling import FormHandlingError, extract_and_upsert_new_parameter
from .target_sections_form import DropdownOptions, TargetSectionFormValues, target_section_form


def _get_main_title(operation: AMOperation, is_edition: bool, rank: int) -> Component:
    if is_edition:
        return (
            html.H4(f'Condition de non-application n°{rank}')
            if operation == operation.ADD_CONDITION
            else html.H4(f'Paragraphe alternatif n°{rank}')
        )
    return (
        html.H4('Nouvelle condition de non-application')
        if operation == operation.ADD_CONDITION
        else html.H4('Nouveau paragraphe alternatif')
    )


def _go_back_button(parent_page: str) -> Component:
    return dcc.Link(html.Button('Retour', className='btn btn-link center'), href=parent_page)


def _buttons(parent_page: str) -> Component:
    return html.Div(
        [
            html.Button(
                'Enregistrer',
                id='submit-val-param-edition',
                className='btn btn-primary',
                style={'margin-right': '5px'},
                n_clicks=0,
            ),
            _go_back_button(parent_page),
        ],
        style={'margin-top': '10px', 'margin-bottom': '100px'},
    )


def _get_source_form(options: DropdownOptions, loaded_parameter: Optional[ParameterObject]) -> Component:
    if loaded_parameter:
        default_value = dump_path(loaded_parameter.source.reference.section.path)
    else:
        default_value = ''
    dropdown_source = dcc.Dropdown(
        value=default_value, options=options, id=page_ids.SOURCE, style={'font-size': '0.8em'}
    )
    return html.Div([html.H5('Source'), dropdown_source])


def _get_delete_button(is_edition: bool) -> Component:
    return html.Button(
        'Supprimer',
        id='param-edition-delete-button',
        className='btn btn-danger',
        style={'margin-right': '5px'},
        n_clicks=0,
        hidden=not is_edition,
    )


def _add_block_button(is_edition: bool) -> Component:
    txt = 'Ajouter un paragraphe'
    btn = html.Button(txt, className='mt-2 mb-2 btn btn-light btn-sm', id=page_ids.ADD_TARGET_BLOCK)
    return html.Div(btn, hidden=is_edition)


def _get_target_section_block(
    operation: AMOperation,
    text_title_options: DropdownOptions,
    loaded_parameter: Optional[ParameterObject],
    text: StructuredText,
    is_edition: bool,
) -> Component:
    blocks = [target_section_form(operation, text_title_options, loaded_parameter, text, 0, is_edition)]
    return html.Div(
        [html.H5('Paragraphes visés'), html.Div(blocks, id=page_ids.TARGET_BLOCKS), _add_block_button(is_edition)]
    )


def _make_form(
    text_title_options: DropdownOptions,
    operation: AMOperation,
    parent_page: str,
    loaded_parameter: Optional[ParameterObject],
    destination_rank: int,
    text: StructuredText,
) -> Component:
    return html.Div(
        [
            _get_main_title(operation, is_edition=destination_rank != -1, rank=destination_rank),
            _get_delete_button(is_edition=destination_rank != -1),
            _get_source_form(text_title_options, loaded_parameter),
            _get_target_section_block(
                operation, text_title_options, loaded_parameter, text, is_edition=destination_rank != -1
            ),
            condition_form(loaded_parameter.condition if loaded_parameter else None),
            html.Div(id='param-edition-upsert-output'),
            html.Div(id='param-edition-delete-output'),
            dcc.Store(id=page_ids.DROPDOWN_OPTIONS, data=json.dumps(text_title_options)),
            _buttons(parent_page),
        ]
    )


def _extract_reference_and_values_titles(text: StructuredText, path: Ints, level: int = 0) -> List[Tuple[str, str]]:
    return [(dump_path(path), get_truncated_str('#' * level + ' ' + text.title.text))] + [
        elt
        for rank, sec in enumerate(text.sections)
        for elt in _extract_reference_and_values_titles(sec, path + (rank,), level + 1)
    ]


def _extract_paragraph_reference_dropdown_values(text: StructuredText) -> DropdownOptions:
    title_references_and_values = _extract_reference_and_values_titles(text, ())
    return [{'label': title, 'value': reference} for reference, title in title_references_and_values]


def _get_instructions() -> Component:
    return html.Div(
        html.A(
            'Guide de paramétrage',
            href='https://www.notion.so/R-gles-de-param-trisation-47d8e5c4d3434d8691cbd9f59d556f0f',
            target='_blank',
        ),
        className='alert alert-light',
    )


def form(
    text: StructuredText,
    operation: AMOperation,
    parent_page: str,
    loaded_parameter: Optional[ParameterObject],
    destination_rank: int,
) -> Component:
    dropdown_values = _extract_paragraph_reference_dropdown_values(text)
    return html.Div(
        [
            _get_instructions(),
            _make_form(dropdown_values, operation, parent_page, loaded_parameter, destination_rank, text),
        ]
    )


def _handle_submit(
    operation: AMOperation,
    am_id: str,
    parameter_rank: int,
    source_str: str,
    target_section_form_values: TargetSectionFormValues,
    condition_form_values: ConditionFormValues,
) -> Component:
    try:
        extract_and_upsert_new_parameter(
            operation,
            am_id,
            parameter_rank,
            source_str,
            target_section_form_values,
            condition_form_values,
        )
    except FormHandlingError as exc:
        return dbc.Alert(f'Erreur dans le formulaire:\n{exc}', color='danger')
    except ParametrizationError as exc:
        return dbc.Alert(
            f'Erreur: la section visée est déjà visée par au moins une autre condition.'
            f' Celle-ci est incompatible avec celle(s) déjà définie(s) :\n{exc}',
            color='danger',
        )
    except Exception:  # pylint: disable=broad-except
        return dbc.Alert(f'Unexpected error:\n{traceback.format_exc()}', color='danger')
    return html.Div(
        [
            dbc.Alert(f'Enregistrement réussi.', color='success'),
            dcc.Location(pathname=build_am_page(am_id), id='param-edition-success-redirect'),
        ]
    )


def _handle_delete(n_clicks: int, operation_str: str, am_id: str, parameter_rank: int) -> Component:
    if n_clicks == 0:
        return html.Div()
    try:
        operation = AMOperation(operation_str)
        remove_parameter(am_id, operation, parameter_rank)
    except Exception:  # pylint: disable=broad-except
        return dbc.Alert(f'Unexpected error:\n{traceback.format_exc()}', color='danger')
    return html.Div(
        [
            dbc.Alert(f'Suppression réussie.', color='success'),
            dcc.Location(pathname=build_am_page(am_id), id='param-edition-success-redirect'),
        ]
    )


def _add_callbacks(app: dash.Dash):
    @app.callback(
        Output('param-edition-upsert-output', 'children'),
        Input('submit-val-param-edition', 'n_clicks'),
        State(page_ids.AM_OPERATION, 'children'),
        State(page_ids.AM_ID, 'children'),
        State(page_ids.PARAMETER_RANK, 'children'),
        State(page_ids.SOURCE, 'value'),
        State(page_ids.new_text_title(cast(int, ALL)), 'value'),
        State(page_ids.new_text_content(cast(int, ALL)), 'value'),
        State(page_ids.target_section(cast(int, ALL)), 'value'),
        State(page_ids.target_alineas(cast(int, ALL)), 'value'),
        State(page_ids.condition_parameter(cast(int, ALL)), 'value'),
        State(page_ids.condition_operation(cast(int, ALL)), 'value'),
        State(page_ids.condition_value(cast(int, ALL)), 'value'),
        State(page_ids.CONDITION_MERGE, 'value'),
        prevent_initial_call=True,
    )
    def handle_submit(
        _,
        operation_str,
        am_id,
        parameter_rank,
        source_str,
        new_texts_titles,
        new_texts_contents,
        target_sections,
        target_alineas,
        condition_parameters,
        condition_operations,
        condition_values,
        condition_merge,
    ):
        condition_form_values = ConditionFormValues(
            condition_parameters, condition_operations, condition_values, condition_merge
        )
        target_section_form_values = TargetSectionFormValues(
            new_texts_titles, new_texts_contents, target_sections, target_alineas
        )
        return _handle_submit(
            AMOperation(operation_str),
            am_id,
            parameter_rank,
            source_str,
            target_section_form_values,
            condition_form_values,
        )

    @app.callback(
        Output('param-edition-delete-output', 'children'),
        Input('param-edition-delete-button', 'n_clicks'),
        State(page_ids.AM_OPERATION, 'children'),
        State(page_ids.AM_ID, 'children'),
        State(page_ids.PARAMETER_RANK, 'children'),
    )
    def handle_delete(n_clicks, operation, am_id, parameter_rank):
        return _handle_delete(n_clicks, operation, am_id, parameter_rank)

    @app.callback(
        Output(page_ids.TARGET_BLOCKS, 'children'),
        Input(page_ids.ADD_TARGET_BLOCK, 'n_clicks'),
        State(page_ids.TARGET_BLOCKS, 'children'),
        State(page_ids.AM_OPERATION, 'children'),
        State(page_ids.DROPDOWN_OPTIONS, 'data'),
        prevent_initial_call=True,
    )
    def add_block(n_clicks, children, operation_str, options_str):
        new_block = target_section_form(
            AMOperation(operation_str), json.loads(options_str), None, None, n_clicks + 1, False
        )
        return children + [new_block]


_add_callbacks(app)
