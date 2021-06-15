from datetime import date, datetime
from typing import Any, Dict, List, Optional

from envinorma.models.classement import Regime

from .models.condition import (
    AndCondition,
    Condition,
    Equal,
    Greater,
    LeafCondition,
    LeafConditions,
    Littler,
    MergeCondition,
    MergeConditions,
    MergeType,
    OrCondition,
    Range,
)
from .models.parameter import Parameter, ParameterEnum, ParameterType, parameter_value_to_str

'''
Missing parameter warning
'''


def _parameter_id_to_str(parameter_id: str) -> str:
    if parameter_id == ParameterEnum.DATE_AUTORISATION.value.id:
        return 'la date d\'autorisation'
    if parameter_id == ParameterEnum.DATE_ENREGISTREMENT.value.id:
        return 'la date d\'enregistrement'
    if parameter_id == ParameterEnum.DATE_DECLARATION.value.id:
        return 'la date de déclaration'
    if parameter_id == ParameterEnum.DATE_INSTALLATION.value.id:
        return 'la date de mise en service'
    if parameter_id == ParameterEnum.REGIME.value.id:
        return 'le régime'
    if parameter_id == ParameterEnum.RUBRIQUE.value.id:
        return 'la rubrique'
    if parameter_id == ParameterEnum.ALINEA.value.id:
        return 'l\'alinéa'
    if parameter_id == ParameterEnum.RUBRIQUE_QUANTITY.value.id:
        return 'la quantité associée à la rubrique'
    return f'la valeur du paramètre {parameter_id}'


def _merge_words(words: List[str], merge_type: MergeType) -> str:
    if not words:
        return ''
    if len(words) == 1:
        return words[0]
    merge_word = 'et' if merge_type == 'AND' else 'ou'
    return ', '.join(words[:-1]) + f' {merge_word} ' + words[-1]


def _is_range_of_size_at_least_2(alineas: List[int]) -> bool:
    return len(set(alineas)) == max(alineas) - min(alineas) + 1 and len(set(alineas)) >= 3


def _alineas_prefix(alineas: List[int]) -> str:
    if not alineas:
        raise ValueError('Expecting at least one alinea.')
    if _is_range_of_size_at_least_2(alineas):
        return f'Les alinéas n°{min(alineas) + 1} à {max(alineas) + 1}'
    str_alineas = [str(i + 1) for i in sorted(alineas)]
    suffix = _merge_words(str_alineas, 'AND')
    return f'Les alinéas n°{suffix}'


def _generate_prefix(alineas: Optional[List[int]], modification: bool, whole_text: bool) -> str:
    if modification:
        return 'Ce paragraphe pourrait être modifié'
    if whole_text:
        return 'Cet arrêté pourrait ne pas être applicable'
    if not alineas:
        return 'Ce paragraphe pourrait ne pas être applicable'
    if len(alineas) == 1:
        return f'L\'alinéa n°{alineas[0] + 1} de ce paragraphe pourrait ne pas être applicable'
    return f'{_alineas_prefix(alineas)} de ce paragraphe pourraient ne pas être applicables'


def generate_warning_missing_value(
    condition: Condition,
    parameter_values: Dict[Parameter, Any],
    alineas: Optional[List[int]],
    modification: bool,
    whole_text: bool,
) -> str:
    return (
        f'{_generate_prefix(alineas, modification, whole_text)}. C\'est le cas '
        f'pour les installations dont {_modification_warning(condition, parameter_values)}.'
    )


