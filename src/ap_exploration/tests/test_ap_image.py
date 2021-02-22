import pytest
from ap_exploration.pages.ap_image import _seems_georisques_document_id, _generate_output_filename
from ap_exploration.pages.ap_image.process import _remove_pdf_extension


def test_seems_georisques_document_id():
    assert not _seems_georisques_document_id('a_b_c790bcaf9fe84c3c80de3f21d22f3d61')
    assert not _seems_georisques_document_id('a_b_c790bcaf9fe84c3c80de3f21d22f3d611.pdf')
    assert not _seems_georisques_document_id('a_b_c790bcaf9fe84c3c80de3f21d22f3d6x.pdf')
    assert not _seems_georisques_document_id('a_b_c790bcaf9fe84c3c80de3f21d22f3d6A.pdf')
    assert not _seems_georisques_document_id('')
    assert _seems_georisques_document_id('c_9_8aa100b165196719016519b58149377e.pdf')
    assert _seems_georisques_document_id('c_9_c790bcaf9fe84c3c80de3f21d22f3d61.pdf')
    assert _seems_georisques_document_id('c_9_8aac032462d864b20162d86ab1470020.pdf')
    assert _seems_georisques_document_id('c_9_8ac510ca5f390e97015f39c4e25e0004.pdf')


def test_generate_output_filename():
    res = _generate_output_filename('a/b/c790bcaf9fe84c3c80de3f21d22f3d6x.pdf')
    assert res == 'a_b_c790bcaf9fe84c3c80de3f21d22f3d6x.pdf'
    assert _generate_output_filename('') == ''


def test_remove_pdf_extension():
    assert _remove_pdf_extension('eifohzeoif.pdf') == 'eifohzeoif'
    with pytest.raises(ValueError):
        _remove_pdf_extension('eifohzeoif.df')
    with pytest.raises(ValueError):
        _remove_pdf_extension('')