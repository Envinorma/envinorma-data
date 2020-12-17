from typing import Optional
from pdf2docx import parse

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError


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
