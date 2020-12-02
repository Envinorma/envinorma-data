import dash
import dash_html_components as html

from lib.graphs.rubriques_over_time import component as component_rubriques_over_time
from lib.graphs.icpe_map import component as component_icpe_map
from lib.graphs.tables_in_am import component as component_am_tables

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = dash.Dash(__name__, external_stylesheets=external_stylesheets)


app.layout = html.Div(
    [
        html.Div([html.H1(['Envinorma'])]),
        html.Div([html.H2(['Distribution des classements selon l\'année par rubrique et département.'])]),
        component_rubriques_over_time.component,
        # html.Div([html.H2(['Distribution des rubriques dans les départements de France métropolitaine et Corse.'])]),
        # component_icpe_map.component,
        # html.Div([html.H2(['Statistiques sur les tableaux extraits des AM.'])]),
        # component_am_tables.component,
    ],
    style={'width': '80%', 'margin': 'auto'},
)
component_rubriques_over_time.add_callback(app)
# component_icpe_map.add_callback(app)
# component_am_tables.add_callback(app)


if __name__ == '__main__':
    app.run_server(debug=True)
