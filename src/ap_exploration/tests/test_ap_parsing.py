from ap_exploration.pages.ap_pdf import _generate_new_filename, _extension


def test_generate_new_filename():

    assert _generate_new_filename('test.hello')[-6:] == '.hello'
    assert _generate_new_filename('test.hello')[:4] == 'test'
    assert len(_generate_new_filename('test.hello')) == 4 + 6 + 1 + 5
    assert _generate_new_filename('test')[-8:] == '.unknown'
    assert len(_generate_new_filename('test')) == 4 + 6 + 1 + 7
    assert len(_generate_new_filename('test.txt')) == 4 + 6 + 1 + 3


def test_extension():
    assert _extension('') == ''
    assert _extension('.') == ''
    assert _extension('.text') == 'text'
    assert _extension('text') == 'text'