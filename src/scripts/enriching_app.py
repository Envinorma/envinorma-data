'''
Script for testing io of open document.
TODO: use to define unit tests or deprecate
'''

import json
import os
import random
from typing import List

from bs4 import BeautifulSoup
from tqdm import tqdm

from envinorma.am_enriching import _remove_table_html
from envinorma.config import AM_DATA_FOLDER
from envinorma.data import ArreteMinisteriel, EnrichedString, StructuredText, load_am_data
from envinorma.io.markdown import extract_markdown_text
from envinorma.io.open_document import load_and_transform, structured_text_to_odt_file, structured_text_to_odt_xml

_DOC_NAME = '2020-06-11-AUTO 2001-AP AUTORISATION-Projet_AP_VF'

FILENAME = f'/Users/remidelbouys/EnviNorma/brouillons/data/icpe_ap_odt/{_DOC_NAME}.odt'
FILENAME = f'test_data/simple_document.odt'
TEXT = load_and_transform(FILENAME, False)
XML = structured_text_to_odt_xml(TEXT)
structured_text_to_odt_file(TEXT, 'tmp.odt')
BACK = load_and_transform('tmp.odt', False)


def _exists(folder: str) -> bool:
    if os.path.exists(folder):
        return True
    print(f'Warning: folder {folder} does not exist.')
    return False


def am_to_text(am: ArreteMinisteriel) -> StructuredText:
    return StructuredText(EnrichedString(''), [], [_remove_table_html(sec) for sec in am.sections], None)


PARAMETRIC_TEXTS_FOLDER = AM_DATA_FOLDER + '/parametric_texts'


def _get_am_files() -> List[str]:
    data = load_am_data()
    all_folders = [md.nor or md.cid for md in data.metadata if md.state == md.state.VIGUEUR]
    folders_to_copy = [fd for fd in all_folders if _exists(PARAMETRIC_TEXTS_FOLDER + '/' + fd)]
    res = []
    for folder in tqdm(folders_to_copy):
        for file_ in os.listdir(PARAMETRIC_TEXTS_FOLDER + '/' + folder):
            if 'no_date' in file_:
                res.append(os.path.join(PARAMETRIC_TEXTS_FOLDER, folder, file_))
    return res


_AM_FILES = _get_am_files()


def _write_odt(file_: str):
    text = json.load(open(file_))
    am = ArreteMinisteriel.from_dict(text)
    structured_text = am_to_text(am)
    structured_text_to_odt_file(structured_text, 'tmp.odt')


def pretty(xml: str) -> str:
    return str(BeautifulSoup(xml, 'lxml-xml').prettify())


filename = random.choice(_AM_FILES)
print(filename)
_write_odt(filename)
after = load_and_transform('tmp_2.odt', False)
open('before.md', 'w').write(
    '\n'.join(extract_markdown_text(am_to_text(ArreteMinisteriel.from_dict(json.load(open(filename)))), 0))
)
open('after.md', 'w').write('\n'.join(extract_markdown_text(after, 0)))
