'''
Script for scraping Legifrance nomenclature
'''
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Optional

from bs4 import BeautifulSoup
from tqdm import tqdm

from envinorma.config import AM_DATA_FOLDER, config
from envinorma.data import (
    Cell,
    EnrichedString,
    Nomenclature,
    Regime,
    Row,
    RubriqueSimpleThresholds,
    Table,
    is_increasing,
    load_am_data,
)
from envinorma.data.load import load_classements, load_installations
from envinorma.data_build.georisques_data import GRClassementActivite, deduce_regime_if_possible
from envinorma.io.parse_html import extract_table_from_soup
from envinorma.utils import write_json
from legifrance.legifrance_API import get_article_by_id, get_legifrance_client

_ARTICLE_IDS = [
    'LEGIARTI000039330431',
    'LEGIARTI000042371146',
    'LEGIARTI000042371619',
    'LEGIARTI000037531043',
    'LEGIARTI000039330429',
]
_CLIENT = get_legifrance_client(config.legifrance.client_id, config.legifrance.client_secret)

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
    rubrique: str
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
    return len(row.cells) == 4 and len(_extract_stripped_text(row.cells[0].content.text)) == 4


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
        current_rubrique = _extract_stripped_text(row.cells[0].content.text)
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


def _str_type(str_: str) -> str:
    if 'mais inf' in str_:
        return 'between'
    if 'ou égal' in str_ or 'supérieur' in str_.lower():
        return 'greater'
    print(str_)
    return 'not'


Counter(
    [
        _str_type(rubrique)
        for row in _DATA
        for (regime, rubrique) in zip(row.regimes, row.rubrique_lines)
        if regime and rubrique
    ]
)

_PATTERNS = [
    r'^[0-9]+\. ',
    r'^[a-z]\)',
    r'^[A-Z]\. ',
]


def _has_enumeration(str_: str) -> bool:
    for pattern in _PATTERNS:
        if re.match(pattern, str_):
            return True
    return False


def _extract_matched_str(string: str, match: re.Match) -> str:
    return string[match.span()[0] : match.span()[1]]


def _get_match(str_: str) -> str:
    for pattern in _PATTERNS:
        match = re.match(pattern, str_)
        if match:
            return _extract_matched_str(str_, match)
    return ''


def _extract_alineas(row: _NomenclatureTableRow) -> List[str]:
    current_paragraph = ''
    alineas: List[str] = []
    for regime, text in zip(row.regimes, row.rubrique_lines):
        if not regime:
            if _has_enumeration(text):
                current_paragraph = _get_match(text).strip()
        else:
            alineas.append(current_paragraph + _get_match(text).strip())
    return alineas


_ALINEAS = {row.rubrique: _extract_alineas(row) for row in _DATA}


def _is_decreasing(list_: List[float]) -> bool:
    if not list_:
        return True
    for a, b in zip(list_, list_[1:]):
        if a <= b:
            return False
    return True


def _has_one_numbering_level(row: _NomenclatureTableRow) -> bool:
    for regime, text in zip(row.regimes, row.rubrique_lines):
        if not regime and _has_enumeration(text):
            return False
    return True


def _has_different_regimes(row: _NomenclatureTableRow) -> bool:
    non_null = [rg for rg in row.regimes if rg]
    return len(non_null) == len(set(non_null))


def _is_rubrique_simple(row: _NomenclatureTableRow) -> bool:
    return _has_one_numbering_level(row) and _has_different_regimes(row)


Counter([_is_rubrique_simple(row) for row in _DATA])  # Counter({True: 193, False: 73})


def _extract_prefix_number(digit_start: str) -> float:
    i = -1
    for i, char in enumerate(digit_start):
        if not char.isdigit() and char != '.':
            break
    if i == -1:
        raise ValueError(f'Should not happen for string starting with digit. Received {digit_start}')
    return float(digit_start[:i])


def _extract_lower_threshold_superieur(text: str) -> float:
    lower_text = text.lower()
    clean_text = (
        lower_text.replace('supérieure', 'supérieur').replace('égale', 'égal').replace('ou égal', '').replace('à', '')
    )
    digit_start = clean_text.split('supérieur')[1].replace(' ', '')
    return _extract_prefix_number(digit_start)


class UnhandledClassementDescriptionError(Exception):
    pass


def _extract_lower_threshold(text: str) -> float:
    if 'supérieur' in text.lower():
        return _extract_lower_threshold_superieur(text)
    if 'inférieur' in text.lower():
        return 0
    raise UnhandledClassementDescriptionError(text)


def _rearrange(list_: List[float]) -> List[float]:
    if not is_increasing(list_) and not _is_decreasing(list_):
        raise ValueError(f'Expecting monotonous list, received {list_}')
    return list_


def _extract_thresholds(row: _NomenclatureTableRow) -> List[float]:
    thresholds: List[float] = []
    for regime, text in zip(row.regimes, row.rubrique_lines):
        if regime:
            thresholds.append(_extract_lower_threshold(text))
    return _rearrange(thresholds)


def _extract_regimes(row: _NomenclatureTableRow) -> List[Regime]:
    return [reg for reg in row.regimes if reg]


def _extract_simple_rubrique(row: _NomenclatureTableRow) -> Optional[RubriqueSimpleThresholds]:
    assert _is_rubrique_simple(row)
    try:
        thresholds, regimes = _extract_thresholds(row), _extract_regimes(row)
        if _is_decreasing(thresholds):
            thresholds = thresholds[::-1]
            regimes = regimes[::-1]
        return RubriqueSimpleThresholds(row.rubrique, thresholds, regimes, _extract_alineas(row), '', '')
    except UnhandledClassementDescriptionError:
        return None


_RUBRIQUES_OPT = [_extract_simple_rubrique(row) for row in _DATA if _is_rubrique_simple(row)]
_RUBRIQUES = {rb.code: rb for rb in _RUBRIQUES_OPT if rb}


def _dump_nomenclature() -> Nomenclature:
    am_data = load_am_data()
    metadata = am_data.metadata
    nomenclature = Nomenclature(metadata, _RUBRIQUES)
    write_json(nomenclature.to_dict(), f'{AM_DATA_FOLDER}/nomenclature.json')
    return nomenclature


_NOMENCLATURE = _dump_nomenclature()


def _is_simple(code: str) -> bool:
    if code and code in _RUBRIQUES:
        return True
    return False


_INSTALLATIONS = load_installations('all')
_CLASSEMENTS = load_classements('all')
_SIMPLE_CLASSEMENTS = [cl for cl in _CLASSEMENTS if _is_simple(cl.code_nomenclature)]
_SIMPLE_ACTIVE_CLASSEMENTS = [cl for cl in _SIMPLE_CLASSEMENTS if cl.etat_activite == GRClassementActivite.ACTIVE]


Counter([_is_simple(cl.code_nomenclature) for ins in _INSTALLATIONS for cl in ins.classements])
# Counter({False: 186258, True: 73714})
Counter(
    [
        _is_simple(cl.code_nomenclature)
        for ins in _INSTALLATIONS
        for cl in ins.classements
        if cl.etat_activite == GRClassementActivite.ACTIVE
    ]
)
# Counter({False: 116419, True: 59810})


_COMPUTED_REGIMES = [deduce_regime_if_possible(cl, _NOMENCLATURE) for cl in _SIMPLE_ACTIVE_CLASSEMENTS]
Counter([(reg, cl.regime) for reg, cl in zip(_COMPUTED_REGIMES, _SIMPLE_ACTIVE_CLASSEMENTS)])
