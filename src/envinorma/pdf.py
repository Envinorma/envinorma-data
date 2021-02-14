from typing import Optional

import pdfplumber
from pdf2docx import parse
from pdfminer.pdfparser import PDFSyntaxError

from envinorma.data import StructuredText
from envinorma.io.docx import build_structured_text_from_docx_xml, get_docx_xml
from envinorma.utils import random_string


def pdf_to_docx(filename: str, output_filename: Optional[str] = None) -> None:
    output_filename = output_filename or filename.replace('.pdf', '.docx')
    parse(filename, output_filename)


def _count_nb_characters(filename: str) -> int:
    try:
        pdf = pdfplumber.open(filename)
    except PDFSyntaxError as exc:
        print(exc)
        return 0
    return sum([len(page.chars) for page in pdf.pages])


def is_searchable(filename: str) -> bool:
    return _count_nb_characters(filename) >= 50


def extract_text(file_content: bytes) -> StructuredText:
    pdf_filename = f'/tmp/{random_string()}.pdf'
    open(pdf_filename, 'wb').write(file_content)
    docx_filename = pdf_filename.replace('.pdf', '.docx')
    pdf_to_docx(pdf_filename, docx_filename)
    xml = get_docx_xml(docx_filename)
    return build_structured_text_from_docx_xml(xml)
