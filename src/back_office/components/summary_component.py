from typing import List

import dash_html_components as html
from back_office.utils import get_truncated_str
from dash.development.base_component import Component
from lib.data import StructuredText
from lib.structure_extraction import Title, structured_text_to_text_elements


def _build_summary_line(title: Title) -> Component:
    trunc_title = title.level * '—' + ' ' + get_truncated_str(title.text)
    class_name = 'level_0' if title.level <= 1 else 'level_1'
    return html.Dd(html.A(trunc_title, href=f'#{title.id}', className=class_name))


def _extract_titles(text: StructuredText) -> List[Title]:
    return [el for el in structured_text_to_text_elements(text, level=0) if isinstance(el, Title)]


def _build_component(titles: List[Title]) -> Component:
    lines = [_build_summary_line(title) for title in titles]
    return html.Dl(lines, className='summary')


def summary_component(text: StructuredText) -> Component:
    titles = _extract_titles(text)
    return _build_component(titles)
