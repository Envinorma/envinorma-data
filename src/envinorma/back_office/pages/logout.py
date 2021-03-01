import dash_core_components as dcc
from dash.development.base_component import Component
from envinorma.back_office.routing import Page
from envinorma.back_office.utils import get_current_user
from flask_login import logout_user


def _layout() -> Component:
    if get_current_user().is_authenticated:
        logout_user()
    return dcc.Location(pathname='/', id='back_home')


PAGE = Page(_layout, None)
