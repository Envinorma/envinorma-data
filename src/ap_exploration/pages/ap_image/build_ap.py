import os
import random
import string
from dataclasses import dataclass
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar, Union

import cv2
from ap_exploration.models import ArretePrefectoral
from ap_exploration.pages.ap_image.extract_ap_structure import extract_ap_intro, keep_alphanumeric, lower_unicode
from ap_exploration.pages.ap_image.table_extraction import LocatedTable, extract_and_remove_tables
from envinorma.data import Row, Table
from envinorma.data.text_elements import TextElement, Title
from envinorma.io.alto import AltoFile, AltoPage, AltoTextBlock, AltoTextLine, extract_lines, extract_text_blocks
from pdf2image import convert_from_path, pdfinfo_from_path
from pytesseract.pytesseract import run_tesseract
from tqdm import tqdm

_AdvancementCallback = Callable[[float], None]


def _nb_pages_in_pdf(filename: str) -> int:
    return pdfinfo_from_path(filename)['Pages']


def _ensure_one_page_and_get_it(alto: AltoFile) -> AltoPage:
    if len(alto.layout.pages) != 1:
        raise ValueError(f'Expecting exactly one page, got {len(alto.layout.pages)}')
    return alto.layout.pages[0]


def _tesseract(filename: str) -> AltoPage:
    output_filename_base = filename.replace('.png', '')
    run_tesseract(
        input_filename=filename,
        output_filename_base=output_filename_base,
        extension='xml',
        lang='fra',
        config='-c tessedit_create_alto=1',
    )
    xml = open(output_filename_base + '.xml').read()
    os.remove(output_filename_base + '.xml')
    return _ensure_one_page_and_get_it(AltoFile.from_xml(xml))


_PageContent = Tuple[AltoPage, List[LocatedTable]]


def _build_tmp_file() -> str:
    return '/tmp/' + ''.join([random.choice(string.ascii_letters) for _ in range(10)])


def _extract_page_content(filename: str, page_rank: int) -> _PageContent:
    page = convert_from_path(filename, first_page=page_rank + 1, last_page=page_rank + 1)[0]
    file_ = _build_tmp_file() + '.png'
    page.save(file_)
    img = cv2.imread(file_, 0)
    img_without_tables, tables = extract_and_remove_tables(img)
    cv2.imwrite(file_, img_without_tables)
    page = _tesseract(file_)
    os.remove(file_)
    return (page, tables)


def _extract_pages_content(filename: str, advancement_callback: _AdvancementCallback) -> List[_PageContent]:
    nb_pages = _nb_pages_in_pdf(filename)
    result: List[_PageContent] = []
    for page_rank in tqdm(range(nb_pages), 'OCRing pages'):
        result.append(_extract_page_content(filename, page_rank))
        advancement_callback((page_rank + 1) / nb_pages * 0.8)
    return result


T = TypeVar('T')


@dataclass
class Located(Generic[T]):
    element: T
    page_index: int
    distance_from_top: float
    distance_from_left: float

    def sort_key(self) -> Tuple[int, float, float]:
        return (self.page_index, self.distance_from_top, self.distance_from_left)


def _extract_located_text_blocks(pages: List[AltoPage]) -> List[Located[AltoTextBlock]]:
    return [
        Located(block, i, block.vpos, block.hpos) for i, page in enumerate(pages) for block in extract_text_blocks(page)
    ]


def _find_first(elements: List[T], criterion: Callable[[T], bool]) -> Optional[int]:
    for i, element in enumerate(elements):
        if criterion(element):
            return i
    return None


_LocBlock = Located[AltoTextBlock]
_LocTable = Located[Table]
_LocElement = Union[_LocBlock, _LocTable]


def _merge_block_and_tables(lines: List[_LocBlock], tables: List[_LocTable]) -> List[_LocElement]:
    return sorted([*lines, *tables], key=lambda x: x.sort_key())


def _line_in_upper_third(line: AltoTextLine, page_height: float) -> bool:
    bottom = line.vpos + line.height
    return bottom <= page_height / 3


def _is_in_the_center(line: AltoTextLine, page_width: float) -> bool:
    return line.hpos >= 0.25 * page_width and line.hpos + line.width <= 0.75 * page_width


