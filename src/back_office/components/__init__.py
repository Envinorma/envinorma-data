from typing import List, Union

import dash_html_components as html
from dash.development.base_component import Component


def _replace_line_breaks(message: str) -> List[Union[str, Component]]:
    return [el for piece in message.split('\n') for el in [piece, html.Br()]]


def error_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-danger')


def success_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-success')
