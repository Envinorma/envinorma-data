from typing import List

import plotly.express as px
from dash.dash import Dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from plotly.graph_objects import Figure
from lib.graphs.rubriques_over_time.data import RubriqueOverTimeDataset
from lib.graphs.utils import build_data_file_name


dataframe = RubriqueOverTimeDataset.load_csv(build_data_file_name(__file__))

available_rubrique = sorted(list(set(dataframe.rubriques)))
available_departments = sorted(list(set(dataframe.departments)))
RUBRIQUE_DROPDOWN = 'rubrique_dropdown'
DEPARTMENTS_DROPDOWN = 'departments_dropdown'
DATE_GRAPH = 'date_graph'
dropdown_rubrique = dcc.Dropdown(
    id=RUBRIQUE_DROPDOWN,
    options=[{'label': i, 'value': i} for i in available_rubrique],
    value=[],
    multi=True,
    placeholder='Rubrique',
)
dropdown_department = dcc.Dropdown(
    id=DEPARTMENTS_DROPDOWN,
    options=[{'label': i, 'value': i} for i in available_departments],
    value=[],
    multi=True,
    placeholder='Département',
)
component = html.Div(
    [
        html.Div(
            [
                html.Div([dropdown_rubrique], style={'width': '20%', 'display': 'inline-block'}),
                html.Div([dropdown_department], style={'width': '20%', 'display': 'inline-block'}),
            ]
        ),
        dcc.Graph(id=DATE_GRAPH),
    ]
)


def add_callback(app: Dash):
    @app.callback(Output(DATE_GRAPH, 'figure'), Input(RUBRIQUE_DROPDOWN, 'value'), Input(DEPARTMENTS_DROPDOWN, 'value'))
    def _update_graph(rubriques: List[str], departments: List[str]):
        if rubriques and departments:
            filter_ = dataframe['rubriques'].isin(rubriques) & dataframe['departments'].isin(departments)
        elif rubriques and not departments:
            filter_ = dataframe['rubriques'].isin(rubriques)
        elif not rubriques and departments:
            filter_ = dataframe['departments'].isin(departments)
        else:
            filter_ = None
        filtered_dataframe = dataframe[filter_] if filter_ is not None else dataframe
        year_agg = filtered_dataframe.groupby('years').sum()
        year_range = list(range(1970, 2021))
        year_counter = {year: occ for year, occ in zip(year_agg.index, year_agg.occurrences)}

        fig: Figure = px.bar(x=year_range, y=[year_counter.get(x, 0) for x in year_range])
        fig.update_layout(margin={'l': 40, 'b': 40, 't': 10, 'r': 0}, hovermode='closest')
        fig.update_xaxes(title_text='Année de création')
        fig.update_yaxes(title_text='Nombre d\'occurrences')

        return fig
