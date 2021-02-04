from typing import List, Union

import dash_html_components as html
from dash.development.base_component import Component

ExtendedComponent = Union[Component, str]


def table_component(
    headers: List[List[ExtendedComponent]], rows: List[List[ExtendedComponent]], class_name: str = ''
) -> Component:
    header = html.Thead([html.Tr([html.Th(cell) for cell in hd]) for hd in headers])
    body = html.Tbody([html.Tr([html.Td(cell) for cell in row]) for row in rows])
    return html.Table([header, body], className='table ' + class_name)
