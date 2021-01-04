import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.development.base_component import Component
from lib.config import STORAGE
from lib.data import ArreteMinisteriel, StructuredText, am_to_text
from lib.utils import get_structured_text_filename

from back_office.utils import ID_TO_AM_MD

_Options = List[Dict[str, Any]]

_CONDITION_VARIABLES = ['Régime', 'Date d\'autorisation']
_CONDITION_VARIABLE_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_VARIABLES]
_CONDITION_OPERATIONS = ['<', '<=', '=', '>', '>=']
_CONDITION_OPERATION_OPTIONS = [{'label': condition, 'value': condition} for condition in _CONDITION_OPERATIONS]


def _get_condition_component() -> Component:
    style = {'width': '200px'}
    dropdown_conditions = [
        dcc.Dropdown(options=_CONDITION_VARIABLE_OPTIONS, clearable=False, value='Date d\'autorisation', style=style),
        dcc.Dropdown(options=_CONDITION_OPERATION_OPTIONS, clearable=False, value='=', style=dict(width='50px')),
        dcc.Input(value='', type='text', style={'padding': '0', 'height': '36px'}),
    ]
    return div([*dropdown_conditions], style=dict(display='flex'))


def _get_condition_components(nb_components: int) -> Component:
    dropdown_conditions = [_get_condition_component() for _ in range(nb_components)]
    return div([*dropdown_conditions])


_ALINEA_TARGETS_OPERATIONS = [*range(1, 51), 'TOUS']
_ALINEA_OPTIONS = [{'label': condition, 'value': condition} for condition in _ALINEA_TARGETS_OPERATIONS]


def _make_non_application_form(options: _Options) -> Component:
    dropdown_source = dcc.Dropdown(options=options)
    dropdown_target = dcc.Dropdown(options=options)
    dropdown_alineas = dcc.Dropdown(options=_ALINEA_OPTIONS, multi=True, value=['TOUS'])
    dropdown_condition_merge = dcc.Dropdown(
        options=[{'value': 'and', 'label': 'ET'}, {'value': 'or', 'label': 'OU'}], clearable=False, value='and'
    )
    dropdown_nb_conditions = dcc.Dropdown(
        'nac-nb-conditions', options=[{'label': i, 'value': i} for i in range(10)], clearable=False, value=1
    )
    return html.Div(
        [
            html.H2('Nouvelle condition de non application'),
            html.H4('Description (visible par l\'utilisateur)'),
            dcc.Textarea(value=''),
            html.H4('Source'),
            dropdown_source,
            html.H4('Paragraphe visé'),
            dropdown_target,
            html.H4('Alineas visés'),
            dropdown_alineas,
            html.H4('Condition'),
            html.H4(''),
            html.P('Opération :'),
            dropdown_condition_merge,
            html.P('Nombre de conditions :'),
            dropdown_nb_conditions,
            html.P('Liste de conditions :'),
            html.Div(id='nac-conditions'),
            html.Div(id='form-output-param-edition'),
            html.Button('Submit', id='submit-val-param-edition'),
            # html.H3(am_id, hidden=True, id='am-id-param-edition'),
        ]
    )


def div(children: List[Component], style: Optional[Dict[str, Any]] = None) -> Component:
    return html.Div(children, style=style)


def _extract_cut_titles(text: StructuredText, level: int = 0) -> List[str]:
    return [('#' * level + ' ' + text.title.text)[:60]] + [
        title for sec in text.sections for title in _extract_cut_titles(sec, level + 1)
    ]


def _extract_paragraph_reference_dropdown_values(text: StructuredText) -> _Options:
    title_references = _extract_cut_titles(text)
    return [{'label': title, 'value': i} for i, title in enumerate(title_references)]


def _structure_edition_component(text: StructuredText) -> Component:
    dropdown_values = _extract_paragraph_reference_dropdown_values(text)
    return _make_non_application_form(dropdown_values)


def _am_not_found_component(am_id: str) -> Component:
    return html.P(f'L\'arrêté ministériel avec id {am_id} n\'a pas été trouvé.')


def _load_am_from_file(am_id: str) -> ArreteMinisteriel:
    path = get_structured_text_filename(am_id)
    return ArreteMinisteriel.from_dict(json.load(open(path)))


def _load_am(am_id: str) -> Optional[ArreteMinisteriel]:
    am_md = ID_TO_AM_MD.get(am_id)
    if not am_md:
        return None
    return _load_am_from_file(am_md.nor or am_md.cid)


def make_am_parametrization_edition_component(am_id: str) -> Component:
    am = _load_am(am_id)
    if not am:
        return _am_not_found_component(am_id)
    text = am_to_text(am)
    return div(_structure_edition_component(text))


