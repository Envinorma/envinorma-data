'''
Temporary script: download and transform a set of PDF documents to get the alto version
'''

import json
import os

import cv2
from tqdm import tqdm

from ap_exploration.pages.ap_image import _generate_output_filename, download_document
from ap_exploration.pages.ap_image.process import _load_raw_page, _process_file, _remove_pdf_extension
from ap_exploration.pages.ap_image.table_extraction import extract_and_remove_tables
from envinorma.config import config
from envinorma.data_build.georisques_data import GR_DOC_BASE_URL

_DOC_IDS = json.load(open('ap_exploration/db/gr_ap_sample.json'))
_PDF_AP_FOLDER = config.storage.ap_data_folder


for doc_id in tqdm(_DOC_IDS):
    output_filename = os.path.join(_PDF_AP_FOLDER, _generate_output_filename(doc_id))
    if os.path.exists(output_filename):
        continue
    input_url = GR_DOC_BASE_URL + '/' + doc_id
    download_document(input_url, output_filename)


for file_ in tqdm(os.listdir(_PDF_AP_FOLDER)):
    if '.pdf' in file_:
        path = os.path.join(_PDF_AP_FOLDER, file_)
        _process_file(path)

for file_ in tqdm(os.listdir(_PDF_AP_FOLDER)):
    if '.pdf' not in file_:
        continue
    path = os.path.join(_PDF_AP_FOLDER, file_)
    folder = _remove_pdf_extension(path)
    pages = [x for x in os.listdir(folder) if x.endswith('.raw')]
    for page in tqdm(pages, leave=False):
        page_path = os.path.join(folder, page)
        new_path = page_path.replace('.raw', '_tables.json')
        if os.path.exists(new_path):
            continue
        image_ = _load_raw_page(page_path)
        tmpfile = 'tmp.png'
        image_.save(tmpfile)
        image = cv2.imread(tmpfile, 0)
        _, tables = extract_and_remove_tables(image)
        json.dump([table.to_dict() for table in tables], open(new_path, 'w'))
