from ap_exploration.db.ap import seems_georisques_document_id
from ap_exploration.pages.ap_image.alto_to_html import _is_article_number


def test_seems_georisques_document_id():
    assert seems_georisques_document_id('a_b_c790bcaf9fe84c3c80de3f21d22f3d61')
    assert not seems_georisques_document_id('a_b_c790bcaf9fe84c3c80de3f21d22f3d611.pdf')
    assert not seems_georisques_document_id('a_b_c790bcaf9fe84c3c80de3f21d22f3d6x.pdf')
    assert not seems_georisques_document_id('a_b_c790bcaf9fe84c3c80de3f21d22f3d6A.pdf')
    assert not seems_georisques_document_id('')
    assert seems_georisques_document_id('c_9_8aa100b165196719016519b58149377e')
    assert seems_georisques_document_id('c_9_c790bcaf9fe84c3c80de3f21d22f3d61')
    assert seems_georisques_document_id('c_9_8aac032462d864b20162d86ab1470020')
    assert seems_georisques_document_id('c_9_8ac510ca5f390e97015f39c4e25e0004')


def test_is_article_number():
    assert _is_article_number('1.3')
    assert _is_article_number('1')
    assert _is_article_number('10')
    assert _is_article_number('18')
    assert not _is_article_number('.')
    assert not _is_article_number('')
    assert not _is_article_number('1A')
    assert not _is_article_number('123"')