def _make_list(candidate: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]) -> List[Dict[str, Any]]:
    if not candidate:
        return []
    if isinstance(candidate, list):
        return candidate
    return [candidate]


def _extract_dropdown_values(components: List[Dict[str, Any]]) -> List[Optional[int]]:
    res: List[Optional[int]] = []
    for component in components:
        if isinstance(component, str):
            continue
        assert isinstance(component, dict)
        if component['type'] == 'Dropdown':
            res.append(component['props'].get('value'))
        else:
            res.extend(_extract_dropdown_values(_make_list(component['props'].get('children'))))
    return res


class _FormHandlingError(Exception):
    pass


def _write_file(content: str, filename: str):
    if STORAGE != 'local':
        raise ValueError(f'Unhandled storage value {STORAGE}')
    with open(filename, 'w') as file_:
        file_.write(content)


# def _save_text(am_id: str, title_levels: List[Optional[int]]) -> str:
#     new_version = datetime.now().strftime('%y%m%d_%H%M')
#     filename = os.path.join(get_parametrization_filename(am_id), new_version + '.json')
#     text = _structure_text(am_id, title_levels)
#     json_ = jsonify(text.to_dict())
#     _write_file(json_, filename)
#     return f'Enregistrement réussi. (Filename={filename})'


def _extract_form_values(component_values: Dict[str, Any]) -> List[Optional[int]]:
    return _extract_dropdown_values(_make_list(component_values['props']['children']))


def add_parametrization_edition_callbacks(app: dash.Dash):
    # def update_output(_, am_id, children):
    def update_output(n_clicks, state):
        print(n_clicks)
        print(state)
        form_values = _extract_form_values(state)
        print(form_values)
        return html.P(datetime.now().strftime('%y%m%d_%H%M'))

    app.callback(
        dash.dependencies.Output('form-output-param-edition', 'children'),
        [
            dash.dependencies.Input('submit-val-param-edition', 'n_clicks'),
            # dash.dependencies.Input('am-id-param-edition', 'children'),
        ],
        [dash.dependencies.State('page-content', 'children')],
    )(update_output)

    def nb_conditions(value):
        return _get_condition_components(value)

    app.callback(
        dash.dependencies.Output('nac-conditions', 'children'),
        [
            dash.dependencies.Input('nac-nb-conditions', 'value'),
            # dash.dependencies.Input('am-id-param-edition', 'children'),
        ],
        # [dash.dependencies.State('page-content', 'children')],
    )(nb_conditions)


