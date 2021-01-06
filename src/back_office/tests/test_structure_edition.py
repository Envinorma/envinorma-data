from lib.data import Table
from lib.structure_extraction import Title
import dash_html_components as html
from back_office.structure_edition import (
    _get_html_heading_classname,
    _extract_dropdown_values,
    _modify_elements_with_new_title_levels,
    _ensure_title,
)


def test_get_html_heading_classname():
    assert isinstance(_get_html_heading_classname(1)(), html.H1)
    assert isinstance(_get_html_heading_classname(6)(), html.H6)
    assert isinstance(_get_html_heading_classname(7)(), html.H6)


def test_extract_dropdown_values():
    assert _extract_dropdown_values([]) == []
    assert _extract_dropdown_values([{'type': 'Dropdown', 'props': {'value': 1}}]) == [1]
    assert _extract_dropdown_values(
        [{'type': 'Dropdown', 'props': {'value': 1}}, {'type': 'Dropdown', 'props': {'value': 2}}]
    ) == [1, 2]
    assert _extract_dropdown_values(
        [{'type': 'Dropdown', 'props': {'value': 1}}, {'type': 'xx', 'props': {'children': []}}]
    ) == [1]
    dicts = [
        {'type': 'Dropdown', 'props': {'value': 1}},
        {'type': 'xx', 'props': {'children': {'type': 'Dropdown', 'props': {'value': 2}}}},
    ]
    assert _extract_dropdown_values(dicts) == [1, 2]


def test_modify_elements_with_new_title_levels():
    assert _modify_elements_with_new_title_levels([], []) == []
    assert _modify_elements_with_new_title_levels([Title('', 0)], [-1]) == ['']
    assert _ensure_title(_modify_elements_with_new_title_levels([Title('', 0)], [1])[0]).level == 1
    assert _ensure_title(_modify_elements_with_new_title_levels([Title('', 0)], [1])[0]).text == ''
    assert _modify_elements_with_new_title_levels([''], [-1]) == ['']
    assert _ensure_title(_modify_elements_with_new_title_levels([''], [1])[0]).level == 1
    assert _ensure_title(_modify_elements_with_new_title_levels([''], [1])[0]).text == ''
    assert _modify_elements_with_new_title_levels(['', ''], [-1, -1]) == ['', '']
    tb = Table([])
    assert _modify_elements_with_new_title_levels(['', '', tb], [-1, -1, -1]) == ['', '', tb]