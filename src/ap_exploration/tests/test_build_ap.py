from ap_exploration.pages.ap_image.build_ap import _group_str


def test_group_str():
    assert _group_str([]) == []
    assert _group_str(['Test']) == ['Test']
    assert _group_str(['Test', '1']) == ['Test 1']
    assert _group_str(['Test', '1', 'Article 1.3']) == ['Test 1', 'Article 1.3']
    assert _group_str(['Test', '1', 'Article 1.3', 'DISPOSITIONS']) == ['Test 1', 'Article 1.3 DISPOSITIONS']
    to_group = ['Test', '1', 'Article 1.3', 'DISPOSITIONS GENERALES']
    assert _group_str(to_group) == ['Test 1', 'Article 1.3 DISPOSITIONS GENERALES']
    to_group = ['Test', '1', 'Article 1.3', 'DISPOSITIONS GENERALES', 'RELATIVES A ETC']
    assert _group_str(to_group) == ['Test 1', 'Article 1.3 DISPOSITIONS GENERALES RELATIVES A ETC']
    to_group = ['DISPOSITIONS GENERALES', 'RELATIVES A ETC']
    assert _group_str(to_group) == ['DISPOSITIONS GENERALES RELATIVES A ETC']
    to_group = ['Test', '1', 'Article 1.3', 'DISP GENERALES', 'RELATIVES A ETC', 'Contenu', 'SUITE']
    assert _group_str(to_group) == ['Test 1', 'Article 1.3 DISP GENERALES RELATIVES A ETC', 'Contenu SUITE']


test_group_str()
