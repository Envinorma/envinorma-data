import re
import traceback
from dataclasses import replace
from typing import Any, Dict, List, Optional, Tuple, Union

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_editable_div as ded
import dash_html_components as html
from bs4 import BeautifulSoup
from dash.dependencies import Input, Output, State
from dash.development.base_component import Component
from lib.data import ArreteMinisteriel, EnrichedString, StructuredText, Table, am_to_text
from lib.parse_html import extract_text_elements
from lib.structure_extraction import TextElement, Title, build_structured_text, structured_text_to_text_elements

from back_office.app_init import app
from back_office.components import error_component, success_component
from back_office.components.am_component import table_to_component
from back_office.fetch_data import load_initial_am, load_structured_am, upsert_structured_am
from back_office.routing import build_am_page
from back_office.utils import AMOperation, RouteParsingError, assert_str, get_truncated_str

_TOC_COMPONENT = 'structure-edition-toc'
_TEXT_AREA_COMPONENT = 'structure-edition-text-area-component'
_FORM_OUTPUT = 'structure-edition-form-output'


def _text_to_elements(text: StructuredText) -> List[TextElement]:
    return structured_text_to_text_elements(text, 0)


def _element_to_component(element: TextElement) -> Component:
    if isinstance(element, Table):
        return table_to_component(element, None)
    elif isinstance(element, Title):
        classname = f'H{element.level + 3}' if element.level <= 3 else 'H6'
        return getattr(html, classname)('#' * element.level + ' ' + element.text, id=element.id)
    elif isinstance(element, str):
        return html.P(element)
    raise NotImplementedError(f'Not implemented for type {type(element)}')


def _prepare_editable_div_value(elements: List[TextElement]) -> List[Component]:
    return [_element_to_component(el) for el in elements]


def _structure_edition_component(text: StructuredText) -> Component:
    text_elements = _text_to_elements(text)[1:]  # Don't modify main title.
    return ded.EditableDiv(
        id=_TEXT_AREA_COMPONENT,
        children=_prepare_editable_div_value(text_elements),
        className='text',
        style={'padding': '10px', 'border': '1px solid rgba(0,0,0,.1)', 'border-radius': '5px'},
    )


def _get_toc_component(text: StructuredText) -> Component:
    elements = _text_to_elements(text)
    initial_value = html.P([_format_toc_line(el) for el in elements if isinstance(el, Title) and el.level > 0])
    return html.Div(
        dbc.Spinner(html.Div(initial_value, id=_TOC_COMPONENT)), className='summary', style={'height': '60vh'}
    )


def _submit_button() -> Component:
    return html.Button(
        'Enregistrer et continuer à éditer',
        id='submit-val-structure-edition',
        className='btn btn-primary center',
        n_clicks=0,
        style={'margin-right': '10px'},
    )


def _go_back_button(am_page: str) -> Component:
    return dcc.Link(html.Button('Quitter le mode édition', className='btn btn-link center'), href=am_page)


def _footer_buttons(am_page: str) -> Component:
    style = {'display': 'inline-block'}
    return html.Div([_submit_button(), _go_back_button(am_page)], style=style)


def _fixed_footer(am_page: str) -> Component:
    output = html.Div(html.Div(id=_FORM_OUTPUT), style={'display': 'inline-block'})
    content = html.Div([output, html.Br(), _footer_buttons(am_page)])
    return html.Div(
        content,
        style={
            'position': 'fixed',
            'bottom': '0px',
            'left': '0px',
            'width': '100%',
            'text-align': 'center',
            'background-color': 'white',
            'padding-bottom': '10px',
            'padding-top': '10px',
        },
    )


def _get_instructions() -> Component:
    return html.Div(
        html.A(
            'Guide de structuration',
            href='https://www.notion.so/R-gles-de-structuration-c1ee7ecc6d79474097991595cba3471b',
            target='_blank',
        ),
        className='alert alert-light',
        style={'margin-top': '30px'},
    )


