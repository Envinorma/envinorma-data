from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from envinorma.data import Regime


class ParameterType(Enum):
    DATE = 'DATE'
    REGIME = 'REGIME'
    BOOLEAN = 'BOOLEAN'
    RUBRIQUE = 'RUBRIQUE'
    REAL_NUMBER = 'REAL_NUMBER'
    STRING = 'STRING'

    def __repr__(self):
        return f'ParameterType("{self.value}")'


@dataclass(eq=True, frozen=True)
class Parameter:
    id: str
    type: ParameterType

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Parameter':
        return Parameter(dict_['id'], ParameterType(dict_['type']))


class ParameterEnum(Enum):
    DATE_AUTORISATION = Parameter('date-d-autorisation', ParameterType.DATE)
    DATE_DECLARATION = Parameter('date-d-declaration', ParameterType.DATE)
    DATE_ENREGISTREMENT = Parameter('date-d-enregistrement', ParameterType.DATE)
    DATE_INSTALLATION = Parameter('date-d-installation', ParameterType.DATE)
    REGIME = Parameter('regime', ParameterType.REGIME)
    RUBRIQUE = Parameter('rubrique', ParameterType.RUBRIQUE)
    RUBRIQUE_QUANTITY = Parameter('quantite-rubrique', ParameterType.REAL_NUMBER)
    ALINEA = Parameter('alinea', ParameterType.STRING)

    def __repr__(self):
        return f'ParameterEnum("{self.value}")'


class ConditionType(Enum):
    EQUAL = 'EQUAL'
    AND = 'AND'
    OR = 'OR'
    RANGE = 'RANGE'
    GREATER = 'GREATER'
    LITTLER = 'LITTLER'


def load_condition(dict_: Dict[str, Any]) -> 'Condition':
    type_ = ConditionType(dict_['type'])
    if type_ == ConditionType.AND:
        return AndCondition.from_dict(dict_)
    if type_ == ConditionType.OR:
        return OrCondition.from_dict(dict_)
    if type_ == ConditionType.EQUAL:
        return Equal.from_dict(dict_)
    if type_ == ConditionType.GREATER:
        return Greater.from_dict(dict_)
    if type_ == ConditionType.LITTLER:
        return Littler.from_dict(dict_)
    if type_ == ConditionType.RANGE:
        return Range.from_dict(dict_)
    raise ValueError(f'Unknown condition type {type_}')


@dataclass
class AndCondition:
    conditions: List['Condition']
    type: ConditionType = ConditionType.AND

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['conditions'] = [cd.to_dict() for cd in self.conditions]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AndCondition':
        return AndCondition([load_condition(cd) for cd in dict_['conditions']])


@dataclass
class OrCondition:
    conditions: List['Condition']
    type: ConditionType = ConditionType.OR

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['conditions'] = [cd.to_dict() for cd in self.conditions]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'OrCondition':
        return OrCondition([load_condition(cd) for cd in dict_['conditions']])


def parameter_value_to_dict(value: Any, type_: ParameterType) -> Any:
    if type_ == ParameterType.DATE:
        return int(value.timestamp())
    if type_ == ParameterType.REGIME:
        return value.value
    return value


def load_target(json_value: Any, type_: ParameterType) -> Any:
    if type_ == ParameterType.DATE:
        return datetime.fromtimestamp(json_value)
    if type_ == ParameterType.REGIME:
        return Regime(json_value)
    return json_value


@dataclass
class Littler:
    parameter: Parameter
    target: Any
    strict: bool = True
    type: ConditionType = ConditionType.LITTLER

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Littler':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Littler(parameter, load_target(dict_['target'], parameter.type), dict_['strict'])


@dataclass
class Greater:
    parameter: Parameter
    target: Any
    strict: bool = False
    type: ConditionType = ConditionType.GREATER

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Greater':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Greater(parameter, load_target(dict_['target'], parameter.type), dict_['strict'])


