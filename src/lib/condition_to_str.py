from datetime import datetime
from typing import Any, Dict, KeysView, List, Optional, Union
from lib.parametrization import (
    AndCondition,
    Condition,
    Equal,
    Greater,
    LeafCondition,
    Littler,
    OrCondition,
    Parameter,
    ParameterEnum,
    Range,
    condition_to_str,
    parameter_value_to_str,
)
from lib.data import Regime

_MergeCondition = Union[AndCondition, OrCondition]


def extract_parameters_from_condition(condition: Condition) -> List[Parameter]:
    if isinstance(condition, (OrCondition, AndCondition)):
        return [param for cd in condition.conditions for param in extract_parameters_from_condition(cd)]
    return [condition.parameter]


def _is_satisfied_range(condition: Range, parameter_value: Any) -> bool:
    if condition.left_strict and condition.right_strict:
        return condition.left < parameter_value < condition.right
    if condition.left_strict and not condition.right_strict:
        return condition.left < parameter_value <= condition.right
    if not condition.left_strict and condition.right_strict:
        return condition.left <= parameter_value < condition.right
    if not condition.left_strict and not condition.right_strict:
        return condition.left <= parameter_value <= condition.right
    raise NotImplementedError()


def _is_satisfied_leaf(condition: LeafCondition, parameter_values: Dict[Parameter, Any]) -> bool:
    if condition.parameter not in parameter_values:
        return False
    value = parameter_values[condition.parameter]
    if isinstance(condition, Littler):
        return (value < condition.target) if condition.strict else (value <= condition.target)
    if isinstance(condition, Greater):
        return (value > condition.target) if condition.strict else (value >= condition.target)
    if isinstance(condition, Equal):
        return value == condition.target
    if isinstance(condition, Range):
        return _is_satisfied_range(condition, parameter_values[condition.parameter])
    raise NotImplementedError(f'Condition {type(condition)} not implemented yet.')


def is_satisfied(condition: Condition, parameter_values: Dict[Parameter, Any]) -> bool:
    if isinstance(condition, AndCondition):
        return all([is_satisfied(cd, parameter_values) for cd in condition.conditions])
    if isinstance(condition, OrCondition):
        return any([is_satisfied(cd, parameter_values) for cd in condition.conditions])
    return _is_satisfied_leaf(condition, parameter_values)


'''
Missing parameter warning
'''


def _parameter_id_to_str(parameter_id: str) -> str:
    if parameter_id == ParameterEnum.DATE_AUTORISATION.value.id:
        return 'la date d\'autorisation'
    if parameter_id == ParameterEnum.DATE_INSTALLATION.value.id:
        return 'la date de mise en service'
    if parameter_id == ParameterEnum.REGIME.value.id:
        return 'le régime'
    return f'la valeur du paramètre {parameter_id}'


def _merge_words(words: List[str]) -> str:
    if not words:
        return ''
    if len(words) == 1:
        return words[0]
    return ', '.join(words[:-1]) + ' et ' + words[-1]


