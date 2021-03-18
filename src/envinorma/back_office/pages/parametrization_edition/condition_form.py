from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import dash
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import ALL, MATCH, Input, Output, State
from dash.development.base_component import Component

from envinorma.back_office.app_init import app
from envinorma.data import Regime, ensure_rubrique
from envinorma.parametrization.conditions import (
    AndCondition,
    Condition,
    Equal,
    Greater,
    Littler,
    MonoCondition,
    OrCondition,
    ParameterEnum,
    ParameterType,
    Range,
    ensure_mono_conditions,
)

from . import page_ids

_CONDITION_VARIABLES = page_ids.CONDITION_VARIABLES
_CONDITION_VARIABLE_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_VARIABLES]
_CONDITION_OPERATIONS = ['<', '=', '>=']
_CONDITION_OPERATION_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_OPERATIONS]
_AND_ID = 'and'
_OR_ID = 'or'
_MERGE_VALUES_OPTIONS = [{'value': _AND_ID, 'label': 'ET'}, {'value': _OR_ID, 'label': 'OU'}]


def _get_str_operation(condition: MonoCondition) -> str:
    if isinstance(condition, Equal):
        return '='
    if isinstance(condition, Greater):
        return '>' if condition.strict else '>='
    if isinstance(condition, Littler):
        return '<' if condition.strict else '<='
    raise NotImplementedError(f'Unknown type {type(condition)}')


def _get_str_variable(condition: MonoCondition) -> str:
    for variable_name, variable in _CONDITION_VARIABLES.items():
        if variable.value == condition.parameter:
            return variable_name
    return ''


def _date_to_dmy(date_: Union[date, datetime]) -> str:
    return date_.strftime('%d/%m/%Y')


def _ensure_date(value: Any) -> Union[date, datetime]:
    if isinstance(value, (date, datetime)):
        return value
    raise ValueError(f'Expected type (date, datetime), received type {type(value)}')


def _ensure_regime(value: Any) -> Regime:
    if isinstance(value, Regime):
        return value
    raise ValueError(f'Expected type Regime, received type {type(value)}')


def _ensure_str(value: Any) -> str:
    if isinstance(value, str):
        return value
    raise ValueError(f'Expected type str, received type {type(value)}')


def _ensure_float(candidate: str) -> float:
    try:
        return float(candidate)
    except ValueError:
        raise ValueError(f'Expected type float, received {candidate} of type {type(candidate)}.')


def _get_str_target(value: Any, parameter_type: ParameterType) -> str:
    if value is None:
        return ''
    if parameter_type == parameter_type.DATE:
        return _date_to_dmy(_ensure_date(value))
    if parameter_type == parameter_type.REGIME:
        return _ensure_regime(value).value
    if parameter_type == parameter_type.REAL_NUMBER:
        return str(_ensure_float(value))
    if parameter_type == parameter_type.RUBRIQUE:
        return ensure_rubrique(value)
    if parameter_type == parameter_type.STRING:
        return _ensure_str(value)
    raise ValueError(f'Unhandled parameter type: {parameter_type.value}')


def _delete_button(rank: int) -> Component:
    return dbc.Button('X', color='light', id=page_ids.delete_condition_button(rank), size='sm', className='ml-1')


def _parameter_input(rank: int, default_condition: Optional[MonoCondition]) -> Component:
    default_variable = page_ids.INSTALLATION_DATE_FR if not default_condition else _get_str_variable(default_condition)
    return dcc.Dropdown(
        id=page_ids.condition_parameter(rank),
        options=_CONDITION_VARIABLE_OPTIONS,
        clearable=False,
        value=default_variable,
        style={'width': '195px', 'margin-right': '5px'},
        optionHeight=50,
    )


def _operation_input(rank: int, default_condition: Optional[MonoCondition]) -> Component:
    return dcc.Dropdown(
        id=page_ids.condition_operation(rank),
        options=_CONDITION_OPERATION_OPTIONS,
        clearable=False,
        value='=' if not default_condition else _get_str_operation(default_condition),
        style={'width': '45px', 'margin-right': '5px'},
    )


def _value_input(rank: int, default_condition: Optional[MonoCondition]) -> Component:
    default_target = (
        '' if not default_condition else _get_str_target(default_condition.target, default_condition.parameter.type)
    )
    return dcc.Input(
        id=page_ids.condition_value(rank),
        value=str(default_target),
        type='text',
        className='form-control form-control-sm',
    )