def _get_main_row(text: StructuredText) -> Component:
    first_column = html.Div(className='col-3', children=[_get_toc_component(text)])
    second_column = html.Div(
        className='col-9',
        children=[html.P(text.title.text), _structure_edition_component(text)],
    )
    return html.Div(className='row', children=[first_column, second_column])


def _make_am_structure_edition_component(am_id: str, am: ArreteMinisteriel) -> Component:
    components = [
        html.Div(className='row', children=_get_instructions()),
        _get_main_row(am_to_text(am)),
        _fixed_footer(build_am_page(am_id)),
        html.P(am_id, hidden=True, id='am-id-structure-edition'),
    ]
    return html.Div(components, style={'margin-bottom': '300px'})


def _parse_route(route: str) -> str:
    pieces = route.split('/')[1:]
    if len(pieces) != 2:
        raise RouteParsingError(f'Error parsing route {route}')
    am_id = pieces[0]
    try:
        operation = AMOperation(pieces[1])
    except ValueError:
        raise RouteParsingError(f'Error parsing route {route}')
    if operation != AMOperation.EDIT_STRUCTURE:
        raise RouteParsingError(f'Error parsing route {route}')
    return am_id


def router(pathname: str) -> Component:
    try:
        am_id = _parse_route(pathname)
        am = load_structured_am(am_id) or load_initial_am(am_id)
    except RouteParsingError as exc:
        return html.P(f'404 - Page introuvable - {str(exc)}')
    if not am:
        return html.P(f'404 - Arrêté {am_id} introuvable.')
    return _make_am_structure_edition_component(am_id, am)


class _FormHandlingError(Exception):
    pass


def _ensure_no_outer_alineas(text: StructuredText) -> None:
    if len(text.outer_alineas) != 0:
        raise _FormHandlingError(f'There should be no alineas at toplevel, found {len(text.outer_alineas)}.')


def _extract_tables(text: StructuredText) -> List[Table]:
    return [al.table for al in text.outer_alineas if al.table] + [
        tb for sec in text.sections for tb in _extract_tables(sec)
    ]


def _build_title(line: str) -> Title:
    nb_hastags = _count_prefix_hashtags(line)
    return Title(line[nb_hastags:].strip(), level=nb_hastags)


_TABLE_MARK = 'XXXTABLEAUXXX'


def _clean_element(element: TextElement) -> TextElement:
    if not isinstance(element, (Title, str)):
        return element
    str_ = element.text if isinstance(element, Title) else element
    if not str_.startswith('#'):
        return str_
    return _build_title(str_)


def _remove_hashtags_from_elements(elements: List[TextElement]) -> List[TextElement]:
    return [_clean_element(el) for el in elements]


def _replace_tables(elements: List[TextElement], tables: List[Table]) -> List[TextElement]:
    i = 0
    final_elements: List[TextElement] = []
    for element in elements:
        if isinstance(element, Table):
            if i >= len(tables):
                raise ValueError('Not enough tables to replace')
            final_elements.append(tables[i])
            i += 1
        else:
            final_elements.append(element)
    return final_elements


def _build_new_elements(am_soup: BeautifulSoup, tables: List[Table]) -> List[TextElement]:
    elements = _replace_tables(extract_text_elements(am_soup), tables)
    return _remove_hashtags_from_elements(elements)


def _keep_tables(elements: List[TextElement]) -> List[Table]:
    return [el for el in elements if isinstance(el, Table)]


def _ensure_all_tables_are_found_once(initial_tables: List[Table], new_tables: List[Table]) -> None:
    missing_tables = [i for i, table in enumerate(initial_tables) if table not in new_tables]
    if missing_tables:
        raise _FormHandlingError(
            f'Erreur lors de l\'enregistrement: dans le texte de sortie, il manque les tableaux n° {missing_tables}.'
        )
    if len(initial_tables) != len(new_tables):
        raise _FormHandlingError(
            f'Erreur lors de l\'enregistrement: dans le texte de sortie, il y a trop '
            f'de tableaux: {len(new_tables)} contre {len(initial_tables) } dans le texte d\'entrée.'
        )


