import random
import string
from dataclasses import replace
from typing import Any, Dict, List, Optional

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component

from ap_exploration.pages.ap_image.build_ap import ArretePrefectoral
from envinorma.back_office.components.am_component import table_to_component
from envinorma.back_office.utils import get_truncated_str
from envinorma.data import Table
from envinorma.structure import TextElement, Title


def _get_html_heading_classname(level: int) -> type:
    if level <= 6:
        return getattr(html, f'H{level}')
    return html.H6


def _title_to_component(title: Title, smallest_level: int) -> Component:
    if title.level == 0:
        return html.P(title.text)
    cls_ = _get_html_heading_classname(title.level + smallest_level - 1)
    if title.id:
        title_component = cls_(title.text, id=title.id)
    else:
        title_component = cls_(title.text)
    return title_component


def _make_component(element: TextElement, smallest_level: int) -> Component:
    if isinstance(element, Table):
        return table_to_component(element, None)
    if isinstance(element, Title):
        return _title_to_component(element, smallest_level)
    if isinstance(element, str):
        return html.P(element)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _visa_modal(visas: List[str], modal_id: str, close_button_id: str, trigger_id: str) -> Component:
    modal = dbc.Modal(
        [
            dbc.ModalHeader('Visas/Condidérants'),
            dbc.ModalBody([html.P(x) for x in visas]),
            dbc.ModalFooter([html.Button('Fermer', id=close_button_id, className='btn btn-light')]),
        ],
        size='xl',
        id=modal_id,
        scrollable=True,
    )
    trigger = dbc.Button('Visas/Considérants', id=trigger_id, color='primary')
    return html.Span([modal, trigger])


def _build_summary_line(title: Title, with_dots: bool) -> Component:
    prefix = (title.level * '•' + ' ') if with_dots else ''
    trunc_title = prefix + get_truncated_str(title.text)
    class_name = 'level_0' if title.level <= 1 else 'level_1'
    return html.Dd(html.A(trunc_title, href=f'#{title.id}', className=class_name))


def _summary(titles: List[Title], with_dots: bool) -> Component:
    lines = [_build_summary_line(title, with_dots) for title in titles]
    return html.Dl(lines, className='summary')


def _summary_and_content(content: Component, summary: Component, height: int = 75) -> Component:
    style = {'max-height': f'{height}vh', 'overflow-y': 'auto'}
    return html.Div(
        html.Div([html.Div(summary, className='col-3'), html.Div(content, className='col-9')], className='row'),
        style=style,
    )


def _random_string() -> str:
    return ''.join([random.choice(string.ascii_letters) for _ in range(9)])


def _add_id(element: TextElement) -> TextElement:
    if isinstance(element, Title):
        return replace(element, id=_random_string())
    return element


def ap_component(
    ap: ArretePrefectoral, visa_modal_id: str, visa_close_button_id: str, visa_trigger_id: str
) -> Component:
    ap.content = [_add_id(x) for x in ap.content]
    content = [_make_component(elt, 4) for elt in ap.content]
    titles = [x for x in ap.content if isinstance(x, Title)]
    title = html.H3(ap.title)
    content = html.Div(
        [title, _visa_modal(ap.visas_considerant, visa_modal_id, visa_close_button_id, visa_trigger_id), *content]
    )
    return _summary_and_content(content, _summary(titles, False))