def _is_arrete_line(line: AltoTextLine, page_rank: int, page_height: float, page_width: float) -> bool:
    if not _is_in_the_center(line, page_width):
        return False
    clean_words = keep_alphanumeric(lower_unicode(''.join(line.extract_strings())))
    if clean_words == 'arrete':
        if page_rank != 0:
            return True
        return not _line_in_upper_third(line, page_height)  # in this case, it is probably the doc title
    return False


def find_arrete_start_lines(pages: List[AltoPage]) -> List[Located[AltoTextLine]]:
    return [
        Located(line, page_rank, line.vpos, line.hpos)
        for page_rank, page in enumerate(pages[:4])
        for line in extract_lines(page)
        if _is_arrete_line(line, page_rank, page.height, page.width)
    ]


def _split_blocks_and_tables(
    pages: List[AltoPage], lines: List[_LocBlock], tables: List[_LocTable]
) -> Tuple[List[_LocElement], List[_LocElement]]:
    arrete_lines = find_arrete_start_lines(pages)
    lines_and_tables = _merge_block_and_tables(lines, tables)
    if not arrete_lines:
        return [], lines_and_tables
    line = arrete_lines[0]

    def criterion(element: _LocElement) -> bool:
        return element.sort_key() >= (line.page_index, line.distance_from_top, line.distance_from_left)

    index = _find_first(lines_and_tables, criterion)
    return lines_and_tables[:index], lines_and_tables[index:]


def _row_to_str(row: Row) -> str:
    return ' '.join([cell.content.text for cell in row.cells])


def _table_to_str(table: Table) -> str:
    return '\n'.join([_row_to_str(row) for row in table.rows])


def _build_visa_str(located_element: _LocElement) -> str:
    if isinstance(located_element.element, AltoTextBlock):
        return ' '.join(located_element.element.extract_string_lines())
    return _table_to_str(located_element.element)


def _build_visa(elements: List[_LocElement], intro_visa: List[str]) -> List[str]:
    return intro_visa + [_build_visa_str(elt) for elt in elements]


def _is_article_number(word: str) -> bool:
    if word in ('1er', '1°°', '1"°', '1°"', '1°”', '1”°', 'Ier', '1""'):
        return True
    if not word or len(set(word) - {'.', ',', '-', '—'}) == 0:
        return False
    return len(set(word) - set('0123456789S.,-—')) == 0


def _is_title_first_word(word: str) -> bool:
    return word.lower() in ('titre', 'chapitre', 'article')


def _is_title(line: str) -> bool:
    words = line.split()
    return len(words) >= 2 and _is_title_first_word(words[0]) and _is_article_number(words[1])


def _to_element(line: str) -> TextElement:
    if _is_title(line):
        return Title(line, level=1)
    return line


def _group_str(strs: List[str]) -> List[str]:
    groups: List[List[str]] = [[]]
    in_title = False
    for str_ in strs:
        if _is_title(str_):
            in_title = True
            groups.append([str_])
            continue
        if in_title:
            if str_.isupper():
                groups[-1].append(str_)  # Append to title
                continue
            groups.append([str_])  # Start new line
            in_title = False
            continue
        groups[-1].append(str_)
    return [' '.join(group) for group in groups if group]


def _extract_text_element(located_element: _LocElement) -> List[TextElement]:
    if isinstance(located_element.element, AltoTextBlock):
        grouped_strings = _group_str(located_element.element.extract_string_lines())
        return [_to_element(str_) for str_ in grouped_strings]
    return [located_element.element]  # element is a table


def _build_content(elements: List[_LocElement]) -> List[TextElement]:
    return [tx_elt for element in elements for tx_elt in _extract_text_element(element)]


def build(ap_id: str, filename: str, advancement_callback: _AdvancementCallback) -> ArretePrefectoral:
    alto_pages = _extract_pages_content(filename, advancement_callback)
    if not alto_pages:
        raise ValueError('Expecting at least one page to extract AP.')
    intro, first_page_remainder = extract_ap_intro(alto_pages[0][0])
    pages = [first_page_remainder] + [pg for pg, _ in alto_pages[1:]]
    tables = [Located(tb.table, i, tb.v_pos, tb.h_pos) for i, (_, tbs) in enumerate(alto_pages) for tb in tbs]
    blocks = _extract_located_text_blocks(pages)
    visa_elements, content_elements = _split_blocks_and_tables(pages, blocks, tables)
    res = ArretePrefectoral(
        ap_id,
        '\n'.join(intro.title),
        visas_considerant=_build_visa(visa_elements, intro.visa),
        content=_build_content(content_elements),
    )
    advancement_callback(1.0)
    return res
