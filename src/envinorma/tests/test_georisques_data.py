from envinorma.data import Regime, RubriqueSimpleThresholds
from envinorma.data_build.georisques_data import _compute_regime, _snake_to_camel, _split_string


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


def test_compute_regime():
    ts = RubriqueSimpleThresholds('1510', [1], [Regime.A], ['1'], '', '')
    assert _compute_regime(10, ts) == Regime.A
    assert _compute_regime(0, ts) == Regime.NC

    ts = RubriqueSimpleThresholds('1510', [1, 4, 5], [Regime.DC, Regime.E, Regime.A], ['1'], '', '')
    assert _compute_regime(10, ts) == Regime.A
    assert _compute_regime(4.5, ts) == Regime.E
    assert _compute_regime(3, ts) == Regime.DC
    assert _compute_regime(-3, ts) == Regime.NC
