from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from envinorma.models.classement import Classement


class AMState(Enum):
    VIGUEUR = 'VIGUEUR'
    ABROGE = 'ABROGE'
    DELETED = 'DELETED'


class AMSource(Enum):
    LEGIFRANCE = 'LEGIFRANCE'
    AIDA = 'AIDA'


@dataclass
class AMMetadata:
    cid: str
    aida_page: str
    title: str
    classements: List[Classement]
    state: AMState
    date_of_signature: date
    source: AMSource
    nor: Optional[str] = None
    reason_deleted: Optional[str] = None

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'AMMetadata':
        dict_ = dict_.copy()
        dict_['aida_page'] = str(dict_['aida_page'])
        dict_['state'] = AMState(dict_['state'])
        dict_['source'] = AMSource(dict_['source'])
        date_of_signature = date.fromtimestamp(dict_['date_of_signature'])
        dict_['date_of_signature'] = date_of_signature
        dict_['classements'] = [Classement.from_dict(classement) for classement in dict_['classements']]
        return AMMetadata(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        dict_ = asdict(self)
        dict_['state'] = self.state.value
        dict_['source'] = self.source.value
        dict_['date_of_signature'] = int(datetime.fromordinal(self.date_of_signature.toordinal()).timestamp())
        dict_['classements'] = [classement.to_dict() for classement in self.classements]
        return dict_
