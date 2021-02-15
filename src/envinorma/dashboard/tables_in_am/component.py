from typing import List, Optional

import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.express as px
from dash.dash import Dash
from dash.dependencies import Input, Output
from .data import TablesDataset
from ..utils import apply_filter, apply_sort, build_data_file_name, generate_dropdown, random_id

DATAFRAME = TablesDataset.load_csv(build_data_file_name(__file__))

_TABLES_TABLE = '_TABLES_TABLE'
_TABLE_PAGING = '_TABLES_TABLE_PAGING'
_DROPDOWN_ID, _DROPDOWN_COMPONENT = generate_dropdown(options=list(DATAFRAME.keys()), placeholder='Colonne à analyser')


PAGE_SIZE = 20
_DIVS = [
    html.Div(
        dash_table.DataTable(
            id=_TABLES_TABLE,
            columns=[{'name': i, 'id': i} for i in sorted(DATAFRAME.columns)],
            page_current=0,
            page_size=20,
            page_action='custom',
            filter_action='custom',
            filter_query='',
            sort_action='custom',
            sort_mode='single',
            sort_by=[],
        ),
        style={'height': 750, 'overflowY': 'scroll', 'width': '65%', 'display': 'inline-block', 'margin': 'auto'},
    ),
    html.Div(
        [html.Div([_DROPDOWN_COMPONENT]), html.Div(id=_TABLE_PAGING)],
        style={'width': '30%', 'display': 'inline-block', 'margin': 'auto', 'float': 'right'},
    ),
]
component = html.Div(_DIVS, className='row')


def add_callback(app: Dash):
    @app.callback(
        Output(_TABLES_TABLE, "data"),
        Input(_TABLES_TABLE, "page_current"),
        Input(_TABLES_TABLE, "page_size"),
        Input(_TABLES_TABLE, "sort_by"),
        Input(_TABLES_TABLE, "filter_query"),
    )
    def _update_table(page_current, page_size, sort_by, filter_query):
        new_dataframe = apply_sort(apply_filter(DATAFRAME, filter_query), sort_by)
        return new_dataframe.iloc[page_current * page_size : (page_current + 1) * page_size].to_dict('records')

    @app.callback(Output(_TABLE_PAGING, "children"), Input(_TABLES_TABLE, "filter_query"), Input(_DROPDOWN_ID, 'value'))
    def _update_graph(filter_query: str, column_to_analyze: Optional[str]):
        dataframe = apply_filter(DATAFRAME, filter_query)
        if not column_to_analyze:
            return html.Div(['Select a column to display graph.'])
        fig = px.histogram(dataframe, x=column_to_analyze, hover_data=dataframe.columns, nbins=10)
        return html.Div([dcc.Graph(id=random_id(column_to_analyze), figure=fig)])
