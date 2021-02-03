from datetime import datetime

from lib.condition_to_str import (
    _merge_words,
    generate_inactive_warning,
    generate_modification_warning,
    generate_warning_missing_value,
)
from lib.data import Regime
from lib.parametrization import AndCondition, Equal, Greater, Littler, OrCondition, ParameterEnum, Range


def test_merge_words():
    assert _merge_words([]) == ''
    assert _merge_words(['foo']) == 'foo'
    assert _merge_words(['foo', 'bar']) == 'foo et bar'
    assert _merge_words(['foo', 'bar', 'baz']) == 'foo, bar et baz'
    assert _merge_words(['foo', 'bar', 'baz', 'etc']) == 'foo, bar, baz et etc'


def test_generate_warning_missing_value():
    parameter = ParameterEnum.DATE_AUTORISATION.value
    parameter_regime = ParameterEnum.REGIME.value
    date_1 = datetime(2018, 1, 1)
    date_2 = datetime(2019, 1, 1)
    condition_1 = Greater(parameter, date_1, False)
    condition_2 = Range(parameter, date_1, date_2, left_strict=False, right_strict=True)
    condition_3 = Littler(parameter, date_2, True)
    condition_regime = Equal(parameter_regime, Regime.A)

    exp = f'Ce paragraphe pourrait être modifié selon la date d\'autorisation et le régime de l\'installation.'
    assert generate_warning_missing_value(AndCondition([condition_3, condition_regime]), {}) == exp
    assert generate_warning_missing_value(AndCondition([condition_2, condition_3, condition_regime]), {}) == exp
    assert (
        generate_warning_missing_value(AndCondition([condition_1, condition_2, condition_3, condition_regime]), {})
        == exp
    )

    exp = f'Ce paragraphe pourrait être modifié selon le régime de l\'installation.'
    val = {parameter: datetime.now()}
    assert generate_warning_missing_value(AndCondition([condition_3, condition_regime]), val) == exp
    assert generate_warning_missing_value(AndCondition([condition_2, condition_3, condition_regime]), val) == exp
    assert (
        generate_warning_missing_value(AndCondition([condition_1, condition_2, condition_3, condition_regime]), val)
        == exp
    )

    exp = f'Ce paragraphe pourrait être modifié selon la date d\'autorisation de l\'installation.'
    val = {parameter_regime: Regime.E}
    assert generate_warning_missing_value(AndCondition([condition_3, condition_regime]), val) == exp
    assert generate_warning_missing_value(AndCondition([condition_2, condition_3, condition_regime]), val) == exp
    assert (
        generate_warning_missing_value(AndCondition([condition_1, condition_2, condition_3, condition_regime]), val)
        == exp
    )


def test_generate_inactive_warning():
    parameter = ParameterEnum.DATE_AUTORISATION.value
    parameter_regime = ParameterEnum.REGIME.value
    date_1 = datetime(2018, 1, 1)
    date_2 = datetime(2019, 1, 1)
    condition_2 = Range(parameter, date_1, date_2, left_strict=False, right_strict=True)
    condition_3 = Littler(parameter, date_2, True)
    condition_regime = Equal(parameter_regime, Regime.A)

    exp = (
        'Ce paragraphe ne s’applique pas à cette installation car '
        'la date d\'autorisation est antérieure au 01/01/2019.'
    )
    assert generate_inactive_warning(condition_3, {parameter: datetime(2016, 1, 1)}, True) == exp
    assert generate_inactive_warning(condition_3, {}, True) == exp

    exp = 'Une partie de ce paragraphe ne s’applique pas à cette installation car le régime est à autorisation.'
    assert generate_inactive_warning(condition_regime, {}, False) == exp
    val = {parameter: datetime(2016, 6, 1), parameter_regime: Regime.A}
    assert generate_inactive_warning(OrCondition([condition_2, condition_regime]), val, False) == exp

    exp = (
        'Ce paragraphe ne s’applique pas à cette installation car la'
        ' date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019.'
    )
    assert generate_inactive_warning(condition_2, {}, True) == exp
    assert generate_inactive_warning(AndCondition([condition_2]), {}, True) == exp
    val = {parameter_regime: Regime.E, parameter: datetime(2018, 6, 1)}
    assert generate_inactive_warning(OrCondition([condition_2, condition_regime]), val, True) == exp
    assert generate_inactive_warning(OrCondition([condition_2]), {parameter: datetime(2018, 6, 1)}, True) == exp

    exp = (
        'Ce paragraphe ne s’applique pas à cette installation car '
        'la date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.E, parameter: datetime(2016, 1, 1)}
    assert generate_inactive_warning(AndCondition([condition_2, condition_regime]), val, True) == exp
    assert generate_inactive_warning(AndCondition([condition_2, condition_regime]), {}, True) == exp

    exp = (
        'Ce paragraphe ne s’applique pas à cette installation car '
        'la date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.A, parameter: datetime(2018, 1, 5)}
    assert generate_inactive_warning(OrCondition([condition_2, condition_regime]), val, True) == exp


def test_generate_modification_warning():
    parameter = ParameterEnum.DATE_AUTORISATION.value
    parameter_regime = ParameterEnum.REGIME.value
    date_1 = datetime(2018, 1, 1)
    date_2 = datetime(2019, 1, 1)
    condition_2 = Range(parameter, date_1, date_2, left_strict=False, right_strict=True)
    condition_3 = Littler(parameter, date_2, True)
    condition_regime = Equal(parameter_regime, Regime.A)

    exp = (
        'Ce paragraphe a été modifié pour cette installation car la date d\'autorisation est antérieure au 01/01/2019.'
    )
    assert generate_modification_warning(condition_3, {parameter: datetime(2016, 1, 1)}) == exp
    assert generate_modification_warning(condition_3, {}) == exp

    exp = 'Ce paragraphe a été modifié pour cette installation car le régime est à autorisation.'
    assert generate_modification_warning(condition_regime, {}) == exp
    val = {parameter: datetime(2016, 6, 1), parameter_regime: Regime.A}
    assert generate_modification_warning(OrCondition([condition_2, condition_regime]), val) == exp

    exp = (
        'Ce paragraphe a été modifié pour cette installation car la'
        ' date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019.'
    )
    assert generate_modification_warning(condition_2, {}) == exp
    assert generate_modification_warning(AndCondition([condition_2]), {}) == exp
    val = {parameter_regime: Regime.E, parameter: datetime(2018, 6, 1)}
    assert generate_modification_warning(OrCondition([condition_2, condition_regime]), val) == exp
    assert generate_modification_warning(OrCondition([condition_2]), {parameter: datetime(2018, 6, 1)}) == exp

    exp = (
        'Ce paragraphe a été modifié pour cette installation car'
        ' la date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.E, parameter: datetime(2016, 1, 1)}
    assert generate_modification_warning(AndCondition([condition_2, condition_regime]), val) == exp
    assert generate_modification_warning(AndCondition([condition_2, condition_regime]), {}) == exp

    exp = (
        'Ce paragraphe a été modifié pour cette installation car'
        ' la date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.A, parameter: datetime(2018, 1, 5)}
    assert generate_modification_warning(OrCondition([condition_2, condition_regime]), val) == exp
