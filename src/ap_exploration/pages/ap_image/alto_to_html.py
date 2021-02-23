from typing import Callable, List

import dash_html_components as html
from dash.development.base_component import Component
from envinorma.back_office.components.am_component import structured_text_component
from envinorma.data import StructuredText
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
from envinorma.structure import TextElement, Title, build_structured_text, structured_text_to_text_elements

Sizer = Callable[[float, bool], str]


def _string_to_component(string: AltoString, sizer: Sizer, filled_blocks: bool) -> Component:
    style = {'position': 'absolute', 'top': sizer(string.vpos, True), 'left': sizer(string.hpos, False)}
    if not filled_blocks:
        style['background-color'] = f'rgba(255, 0, 0, {1 - string.confidence})'
    return html.Div(string.content, style=style)


def _line_border(text_line: AltoTextLine, sizer: Sizer, filled_blocks: bool) -> Component:
    style = {
        'position': 'absolute',
        'top': sizer(text_line.vpos, True),
        'left': sizer(text_line.hpos, False),
        'width': sizer(text_line.width, False),
        'height': sizer(text_line.height, True),
        'border': '1px solid rgba(0, 0, 0, 0.5)',
    }
    if filled_blocks:
        style['background-color'] = f'rgba(150, 150, 255)'
    return html.Div('', style=style)


def _block_border(block: AltoComposedBlock, sizer: Sizer, filled_blocks: bool) -> Component:
    style = {
        'position': 'absolute',
        'top': sizer(block.vpos, True),
        'left': sizer(block.hpos, False),
        'width': sizer(block.width, False),
        'height': sizer(block.height, True),
        'border': '1px solid rgba(0, 0, 0, 0.3)',
    }
    if filled_blocks:
        style['background-color'] = f'rgba(255, 150, 150)'
    return html.Div('', style=style)


def _text_block_border(block: AltoTextBlock, sizer: Sizer, filled_blocks: bool) -> Component:
    style = {
        'position': 'absolute',
        'top': sizer(block.vpos, True),
        'left': sizer(block.hpos, False),
        'width': sizer(block.width, False),
        'height': sizer(block.height, True),
        'border': '1px solid rgba(0, 0, 0, 0.4)',
    }
    if filled_blocks:
        style['background-color'] = f'rgba(150, 255, 150)'
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


def _pct_sizer(ratio_width: float, ratio_height: float) -> Sizer:
    def sizer(in_: float, height: bool = False) -> str:
        if height:
            return f'{in_ * ratio_height}%'
        return f'{in_ * ratio_width}%'

    return sizer


def _default_page_sizer(page: AltoPage) -> Sizer:
    ratio_width = 100 / page.width
    ratio_height = 100 / page.height
    sizer = _pct_sizer(ratio_width, ratio_height)
    return sizer


def alto_page_to_html(page: AltoPage, filled_blocks: bool) -> Component:
    ratio_height = 100 / page.height
    sizer = _default_page_sizer(page)
    return html.Div(
        [
            _page_border(page, sizer),
            *[_block_border(block, sizer, filled_blocks) for block in extract_blocks(page)],
            *[_text_block_border(block, sizer, filled_blocks) for block in extract_text_blocks(page)],
            *[_line_border(line, sizer, filled_blocks) for line in extract_lines(page)],
            *[_string_to_component(string, sizer, filled_blocks) for string in extract_strings(page)],
        ],
        style={'height': f'{page.height*ratio_height * 1.5}vh', 'position': 'relative'},
    )


def _line_to_component(line: AltoTextLine, sizer: Sizer) -> Component:
    style = {'position': 'absolute', 'top': sizer(line.vpos, True), 'left': sizer(line.hpos, False)}
    content = ' '.join([string.content for string in line.strings if isinstance(string, AltoString)])
    return html.Div(content, style=style)


def alto_page_to_grouped_lines(page: AltoPage) -> Component:
    ratio_height = 100 / page.height
    sizer = _default_page_sizer(page)

    return html.Div(
        [
            _page_border(page, sizer),
            *[_line_to_component(line, sizer) for line in extract_lines(page)],
        ],
        style={'height': f'{page.height*ratio_height * 1.5}vh', 'position': 'relative'},
    )


def _extract_block_text(block: AltoTextBlock) -> str:
    return ' '.join(
        [string.content for line in block.text_lines for string in line.strings if isinstance(string, AltoString)]
    )


def _text_block_to_component(block: AltoTextBlock, sizer: Sizer) -> Component:
    style = {
        'position': 'absolute',
        'top': sizer(block.vpos, True),
        'left': sizer(block.hpos, False),
        'width': sizer(block.width, False),
    }
    return html.Div(_extract_block_text(block), style=style)


def alto_page_to_grouped_paragraphs(page: AltoPage) -> Component:
    ratio_height = 100 / page.height
    sizer = _default_page_sizer(page)

    return html.Div(
        [
            _page_border(page, sizer),
            *[_text_block_to_component(block, sizer) for block in extract_text_blocks(page)],
        ],
        style={'height': f'{page.height*ratio_height * 1.5}vh', 'position': 'relative'},
    )


def alto_pages_to_paragraphs(pages: List[AltoPage]) -> Component:
    paragraphs = [_extract_block_text(block) for page in pages for block in extract_text_blocks(page)]
    return html.Div([html.P(paragraph) for paragraph in paragraphs])


def _is_article_number(word: str) -> bool:
    if word in ('1er', '1°°', '1"°', '1°"', '1°”', '1”°'):
        return True
    if not word or len(set(word) - {'.', ',', '-', '—'}) == 0:
        return False
    return len(set(word) - set('0123456789S.,-—')) == 0


def _is_title_first_word(word: str) -> bool:
    return word.lower() in ('titre', 'chapitre', 'article')


def _is_title(line: str) -> bool:
    words = line.split()
    return len(words) >= 2 and _is_title_first_word(words[0]) and _is_article_number(words[1])


def _to_element(line: str) -> TextElement:
    if _is_title(line):
        return Title(line, level=1)
    return line


def _group_lines(lines: List[AltoTextLine]) -> List[str]:
    strs = [' '.join([string.content for string in line.strings if isinstance(string, AltoString)]) for line in lines]
    groups: List[List[str]] = [[]]
    for str_ in strs:
        if _is_title(str_):
            groups.extend([[str_], []])
        else:
            groups[-1].append(str_)
    return [' '.join(group) for group in groups if group]


def _extract_text_elements(pages: List[AltoPage]) -> List[TextElement]:
    paragraphs = [
        line for page in pages for block in extract_text_blocks(page) for line in _group_lines(block.text_lines)
    ]
    return [_to_element(paragraph) for paragraph in paragraphs]


def _extract_structured_text(pages: List[AltoPage]) -> StructuredText:
    text_elements = _extract_text_elements(pages)
    return build_structured_text('', text_elements)


def alto_pages_to_structured_text(pages: List[AltoPage]) -> Component:
    structured_text = _extract_structured_text(pages)
    return structured_text_component(structured_text, [], 3)
