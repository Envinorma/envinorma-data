from enum import Enum
from typing import Dict, List, Optional, Union

import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component


def _replace_line_breaks(message: str) -> List[Union[str, Component]]:
    return [el for piece in message.split('\n') for el in [piece, html.Br()]]


def error_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-danger')


def success_component(message: str) -> Component:
    return html.Div(_replace_line_breaks(message), className='alert alert-success')


class ButtonState(Enum):
    NORMAL = 0
    DISABLED = 1
    HIDDEN = 2
    NORMAL_LINK = 3
    NORMAL_LIGHT = 4


def button(text: str, state: ButtonState, id_: Optional[Union[str, Dict]] = None) -> html.Button:
    disabled = state not in (ButtonState.NORMAL, ButtonState.NORMAL_LINK, ButtonState.NORMAL_LIGHT)
    hidden = state == ButtonState.HIDDEN
    className = 'btn btn-primary'
    if state == ButtonState.NORMAL_LINK:
        className = 'btn btn-link'
    if state == ButtonState.NORMAL_LIGHT:
        className = 'btn btn-light'
    if id_:
        return html.Button(
            text,
            id=id_,
            disabled=disabled,
            className=className,
            n_clicks=0,
            hidden=hidden,
        )
    return html.Button(text, disabled=disabled, className=className, n_clicks=0, hidden=hidden)


def link_button(text: str, href: str, state: ButtonState) -> html.Button:
    if state not in (ButtonState.NORMAL, ButtonState.NORMAL_LINK):
        return button(text, state)
    return dcc.Link(button(text, state), href=href)
