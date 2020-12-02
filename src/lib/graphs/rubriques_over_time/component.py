import dash_table

import plotly.express as px
from dash.dash import Dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from plotly.graph_objects import Figure
from lib.graphs.rubriques_over_time.data import RubriquesDataset
from lib.graphs.utils import apply_filter, apply_sort, build_data_file_name, generate_dropdown, random_id


_DATAFRAME = RubriquesDataset.load_csv(build_data_file_name(__file__))
_DATAFRAME = _DATAFRAME.loc[_DATAFRAME.year.apply(lambda x: 1950 <= x <= 2030)]
_PAGE_SIZE = 20
_TABLE_ID = random_id('TABLE')
_TABLE = dash_table.DataTable(
    id=_TABLE_ID,
    columns=[{'name': i, 'id': i} for i in sorted(_DATAFRAME.columns)],
    page_current=0,
    page_size=_PAGE_SIZE,
    page_action='custom',
    filter_action='custom',
    filter_query='',
    sort_action='custom',
    sort_mode='single',
    sort_by=[],
)
_BAR_CHART = '_BAR_CHART'

component = html.Div(
    className='row',
    children=[
        html.Div(
            _TABLE,
            style={'height': 750, 'overflowY': 'scroll', 'width': '65%', 'display': 'inline-block', 'margin': 'auto'},
        ),
        html.Div(
            [html.Div(id=_BAR_CHART)],
            style={'width': '30%', 'display': 'inline-block', 'margin': 'auto', 'float': 'right'},
        ),
    ],
)


def add_callback(app: Dash):
    @app.callback(
        Output(_TABLE_ID, 'data'),
        Input(_TABLE_ID, 'page_current'),
        Input(_TABLE_ID, 'page_size'),
        Input(_TABLE_ID, 'sort_by'),
        Input(_TABLE_ID, 'filter_query'),
    )
    def _update_table(page_current, page_size, sort_by, filter_query):
        new_dataframe = apply_sort(apply_filter(_DATAFRAME, filter_query), sort_by)
        return new_dataframe.iloc[page_current * page_size : (page_current + 1) * page_size].to_dict('records')

    @app.callback(Output(_BAR_CHART, 'children'), Input(_TABLE_ID, 'filter_query'))
    def _update_graph(filter_query: str):
        dataframe = apply_filter(_DATAFRAME, filter_query)
        year_agg = dataframe.groupby('year').count().reset_index()
        print(year_agg.head())

        fig: Figure = px.bar(year_agg, x='year', y='department')
        return html.Div([dcc.Graph(id=random_id('year_distribution'), figure=fig)])

