import pytest

from envinorma.utils import _split_string, batch, snake_to_camel


def test_split_string():
    assert _split_string('fooBarFoo', []) == ['fooBarFoo']
    assert _split_string('fooBarFoo', [3]) == ['foo', 'BarFoo']
    assert _split_string('fooBarFoo', [3, 6]) == ['foo', 'Bar', 'Foo']


def test_snake_to_camel():
    assert snake_to_camel('fooBarFoo') == 'foo_bar_foo'
    assert snake_to_camel('fooBARFoo') == 'foo_bar_foo'
    assert snake_to_camel('fooBarFOO') == 'foo_bar_foo'
    assert snake_to_camel('FooBarFoo') == 'foo_bar_foo'
    assert snake_to_camel('FOOBARFOO') == 'foobarfoo'


def test_batch():
    assert batch([], 1) == []
    assert batch([0, 1, 2, 3], 1) == [[0], [1], [2], [3]]
    assert batch([0, 1, 2, 3], 2) == [[0, 1], [2, 3]]
    assert batch([0, 1, 2, 3], 3) == [[0, 1, 2], [3]]
    with pytest.raises(ValueError):
        batch([0, 1, 2, 3], 0)
