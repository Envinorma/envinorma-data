from lib.georisques_data import _snake_to_camel, _split_string


def test_snake_to_camel():
    assert _snake_to_camel('fooBarFoo') == 'foo_bar_foo'
    assert _snake_to_camel('fooBARFoo') == 'foo_bar_foo'
    assert _snake_to_camel('fooBarFOO') == 'foo_bar_foo'
    assert _snake_to_camel('FooBarFoo') == 'foo_bar_foo'
    assert _snake_to_camel('FOOBARFOO') == 'foobarfoo'


def test_split_string():
    assert _split_string('fooBarFoo', []) == ['fooBarFoo']
    assert _split_string('fooBarFoo', [3]) == ['foo', 'BarFoo']
    assert _split_string('fooBarFoo', [3, 6]) == ['foo', 'Bar', 'Foo']

