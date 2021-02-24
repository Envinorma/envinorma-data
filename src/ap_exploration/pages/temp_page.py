import dash
import dash_html_components as html
from ap_exploration.routing import Page
from dash.development.base_component import Component


def _component() -> Component:
    return html.Div()


def _add_callbacks(app: dash.Dash) -> None:
    pass


page: Page = (_component, _add_callbacks)
