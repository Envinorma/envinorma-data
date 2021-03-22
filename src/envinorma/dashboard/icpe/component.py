import json
from typing import Dict, Optional

import dash_core_components as dcc
import dash_html_components as html
import dash_table
import plotly.express as px
from dash.dash import Dash
from dash.dependencies import Input, Output
from plotly.graph_objects import Figure

from ..utils import apply_filter, apply_sort, build_data_file_name, generate_dropdown, random_id
from .data import ICPEDataset

_DATAFRAME = ICPEDataset.load_csv(build_data_file_name(__file__))
_FRENCH_DEPARTMENTS = json.load(open(__file__.replace('icpe/component.py', 'assets/maps/french_departments.geojson')))
_PAGE_SIZE = 25
_TABLE_ID = random_id('TABLE')
_TABLE = dash_table.DataTable(
    id=_TABLE_ID,
    columns=[{'name': i, 'id': i} for i in sorted(_DATAFRAME.columns)],
    page_current=0,
    page_size=_PAGE_SIZE,
    page_action='custom',
    filter_action='custom',
    filter_query='active = "En fonctionnement"',
    sort_action='custom',
    sort_mode='single',
    sort_by=[],
)
_BAR_CHART = random_id('_BAR_CHART')
_MAP_GRAPH = random_id('map_graph')
_DEFAULT_X_VAR = 'region'
_X_DROPDOWN_ID, _X_DROPDOWN = generate_dropdown('En abscisse', list(_DATAFRAME.keys()), _DEFAULT_X_VAR)
_Y_DROPDOWN_ID, _Y_DROPDOWN = generate_dropdown('En couleur', list(_DATAFRAME.keys()), 'family')
_PREVIOUS_X_VAR = _DEFAULT_X_VAR


def _dropdown_default() -> Dict[str, str]:
    return {'width': '500px', 'display': 'inline-block', 'margin': '5'}


component = html.Div(
    className='row',
    children=[
        html.Div(
            [
                html.Div(['X ', html.Div([_X_DROPDOWN], style=_dropdown_default())]),
                html.Div(['Y ', html.Div([_Y_DROPDOWN], style=_dropdown_default())]),
                html.Div(id=_BAR_CHART),
                dcc.Graph(id=_MAP_GRAPH),
            ],
            style={'width': '50%', 'display': 'inline-block', 'margin': 'auto'},
        ),
        html.Div(
            _TABLE,
            style={
                'height': 1000,
                'overflowY': 'scroll',
                'width': '45%',
                'display': 'inline-block',
                'margin': 'auto',
                'float': 'right',
            },
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

    @app.callback(
        Output(_BAR_CHART, 'children'),
        Input(_TABLE_ID, 'filter_query'),
        Input(_X_DROPDOWN_ID, 'value'),
        Input(_Y_DROPDOWN_ID, 'value'),
    )
    def _update_graph(filter_query: str, x_var: Optional[str], y_var: Optional[str]):
        global _PREVIOUS_X_VAR
        if x_var:
            _PREVIOUS_X_VAR = x_var
        else:
            x_var = _PREVIOUS_X_VAR
        if y_var == x_var:
            y_var = None
        dataframe = apply_filter(_DATAFRAME, filter_query)
        group = [x_var, y_var] if y_var else [x_var]
        year_agg = dataframe.groupby(group).count().reset_index()

        fig: Figure = px.bar(
            year_agg,
            x=x_var,
            y='code_postal',
            color=y_var,
            title=f'Nombre d\'installations par {x_var}.',
            labels={'code_postal': 'Nombre d\'occurrences.'},
        )
        return html.Div([dcc.Graph(id=random_id('bars'), figure=fig)])

    @app.callback(Output(_MAP_GRAPH, 'figure'), Input(_TABLE_ID, 'filter_query'))
    def _update_map(filter_query: str):
        dataframe = apply_filter(_DATAFRAME, filter_query)
        agg_dataframe = dataframe.groupby(by='num_dep').count().reset_index()

        fig: Figure = px.choropleth(
            agg_dataframe,
            geojson=_FRENCH_DEPARTMENTS,
            locations='num_dep',
            color='code_postal',
            color_continuous_scale='Viridis',
            featureidkey='properties.code',
            labels={'code_postal': 'Nombre d\'installations.'},
            title='Nombre d\'installations par départements.',
        )
        fig.update_geos(fitbounds='locations', visible=False)
        return fig