# {
#     'props': {
#         'children': {
#             'props': {
#                 'children': [
#                     {
#                         'props': {'children': 'Nouvelle condition de non application'},
#                         'type': 'H2',
#                         'namespace': 'dash_html_components',
#                     },
#                     {
#                         'props': {'children': "Description (visible par l'utilisateur)"},
#                         'type': 'H4',
#                         'namespace': 'dash_html_components',
#                     },
#                     {
#                         'props': {
#                             'value': 'ceci est la description ',
#                             'n_clicks': 1,
#                             'n_clicks_timestamp': 1609772197356,
#                             'n_blur': 1,
#                             'n_blur_timestamp': 1609772208629,
#                         },
#                         'type': 'Textarea',
#                         'namespace': 'dash_core_components',
#                     },
#                     {'props': {'children': 'Source'}, 'type': 'H4', 'namespace': 'dash_html_components'},
#                     {
#                         'props': {
#                             'options': [
#                                 {'label': ' Arrêté du 16 juillet 2012 relatif aux stockages en récipien', 'value': 0},
#                                 {'label': '# Article 1', 'value': 1},
#                                 {'label': '# TITRE Ier : GÉNÉRALITÉS', 'value': 2},
#                                 {'label': '## Article 2', 'value': 3},
#                                 {'label': '# TITRE II : IMPLANTATION ET ACCESSIBILITÉ', 'value': 4},
#                                 {'label': '## Article 3', 'value': 5},
#                                 {'label': '## Article 4', 'value': 6},
#                                 {'label': '## Article 5', 'value': 7},
#                                 {'label': '### I. ― Le site dispose en permanence de deux accès au moin', 'value': 8},
#                                 {'label': "### II. ― L'accès au site est conçu pour pouvoir être ouvert", 'value': 9},
#                                 {'label': '## Article 6', 'value': 10},
#                                 {'label': "### I. ― L'installation dispose d'une voie « engins » permet", 'value': 11},
#                                 {'label': '### II. ― Chaque cellule de liquides inflammables a au moins', 'value': 12},
#                                 {'label': '### III. ― A partir de chaque voie « engins » ou « échelle »', 'value': 13},
#                                 {'label': '### IV. ― Les accès des cellules de liquides inflammables pe', 'value': 14},
#                                 {'label': '# TITRE III : DISPOSITIONS CONSTRUCTIVES,  AMÉNAGEMENT ET ÉQ', 'value': 15},
#                                 {'label': '## Article 7', 'value': 16},
#                                 {'label': "### I. ― A l'exception des bâtiments dont la structure est e", 'value': 17},
#                                 {'label': '### II. ― Les cellules de liquides inflammables ont une surf', 'value': 18},
#                                 {'label': '### III. ― Lorsque leurs dimensions le permettent, les cellu', 'value': 19},
#                                 {'label': '### IV. ― Les cantons de désenfumage sont équipés en partie ', 'value': 20},
#                                 {'label': "### V. ― Des amenées d'air frais d'une superficie égale à la", 'value': 21},
#                                 {'label': "### VI. ― Un dispositif de détection automatique d'incendie ", 'value': 22},
#                                 {'label': '### VII. ― Les installations nouvelles ne comprennent pas, n', 'value': 23},
#                                 {'label': "### VIII. ― Les dispositions des I à V de l'article 7 du pré", 'value': 24},
#                                 {'label': '## Article 8', 'value': 25},
#                                 {'label': "### I. ― A l'exception des paletiers couverts d'une peinture", 'value': 26},
#                                 {'label': "### II. ― Le chauffage artificiel de l'entrepôt ne peut être", 'value': 27},
#                                 {'label': '## Article 9', 'value': 28},
#                                 {'label': "### I. ― S'il existe une chaufferie ou un local de charge de", 'value': 29},
#                                 {'label': "### II. ― A l'extérieur de la chaufferie sont installés :", 'value': 30},
#                                 {'label': '### III. ― La recharge de batteries est interdite hors des l', 'value': 31},
#                                 {'label': '## Article 10', 'value': 32},
#                                 {'label': '### I. ― Chaque cellule de liquides inflammables est divisée', 'value': 33},
#                                 {'label': '### II. ― Tout stockage de produits liquides susceptibles de', 'value': 34},
#                                 {'label': "### III. ― Lorsqu'elle est nécessaire, la capacité de rétent", 'value': 35},
#                                 {'label': "### IV. ― A l'exception des cellules de liquides inflammable", 'value': 36},
#                                 {'label': "### V. ― Les eaux pluviales susceptibles d'être polluées et ", 'value': 37},
#                                 {'label': '## Article 11', 'value': 38},
#                                 {'label': '### I. ― La disposition et la pente du sol autour des récipi', 'value': 39},
#                                 {'label': '### II. ― Pour les sites nouveaux, les rétentions :', 'value': 40},
#                                 {'label': '## Article 12', 'value': 41},
#                                 {'label': '### I. ― Les rétentions construites après le 1er janvier 201', 'value': 42},
#                                 {'label': '### II. ― Les rétentions prévues aux articles 10 et 11 du pr', 'value': 43},
#                                 {'label': '# TITRE IV : EXPLOITATION ET ENTRETIEN', 'value': 44},
#                                 {'label': '## Article 13', 'value': 45},
#                                 {'label': '## Article 14', 'value': 46},
#                                 {'label': '## Article 15', 'value': 47},
#                                 {'label': '## Article 16', 'value': 48},
#                                 {'label': '## Article 17', 'value': 49},
#                                 {'label': '## Article 18', 'value': 50},
#                                 {'label': '## Article 19', 'value': 51},
#                                 {'label': '### I. ― Une distance minimale de 1 mètre est maintenue entr', 'value': 52},
#                                 {'label': '### II. ― La hauteur de stockage des liquides inflammables e', 'value': 53},
#                                 {'label': '### III. ― Les produits stockés en vrac sont séparés des aut', 'value': 54},
#                                 {'label': '### IV. ― Une distance minimale de 1 mètre est respectée par', 'value': 55},
#                                 {'label': "### V. ― Les dispositions de l'article 19 sont applicables a", 'value': 56},
#                                 {'label': '## Article 20', 'value': 57},
#                                 {'label': '## Article 21', 'value': 58},
#                                 {'label': '# TITRE V : AUTRES DISPOSITIONS DE PRÉVENTION DES RISQUES', 'value': 59},
#                                 {'label': '## Article 22', 'value': 60},
#                                 {'label': '## Article 23', 'value': 61},
#                                 {'label': "# TITRE VI : DÉFENSE CONTRE L'INCENDIE", 'value': 62},
#                                 {'label': '## Article 24', 'value': 63},
#                                 {'label': '## Article 25', 'value': 64},
#                                 {'label': "### I. ― Afin d'atteindre les objectifs définis à l'article ", 'value': 65},
#                                 {'label': "### II. ― La disponibilité des moyens de lutte contre l'ince", 'value': 66},
#                                 {'label': "### III. ― L'exploitant s'assure qu'en cas d'incendie :", 'value': 67},
#                                 {'label': "### IV. ― Le personnel de l'exploitant chargé de la mise en ", 'value': 68},
#                                 {'label': '## Article 26', 'value': 69},
#                                 {'label': "### I. ― L'exploitant dispose des ressources et réserves en ", 'value': 70},
#                                 {'label': "### II. ― Le débit d'eau incendie, de solution moussante et ", 'value': 71},
#                                 {'label': "### III. ― Si la stratégie de lutte contre l'incendie prévoi", 'value': 72},
#                                 {'label': '### IV. ― Les réseaux, les éventuelles réserves en eau ou en', 'value': 73},
#                                 {'label': "### V. ― L'ensemble des moyens prévus dans l'article 26 est ", 'value': 74},
#                                 {'label': '## Article 27', 'value': 75},
#                                 {'label': '## Article 28', 'value': 76},
#                                 {'label': "### I. ― Un système d'extinction automatique d'incendie répo", 'value': 77},
#                                 {'label': '### II. ― Si un arrêté préfectoral, applicable au site à la ', 'value': 78},
#                                 {'label': '## Article 29', 'value': 79},
#                                 {'label': '## Article 30', 'value': 80},
#                                 {'label': '# TITRE VII : PRÉVENTION DES POLLUTIONS', 'value': 81},
#                                 {'label': '## Chapitre 7.1 : Protection des ressources en eaux  et des ', 'value': 82},
#                                 {'label': '### Article 31', 'value': 83},
#                                 {'label': "### Article 32 - Tous les effluents liquides susceptibles d'", 'value': 84},
#                                 {'label': '### Article 33', 'value': 85},
#                                 {'label': '#### I. ― Les réseaux de collecte des effluents séparent les', 'value': 86},
#                                 {'label': '#### II. ― La dilution des effluents est interdite. En aucun', 'value': 87},
#                                 {'label': "#### III. ― Les réseaux d'eaux pluviales susceptibles de col", 'value': 88},
#                                 {'label': '#### IV. ― Les dispositifs de rejet des effluents liquides s', 'value': 89},
#                                 {'label': '#### V. ― La conception et la performance des installations ', 'value': 90},
#                                 {'label': '#### VI. ― Les emplacements autres que les rétentions où un ', 'value': 91},
#                                 {'label': "#### VII. ― L'exploitant met en place un programme de survei", 'value': 92},
#                                 {'label': '## Chapitre 7.2 : Déchets', 'value': 93},
#                                 {'label': '### Article 34', 'value': 94},
#                                 {'label': '### Article 35', 'value': 95},
#                                 {'label': '### Article 36', 'value': 96},
#                                 {'label': '### Article 37', 'value': 97},
#                                 {'label': '### Article 38', 'value': 98},
#                                 {'label': '### Article 39', 'value': 99},
#                                 {'label': '## Chapitre 7.3 : Nuisances sonores et vibrations', 'value': 100},
#                                 {'label': '### Article 40', 'value': 101},
#                                 {'label': '## Chapitre 7.4 : Poussières', 'value': 102},
#                                 {'label': '### Article 41', 'value': 103},
#                                 {'label': '## Chapitre 7.5 : Intégration dans le paysage', 'value': 104},
#                                 {'label': '### Article 42', 'value': 105},
#                                 {'label': '# TITRE VIII : MODIFICATION DE TEXTES EXISTANTS', 'value': 106},
#                                 {'label': '## Article 43', 'value': 107},
#                                 {'label': '## Article 44', 'value': 108},
#                             ],
#                             'search_value': '',
#                             'value': 2,
#                         },
#                         'type': 'Dropdown',
#                         'namespace': 'dash_core_components',
#                     },
#                     {'props': {'children': 'Paragraphe visé'}, 'type': 'H4', 'namespace': 'dash_html_components'},
#                     {
#                         'props': {
#                             'options': [
#                                 {'label': ' Arrêté du 16 juillet 2012 relatif aux stockages en récipien', 'value': 0},
#                                 {'label': '# Article 1', 'value': 1},
#                                 {'label': '# TITRE Ier : GÉNÉRALITÉS', 'value': 2},
#                                 {'label': '## Article 2', 'value': 3},
#                                 {'label': '# TITRE II : IMPLANTATION ET ACCESSIBILITÉ', 'value': 4},
#                                 {'label': '## Article 3', 'value': 5},
#                                 {'label': '## Article 4', 'value': 6},
#                                 {'label': '## Article 5', 'value': 7},
#                                 {'label': '### I. ― Le site dispose en permanence de deux accès au moin', 'value': 8},
#                                 {'label': "### II. ― L'accès au site est conçu pour pouvoir être ouvert", 'value': 9},
#                                 {'label': '## Article 6', 'value': 10},
#                                 {'label': "### I. ― L'installation dispose d'une voie « engins » permet", 'value': 11},
#                                 {'label': '### II. ― Chaque cellule de liquides inflammables a au moins', 'value': 12},
#                                 {'label': '### III. ― A partir de chaque voie « engins » ou « échelle »', 'value': 13},
#                                 {'label': '### IV. ― Les accès des cellules de liquides inflammables pe', 'value': 14},
#                                 {'label': '# TITRE III : DISPOSITIONS CONSTRUCTIVES,  AMÉNAGEMENT ET ÉQ', 'value': 15},
#                                 {'label': '## Article 7', 'value': 16},
#                                 {'label': "### I. ― A l'exception des bâtiments dont la structure est e", 'value': 17},
#                                 {'label': '### II. ― Les cellules de liquides inflammables ont une surf', 'value': 18},
#                                 {'label': '### III. ― Lorsque leurs dimensions le permettent, les cellu', 'value': 19},
#                                 {'label': '### IV. ― Les cantons de désenfumage sont équipés en partie ', 'value': 20},
#                                 {'label': "### V. ― Des amenées d'air frais d'une superficie égale à la", 'value': 21},
#                                 {'label': "### VI. ― Un dispositif de détection automatique d'incendie ", 'value': 22},
#                                 {'label': '### VII. ― Les installations nouvelles ne comprennent pas, n', 'value': 23},
#                                 {'label': "### VIII. ― Les dispositions des I à V de l'article 7 du pré", 'value': 24},
#                                 {'label': '## Article 8', 'value': 25},
#                                 {'label': "### I. ― A l'exception des paletiers couverts d'une peinture", 'value': 26},
#                                 {'label': "### II. ― Le chauffage artificiel de l'entrepôt ne peut être", 'value': 27},
#                                 {'label': '## Article 9', 'value': 28},
#                                 {'label': "### I. ― S'il existe une chaufferie ou un local de charge de", 'value': 29},
#                                 {'label': "### II. ― A l'extérieur de la chaufferie sont installés :", 'value': 30},
#                                 {'label': '### III. ― La recharge de batteries est interdite hors des l', 'value': 31},
#                                 {'label': '## Article 10', 'value': 32},
#                                 {'label': '### I. ― Chaque cellule de liquides inflammables est divisée', 'value': 33},
#                                 {'label': '### II. ― Tout stockage de produits liquides susceptibles de', 'value': 34},
#                                 {'label': "### III. ― Lorsqu'elle est nécessaire, la capacité de rétent", 'value': 35},
#                                 {'label': "### IV. ― A l'exception des cellules de liquides inflammable", 'value': 36},
#                                 {'label': "### V. ― Les eaux pluviales susceptibles d'être polluées et ", 'value': 37},
#                                 {'label': '## Article 11', 'value': 38},
#                                 {'label': '### I. ― La disposition et la pente du sol autour des récipi', 'value': 39},
#                                 {'label': '### II. ― Pour les sites nouveaux, les rétentions :', 'value': 40},
#                                 {'label': '## Article 12', 'value': 41},
#                                 {'label': '### I. ― Les rétentions construites après le 1er janvier 201', 'value': 42},
#                                 {'label': '### II. ― Les rétentions prévues aux articles 10 et 11 du pr', 'value': 43},
#                                 {'label': '# TITRE IV : EXPLOITATION ET ENTRETIEN', 'value': 44},
#                                 {'label': '## Article 13', 'value': 45},
#                                 {'label': '## Article 14', 'value': 46},
#                                 {'label': '## Article 15', 'value': 47},
#                                 {'label': '## Article 16', 'value': 48},
#                                 {'label': '## Article 17', 'value': 49},
#                                 {'label': '## Article 18', 'value': 50},
#                                 {'label': '## Article 19', 'value': 51},
#                                 {'label': '### I. ― Une distance minimale de 1 mètre est maintenue entr', 'value': 52},
#                                 {'label': '### II. ― La hauteur de stockage des liquides inflammables e', 'value': 53},
#                                 {'label': '### III. ― Les produits stockés en vrac sont séparés des aut', 'value': 54},
#                                 {'label': '### IV. ― Une distance minimale de 1 mètre est respectée par', 'value': 55},
#                                 {'label': "### V. ― Les dispositions de l'article 19 sont applicables a", 'value': 56},
#                                 {'label': '## Article 20', 'value': 57},
#                                 {'label': '## Article 21', 'value': 58},
#                                 {'label': '# TITRE V : AUTRES DISPOSITIONS DE PRÉVENTION DES RISQUES', 'value': 59},
#                                 {'label': '## Article 22', 'value': 60},
#                                 {'label': '## Article 23', 'value': 61},
#                                 {'label': "# TITRE VI : DÉFENSE CONTRE L'INCENDIE", 'value': 62},
#                                 {'label': '## Article 24', 'value': 63},
#                                 {'label': '## Article 25', 'value': 64},
#                                 {'label': "### I. ― Afin d'atteindre les objectifs définis à l'article ", 'value': 65},
#                                 {'label': "### II. ― La disponibilité des moyens de lutte contre l'ince", 'value': 66},
#                                 {'label': "### III. ― L'exploitant s'assure qu'en cas d'incendie :", 'value': 67},
#                                 {'label': "### IV. ― Le personnel de l'exploitant chargé de la mise en ", 'value': 68},
#                                 {'label': '## Article 26', 'value': 69},
#                                 {'label': "### I. ― L'exploitant dispose des ressources et réserves en ", 'value': 70},
#                                 {'label': "### II. ― Le débit d'eau incendie, de solution moussante et ", 'value': 71},
#                                 {'label': "### III. ― Si la stratégie de lutte contre l'incendie prévoi", 'value': 72},
#                                 {'label': '### IV. ― Les réseaux, les éventuelles réserves en eau ou en', 'value': 73},
#                                 {'label': "### V. ― L'ensemble des moyens prévus dans l'article 26 est ", 'value': 74},
#                                 {'label': '## Article 27', 'value': 75},
#                                 {'label': '## Article 28', 'value': 76},
#                                 {'label': "### I. ― Un système d'extinction automatique d'incendie répo", 'value': 77},
#                                 {'label': '### II. ― Si un arrêté préfectoral, applicable au site à la ', 'value': 78},
#                                 {'label': '## Article 29', 'value': 79},
#                                 {'label': '## Article 30', 'value': 80},
#                                 {'label': '# TITRE VII : PRÉVENTION DES POLLUTIONS', 'value': 81},
#                                 {'label': '## Chapitre 7.1 : Protection des ressources en eaux  et des ', 'value': 82},
#                                 {'label': '### Article 31', 'value': 83},
#                                 {'label': "### Article 32 - Tous les effluents liquides susceptibles d'", 'value': 84},
#                                 {'label': '### Article 33', 'value': 85},
#                                 {'label': '#### I. ― Les réseaux de collecte des effluents séparent les', 'value': 86},
#                                 {'label': '#### II. ― La dilution des effluents est interdite. En aucun', 'value': 87},
#                                 {'label': "#### III. ― Les réseaux d'eaux pluviales susceptibles de col", 'value': 88},
#                                 {'label': '#### IV. ― Les dispositifs de rejet des effluents liquides s', 'value': 89},
#                                 {'label': '#### V. ― La conception et la performance des installations ', 'value': 90},
#                                 {'label': '#### VI. ― Les emplacements autres que les rétentions où un ', 'value': 91},
#                                 {'label': "#### VII. ― L'exploitant met en place un programme de survei", 'value': 92},
#                                 {'label': '## Chapitre 7.2 : Déchets', 'value': 93},
#                                 {'label': '### Article 34', 'value': 94},
#                                 {'label': '### Article 35', 'value': 95},
#                                 {'label': '### Article 36', 'value': 96},
#                                 {'label': '### Article 37', 'value': 97},
#                                 {'label': '### Article 38', 'value': 98},
#                                 {'label': '### Article 39', 'value': 99},
#                                 {'label': '## Chapitre 7.3 : Nuisances sonores et vibrations', 'value': 100},
#                                 {'label': '### Article 40', 'value': 101},
#                                 {'label': '## Chapitre 7.4 : Poussières', 'value': 102},
#                                 {'label': '### Article 41', 'value': 103},
#                                 {'label': '## Chapitre 7.5 : Intégration dans le paysage', 'value': 104},
#                                 {'label': '### Article 42', 'value': 105},
#                                 {'label': '# TITRE VIII : MODIFICATION DE TEXTES EXISTANTS', 'value': 106},
#                                 {'label': '## Article 43', 'value': 107},
#                                 {'label': '## Article 44', 'value': 108},
#                             ],
#                             'search_value': '',
#                             'value': 5,
#                         },
#                         'type': 'Dropdown',
#                         'namespace': 'dash_core_components',
#                     },
#                     {'props': {'children': 'Alineas visés'}, 'type': 'H4', 'namespace': 'dash_html_components'},
#                     {
#                         'props': {
#                             'options': [
#                                 {'label': 1, 'value': 1},
#                                 {'label': 2, 'value': 2},
#                                 {'label': 3, 'value': 3},
#                                 {'label': 4, 'value': 4},
#                                 {'label': 5, 'value': 5},
#                                 {'label': 6, 'value': 6},
#                                 {'label': 7, 'value': 7},
#                                 {'label': 8, 'value': 8},
#                                 {'label': 9, 'value': 9},
#                                 {'label': 10, 'value': 10},
#                                 {'label': 11, 'value': 11},
#                                 {'label': 12, 'value': 12},
#                                 {'label': 13, 'value': 13},
#                                 {'label': 14, 'value': 14},
#                                 {'label': 15, 'value': 15},
#                                 {'label': 16, 'value': 16},
#                                 {'label': 17, 'value': 17},
#                                 {'label': 18, 'value': 18},
#                                 {'label': 19, 'value': 19},
#                                 {'label': 20, 'value': 20},
#                                 {'label': 21, 'value': 21},
#                                 {'label': 22, 'value': 22},
#                                 {'label': 23, 'value': 23},
#                                 {'label': 24, 'value': 24},
#                                 {'label': 25, 'value': 25},
#                                 {'label': 26, 'value': 26},
#                                 {'label': 27, 'value': 27},
#                                 {'label': 28, 'value': 28},
#                                 {'label': 29, 'value': 29},
#                                 {'label': 30, 'value': 30},
#                                 {'label': 31, 'value': 31},
#                                 {'label': 32, 'value': 32},
#                                 {'label': 33, 'value': 33},
#                                 {'label': 34, 'value': 34},
#                                 {'label': 35, 'value': 35},
#                                 {'label': 36, 'value': 36},
#                                 {'label': 37, 'value': 37},
#                                 {'label': 38, 'value': 38},
#                                 {'label': 39, 'value': 39},
#                                 {'label': 40, 'value': 40},
#                                 {'label': 41, 'value': 41},
#                                 {'label': 42, 'value': 42},
#                                 {'label': 43, 'value': 43},
#                                 {'label': 44, 'value': 44},
#                                 {'label': 45, 'value': 45},
#                                 {'label': 46, 'value': 46},
#                                 {'label': 47, 'value': 47},
#                                 {'label': 48, 'value': 48},
#                                 {'label': 49, 'value': 49},
#                                 {'label': 50, 'value': 50},
#                                 {'label': 'TOUS', 'value': 'TOUS'},
#                             ],
#                             'value': ['TOUS', 3],
#                             'multi': True,
#                             'search_value': '',
#                         },
#                         'type': 'Dropdown',
#                         'namespace': 'dash_core_components',
#                     },
#                     {'props': {'children': 'Condition'}, 'type': 'H4', 'namespace': 'dash_html_components'},
#                     {'props': {'children': ''}, 'type': 'H4', 'namespace': 'dash_html_components'},
#                     {'props': {'children': 'Opération :'}, 'type': 'P', 'namespace': 'dash_html_components'},
#                     {
#                         'props': {
#                             'options': [{'value': 'and', 'label': 'ET'}, {'value': 'or', 'label': 'OU'}],
#                             'value': 'or',
#                             'clearable': False,
#                             'search_value': '',
#                         },
#                         'type': 'Dropdown',
#                         'namespace': 'dash_core_components',
#                     },
#                     {'props': {'children': 'Nombre de conditions :'}, 'type': 'P', 'namespace': 'dash_html_components'},
#                     {
#                         'props': {
#                             'id': 'nac-nb-conditions',
#                             'options': [
#                                 {'label': 0, 'value': 0},
#                                 {'label': 1, 'value': 1},
#                                 {'label': 2, 'value': 2},
#                                 {'label': 3, 'value': 3},
#                                 {'label': 4, 'value': 4},
#                                 {'label': 5, 'value': 5},
#                                 {'label': 6, 'value': 6},
#                                 {'label': 7, 'value': 7},
#                                 {'label': 8, 'value': 8},
#                                 {'label': 9, 'value': 9},
#                             ],
#                             'value': 2,
#                             'clearable': False,
#                             'search_value': '',
#                         },
#                         'type': 'Dropdown',
#                         'namespace': 'dash_core_components',
#                     },
#                     {'props': {'children': 'Liste de conditions :'}, 'type': 'P', 'namespace': 'dash_html_components'},
#                     {
#                         'props': {
#                             'children': {
#                                 'props': {
#                                     'children': [
#                                         {
#                                             'props': {
#                                                 'children': [
#                                                     {
#                                                         'props': {
#                                                             'options': [
#                                                                 {'label': 'Régime', 'value': 'Régime'},
#                                                                 {
#                                                                     'label': "Date d'autorisation",
#                                                                     'value': "Date d'autorisation",
#                                                                 },
#                                                             ],
#                                                             'value': 'Régime',
#                                                             'clearable': False,
#                                                             'style': {'width': '200px'},
#                                                             'search_value': '',
#                                                         },
#                                                         'type': 'Dropdown',
#                                                         'namespace': 'dash_core_components',
#                                                     },
#                                                     {
#                                                         'props': {
#                                                             'options': [
#                                                                 {'label': '<', 'value': '<'},
#                                                                 {'label': '<=', 'value': '<='},
#                                                                 {'label': '=', 'value': '='},
#                                                                 {'label': '>', 'value': '>'},
#                                                                 {'label': '>=', 'value': '>='},
#                                                             ],
#                                                             'value': '=',
#                                                             'clearable': False,
#                                                             'style': {'width': '50px'},
#                                                         },
#                                                         'type': 'Dropdown',
#                                                         'namespace': 'dash_core_components',
#                                                     },
#                                                     {
#                                                         'props': {
#                                                             'value': 'E',
#                                                             'style': {'padding': '0', 'height': '36px'},
#                                                             'type': 'text',
#                                                             'n_blur': 2,
#                                                             'n_blur_timestamp': 1609772223215,
#                                                         },
#                                                         'type': 'Input',
#                                                         'namespace': 'dash_core_components',
#                                                     },
#                                                 ],
#                                                 'style': {'display': 'flex'},
#                                                 'n_clicks': 5,
#                                                 'n_clicks_timestamp': 1609772222560,
#                                             },
#                                             'type': 'Div',
#                                             'namespace': 'dash_html_components',
#                                         },
#                                         {
#                                             'props': {
#                                                 'children': [
#                                                     {
#                                                         'props': {
#                                                             'options': [
#                                                                 {'label': 'Régime', 'value': 'Régime'},
#                                                                 {
#                                                                     'label': "Date d'autorisation",
#                                                                     'value': "Date d'autorisation",
#                                                                 },
#                                                             ],
#                                                             'value': 'Régime',
#                                                             'clearable': False,
#                                                             'style': {'width': '200px'},
#                                                             'search_value': '',
#                                                         },
#                                                         'type': 'Dropdown',
#                                                         'namespace': 'dash_core_components',
#                                                     },
#                                                     {
#                                                         'props': {
#                                                             'options': [
#                                                                 {'label': '<', 'value': '<'},
#                                                                 {'label': '<=', 'value': '<='},
#                                                                 {'label': '=', 'value': '='},
#                                                                 {'label': '>', 'value': '>'},
#                                                                 {'label': '>=', 'value': '>='},
#                                                             ],
#                                                             'value': '=',
#                                                             'clearable': False,
#                                                             'style': {'width': '50px'},
#                                                             'search_value': '',
#                                                         },
#                                                         'type': 'Dropdown',
#                                                         'namespace': 'dash_core_components',
#                                                     },
#                                                     {
#                                                         'props': {
#                                                             'value': 'A',
#                                                             'style': {'padding': '0', 'height': '36px'},
#                                                             'type': 'text',
#                                                             'n_blur': 1,
#                                                             'n_blur_timestamp': 1609772226317,
#                                                         },
#                                                         'type': 'Input',
#                                                         'namespace': 'dash_core_components',
#                                                     },
#                                                 ],
#                                                 'style': {'display': 'flex'},
#                                                 'n_clicks': 2,
#                                                 'n_clicks_timestamp': 1609772222119,
#                                             },
#                                             'type': 'Div',
#                                             'namespace': 'dash_html_components',
#                                         },
#                                     ],
#                                     'style': None,
#                                     'n_clicks': 7,
#                                     'n_clicks_timestamp': 1609772222560,
#                                 },
#                                 'type': 'Div',
#                                 'namespace': 'dash_html_components',
#                             },
#                             'id': 'nac-conditions',
#                             'n_clicks': 7,
#                             'n_clicks_timestamp': 1609772222560,
#                         },
#                         'type': 'Div',
#                         'namespace': 'dash_html_components',
#                     },
#                     {
#                         'props': {
#                             'children': {
#                                 'props': {
#                                     'children': '210104_1556',
#                                     'n_clicks': 1,
#                                     'n_clicks_timestamp': 1609772226439,
#                                 },
#                                 'type': 'P',
#                                 'namespace': 'dash_html_components',
#                             },
#                             'id': 'form-output-param-edition',
#                             'n_clicks': 1,
#                             'n_clicks_timestamp': 1609772226439,
#                         },
#                         'type': 'Div',
#                         'namespace': 'dash_html_components',
#                     },
#                     {
#                         'props': {
#                             'children': 'Submit',
#                             'id': 'submit-val-param-edition',
#                             'n_clicks': 1,
#                             'n_clicks_timestamp': 1609772230263,
#                         },
#                         'type': 'Button',
#                         'namespace': 'dash_html_components',
#                     },
#                 ],
#                 'n_clicks': 21,
#                 'n_clicks_timestamp': 1609772230264,
#             },
#             'type': 'Div',
#             'namespace': 'dash_html_components',
#         },
#         'style': None,
#         'n_clicks': 21,
#         'n_clicks_timestamp': 1609772230264,
#     },
#     'type': 'Div',
#     'namespace': 'dash_html_components',
# }
