import dash
import dash_html_components as html
from dash.development.base_component import Component

from ap_exploration.routing import Page


def _component() -> Component:
    return html.Div()


def _add_callbacks(app: dash.Dash) -> None:
    pass


page: Page = (_component, _add_callbacks)
