'''
Temporary script: download and transform a set of PDF documents to get the alto version
'''
import os

from ap_exploration.db.ap import SAMPLE_DOC_IDS, download_document, georisques_full_url, input_pdf_path
from ap_exploration.pages.ap_image.process import simple_ocr_on_file
from tqdm import tqdm

for doc_id in tqdm(SAMPLE_DOC_IDS, 'Downloading Géorisques documents'):
    output_filename = input_pdf_path(doc_id)
    if os.path.exists(output_filename):
        continue
    download_document(georisques_full_url(doc_id), output_filename)


for doc_id in tqdm(SAMPLE_DOC_IDS, 'Simple OCRing Géorisques documents'):
    simple_ocr_on_file(doc_id)
