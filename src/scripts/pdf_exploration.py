import os
from lib.pdf import pdf_to_docx
from typing import List
import bs4
from bs4 import BeautifulSoup
from lib.docx import (
    _replace_small_tables,
    extract_all_word_styles,
    extract_styles_to_nb_letters,
    extract_table,
    get_docx_xml,
    remove_tables_and_body_text,
    write_new_document,
    write_xml,
)
from zipfile import ZipFile

# _DOCUMENTS_FOLDER = '/Users/remidelbouys/EnviNorma/brouillons/data/icpe_documents'
# _NB_CHARS = {
#     doc: _count_nb_characters(_DOCUMENTS_FOLDER + '/' + doc)
#     for doc in os.listdir(_DOCUMENTS_FOLDER)
#     if 'pdf' in doc
#     # if doc.replace('_', '/') in ap_ids
# }


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

FOLDER = '/Users/remidelbouys/EnviNorma/brouillons/data/icpe_documents'
FILENAME = f'{FOLDER}/L_c_e1707b709fed43bda17568f632b8d3bc.pdf'.replace('.pdf', '.docx')


# XML = get_docx_xml(FILENAME)
# SOUP = BeautifulSoup(str(XML), 'lxml-xml')

# CLEAN_SOUP = _replace_small_tables(SOUP)
# TITLES_SOUP = remove_tables_and_body_text(CLEAN_SOUP)
# print(TITLES_SOUP.text.replace('\n', ''))
# write_new_document(FILENAME, str(TITLES_SOUP), FILENAME.replace('.docx', '_titles.docx'))


def _is_title_beginning(string: str) -> bool:
    patterns = ['title', 'article', 'chapitre']
    for pattern in patterns:
        if string[: len(pattern)].lower() == pattern:
            return True
    return False


def _group_strings(strings: List[str]) -> List[str]:
    groups: List[List[str]] = [[]]
    for string in strings:
        if _is_title_beginning(string):
            groups.append([])
        groups[-1].append(string)
    return [' '.join(group) for group in groups if group]


def _extract_lines(soup: BeautifulSoup) -> List[str]:
    res = []
    for tag in soup.find_all('w:p'):
        res.append(_group_strings(tag.stripped_strings))
    return [x for x in res if x]


def _empty_soup(soup: BeautifulSoup) -> bool:
    return ''.join(soup.stripped_strings) == ''


def _extract_titles(filename: str) -> List[str]:
    output = filename.replace('.pdf', '.docx')
    if not os.path.exists(output):
        return []
    xml = get_docx_xml(output)
    soup = BeautifulSoup(str(xml), 'lxml-xml')
    if _empty_soup(soup):
        return []
    clean_soup = _replace_small_tables(soup)
    titles_soup = remove_tables_and_body_text(clean_soup)
    return _extract_lines(titles_soup)


from tqdm import tqdm
import os

filename_to_title = {filename: _extract_titles(FOLDER + '/' + filename) for filename in tqdm(_SEARCHABLE_PDFS)}
