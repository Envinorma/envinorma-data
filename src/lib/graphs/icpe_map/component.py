import json
from typing import List

import plotly.express as px
from dash.dash import Dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from plotly.graph_objects import Figure
from lib.graphs.icpe_map.data import RubriquePerDepartments
from lib.graphs.utils import build_data_file_name, random_id


_DATAFRAME = RubriquePerDepartments.load_csv(build_data_file_name(__file__))
_FRENCH_DEPARTMENTS = json.load(open('data/maps/french_departments.geojson'))


def _extract_int(rubrique_str: str) -> int:
    if rubrique_str.isdigit():
        return int(rubrique_str)
    return 10000


_available_rubriques = sorted(list({x for x in _DATAFRAME.rubrique.values if x}), key=_extract_int)
_available_regimes = sorted(list({x for x in _DATAFRAME.regime.values if isinstance(x, str)}))
_RUBRIQUE_DROPDOWN = random_id('rubrique_dropdown')
_REGIME_DROPDOWN = random_id('regime_dropdown')
_ICPE_MAP_GRAPH = random_id('map_graph')
dropdown_rubrique = dcc.Dropdown(
    id=_RUBRIQUE_DROPDOWN,
    options=[{'label': i, 'value': i} for i in _available_rubriques],
    value=[],
    multi=True,
    placeholder='Rubrique',
)

dropdown_regime = dcc.Dropdown(
    id=_REGIME_DROPDOWN,
    options=[{'label': i, 'value': i} for i in _available_regimes],
    value=[],
    multi=True,
    placeholder='Régime',
)

component = html.Div(
    [
        html.Div([html.Div([dropdown_regime], style={'width': '20%', 'display': 'inline-block'})]),
        html.Div([html.Div([dropdown_rubrique], style={'width': '20%', 'display': 'inline-block'})]),
        dcc.Graph(id=_ICPE_MAP_GRAPH),
    ]
)


def add_callback(app: Dash):
    def _update_graph(rubriques: List[str], regimes: List[str]):
        if rubriques and regimes:
            filter_ = _DATAFRAME['rubrique'].isin(rubriques) & _DATAFRAME['regime'].isin(regimes)
        elif rubriques and not regimes:
            filter_ = _DATAFRAME['rubrique'].isin(rubriques)
        elif not rubriques and regimes:
            filter_ = _DATAFRAME['regime'].isin(regimes)
        else:
            filter_ = None
        filtered_dataframe = _DATAFRAME[filter_] if filter_ is not None else _DATAFRAME
        agg_dataframe = filtered_dataframe.groupby(by='department').sum().reset_index()

        fig: Figure = px.choropleth(
            agg_dataframe,
            geojson=_FRENCH_DEPARTMENTS,
            locations='department',
            color='count',
            color_continuous_scale='Viridis',
            featureidkey="properties.code",
            labels={'count': 'Nombre d\'installations'},
        )
        fig.update_geos(fitbounds="locations", visible=False)
        # fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
        return fig

    app.callback(
        Output(_ICPE_MAP_GRAPH, 'figure'), Input(_RUBRIQUE_DROPDOWN, 'value'), Input(_REGIME_DROPDOWN, 'value')
    )(_update_graph)
