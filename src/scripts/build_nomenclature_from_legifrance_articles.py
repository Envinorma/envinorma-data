from dataclasses import dataclass
from typing import List, Optional, Tuple
from lib.legifrance_API import get_article_by_id, get_legifrance_client
from bs4 import BeautifulSoup
from lib.data import Cell, EnrichedString, Regime, Row, Table
from lib.am_structure_extraction import extract_table_from_soup
from tqdm import tqdm

_ARTICLE_IDS = [
    'LEGIARTI000039330431',
    'LEGIARTI000042371146',
    'LEGIARTI000042371619',
    'LEGIARTI000037531043',
    'LEGIARTI000039330429',
]
_CLIENT = get_legifrance_client()
_ARTICLES = [get_article_by_id(id_, _CLIENT) for id_ in _ARTICLE_IDS]
_HTML_CONTENTS = [BeautifulSoup(art['article']['texteHtml'], 'html.parser') for art in _ARTICLES]


def _extract_only_table(html: BeautifulSoup) -> Table:
    tables = html.find_all('table')
    if len(tables) != 1:
        raise ValueError(f'Expected one table, found {len(tables)}')
    return extract_table_from_soup(html)


_TABLES = [_extract_only_table(soup) for soup in _HTML_CONTENTS]


@dataclass
class _NomenclatureTableRow:
    rubrique: int
    rubrique_lines: List[str]
    regimes: List[Optional[Regime]]
    rayons: List[Optional[int]]


def _get_non_header_rows(table: Table) -> List[Row]:
    return table.rows[2:]


def _extract_stripped_text(html: str) -> str:
    return '\n'.join(BeautifulSoup(html, 'html.parser').stripped_strings)


def _is_empty(cell: Cell) -> bool:
    return _extract_stripped_text(cell.content.text) == ''


def _row_starts_new_rubrique(row: Row) -> bool:
    return len(row.cells) == 4 and _extract_stripped_text(row.cells[0].content.text).isdigit()


def _extract_regime(cell) -> Optional[Regime]:
    text = _extract_stripped_text(cell.content.text)
    if text == '4' or text == 'AD':
        return None
    return Regime(text) if text else None


def _empty_cell() -> Cell:
    return Cell(EnrichedString(''), 1, 1)


def _extract_and_add_data(cells: List[Cell], row: _NomenclatureTableRow) -> None:
    try:
        if len(cells) not in {1, 2, 3, 4}:
            raise ValueError(f'Expecting 3 or 4 cells, received {len(cells)}: {cells}')
        if len(cells) == 1:
            if cells[0].colspan == 2:
                return None
            if cells[0].content.text == '':
                return None
            raise ValueError('Unexpected case.')
        if len(cells) == 2:
            if 'Lorsque la température' in cells[0].content.text:
                cells = [cells[0], _empty_cell(), _empty_cell()]
            else:
                raise ValueError('Unexpected case.')
        if len(cells) == 4:
            if not _is_empty(cells[0]):
                raise ValueError(f'When getting 4 cells, expecting the first to be empty, received {cells[0]}')
            cells = cells[1:]
        row.rubrique_lines.append(_extract_stripped_text(cells[0].content.text))
        row.regimes.append(_extract_regime(cells[1]))
        rayon = int(cells[2].content.text) if cells[2].content.text.isdigit() else None
        row.rayons.append(rayon)
    except:
        print(cells)
        raise


def _row_is_nota(row: Row) -> bool:
    if len(row.cells) == 1:
        return True
    if 'Désignation de la rubrique' in row.cells[1].content.text:
        return True
    return False


def _extract_table_data(table: Table) -> List[_NomenclatureTableRow]:
    result: List[_NomenclatureTableRow] = []
    non_header_rows = _get_non_header_rows(table)
    i = 0
    while True:
        row = non_header_rows[i]
        assert _row_starts_new_rubrique(row)
        current_rubrique = int(_extract_stripped_text(row.cells[0].content.text))
        result_row = _NomenclatureTableRow(current_rubrique, [], [], [])
        _extract_and_add_data(row.cells[1:], result_row)
        while True:
            i += 1
            if i >= len(non_header_rows):
                break
            row = non_header_rows[i]
            if _row_starts_new_rubrique(row):
                break
            if _row_is_nota(row):
                continue
            _extract_and_add_data(row.cells, result_row)
        result.append(result_row)
        if i >= len(non_header_rows):
            break
    return result


_DATA = [x for table in tqdm(_TABLES) for x in _extract_table_data(table)]