def _add_block_button() -> Component:
    txt = '+'
    btn = html.Button(txt, className='mt-2 mb-2 btn btn-light btn-sm', id=page_ids.ADD_CONDITION_BLOCK)
    return html.Div(btn)


def _condition_block(rank: int, default_condition: Optional[MonoCondition] = None) -> Component:
    conditions_block = [
        _parameter_input(rank, default_condition),
        _operation_input(rank, default_condition),
        _value_input(rank, default_condition),
        _delete_button(rank),
    ]
    return html.Div(
        conditions_block,
        className='small-dropdown',
        style={'display': 'flex', 'margin-bottom': '5px'},
        id=page_ids.condition_block(rank),
    )


def _condition_blocks(default_conditions: Optional[List[MonoCondition]] = None) -> Component:
    if default_conditions:
        condition_blocks = [_condition_block(i, cd) for i, cd in enumerate(default_conditions)]
    else:
        condition_blocks = [_condition_block(0)]
    return html.Div(condition_blocks, id=page_ids.CONDITION_BLOCKS)


def _get_condition_tooltip() -> Component:
    return html.Div(
        [
            'Liste de conditions ',
            dbc.Badge('?', id='param-edition-conditions-tooltip', pill=True),
            dbc.Tooltip(
                ['Formats:', html.Br(), 'Régime: A, E, D ou NC.', html.Br(), 'Date: JJ/MM/AAAA'],
                target='param-edition-conditions-tooltip',
            ),
        ]
    )


def _make_mono_conditions(condition: Condition) -> List[MonoCondition]:
    if isinstance(condition, (Equal, Greater, Littler)):
        return [condition]
    if isinstance(condition, Range):
        return [
            Littler(condition.parameter, condition.right, condition.right_strict),
            Greater(condition.parameter, condition.left, condition.left_strict),
        ]
    raise ValueError(f'Unexpected condition type {type(condition)}')


def _change_to_mono_conditions(condition: Condition) -> Tuple[str, List[MonoCondition]]:
    if isinstance(condition, (Equal, Greater, Littler, Range)):
        return _AND_ID, _make_mono_conditions(condition)
    if isinstance(condition, AndCondition):
        children_mono_conditions = [cd for child in condition.conditions for cd in _make_mono_conditions(child)]
        return _AND_ID, children_mono_conditions
    if isinstance(condition, (AndCondition, OrCondition)):
        return _OR_ID, ensure_mono_conditions(condition.conditions)
    raise NotImplementedError(f'Unhandled condition {type(condition)}')


def _merge_input(default_merge: str) -> Component:
    merge_dropdown = dcc.Dropdown(
        options=_MERGE_VALUES_OPTIONS, clearable=False, value=default_merge, id=page_ids.CONDITION_MERGE
    )
    return html.Div(['Opération', merge_dropdown])


def condition_form(default_condition: Optional[Condition]) -> Component:
    default_conditions: List[MonoCondition] = []
    if default_condition:
        default_merge, default_conditions = _change_to_mono_conditions(default_condition)
    else:
        default_merge = _AND_ID
        default_conditions = [Littler(ParameterEnum.DATE_INSTALLATION.value, None)]
    tooltip = _get_condition_tooltip()
    conditions = html.Div(children=_condition_blocks(default_conditions))
    return html.Div([html.H5('Condition'), _merge_input(default_merge), tooltip, conditions, _add_block_button()])


@dataclass
class ConditionFormValues:
    parameters: List[str]
    operations: List[str]
    values: List[str]
    merge: str


def _add_callbacks(app: dash.Dash):
    @app.callback(
        Output(page_ids.condition_block(cast(int, MATCH)), 'children'),
        Input(page_ids.delete_condition_button(cast(int, MATCH)), 'n_clicks'),
        prevent_initial_call=True,
    )
    def delete_section(_):
        return html.Div()

    @app.callback(
        Output(page_ids.CONDITION_BLOCKS, 'children'),
        Input(page_ids.ADD_CONDITION_BLOCK, 'n_clicks'),
        State(page_ids.CONDITION_BLOCKS, 'children'),
        State(page_ids.condition_block(cast(int, ALL)), 'id'),
        prevent_initial_call=True,
    )
    def add_block(_, children, ids):
        new_rank = (max([cast(int, id_['rank']) for id_ in ids]) + 1) if ids else 0
        new_block = _condition_block(rank=new_rank, default_condition=None)
        return children + [new_block]


_add_callbacks(app)
