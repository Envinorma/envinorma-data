import pytest
from ap_exploration.pages.ap_pdf import _generate_new_filename, _change_extension_pdf_to_docx


def test_generate_new_filename():

    assert _generate_new_filename('test.hello')[-6:] == '.hello'
    assert _generate_new_filename('test.hello')[:4] == 'test'
    assert len(_generate_new_filename('test.hello')) == 4 + 6 + 1 + 5
    assert _generate_new_filename('test')[-8:] == '.unknown'
    assert len(_generate_new_filename('test')) == 4 + 6 + 1 + 7
    assert len(_generate_new_filename('test.txt')) == 4 + 6 + 1 + 3


def test_change_extension_pdf_to_docx():
    with pytest.raises(ValueError):
        _change_extension_pdf_to_docx('')
        _change_extension_pdf_to_docx('pdf')
        _change_extension_pdf_to_docx('pdf.pdf.p')
        _change_extension_pdf_to_docx('file.docx')

    assert _change_extension_pdf_to_docx('pdf.pdf') == 'pdf.docx'
    assert _change_extension_pdf_to_docx('.pdf') == '.docx'
