from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict

from .regime import Regime


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


def dump_parameter_value(value: Any, type_: ParameterType) -> Any:
    if type_ == ParameterType.DATE:
        if isinstance(value, datetime):
            value = value.date()
        return str(value)
    if type_ == ParameterType.REGIME:
        return value.value
    return value


def load_parameter_value(json_value: Any, type_: ParameterType) -> Any:
    if type_ == ParameterType.DATE:
        if isinstance(json_value, int):
            date_ = datetime.fromtimestamp(json_value).date()
        else:
            date_ = date.fromisoformat(json_value)
        return date_
    if type_ == ParameterType.REGIME:
        return Regime(json_value)
    return json_value


def parameter_value_to_str(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime('%d/%m/%Y')
    return str(value)
