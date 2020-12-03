import random
import string
import dash_core_components as dcc
from pandas import DataFrame
from typing import Any, List, Dict, Optional, Tuple, Union


def check_same_lengths(lists: List[List[Any]]) -> None:

    lengths = [len(list_) for list_ in lists]
    if len(set(lengths)) > 1:
        raise ValueError(f'Expected lists to have same length, received lists with lengths {lengths}')


def build_data_file_name(path: str, format_: str = 'csv') -> str:
    return '/'.join(path.split('/')[:-1] + ['data.' + format_])


def random_id(prefix: str) -> str:
    return prefix + '_' + ''.join([random.choice(string.ascii_letters) for _ in range(6)])


operators = [
    ['ge ', '>='],
    ['le ', '<='],
    ['lt ', '<'],
    ['gt ', '>'],
    ['ne ', '!='],
    ['eq ', '='],
    ['contains '],
    ['datestartswith '],
]


def split_filter_part(filter_part) -> Tuple[Optional[str], Optional[str], Any]:
    for operator_type in operators:
        for operator in operator_type:
            if operator in filter_part:
                name_part, value_part = filter_part.split(operator, 1)
                name = name_part[name_part.find('{') + 1 : name_part.rfind('}')]

                value_part = value_part.strip()
                v0 = value_part[0]
                if v0 == value_part[-1] and v0 in ("'", '"', '`'):
                    value = value_part[1:-1].replace('\\' + v0, v0)
                else:
                    try:
                        value = float(value_part)
                    except ValueError:
                        value = value_part

                # word operators need spaces after them in the filter string,
                # but we don't want these later
                return name, operator_type[0].strip(), value
    return (None, None, None)


def apply_filter(dataframe: DataFrame, filter_query: str) -> DataFrame:
    filtering_expressions = filter_query.split(' && ')
    for filter_part in filtering_expressions:
        col_name, operator, filter_value = split_filter_part(filter_part)
        if not isinstance(operator, str):
            continue
        if operator in ('eq', 'ne', 'lt', 'le', 'gt', 'ge'):
            dataframe = dataframe.loc[getattr(dataframe[col_name], operator)(filter_value)]
        elif operator == 'contains':
            if isinstance(filter_value, float):
                filter_value = str(int(filter_value))
            dataframe = dataframe.loc[dataframe[col_name].str.contains(filter_value)]
        elif operator == 'datestartswith':
            dataframe = dataframe.loc[dataframe[col_name].str.startswith(filter_value)]
    return dataframe


def apply_sort(dataframe: DataFrame, sort_queries: List[Dict[str, str]]) -> DataFrame:
    if not isinstance(sort_queries, list):
        raise ValueError(f'Expected type: dict, received type {type(sort_queries)}')
    if len(sort_queries) > 1:
        raise ValueError(f'Expected one sort, received {len(sort_queries)} sort queries.')
    if not sort_queries:
        return dataframe
    sort_query = sort_queries[0]
    by = sort_query['column_id']
    return dataframe.sort_values(by, ascending=sort_query['direction'] == 'asc', inplace=False)


def generate_dropdown(
    placeholder: str, options: List[str], default_value: Optional[Union[str, List[str]]] = None, multi: bool = False
) -> Tuple[str, dcc.Dropdown]:
    id_ = random_id('dropdown')
    component = dcc.Dropdown(
        id=id_,
        options=[{'label': i, 'value': i} for i in options],
        value=default_value,
        multi=multi,
        placeholder=placeholder,
    )
    return id_, component
