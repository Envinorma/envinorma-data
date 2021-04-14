import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from envinorma.data import ClassementWithAlineas, check_short_title, is_probably_cid
from envinorma.data.text_elements import Table
from envinorma.utils import str_to_date


@dataclass
class FlatArreteMinisteriel:
    id: int
    cid: str
    short_title: str
    title: str
    unique_version: bool
    installation_date_criterion_left: Optional[str]
    installation_date_criterion_right: Optional[str]
    aida_url: str
    legifrance_url: str
    classements_with_alineas: List[ClassementWithAlineas]
    enriched_from_id: Optional[int]

    def __post_init__(self):
        try:
            assert is_probably_cid(self.cid)
            check_short_title(self.short_title)
            assert len(self.title) >= 10
            if self.installation_date_criterion_left:
                str_to_date(self.installation_date_criterion_left)
            if self.installation_date_criterion_right:
                str_to_date(self.installation_date_criterion_right)
            assert len(self.aida_url) >= 10
            assert len(self.legifrance_url) >= 10
            assert len(self.classements_with_alineas) >= 1
            if self.enriched_from_id is not None:
                assert isinstance(self.enriched_from_id, int)
        except AssertionError:
            print(self)
            raise

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['classements_with_alineas'] = [cl.to_dict() for cl in self.classements_with_alineas]
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'FlatArreteMinisteriel':
        dict_ = dict_.copy()
        dict_['classements_with_alineas'] = [
            ClassementWithAlineas.from_dict(x) for x in dict_['classements_with_alineas']
        ]
        return cls(**dict_)


@dataclass
class FlatSection:
    id: int
    rank: int
    title: str
    level: int
    active: bool
    modified: bool
    warnings: str
    reference_str: str
    previous_version: str
    arrete_id: int

    def __post_init__(self):
        for key, type_ in self.__annotations__.items():
            if not isinstance(getattr(self, key), type_):
                raise ValueError(f'Expecting field {key} to be of type {type_}. Got {getattr(self, key)}')

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'FlatSection':
        return cls(**dict_)


@dataclass
class FlatAlinea:
    id: int
    rank: int
    active: bool
    text: str
    table: str
    section_id: int

    def __post_init__(self):
        for key, type_ in self.__annotations__.items():
            if not isinstance(getattr(self, key), type_):
                raise ValueError(f'Expecting field {key} to be of type {type_}. Got {getattr(self, key)}')
        if self.table:
            Table.from_dict(json.loads(self.table))

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'FlatAlinea':
        return cls(**dict_)
