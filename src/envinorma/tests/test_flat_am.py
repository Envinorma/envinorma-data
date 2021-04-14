import json

import pytest

from envinorma.data import ClassementWithAlineas, Regime
from envinorma.data.flat_am import FlatAlinea, FlatArreteMinisteriel, FlatSection
from envinorma.data.text_elements import Table


def test_flat_am():
    dict_ = {
        'id': 1234234,
        'cid': 'LEGITEXT123409',
        'short_title': 'Arrêté du 1er janvier 2021',
        'title': 'Arrêté du 1er janvier 2021 relatif',
        'unique_version': True,
        'installation_date_criterion_left': '',
        'installation_date_criterion_right': '',
        'aida_url': '3223532zerezr5',
        'legifrance_url': '23ezrzer523521',
        'classements_with_alineas': [ClassementWithAlineas('', Regime.A, [])],
        'enriched_from_id': None,
    }
    FlatArreteMinisteriel(**dict_)
    with pytest.raises(ValueError):
        dict_cp = dict_.copy()
        dict_cp['installation_date_criterion_right'] = '239234/432'
        FlatArreteMinisteriel(**dict_cp)
    with pytest.raises(ValueError):
        dict_cp = dict_.copy()
        dict_cp['installation_date_criterion_left'] = '239234/432'
        FlatArreteMinisteriel(**dict_cp)
    with pytest.raises(AssertionError):
        dict_cp = dict_.copy()
        dict_cp['classements_with_alineas'] = []
        FlatArreteMinisteriel(**dict_cp)
    with pytest.raises(AssertionError):
        dict_cp = dict_.copy()
        dict_cp['aida_url'] = ''
        FlatArreteMinisteriel(**dict_cp)
    with pytest.raises(AssertionError):
        dict_cp = dict_.copy()
        dict_cp['legifrance_url'] = ''
        FlatArreteMinisteriel(**dict_cp)
    with pytest.raises(AssertionError):
        dict_cp = dict_.copy()
        dict_cp['enriched_from_id'] = 'ezf'
        FlatArreteMinisteriel(**dict_cp)


def test_flat_section():
    dict_ = {
        'id': 0,
        'rank': 2,
        'title': 'Section title',
        'level': 1,
        'active': True,
        'modified': False,
        'warnings': '',
        'reference_str': 'Art. 1',
        'previous_version': 'Previous version.',
        'arrete_id': 0,
    }
    wrong_values = {
        'id': '',
        'rank': '10',
        'title': None,
        'level': '',
        'active': None,
        'modified': '',
        'warnings': [],
        'reference_str': 2,
        'previous_version': None,
        'arrete_id': '0',
    }
    FlatSection(**dict_)
    for key, wrong_value in wrong_values.items():
        with pytest.raises(ValueError):
            dict_cp = dict_.copy()
            dict_cp[key] = wrong_value
            FlatSection(**dict_cp)


def test_flat_alinea():
    dict_ = {
        'id': 0,
        'rank': 10,
        'active': True,
        'text': 'zefze',
        'table': json.dumps(Table([]).to_dict()),
        'section_id': 23,
    }
    wrong_values = {'id': 'f', 'rank': '10', 'active': None, 'text': 1, 'table': 'ezf', 'section_id': '21'}
    FlatAlinea(**dict_)
    for key, wrong_value in wrong_values.items():
        with pytest.raises(ValueError):
            dict_cp = dict_.copy()
            dict_cp[key] = wrong_value
            FlatAlinea(**dict_cp)
