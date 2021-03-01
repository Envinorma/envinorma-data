import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash import Dash, no_update
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from envinorma.back_office.routing import Page
from envinorma.back_office.utils import UNIQUE_USER, generate_id
from flask_login import login_user


_LOGIN_URL = generate_id(__file__, 'login-url')
_LOGIN_ALERT = generate_id(__file__, 'login-alert')
_LOGIN_USERNAME = generate_id(__file__, 'login-username')
_LOGIN_PASSWORD = generate_id(__file__, 'login-password')
_LOGIN_BUTTON = generate_id(__file__, 'login-button')


def _form() -> Component:
    return dbc.FormGroup(
        [
            dbc.Input(id=_LOGIN_USERNAME, autoFocus=True),
            dbc.FormText('Nom d\'utilisateur'),
            html.Br(),
            dbc.Input(id=_LOGIN_PASSWORD, type='password', debounce=True),
            dbc.FormText('Mot de passe'),
            html.Br(),
            dbc.Button('Valider', color='primary', id=_LOGIN_BUTTON),
        ]
    )


_INFO_TEXT = (
    'L\'édition d\'un arrêté ministériel par toute personne est possible et encouragée. Pour cela,'
    ' des identifiants sont disponibles sur simple contact à l\'adresse remi.delbouys@i-carre.net.'
    ' Vous pouvez également nous faire part de toutes vos remarques, erreurs relevées ou autre '
    'suggestion à cette même adresse.'
)


def _layout() -> Component:
    col = [
        dcc.Location(id=_LOGIN_URL, refresh=True, pathname='/login'),
        html.H2('Connexion'),
        dbc.Alert(_INFO_TEXT, dismissable=True),
        html.Div(id=_LOGIN_ALERT),
        _form(),
    ]
    return dbc.Row(dbc.Col(col, width=6))


def _success() -> Component:
    return dbc.Alert('Connexion réussie.', color='success', dismissable=True)


def _error() -> Component:
    return dbc.Alert('Erreur dans le nom d\'utilisateur ou le mot de passe.', color='danger', dismissable=True)


def _callbacks(app: Dash):
    @app.callback(
        Output(_LOGIN_URL, 'pathname'),
        Output(_LOGIN_ALERT, 'children'),
        Input(_LOGIN_BUTTON, 'n_clicks'),
        State(_LOGIN_PASSWORD, 'value'),
        State(_LOGIN_USERNAME, 'value'),
    )
    def _login(n_clicks, password, username):
        if n_clicks and password and username:
            if username == UNIQUE_USER.username and password == UNIQUE_USER.password:
                login_user(UNIQUE_USER)
                return '/', _success()
            else:
                return no_update, _error()
        return no_update, ''


PAGE = Page(_layout, _callbacks)