def _extract_words_from_structured_text(text: StructuredText) -> List[str]:
    title_words = _extract_words(text.title.text)
    alinea_words = [
        word for al in text.outer_alineas for word in _extract_words(al.text if not al.table else _TABLE_MARK)
    ]
    section_words = [word for sec in text.sections for word in _extract_words_from_structured_text(sec)]
    return title_words + alinea_words + section_words


def _keep_non_empty(strs: List[str]) -> List[str]:
    return [x for x in strs if x]


def _ensure_str(str_: Any) -> str:
    if not isinstance(str_, str):
        raise ValueError('Wrong type {type(str_)}, expecting str')
    return str_


def _ensure_strs(strs: List[Any]) -> List[str]:
    return [_ensure_str(str_) for str_ in strs]


def _extract_words(str_: str) -> List[str]:
    return _keep_non_empty(_ensure_strs(re.split(r'\W+', str_)))


def _extract_str_repr(element: TextElement) -> str:
    if isinstance(element, Table):
        return _TABLE_MARK
    if isinstance(element, str):
        return element
    if isinstance(element, Title):
        return element.text
    raise NotImplementedError(f'Unhandled type {type(element)}')


def _extract_element_words(elements: List[TextElement]) -> List[str]:

    lines = [_extract_str_repr(element) for element in elements]
    return [word for line in lines for word in _extract_words(line)]


def _extract_text_area_words(soup: BeautifulSoup) -> List[str]:
    elements = extract_text_elements(soup)
    return _extract_element_words(elements)


def _extract_first_different_word(text_1: List[str], text_2: List[str]) -> Optional[int]:
    if len(text_1) != len(text_2):
        raise ValueError(
            f'Input texts must have same length, received lists of lengths {len(text_1)} and {len(text_2)}'
        )
    min_length = min(len(text_1), len(text_2))
    for i in range(min_length):
        if text_1[i] != text_2[i]:
            return i
    return None


def _check_have_same_words(am: StructuredText, new_am_soup: BeautifulSoup) -> None:
    previous_am_words = _extract_words_from_structured_text(replace(am, title=EnrichedString('')))
    new_am_words = _extract_text_area_words(new_am_soup)
    min_len = min(len(previous_am_words), len(new_am_words))
    word_index = _extract_first_different_word(previous_am_words[:min_len], new_am_words[:min_len])
    if len(previous_am_words) != len(new_am_words) or word_index:
        message = '\n'.join(
            [
                'Le texte modifié est différent du texte initial',
                f'Taille du texte initial: {len(previous_am_words)}',
                f'Taille du texte modifié: {len(new_am_words)}',
                f'Premier mot différent: {previous_am_words[word_index]} != {new_am_words[word_index]}'
                if word_index is not None
                else '',
            ]
        )
        raise _FormHandlingError(message)


def _create_new_text(previous_text: StructuredText, new_am_str: str) -> StructuredText:
    new_am_soup = BeautifulSoup(new_am_str, 'html.parser')
    _check_have_same_words(previous_text, new_am_soup)
    tables = _extract_tables(previous_text)
    new_elements = _build_new_elements(new_am_soup, tables)
    new_tables = _keep_tables(new_elements)
    _ensure_all_tables_are_found_once(tables, new_tables)
    new_text = build_structured_text(Title(previous_text.title.text, 0), new_elements)
    _ensure_no_outer_alineas(new_text)
    return new_text


