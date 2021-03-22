from enum import Enum
from typing import Any, Callable, Counter, Dict, List, Optional, Tuple

import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.development.base_component import Component

from envinorma.back_office.app_init import app
from envinorma.back_office.components import error_component
from envinorma.back_office.components.diff import diff_component
from envinorma.back_office.fetch_data import load_most_advanced_am
from envinorma.back_office.utils import ID_TO_AM_MD, compute_am_diff, extract_aida_am, extract_legifrance_am
from envinorma.data import AMMetadata, ArreteMinisteriel
from legifrance.legifrance_API import LegifranceRequestError

_PREFIX = __file__.split('/')[-1].replace('.py', '').replace('_', '-')
_ARGS = _PREFIX + '-args'
_SPINNER = _PREFIX + '-spinner'


class CompareWith(Enum):
    AIDA = 'aida'
    LEGIFRANCE = 'legifrance'


def _md(am: ArreteMinisteriel) -> Optional[AMMetadata]:
    return ID_TO_AM_MD.get(am.id or '')


def _diff_component(am_source: ArreteMinisteriel, am_envinorma: ArreteMinisteriel, source_title: str) -> Component:
    differences = compute_am_diff(am_source, am_envinorma)
    return diff_component(differences, source_title, 'Version Envinorma')


def _legifrance_diff(am: ArreteMinisteriel) -> Component:
    md = _md(am)
    if not md:
        return error_component('AM Metadata not found')
    try:
        legifrance_version = extract_legifrance_am(md.cid)
    except LegifranceRequestError as exc:
        return error_component(f'Erreur lors de la récupération de la version Légifrance: {str(exc)}')
    return _diff_component(legifrance_version, am, 'Version Légifrance')


def _aida_diff(am: ArreteMinisteriel) -> Component:
    md = _md(am)
    if not md:
        return error_component('AM Metadata not found')
    aida_version = extract_aida_am(md.aida_page, am_id=am.id or '')
    if not aida_version:
        return error_component('Erreur lors de la récupération de la version AIDA.')
    return _diff_component(aida_version, am, 'Version AIDA')


def _component_builder(compare_with: CompareWith) -> Callable[[ArreteMinisteriel], Component]:
    if compare_with == CompareWith.LEGIFRANCE:
        return _legifrance_diff
    if compare_with == CompareWith.AIDA:
        return _aida_diff
    raise NotImplementedError


def _build_component(am_id: str, compare_with_str: str) -> Component:
    try:
        compare_with = CompareWith(compare_with_str)
    except ValueError:
        return error_component(f'Unhandled comparision with {compare_with_str}')
    am = load_most_advanced_am(am_id)
    if not am:
        return error_component(f'AM with id {am_id} not found')
    try:
        builder = _component_builder(compare_with)
    except NotImplementedError:
        return error_component(f'Not implemented comparison with {compare_with}')
    return builder(am)


def layout(am_id: str, compare_with_str: str) -> Component:
    return html.Div(
        [
            dcc.Link('< Retour à l\'arrêté', href=f'/am/{am_id}'),
            dbc.Spinner(children=html.Div(), id=_SPINNER),
            dcc.Store(data=[am_id, compare_with_str], id=_ARGS),
        ]
    )


@app.callback(Output(_SPINNER, 'children'), Input(_ARGS, 'data'))
def _define_diff_component(args):
    return _build_component(*args)
