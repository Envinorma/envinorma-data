from envinorma.back_office.pages.index import _count_step_cumulated_advancement, _cumsum
from envinorma.back_office.utils import AMStatus


def test_cumsum():
    assert _cumsum([]) == []
    assert _cumsum([1]) == [1]
    assert _cumsum([1, 1]) == [1, 2]
    assert _cumsum([1, -1]) == [1, 0]
    assert _cumsum([1, 3]) == [1, 4]
    assert _cumsum([1, 3]) == [1, 4]
    assert _cumsum(list(range(4))) == [0, 1, 3, 6]


def test_count_step_cumulated_advancement():
    assert _count_step_cumulated_advancement({'': AMStatus.PENDING_INITIALIZATION}, {'': 100}) == [1, 0, 0, 0]
    assert _count_step_cumulated_advancement({'': AMStatus.VALIDATED}, {'': 100}) == [1, 1, 1, 1]
    am_statuses = {'0': AMStatus.VALIDATED, '1': AMStatus.PENDING_INITIALIZATION, '2': AMStatus.PENDING_INITIALIZATION}
    occs = {'0': 98, '1': 1, '2': 1}
    assert _count_step_cumulated_advancement(am_statuses, occs) == [1, 0.98, 0.98, 0.98]
    occs = {'0': 0, '1': 1, '2': 99}
    assert _count_step_cumulated_advancement(am_statuses, occs) == [1, 0.00, 0.00, 0.00]
    am_statuses = {'0': AMStatus.VALIDATED, '1': AMStatus.PENDING_PARAMETRIZATION, '2': AMStatus.PENDING_INITIALIZATION}
    occs = {'0': 98, '1': 1, '2': 1}
    assert _count_step_cumulated_advancement(am_statuses, occs) == [1, 0.99, 0.99, 0.98]