def generate_warning_missing_value(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    parameters = set(extract_parameters_from_condition(condition))
    missing_parameters = sorted(
        [_parameter_id_to_str(param.id) for param in parameters if param not in parameter_values]
    )
    enumeration = _merge_words(missing_parameters)
    return f'Ce paragraphe pourrait être modifié selon {enumeration} de l\'installation.'


'''
Modification to string
'''


def _manual_active_conditions(parameter_id: str, condition: LeafCondition) -> Optional[str]:
    date_autorisation = ParameterEnum.DATE_AUTORISATION.value.id
    if parameter_id == date_autorisation:
        if isinstance(condition, Greater):
            return 'la date d\'autorisation est postérieure au ' + _date_to_human_str(condition.target)
        if isinstance(condition, Littler):
            return 'la date d\'autorisation est antérieure au ' + _date_to_human_str(condition.target)
        if isinstance(condition, Range):
            lf_dt = _date_to_human_str(condition.left)
            rg_dt = _date_to_human_str(condition.right)
            return 'la date d\'autorisation est postérieure au ' + lf_dt + ' et antérieure au ' + rg_dt
    regime = ParameterEnum.REGIME.value.id

    date_installation = ParameterEnum.DATE_INSTALLATION.value.id
    if parameter_id == date_installation:
        if isinstance(condition, Greater):
            return 'la date de mise en service est postérieure au ' + _date_to_human_str(condition.target)
        if isinstance(condition, Littler):
            return 'la date de mise en service est antérieure au ' + _date_to_human_str(condition.target)
        if isinstance(condition, Range):
            lf_dt = _date_to_human_str(condition.left)
            rg_dt = _date_to_human_str(condition.right)
            return 'la date de mise en service est postérieure au ' + lf_dt + ' et antérieure au ' + rg_dt

    if parameter_id == regime:
        if isinstance(condition, Equal):
            if condition.target == Regime.A:
                regime_str = 'autorisation'
            elif condition.target == Regime.E:
                regime_str = 'enregistrement'
            elif condition.target in (Regime.D, Regime.DC):
                regime_str = 'déclaration'
            else:
                regime_str = condition.target.value
            return f'le régime est à {regime_str}'
    return None


def _warning_leaf(condition: LeafCondition) -> str:
    parameter = condition.parameter
    manual = _manual_active_conditions(parameter.id, condition)
    if manual:
        return manual
    if isinstance(condition, Equal):
        return f'le paramètre {parameter.id} est égal à {parameter_value_to_str(condition.target)}'
    if isinstance(condition, Greater):
        return f'le paramètre {parameter.id} est supérieur à {parameter_value_to_str(condition.target)}'
    if isinstance(condition, Littler):
        return f'le paramètre {parameter.id} est inférieur à {parameter_value_to_str(condition.target)}'
    if isinstance(condition, Range):
        return (
            f'le paramètre {parameter.id} est entre {parameter_value_to_str(condition.left)} '
            f'et {parameter_value_to_str(condition.right)}'
        )
    raise NotImplementedError(f'stringifying condition {type(condition)} is not implemented yet.')


_LeafConditions = (Equal, Range, Greater, Littler)


def _ensure_leaf_condition(condition: Condition) -> LeafCondition:
    if not isinstance(condition, _LeafConditions):
        raise ValueError(f'Expecting LeafCondition, got {type(condition)}')
    return condition


def _stringify_all_conditions(conditions: List[Condition]) -> str:
    if any([not isinstance(cond, _LeafConditions) for cond in conditions]):
        str_ = [condition_to_str(subcondition) for subcondition in conditions]
        return 'les conditions d\'application suivantes sont remplies : ' + ', '.join(str_)
    return _merge_words([_warning_leaf(_ensure_leaf_condition(cond)) for cond in conditions])


def _warning_merge_condition(condition: _MergeCondition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, AndCondition):
        if len(condition.conditions) == 1:
            return _modification_warning(condition.conditions[0], parameter_values)
        return _stringify_all_conditions(condition.conditions)
    assert isinstance(condition, OrCondition)
    fulfilled_conditions = [
        subcondition for subcondition in condition.conditions if is_satisfied(subcondition, parameter_values)
    ]
    if len(fulfilled_conditions) == 1:
        return _modification_warning(fulfilled_conditions[0], parameter_values)
    return _stringify_all_conditions(fulfilled_conditions)


def _modification_warning(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, (AndCondition, OrCondition)):
        return _warning_merge_condition(condition, parameter_values)
    return _warning_leaf(condition)


def generate_modification_warning(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    prefix = '''Ce paragraphe a été modifié pour cette installation car'''
    return f'{prefix} {_modification_warning(condition, parameter_values)}.'


def _date_to_human_str(value: Any) -> str:
    if not isinstance(value, datetime):
        raise ValueError(f'Expecting datetime not {type(value)}')
    return value.strftime('%d/%m/%Y')


'''
Inactive section to string
'''


def _inactive_warning(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, (AndCondition, OrCondition)):
        return _warning_merge_condition(condition, parameter_values)
    return _warning_leaf(condition)


def generate_inactive_warning(condition: Condition, parameter_values: Dict[Parameter, Any], all_alineas: bool) -> str:
    if all_alineas:
        prefix = '''Ce paragraphe ne s’applique pas à cette installation car'''
    else:
        prefix = '''Une partie de ce paragraphe ne s’applique pas à cette installation car'''
    return f'{prefix} {_inactive_warning(condition, parameter_values)}.'