def _structure_text(am_id: str, new_am: str) -> ArreteMinisteriel:
    previous_am_version = load_structured_am(am_id) or load_initial_am(am_id)
    if not previous_am_version:
        raise _FormHandlingError(f'am with id {am_id} not found, which should not happen')
    previous_text = am_to_text(previous_am_version)
    new_text = _create_new_text(previous_text, new_am)
    return replace(previous_am_version, sections=new_text.sections)


def _parse_text_and_save_message(am_id: str, new_am: str) -> str:
    text = _structure_text(am_id, new_am)
    upsert_structured_am(am_id, text)
    return f'Enregistrement réussi.'


def _extract_form_value_and_save_text(nb_clicks: int, am_id: str, text_area_content: Optional[str]) -> Component:
    if nb_clicks == 0 or text_area_content is None:
        return html.Div()
    new_am = assert_str(text_area_content)
    try:
        success_message = _parse_text_and_save_message(am_id, new_am)
    except _FormHandlingError as exc:
        return error_component(f'Erreur pendant l\'enregistrement. Détails de l\'erreur:\n{str(exc)}')
    except Exception:  # pylint: disable=broad-except
        return error_component(
            f'Erreur inattendue pendant l\'enregistrement. Détails de l\'erreur:\n{traceback.format_exc()}'
        )
    return success_component(success_message)


def _extract_all_lines_one_element(element: Dict[str, Any]) -> List[str]:
    if not element.get('props', {}).get('children'):
        return []
    children = element.get('props', {}).get('children')
    if isinstance(children, list):
        return _extract_all_lines(children)
    if isinstance(children, str):
        return [children]
    if isinstance(children, dict):
        return _extract_all_lines_one_element(children)
    raise ValueError(f'Unexpected element type type({element})')


def _extract_all_lines(elements: List[Dict[str, Any]]) -> List[str]:
    return [line for element in elements for line in _extract_all_lines_one_element(element)]


def _count_prefix_hashtags(line: str) -> int:
    for i, char in enumerate(line):
        if char != '#':
            return i
    return len(line)


def _make_title(line: str, id_: Optional[str]) -> Title:
    nb_hashtags = _count_prefix_hashtags(line)
    trunc_title = line[nb_hashtags:].strip()
    return Title(trunc_title, level=nb_hashtags, id=id_)


def _format_toc_line(title: Title) -> Component:
    trunc_title = get_truncated_str(title.text)
    trunc_title_component = html.Span(trunc_title) if title.level > 1 else html.B(trunc_title)
    return html.A(
        [html.Span(title.level * '•' + ' ', style={'color': 'grey'}), trunc_title_component], href=f'#{title.id}'
    )


def _extract_lines_with_potential_id(html: BeautifulSoup) -> List[Tuple[str, Optional[str]]]:
    text_elements = extract_text_elements(html)
    strs: List[Tuple[str, Optional[str]]] = []
    for element in text_elements:
        if isinstance(element, Title):
            strs.append((element.text, element.id))
        elif isinstance(element, str):
            strs.append((element, None))
    return strs


def _parse_html_area_and_display_toc(html_str: str) -> Component:
    lines_and_ids = _extract_lines_with_potential_id(BeautifulSoup(html_str, 'html.parser'))
    formatted_lines = [_format_toc_line(_make_title(line, id_)) for line, id_ in lines_and_ids if line.startswith('#')]
    new_title_levels = html.P(formatted_lines)
    return html.P(new_title_levels)


@app.callback(
    Output(_FORM_OUTPUT, 'children'),
    [Input('submit-val-structure-edition', 'n_clicks'), Input('am-id-structure-edition', 'children')],
    [State(_TEXT_AREA_COMPONENT, 'value')],
)
def update_output(nb_clicks, am_id, state: Optional[str]):
    return _extract_form_value_and_save_text(nb_clicks, am_id, state)


@app.callback(Output(_TOC_COMPONENT, 'children'), [Input(_TEXT_AREA_COMPONENT, 'value')], prevent_initial_call=True)
def _(text_area_content):
    return _parse_html_area_and_display_toc(text_area_content)
