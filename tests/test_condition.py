from datetime import datetime

from envinorma.models import Regime
from envinorma.parametrization.models.condition import (
    AndCondition,
    Equal,
    Greater,
    Littler,
    OrCondition,
    Range,
    extract_sorted_interval_sides_targets,
)
from envinorma.parametrization.models.parameter import Parameter, ParameterType


def test_is_satisfied():
    param_1 = Parameter('regime', ParameterType.REGIME)
    param_2 = Parameter('date', ParameterType.DATE)
    condition_1 = Equal(param_1, Regime.A)
    condition_2 = Equal(param_1, Regime.E)
    condition_3 = Littler(param_2, 1, True)
    assert not AndCondition(frozenset([condition_1])).is_satisfied({})
    assert AndCondition(frozenset([condition_1])).is_satisfied({param_1: Regime.A})
    assert OrCondition(frozenset([condition_1, condition_2])).is_satisfied({param_1: Regime.A})
    assert OrCondition(frozenset([condition_1, condition_3])).is_satisfied({param_1: Regime.A})
    assert not AndCondition(frozenset([condition_1, condition_2])).is_satisfied({param_1: Regime.A})
    assert AndCondition(frozenset([condition_1, condition_3])).is_satisfied({param_1: Regime.A, param_2: 0.5})
    assert OrCondition(frozenset([condition_2, condition_3])).is_satisfied({param_1: Regime.E, param_2: 0.5})
    assert not OrCondition(frozenset([condition_1, condition_3])).is_satisfied({param_1: Regime.E, param_2: 5})


def test_extract_sorted_interval_sides_targets():
    parameter = Parameter('test', ParameterType.DATE)
    conditions = [
        Range(parameter, datetime(2020, 1, 1), datetime(2021, 1, 1), False, True),
        Littler(parameter, datetime(2020, 1, 1), True),
        Greater(parameter, datetime(2021, 1, 1), False),
    ]
    assert extract_sorted_interval_sides_targets(conditions, True) == [datetime(2020, 1, 1), datetime(2021, 1, 1)]
