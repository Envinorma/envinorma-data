import dash_html_components as html
from back_office.structure_edition import (
    _get_html_heading_classname,
    _extract_dropdown_values,
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
