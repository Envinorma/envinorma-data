'''
Script for scrapping PDF nomenclature
'''

import os
from dataclasses import dataclass
from typing import List, Optional

import bs4
from bs4 import BeautifulSoup
from docx import Document  # type: ignore
from pdf2docx import parse
from tqdm import tqdm

from envinorma.data import Cell, Regime, Row
from envinorma.io.docx import extract_table, write_xml

if __name__ == '__main__':
    _FOLDER_NAME = '/Users/remidelbouys/Downloads'
    _NOMENCLATURE_PDF_FILENAME = f'{_FOLDER_NAME}/BrochureNom_v49public_vf.pdf'
    _NOMENCLATURE_DOCX_FILENAME = _NOMENCLATURE_PDF_FILENAME.replace('.pdf', '.docx')
    if not os.path.exists(_NOMENCLATURE_DOCX_FILENAME):
        parse(_NOMENCLATURE_PDF_FILENAME, _NOMENCLATURE_DOCX_FILENAME, start=17, end=60)

    def _parse_xml(str_: str) -> BeautifulSoup:
        return BeautifulSoup(str_, 'lxml-xml')

    DOC = Document(_NOMENCLATURE_DOCX_FILENAME)
    XML = DOC.part.element.xml
    SOUP = _parse_xml(str(XML))
    write_xml(SOUP, 'tmp_nomenclature.xml')

    TABLES = SOUP.find_all('tbl')
    print(f'{len(TABLES)} tables found.')

    def _is_nomenclature_table(table: bs4.Tag) -> bool:
        return 'Notes d’interprétation'.lower() in table.text.lower()

    NOMENCLATURE_TABLES = [tb for tb in TABLES if _is_nomenclature_table(tb)]
    print(f'{len(NOMENCLATURE_TABLES)} nomenclature tables found.')

    @dataclass
    class _NomenclatureTableRow:
        rubrique: int
        rubrique_text: List[str]
        regimes: List[Regime]
        rayons: List[Optional[int]]
        ampg: List[Optional[str]]
        interpretation_notes: List[Optional[str]]

    def _extract_rubrique(cell: Cell) -> int:
        rubrique_str = _parse_xml(cell.content.text).text.strip()
        if not rubrique_str.isdigit() or len(rubrique_str) != 4:
            raise ValueError(f'Expecting four-digit number, received {rubrique_str}')
        return int(rubrique_str)

    def _safely_find_unique_tag(str_xml: str, tag_name: str) -> bs4.Tag:
        t_tags = _parse_xml(str_xml).find_all(tag_name)
        if len(t_tags) != 1:
            raise ValueError(f'Expecting one {tag_name} tag, received {len(t_tags)} : {str(t_tags)}')
        return t_tags[0]

    def _extract_all_tags(str_xml: str, tag_name: str) -> List[bs4.Tag]:
        return _parse_xml(str_xml).find_all(tag_name)

    def _extract_rubrique_text(cell: Cell) -> List[str]:
        return [str(x) for x in _parse_xml(cell.content.text).stripped_strings]

    def _extract_regimes(cell: Cell) -> List[Regime]:
        return [
            Regime(tag.text.strip())
            for tag in _extract_all_tags(cell.content.text, 't')
            if tag.text.strip() not in ['', '...']
        ]

    def _extract_rayons(cell: Cell) -> List[Optional[int]]:
        return [
            int(tag.text) if tag.text.isdigit() else None
            for tag in _extract_all_tags(cell.content.text, 't')
            if tag.text
        ]

    def _extract_ampg(cell: Cell) -> List[Optional[str]]:
        return [tag.text if tag.text != '-' else None for tag in _extract_all_tags(cell.content.text, 't') if tag.text]

    def _extract_interpretation_notes(cell: Cell) -> List[Optional[str]]:
        return [tag.text if tag.text != '-' else None for tag in _extract_all_tags(cell.content.text, 't') if tag.text]

    def _build_nomenclature_row(table: Row) -> _NomenclatureTableRow:
        return _NomenclatureTableRow(
            rubrique=_extract_rubrique(table.cells[0]),
            rubrique_text=_extract_rubrique_text(table.cells[1]),
            regimes=_extract_regimes(table.cells[2]),
            rayons=_extract_rayons(table.cells[3]),
            ampg=_extract_ampg(table.cells[4]),
            interpretation_notes=_extract_interpretation_notes(table.cells[5]),
        )

    def _extract_table_data(table: bs4.Tag) -> List[_NomenclatureTableRow]:
        processed_table = extract_table(table)
        return [
            _build_nomenclature_row(row)
            for row in processed_table.rows[1:]
            if 'Notes d’interprétation'.lower() not in row.cells[-1].content.text
        ]

    ALL_ROWS = [row for table in tqdm(NOMENCLATURE_TABLES) for row in _extract_table_data(table)]

    def is_regime_text(text: str) -> bool:
        return text[-2:] == '..' or text[-3:] == '  .'

    def _has_as_many_dots_as_regimes(row: _NomenclatureTableRow) -> bool:
        dots = [x for x in row.rubrique_text if is_regime_text(x)]
        res = len(dots) == len(row.regimes)
        if not res:
            print(row)
        return res

    def _str_type(str_: str) -> str:
        if 'mais inf' in str_:
            return 'between'
        if 'ou égal' in str_ or 'supérieur' in str_.lower():
            return 'greater'
        print(str_)
        return 'not'
