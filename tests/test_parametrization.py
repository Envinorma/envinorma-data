import random
from datetime import datetime, timedelta
from string import ascii_letters
from typing import Optional

import pytest

from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import EnrichedString
from envinorma.parametrization.exceptions import ParametrizationError
from envinorma.parametrization.models.condition import Condition, Greater, Littler, Range
from envinorma.parametrization.models.parameter import ParameterEnum
from envinorma.parametrization.models.parametrization import (
    AlternativeSection,
    ConditionSource,
    EntityReference,
    NonApplicationCondition,
    Parametrization,
    SectionReference,
    _group,
)

_NAC = NonApplicationCondition


def _random_string() -> str:
    return ''.join([random.choice(ascii_letters) for _ in range(9)])


def _random_enriched_string() -> EnrichedString:
    return EnrichedString(_random_string(), [], None)


def _str(text: Optional[str] = None) -> EnrichedString:
    return EnrichedString(text) if text else _random_enriched_string()


@pytest.mark.filterwarnings('ignore')  # for inconsistency warnings
def test_check_parametrization_consistency():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_3 = Littler(date_, dt_1)
    cd_4 = Greater(date_, dt_2)
    cd_5 = Littler(date_, dt_2)
    cd_6 = Greater(date_, dt_1)
    source = ConditionSource('', EntityReference(SectionReference((2,)), None))
    unique_path = (0,)
    entity = EntityReference(SectionReference(unique_path), None)
    new_text = StructuredText(_str('Art. 2'), [_str('version modifiée')], [], None)
    Parametrization(
        [_NAC(entity, cd_1, source), _NAC(entity, cd_3, source)],
        [AlternativeSection(entity.section, new_text, cd_4, source)],
        [],
    ).check_consistency()

    Parametrization([_NAC(entity, cd_3, source)], [], []).check_consistency()
    with pytest.raises(ParametrizationError):
        Parametrization(
            [_NAC(entity, cd_1, source), _NAC(entity, cd_5, source)],
            [AlternativeSection(entity.section, new_text, cd_6, source)],
            [],
        ).check_consistency()
    with pytest.raises(ParametrizationError):
        Parametrization([_NAC(entity, cd_1, source), _NAC(entity, cd_1, source)], [], []).check_consistency()


def test_group():
    assert _group([], lambda x: x) == {}
    assert _group([1, 2, 3, 4, 1], lambda x: x) == {1: [1, 1], 2: [2], 3: [3], 4: [4]}
    assert _group([1, 2, -1], lambda x: abs(x)) == {1: [1, -1], 2: [2]}
    assert _group([{'key': 'value'}, {}], lambda x: x.get('key', '')) == {'value': [{'key': 'value'}], '': [{}]}


def _simple_nac(condition: Condition) -> NonApplicationCondition:
    source = ConditionSource('', EntityReference(SectionReference((0, 1)), None))
    target = EntityReference(SectionReference((0,)), None)
    return _NAC(target, condition, source)


def test_extract_conditions():
    date_ = ParameterEnum.DATE_INSTALLATION.value
    dt_1 = datetime.now()
    dt_2 = dt_1 + timedelta(days=1)
    cd_1 = Range(date_, dt_1, dt_2)
    cd_2 = Greater(date_, dt_2)

    parametrization = Parametrization([], [], [])
    assert parametrization.extract_conditions() == []

    parametrization = Parametrization([_simple_nac(cd_1)], [], [])
    assert parametrization.extract_conditions() == [cd_1]

    parametrization = Parametrization([_simple_nac(cd_1), _simple_nac(cd_2)], [], [])
    assert parametrization.extract_conditions() == [cd_1, cd_2]
