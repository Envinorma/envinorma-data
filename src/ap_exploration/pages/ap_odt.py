import json
import os
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component
from tqdm import tqdm

from ap_exploration.db.ap_sample import AP_FOLDER, APS
from ap_exploration.routing import Endpoint
from envinorma.back_office.components.am_component import structured_text_component, summary_and_content
from envinorma.back_office.components.summary_component import summary_component
from envinorma.back_office.components.table import table_component
from envinorma.data import StructuredText
from envinorma.io.open_document import ODTExtractedText, extract_text_and_metadata
from envinorma.utils import ensure_not_none

_DB_FILENAME = 'tmp_ap_db.json'


def _load_texts() -> Dict[str, ODTExtractedText]:
    if not os.path.exists(_DB_FILENAME):
        db = {ap_id: extract_text_and_metadata(os.path.join(AP_FOLDER, ap_id)) for ap_id in tqdm(APS)}
        to_dump = {id_: dict_.to_dict() for id_, dict_ in db.items()}
        json.dump(to_dump, open(_DB_FILENAME, 'w'))
        return db
    return {id_: ODTExtractedText.from_dict(dict_) for id_, dict_ in json.load(open(_DB_FILENAME)).items()}


_DB = [x for x in sorted(_load_texts().items())]


def _ap_href(ap_id: str) -> str:
    return f'{Endpoint.AP_ODT}/id/{ap_id}'


def _text_cell(text: ODTExtractedText) -> Component:
    if text.text is None:
        return html.Span(text.error, style={'color': 'red'})
    return html.Span('OK', style=dict(color='green'))


def _text_row(ap_id: int, filename: str, extracted_text: ODTExtractedText) -> List[Union[str, Component]]:
    nb_sections = str(extracted_text.metadata.nb_sections) if extracted_text.metadata else ''
    return [str(ap_id), dcc.Link(filename, href=_ap_href(str(ap_id))), _text_cell(extracted_text), nb_sections]


def _ap_list() -> Component:
    headers = [['ID', 'Nom du fichier', 'Ouput', 'Nb sections']]
    rows = [_text_row(ap_id, filename, text) for ap_id, (filename, text) in enumerate(_DB)]
    return table_component(headers, rows)


def _ap_content(text: StructuredText) -> Component:
    return summary_and_content(structured_text_component(text, [], 3), summary_component(text))


def _ap(ap_id: str) -> Component:
    filename, ap_ = _DB[int(ap_id)]
    ap: StructuredText = ensure_not_none(ap_.text)
    return html.Div([html.H1(filename), _ap_content(ap)])


def _ap_layout(ap_id: Optional[str] = None) -> Component:
    if ap_id is None:
        return _ap_list()
    return _ap(ap_id)


page = (_ap_layout, None)
