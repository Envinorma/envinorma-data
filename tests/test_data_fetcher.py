import pytest
from envinorma.data_fetcher import _replace_element_in_list_or_append_if_negative_rank


def test_replace_element_in_list_or_append_if_negative_rank():
    assert _replace_element_in_list_or_append_if_negative_rank('', [], -1) == ['']
    with pytest.raises(ValueError):
        _replace_element_in_list_or_append_if_negative_rank('', [], 0)
    assert _replace_element_in_list_or_append_if_negative_rank('new', ['old'], 0) == ['new']
    assert _replace_element_in_list_or_append_if_negative_rank('new', ['old', 'unchanged'], 0) == ['new', 'unchanged']
    assert _replace_element_in_list_or_append_if_negative_rank('new', ['unchanged'], -1) == ['unchanged', 'new']
