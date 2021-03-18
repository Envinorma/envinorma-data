from ap_exploration.db.ap import georisques_document_id_to_url, georisques_url_to_document_id


def test_georisques_url_to_document_id() -> None:
    exp = 'H_8_d93f0cae3bd54a16909aedde26832718'
    assert georisques_url_to_document_id('H/8/d93f0cae3bd54a16909aedde26832718.pdf') == exp


def test_georisques_document_id_to_url() -> None:
    exp = 'H/8/d93f0cae3bd54a16909aedde26832718.pdf'
    assert georisques_document_id_to_url('H_8_d93f0cae3bd54a16909aedde26832718') == exp
