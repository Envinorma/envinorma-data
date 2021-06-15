from typing import List, Tuple

from envinorma.models.text_elements import (
    Cell,
    Row,
    Table,
    _count_nb_cols_in_each_row,
    _find_next_index_none,
    estr,
    table_to_list,
)


def _tuples_to_table(spans: List[List[Tuple[int, int]]]) -> Table:
    return Table(
        [Row([Cell(estr(str((i, j))), cs, rs) for j, (cs, rs) in enumerate(row)], False) for i, row in enumerate(spans)]
    )


def test_count_nb_cols_in_each_row():
    assert _count_nb_cols_in_each_row(Table([])) == []
    assert _count_nb_cols_in_each_row(Table([Row([], False)])) == [0]
    assert _count_nb_cols_in_each_row(_tuples_to_table([[(1, 1)]])) == [1]
    assert _count_nb_cols_in_each_row(_tuples_to_table([[(1, 1), (1, 1), (1, 1)]])) == [3]
    assert _count_nb_cols_in_each_row(_tuples_to_table([[(1, 1), (1, 1), (1, 1)], [(1, 1), (1, 1), (1, 1)]])) == [3, 3]
    assert _count_nb_cols_in_each_row(_tuples_to_table([[(1, 1), (2, 1)], [(1, 1), (1, 1), (1, 1)]])) == [3, 3]
    assert _count_nb_cols_in_each_row(_tuples_to_table([[(1, 1), (1, 1), (1, 2)], [(1, 1), (1, 1)]])) == [3, 3]
    tb = _tuples_to_table([[(1, 1), (1, 1), (1, 1)], [(1, 1), (1, 1), (1, 1), (1, 1)]])
    assert _count_nb_cols_in_each_row(tb) == [3, 4]
    tb = _tuples_to_table([[(1, 1), (1, 1), (1, 1)], [(3, 3), (1, 1)]])
    assert _count_nb_cols_in_each_row(tb) == [3, 4]
    tb = _tuples_to_table([[(1, 1), (1, 1), (1, 1)], [(3, 3), (1, 1)], [], []])
    assert _count_nb_cols_in_each_row(tb) == [3, 4, 3, 3]
    tb = _tuples_to_table([[(1, 1), (1, 1), (1, 1)], [(3, 3), (1, 1)], [], [(1, 1)], [(1, 1), (1, 1), (1, 1), (1, 1)]])
    assert _count_nb_cols_in_each_row(tb) == [3, 4, 3, 4, 4]


def test_find_next_index_none():
    assert _find_next_index_none(0, ['']) is None
    assert _find_next_index_none(0, [None]) == 0
    assert _find_next_index_none(0, [None, None, None, '']) == 0
    assert _find_next_index_none(0, [None, None, None]) == 0
    assert _find_next_index_none(1, ['', None, None]) == 1
    assert _find_next_index_none(1, ['', '', '', '']) is None
    assert _find_next_index_none(1, ['', '', '', '', None]) == 4
    assert _find_next_index_none(1, []) is None


def test_table_to_list():
    assert table_to_list(_tuples_to_table([])) == []
    assert table_to_list(_tuples_to_table([[]])) == [[]]
    assert table_to_list(_tuples_to_table([[(1, 1)]])) == [['(0, 0)']]
    assert table_to_list(_tuples_to_table([[(1, 1), (1, 1)]])) == [['(0, 0)', '(0, 1)']]
    assert table_to_list(_tuples_to_table([[(1, 1)], [(1, 1)]])) == [['(0, 0)'], ['(1, 0)']]
    exp = [['(0, 0)', '(0, 1)'], ['(1, 0)', '(1, 1)']]
    assert table_to_list(_tuples_to_table([[(1, 1), (1, 1)], [(1, 1), (1, 1)]])) == exp
    exp = [['(0, 0)', '(0, 1)'], ['(1, 0)', '(1, 1)']]
    assert table_to_list(_tuples_to_table([[(1, 1), (1, 1)], [(1, 1), (1, 1)]])) == exp
    exp = [['(0, 0)', '(0, 1)'], ['(1, 0)', '(1, 1)'], ['(2, 0)', '(2, 1)']]
    assert table_to_list(_tuples_to_table([[(1, 1), (1, 1)], [(1, 1), (1, 1)], [(1, 1), (1, 1)]])) == exp
    exp = [['(0, 0)', '(0, 1)'], ['(1, 0)', '(0, 1)'], ['(2, 0)', '(0, 1)']]
    assert table_to_list(_tuples_to_table([[(1, 1), (1, 3)], [(1, 1)], [(1, 1)]])) == exp
    exp = [['(0, 0)', '(0, 1)', '(0, 1)'], ['(0, 0)', '(1, 0)', '(1, 1)'], ['(0, 0)', '(2, 0)', '(2, 1)']]
    assert table_to_list(_tuples_to_table([[(1, 3), (2, 1)], [(1, 1), (1, 1)], [(1, 1), (1, 1)]])) == exp
