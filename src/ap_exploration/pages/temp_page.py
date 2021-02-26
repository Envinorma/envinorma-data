import os
from typing import List, Tuple

import dash
import dash_html_components as html
from ap_exploration.pages.ap_image.alto_to_html import (
    Sizer,
    _default_page_sizer,
    _page_border,
    _string_to_component,
    extract_strings,
)
from ap_exploration.pages.ap_image.extract_ap_structure import Box, _find_main_title
from ap_exploration.pages.ap_image.table_extraction import LocatedTable
from ap_exploration.routing import Page
from dash.development.base_component import Component
from envinorma.config import config
from envinorma.io.alto import AltoPage
from tqdm import tqdm

_PDF_AP_FOLDER = config.storage.ap_data_folder
_DOC_IDS = [os.path.join(_PDF_AP_FOLDER, x) for x in os.listdir(_PDF_AP_FOLDER) if x.endswith('.pdf')][:110]


def _load_data() -> List[Tuple[List[AltoPage], List[LocatedTable]]]:
    import pickle

    return pickle.load(open('tmp.pickle', 'rb'))


_DATA = _load_data()[:100]
_GROUPS = [_find_main_title(pages) for pages, _ in tqdm(_DATA)]


def _draw_box(box: Box, sizer: Sizer) -> Component:
    style = {
        'position': 'absolute',
        'top': sizer(box.vpos, True),
        'left': sizer(box.hpos, False),
        'width': sizer(box.width, False),
        'height': sizer(box.height, True),
        'border': '1px solid rgba(0, 0, 0, 0.4)',
    }
    return html.Div('', style=style)


def alto_page_to_html(page: AltoPage, boxes: List[Box]) -> Component:
    ratio_height = 100 / page.height
    sizer = _default_page_sizer(page)
    return html.Div(
        [
            _page_border(page, sizer),
            *[_draw_box(box, sizer) for box in boxes],
            *[_string_to_component(string, sizer, False) for string in extract_strings(page)],
        ],
        style={'height': f'{page.height*ratio_height * 1.5}vh', 'position': 'relative'},
    )


def _comp(id_: str, page: AltoPage, boxes: List[Box]) -> Component:
    return html.Div([html.H3(id_), alto_page_to_html(page, boxes)])


def _component() -> Component:
    return html.Div([_comp(id_, page, boxes) for id_, (page, boxes) in zip(_DOC_IDS, _GROUPS)])


def _add_callbacks(app: dash.Dash) -> None:
    pass


page: Page = (_component, _add_callbacks)