def _manual_active_conditions(parameter_id: str, condition: LeafCondition) -> Optional[str]:
    for parameter in ParameterEnum:
        if parameter.value.type == ParameterType.DATE:
            prefix = _parameter_id_to_str(parameter_id)
            if parameter_id == parameter.value.id:
                if isinstance(condition, Greater):
                    return f'{prefix} est postérieure au ' + _date_to_human_str(condition.target)
                if isinstance(condition, Littler):
                    return f'{prefix} est antérieure au ' + _date_to_human_str(condition.target)
                if isinstance(condition, Range):
                    lf_dt = _date_to_human_str(condition.left)
                    rg_dt = _date_to_human_str(condition.right)
                    return f'{prefix} est postérieure au ' + lf_dt + ' et antérieure au ' + rg_dt

    if parameter_id == ParameterEnum.REGIME.value.id:
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

    if parameter_id == ParameterEnum.RUBRIQUE.value.id:
        if isinstance(condition, Equal):
            regime_str = condition.target
            return f'la rubrique est {condition.target}'

    if parameter_id == ParameterEnum.ALINEA.value.id:
        if isinstance(condition, Equal):
            regime_str = condition.target
            return f'l\'alinéa de classement est l\'alinéa {condition.target}'

    if parameter_id == ParameterEnum.RUBRIQUE_QUANTITY.value.id:
        prefix = 'la quantité associée à la rubrique'
        if isinstance(condition, Greater):
            return f'{prefix} est supérieure à {condition.target}'
        if isinstance(condition, Littler):
            return f'{prefix} est inférieure à {condition.target}'
        if isinstance(condition, Range):
            return f'{prefix} est comprise entre {condition.left} et {condition.right}'
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


'''
Modification to string
'''


def _ensure_leaf_condition(condition: Condition) -> LeafCondition:
    if not isinstance(condition, LeafConditions):
        raise ValueError(f'Expecting LeafCondition, got {type(condition)}')
    return condition


def _has_non_leaf_condition(conditions: List[Condition]) -> bool:
    return any([not isinstance(cond, LeafConditions) for cond in conditions])


def _stringify_all_conditions(conditions: List[Condition], merge_type: MergeType) -> str:
    if _has_non_leaf_condition(conditions):
        str_ = [subcondition.to_str() for subcondition in conditions]
        return 'les conditions d\'application suivantes sont remplies : ' + ', '.join(str_)
    return _merge_words([_warning_leaf(_ensure_leaf_condition(cond)) for cond in conditions], merge_type)


def _warning_merge_condition(condition: MergeCondition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, AndCondition):
        if len(condition.conditions) == 1:
            return _modification_warning(condition.conditions[0], parameter_values)
        return _stringify_all_conditions(condition.conditions, 'AND')
    assert isinstance(condition, OrCondition)
    fulfilled_conditions = [
        subcondition for subcondition in condition.conditions if subcondition.is_satisfied(parameter_values)
    ]
    if len(fulfilled_conditions) == 1:
        return _modification_warning(fulfilled_conditions[0], parameter_values)
    return _stringify_all_conditions(condition.conditions, 'OR')


def _modification_warning(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, MergeConditions):
        return _warning_merge_condition(condition, parameter_values)
    return _warning_leaf(condition)


def generate_modification_warning(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    prefix = '''Ce paragraphe a été modifié pour cette installation car'''
    return f'{prefix} {_modification_warning(condition, parameter_values)}.'


def _date_to_human_str(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.strftime('%d/%m/%Y')
    raise ValueError(f'Expecting datetime not {type(value)}')


'''
Inactive section to string
'''


def _inactive_warning(condition: Condition, parameter_values: Dict[Parameter, Any]) -> str:
    if isinstance(condition, MergeConditions):
        return _warning_merge_condition(condition, parameter_values)
    return _warning_leaf(condition)


def generate_inactive_warning(
    condition: Condition, parameter_values: Dict[Parameter, Any], all_alineas: bool, whole_text: bool
) -> str:
    if whole_text:
        prefix = 'Cet arrêté ne s\'applique pas à cette installation car'
    else:
        if all_alineas:
            prefix = '''Ce paragraphe ne s’applique pas à cette installation car'''
        else:
            prefix = '''Une partie de ce paragraphe ne s’applique pas à cette installation car'''
    return f'{prefix} {_inactive_warning(condition, parameter_values)}.'
