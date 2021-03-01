'''
Possible entry point for processing copiable pdf
'''


from typing import Optional

from envinorma.io.markdown import extract_markdown_text
from envinorma.io.docx import build_structured_text_from_docx_xml, get_docx_xml
from envinorma.pdf import pdf_to_docx


def structure_searchable_pdf_AP(
    filename: str, docx_filename: Optional[str] = None, markdown_filename: Optional[str] = None
):
    assert '.pdf' in filename
    docx_filename = docx_filename or filename.replace('.pdf', '.docx')
    pdf_to_docx(filename, docx_filename)
    xml = get_docx_xml(filename)
    res = build_structured_text_from_docx_xml(xml)
    markdown_filename = markdown_filename or filename.replace('.pdf', '.md')
    with open(markdown_filename, 'w') as file_:
        file_.write('\n\n'.join(extract_markdown_text(res, 1, False)))