@dataclass
class Equal:
    parameter: Parameter
    target: Any
    type: ConditionType = ConditionType.EQUAL

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['target'] = parameter_value_to_dict(self.target, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Equal':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Equal(parameter, load_target(dict_['target'], parameter.type))


@dataclass
class Range:
    parameter: Parameter
    left: Any
    right: Any
    left_strict: bool = False
    right_strict: bool = True
    type: ConditionType = ConditionType.RANGE

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        res['parameter'] = self.parameter.to_dict()
        res['left'] = parameter_value_to_dict(self.left, self.parameter.type)
        res['right'] = parameter_value_to_dict(self.right, self.parameter.type)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Range':
        parameter = Parameter.from_dict(dict_['parameter'])
        return Range(
            Parameter.from_dict(dict_['parameter']),
            load_target(dict_['left'], parameter.type),
            load_target(dict_['right'], parameter.type),
            dict_['left_strict'],
            dict_['right_strict'],
        )


LeafConditions = (Equal, Range, Greater, Littler)  # for runtime type checking
LeafCondition = Union[Equal, Range, Greater, Littler]  # for typing

Conditions = (LeafCondition, AndCondition, OrCondition)
Condition = Union[LeafCondition, AndCondition, OrCondition]

MergeConditions = (AndCondition, OrCondition)
MergeCondition = Union[AndCondition, OrCondition]

MonoConditions = (Equal, Greater, Littler)
MonoCondition = Union[Equal, Greater, Littler]


def ensure_mono_condition(condition: Condition) -> MonoCondition:
    if isinstance(condition, (Equal, Greater, Littler)):
        return condition
    raise ValueError(f'Unexpected condition type : expecting type MonoCondition, got {type(condition)}')


def ensure_mono_conditions(conditions: List[Condition]) -> List[MonoCondition]:
    return [ensure_mono_condition(x) for x in conditions]


def check_condition(condition: Condition) -> None:
    if isinstance(condition, Equal):
        assert condition.type == ConditionType.EQUAL
    if isinstance(condition, Greater):
        assert condition.type == ConditionType.GREATER
    if isinstance(condition, Littler):
        assert condition.type == ConditionType.LITTLER
    if isinstance(condition, Range):
        assert condition.type == ConditionType.RANGE
    if isinstance(condition, AndCondition):
        assert condition.type == ConditionType.AND
    if isinstance(condition, OrCondition):
        assert condition.type == ConditionType.OR
    if isinstance(condition, (AndCondition, OrCondition)):
        for subcondition in condition.conditions:
            check_condition(subcondition)


def extract_leaf_conditions(condition: Condition, parameter: Parameter) -> List[LeafCondition]:
    if isinstance(condition, MergeConditions):
        return [
            cond for search_cond in condition.conditions for cond in extract_leaf_conditions(search_cond, parameter)
        ]
    if condition.parameter.id == parameter.id:
        return [condition]
    return []


def condition_to_str(condition: Condition) -> str:
    if isinstance(condition, Equal):
        return f'{condition.parameter.id} == {parameter_value_to_str(condition.target)}'
    if isinstance(condition, Littler):
        comp = '<' if condition.strict else '<='
        return f'{condition.parameter.id} {comp} {parameter_value_to_str(condition.target)}'
    if isinstance(condition, Greater):
        comp = '>' if condition.strict else '>='
        return f'{condition.parameter.id} {comp} {parameter_value_to_str(condition.target)}'
    if isinstance(condition, Range):
        left_comp = '<' if condition.left_strict else '<='
        right_comp = '<' if condition.right_strict else '<='
        return (
            f'{parameter_value_to_str(condition.left)} {left_comp} {condition.parameter.id} '
            f'{right_comp} {parameter_value_to_str(condition.right)}'
        )
    if isinstance(condition, AndCondition):
        return '(' + ') and ('.join([condition_to_str(cd) for cd in condition.conditions]) + ')'
    if isinstance(condition, OrCondition):
        return '(' + ') or ('.join([condition_to_str(cd) for cd in condition.conditions]) + ')'
    raise NotImplementedError(f'stringifying condition {condition} is not implemented yet.')


def parameter_value_to_str(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y')
    return str(value)


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


def _merge_words(words: List[str]) -> str:
    if not words:
        return ''
    if len(words) == 1:
        return words[0]
    return ', '.join(words[:-1]) + ' et ' + words[-1]


def _is_range_of_size_at_least_2(alineas: List[int]) -> bool:
    return len(set(alineas)) == max(alineas) - min(alineas) + 1 and len(set(alineas)) >= 3


def _alineas_prefix(alineas: List[int]) -> str:
    if not alineas:
        raise ValueError('Expecting at least one alinea.')
    if _is_range_of_size_at_least_2(alineas):
        return f'Les alinéas n°{min(alineas) + 1} à {max(alineas) + 1}'
    str_alineas = [str(i + 1) for i in sorted(alineas)]
    return f'Les alinéas n°{_merge_words(str_alineas)}'


def _generate_prefix(alineas: Optional[List[int]], modification: bool) -> str:
    if modification:
        return 'Ce paragraphe pourrait être modifié'
    if not alineas:
        return 'Ce paragraphe pourrait ne pas être applicable'
    if len(alineas) == 1:
        return f'L\'alinéa n°{alineas[0] + 1} de ce paragraphe pourrait ne pas être applicable'
    return f'{_alineas_prefix(alineas)} de ce paragraphe pourraient ne pas être applicables'


def generate_warning_missing_value(
    condition: Condition, parameter_values: Dict[Parameter, Any], alineas: Optional[List[int]], modification: bool
) -> str:
    # parameters = set(extract_parameters_from_condition(condition))
    # missing_parameters = sorted(
    #     [_parameter_id_to_str(param.id) for param in parameters if param not in parameter_values]
    # )
    # enumeration = _merge_words(missing_parameters)
    return (
        f'{_generate_prefix(alineas, modification)}. C\'est le cas '
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
            return f'l\'alinéa est {condition.target}'

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


def _stringify_all_conditions(conditions: List[Condition]) -> str:
    if any([not isinstance(cond, LeafConditions) for cond in conditions]):
        str_ = [condition_to_str(subcondition) for subcondition in conditions]
        return 'les conditions d\'application suivantes sont remplies : ' + ', '.join(str_)
    return _merge_words([_warning_leaf(_ensure_leaf_condition(cond)) for cond in conditions])


def _warning_merge_condition(condition: MergeCondition, parameter_values: Dict[Parameter, Any]) -> str:
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
    if isinstance(condition, MergeConditions):
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
    if isinstance(condition, MergeConditions):
        return _warning_merge_condition(condition, parameter_values)
    return _warning_leaf(condition)


def generate_inactive_warning(condition: Condition, parameter_values: Dict[Parameter, Any], all_alineas: bool) -> str:
    if all_alineas:
        prefix = '''Ce paragraphe ne s’applique pas à cette installation car'''
    else:
        prefix = '''Une partie de ce paragraphe ne s’applique pas à cette installation car'''
    return f'{prefix} {_inactive_warning(condition, parameter_values)}.'
