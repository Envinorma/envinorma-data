from datetime import datetime

from envinorma.data import Regime
from envinorma.parametrization.conditions import (
    AndCondition,
    Equal,
    Greater,
    Littler,
    OrCondition,
    ParameterEnum,
    Range,
    _alineas_prefix,
    _generate_prefix,
    _is_range_of_size_at_least_2,
    _merge_words,
    _parameter_id_to_str,
    generate_inactive_warning,
    generate_modification_warning,
    generate_warning_missing_value,
)


def test_merge_words():
    assert _merge_words([], 'AND') == ''
    assert _merge_words(['foo'], 'AND') == 'foo'
    assert _merge_words(['foo', 'bar'], 'AND') == 'foo et bar'
    assert _merge_words(['foo', 'bar', 'baz'], 'AND') == 'foo, bar et baz'
    assert _merge_words(['foo', 'bar', 'baz', 'etc'], 'AND') == 'foo, bar, baz et etc'
    assert _merge_words(['foo', 'bar', 'baz', 'etc'], 'OR') == 'foo, bar, baz ou etc'


def test_generate_warning_missing_value():
    parameter = ParameterEnum.DATE_AUTORISATION.value
    parameter_regime = ParameterEnum.REGIME.value
    date_1 = datetime(2018, 1, 1)
    date_2 = datetime(2019, 1, 1)
    condition_1 = Greater(parameter, date_1, False)
    condition_3 = Littler(parameter, date_2, True)
    condition_regime = Equal(parameter_regime, Regime.A)

    exp = (
        f'Ce paragraphe pourrait être modifié. C\'est le cas pour les installations dont la date '
        'd\'autorisation est antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    assert generate_warning_missing_value(AndCondition([condition_3, condition_regime]), {}, None, True) == exp
    exp = (
        f'Ce paragraphe pourrait être modifié. C\'est le cas pour les installations dont la date'
        ' d\'autorisation est postérieure au 01/01/2018, la date '
        'd\'autorisation est antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    assert (
        generate_warning_missing_value(AndCondition([condition_1, condition_3, condition_regime]), {}, None, True)
        == exp
    )

    exp = (
        f'Ce paragraphe pourrait ne pas être applicable. C\'est le cas pour les installations dont la date'
        ' d\'autorisation est postérieure au 01/01/2018, la date '
        'd\'autorisation est antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    assert (
        generate_warning_missing_value(AndCondition([condition_1, condition_3, condition_regime]), {}, None, False)
        == exp
    )

    exp = (
        f'Les alinéas n°5 à 7 de ce paragraphe pourraient ne pas être applicables. C\'est le cas pour les installations dont la date'
        ' d\'autorisation est postérieure au 01/01/2018, la date '
        'd\'autorisation est antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    assert (
        generate_warning_missing_value(AndCondition([condition_1, condition_3, condition_regime]), {}, [4, 5, 6], False)
        == exp
    )

    exp = (
        f'Ce paragraphe pourrait être modifié. C\'est le cas pour les installations dont la date d\''
        'autorisation est antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    val = {parameter: datetime.now()}
    assert generate_warning_missing_value(AndCondition([condition_3, condition_regime]), val, None, True) == exp

    exp = (
        f'Ce paragraphe pourrait être modifié. C\'est le cas pour les installations dont la date d\'autorisation'
        ' est antérieure au 01/01/2019 et le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.E}
    assert generate_warning_missing_value(AndCondition([condition_3, condition_regime]), val, None, True) == exp

    exp = (
        f'Ce paragraphe pourrait être modifié. C\'est le cas pour les installations dont la date d\'autorisation'
        ' est antérieure au 01/01/2019 ou le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.E}
    assert generate_warning_missing_value(OrCondition([condition_3, condition_regime]), val, None, True) == exp

    exp = (
        f'Ce paragraphe pourrait être modifié. C\'est le cas pour les installations dont la date d\'autorisation'
        ' est antérieure au 01/01/2019 ou le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.E}
    assert generate_warning_missing_value(OrCondition([condition_3, condition_regime]), val, None, True) == exp


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
        'la date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019 ou le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.A, parameter: datetime(2018, 1, 5)}
    assert generate_inactive_warning(OrCondition([condition_2, condition_regime]), val, True) == exp

    exp = (
        'Ce paragraphe ne s’applique pas à cette installation car '
        'la date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019.'
    )
    val = {parameter_regime: Regime.E, parameter: datetime(2018, 1, 5)}
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
        ' la date d\'autorisation est postérieure au 01/01/2018 et antérieure au 01/01/2019 ou le régime est à autorisation.'
    )
    val = {parameter_regime: Regime.A, parameter: datetime(2018, 1, 5)}
    assert generate_modification_warning(OrCondition([condition_2, condition_regime]), val) == exp


def test_parameter_id_to_str():
    for parameter in ParameterEnum:
        res = _parameter_id_to_str(parameter.value.id)
        assert not res.startswith('la valeur du paramètre')  # otherwise means no custom value was defined


def test_alineas_prefix():
    assert _alineas_prefix([0, 1]) == 'Les alinéas n°1 et 2'
    assert _alineas_prefix([0, 2]) == 'Les alinéas n°1 et 3'
    assert _alineas_prefix([0, 1, 2]) == 'Les alinéas n°1 à 3'
    assert _alineas_prefix([1, 2, 4, 5, 3]) == 'Les alinéas n°2 à 6'
    assert _alineas_prefix([1, 2, 4, 5, 3, 7]) == 'Les alinéas n°2, 3, 4, 5, 6 et 8'


def test_generate_prefix():
    assert _generate_prefix(None, False) == 'Ce paragraphe pourrait ne pas être applicable'
    assert _generate_prefix(None, True) == 'Ce paragraphe pourrait être modifié'
    assert _generate_prefix([0], False) == 'L\'alinéa n°1 de ce paragraphe pourrait ne pas être applicable'
    assert _generate_prefix([0, 1], False) == 'Les alinéas n°1 et 2 de ce paragraphe pourraient ne pas être applicables'
    assert _generate_prefix([0, 2], False) == 'Les alinéas n°1 et 3 de ce paragraphe pourraient ne pas être applicables'
    assert (
        _generate_prefix([0, 1, 2], False) == 'Les alinéas n°1 à 3 de ce paragraphe pourraient ne pas être applicables'
    )
    assert (
        _generate_prefix([1, 2, 4, 5, 3], False)
        == 'Les alinéas n°2 à 6 de ce paragraphe pourraient ne pas être applicables'
    )
    assert (
        _generate_prefix([1, 2, 4, 5, 3, 7], False)
        == 'Les alinéas n°2, 3, 4, 5, 6 et 8 de ce paragraphe pourraient ne pas être applicables'
    )


def test_is_range_of_size_at_least_2():
    assert not _is_range_of_size_at_least_2([0])
    assert not _is_range_of_size_at_least_2([0, 1])
    assert not _is_range_of_size_at_least_2([0, 2])
    assert _is_range_of_size_at_least_2([0, 1, 2])
    assert _is_range_of_size_at_least_2([1, 2, 4, 5, 3])
    assert not _is_range_of_size_at_least_2([1, 2, 4, 5, 3, 7])
