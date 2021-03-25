from envinorma.data import Regime, RubriqueSimpleThresholds
from envinorma.data_build.georisques_data import _compute_regime


def test_compute_regime():
    ts = RubriqueSimpleThresholds('1510', [1], [Regime.A], ['1'], '', '')
    assert _compute_regime(10, ts) == Regime.A
    assert _compute_regime(0, ts) == Regime.NC

    ts = RubriqueSimpleThresholds('1510', [1, 4, 5], [Regime.DC, Regime.E, Regime.A], ['1'], '', '')
    assert _compute_regime(10, ts) == Regime.A
    assert _compute_regime(4.5, ts) == Regime.E
    assert _compute_regime(3, ts) == Regime.DC
    assert _compute_regime(-3, ts) == Regime.NC
