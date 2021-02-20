from typing import Callable
from envinorma.io.alto import (
    AltoComposedBlock,
    AltoPage,
    AltoString,
    AltoTextBlock,
    AltoTextLine,
    extract_blocks,
    extract_lines,
    extract_strings,
    extract_text_blocks,
)
import dash_html_components as html
from dash.development.base_component import Component


Sizer = Callable[[float, bool], str]


def _string_to_component(string: AltoString, sizer: Sizer) -> Component:
    string.confidence
    style = {
        'position': 'absolute',
        'top': sizer(string.vpos, True),
        'left': sizer(string.hpos, False),
        'background-color': f'rgba(255, 0, 0, {1 - string.confidence})'
        # 'font-size': f'{string.height * 0.6}px',
    }
    return html.Div(string.content, style=style)


def _line_border(text_line: AltoTextLine, sizer: Sizer) -> Component:
    style = {
        'position': 'absolute',
        'top': sizer(text_line.vpos, True),
        'left': sizer(text_line.hpos, False),
        'width': sizer(text_line.width, False),
        'height': sizer(text_line.height, True),
        'border': '1px solid rgba(0, 0, 0, 0.5)',
    }
    return html.Div('', style=style)


def _block_border(block: AltoComposedBlock, sizer: Sizer) -> Component:
    style = {
        'position': 'absolute',
        'top': sizer(block.vpos, True),
        'left': sizer(block.hpos, False),
        'width': sizer(block.width, False),
        'height': sizer(block.height, True),
        'border': '1px solid rgba(0, 0, 0, 0.3)',
    }
    return html.Div('', style=style)


def _text_block_border(block: AltoTextBlock, sizer: Sizer) -> Component:
    style = {
        'position': 'absolute',
        'top': sizer(block.vpos, True),
        'left': sizer(block.hpos, False),
        'width': sizer(block.width, False),
        'height': sizer(block.height, True),
        'border': '1px solid rgba(0, 0, 0, 0.4)',
    }
    return html.Div('', style=style)


def _page_border(page: AltoPage, sizer: Sizer) -> Component:
    style = {
        'position': 'absolute',
        'top': 0,
        'left': 0,
        'width': sizer(page.width, False),
        'height': sizer(page.height, True),
        'border': '1px solid rgba(0, 0, 0, 0.8)',
    }
    return html.Div('', style=style)


def alto_page_to_html(page: AltoPage) -> Component:
    ratio_width = 100 / page.width
    ratio_height = 100 / page.height

    def sizer(in_: float, height: bool = False) -> str:
        if height:
            return f'{in_ * ratio_height}%'
        return f'{in_ * ratio_width}%'

    return html.Div(
        [
            _page_border(page, sizer),
            *[_block_border(block, sizer) for block in extract_blocks(page)],
            *[_text_block_border(block, sizer) for block in extract_text_blocks(page)],
            *[_line_border(line, sizer) for line in extract_lines(page)],
            *[_string_to_component(string, sizer) for string in extract_strings(page)],
        ],
        style={'height': f'{page.height*ratio_height * 1.5}vh', 'position': 'relative'},
    )