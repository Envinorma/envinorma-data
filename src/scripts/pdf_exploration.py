import os
import pdfplumber
from typing import Any, List
from pdfminer.pdfparser import PDFSyntaxError
from bs4 import BeautifulSoup
from bs4.element import Tag
from odf import odf2xhtml


def _count_nb_characters(filename: str) -> int:
    try:
        pdf = pdfplumber.open(filename)
    except PDFSyntaxError as exc:
        print(exc)
        return 0
    return sum([len(page.chars) for page in pdf.pages])


def _is_searchable(filename: str) -> bool:
    return _count_nb_characters(filename) >= 50


_DOCUMENTS_FOLDER = '/Users/remidelbouys/EnviNorma/brouillons/data/icpe_documents'
_NB_CHARS = {
    doc: _count_nb_characters(_DOCUMENTS_FOLDER + '/' + doc)
    for doc in os.listdir(_DOCUMENTS_FOLDER)
    if 'pdf' in doc
    # if doc.replace('_', '/') in ap_ids
}


_SEARCHABLE_PDFS = [
    'L_a_320fd0e651204af8a92c67c2eb08065a.pdf',
    'D_f_ab53da82a80548e4843f3827f16deeef.pdf',
    'L_e_134176c5ab194f3aa796bfd2269e7fde.pdf',
    'N_0_0dd241fd55a6458c87c6a9bfe29eb910.pdf',
    'M_0_8ab90ca260e0618f0160e0a794a50020.pdf',
    'E_4_3d2152eefb4949adaf64de59d21eb724.pdf',
    'T_8_df527e38b8f949b28a8db21d9da3e6d8.pdf',
    'E_1_6f40f3cc3d2740738ef4ba25033794a1.pdf',
    'B_2_41254cfe1ad349dca59d95690d9e8b72.pdf',
    'M_c_8ab90ca260ff490e0160ffb115a5001c.pdf',
    'N_c_252a043a70ef493eb7e84f754c5c0f2c.pdf',
    'M_c_de4915760dfc4fc78829032d1aaa63bc.pdf',
    'M_1_2c92c054491ce04d01491e35a29e0041.pdf',
    'V_f_44bbc704b5da44949b8e99b504e49c5f.pdf',
    'E_4_3ad98f7bb1cf442bb0dce161e533d524.pdf',
    'B_0_56d111b6219f4cba9753ee3a0b57f850.pdf',
    'L_5_b1373bae5be94a6f95b28c24135a39c5.pdf',
    'N_3_8aac03246b897e18016b89cd859f0073.pdf',
    'B_b_94cbccc97b694090ad2844d62fbf215b.pdf',
    'T_9_5623aeac7e9049ef89cee59095405869.pdf',
    'L_d_8ac510ca5ab3e08e015ab3fe2528000d.pdf',
    'B_6_096e719926494d22a165b76abbc31566.pdf',
    'M_6_d8867fb48a0c48ed8ef6d4691f9d9d56.pdf',
    'B_a_681f198ec8354a9aa9f29daed42ec79a.pdf',
    'B_6_39c27a3248af4da4933f23f803be7db6.pdf',
    'N_7_c06769742298451baeb506f8ebbcdf57.pdf',
    'B_7_e32ce299d1394e4b89f2c7c1f3fe6eb7.pdf',
    'M_a_7b80c752a92946b3bc4ee702a7c0d7ea.pdf',
    'L_5_8ac510ca50655697015066c999350015.pdf',
    'M_4_e24d86e850274c679dc87667d2d4eaf4.pdf',
    'D_3_4522ad909ea040b2bddead1c844b1743.pdf',
    'L_4_8ac510ca44fecea10144fee289180044.pdf',
    'B_b_2812ff7b0b174134868ca08c4ac4cc7b.pdf',
    'B_b_5ad4bb14d3014789957bff2ce504912b.pdf',
    'N_b_be946eb3d6fd4c59bab07b496f7b88bb.pdf',
    'L_5_8ac510ca4d7562eb014d767bca830005.pdf',
    'L_8_8ac510ca5065bae40150668794310018.pdf',
    'L_c_ccff9c9a4d3745828f4a5256718612ac.pdf',
    'L_c_e1707b709fed43bda17568f632b8d3bc.pdf',
]


def _extract_lines_from_page_element(page_element: Any) -> List[str]:
    if isinstance(page_element, str):
        return [page_element]
    if isinstance(page_element, Tag):
        return [line for child in page_element.children for line in _extract_lines_from_page_element(child)]
    raise ValueError(f'Unhandled type {type(page_element)}')


def _extract_lines_from_soup(soup: BeautifulSoup) -> List[str]:
    return [line for child in soup.children for line in _extract_lines_from_page_element(child)]


def _extract_lines(filename: str) -> List[str]:
    html = odf2xhtml.load(filename).toXml()
    soup = BeautifulSoup(html)
    return _extract_lines_from_soup(soup)


res = _extract_lines(
    '/Users/remidelbouys/EnviNorma/brouillons/data/icpe_ap_odt/D_f_ab53da82a80548e4843f3827f16deeef.odt'
)
