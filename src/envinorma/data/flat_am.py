import json
from dataclasses import dataclass
from typing import List, Optional

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
    enriched_from_id: Optional[str]

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
            if self.enriched_from_id:
                assert is_probably_cid(self.enriched_from_id)
        except AssertionError:
            print(self)
            raise


@dataclass
class FlatSection:
    id: str
    rank: int
    title: str
    level: int
    active: bool
    modified: bool
    warnings: str
    reference_str: str
    previous_version: str
    arrete_id: str

    def __post_init__(self):
        for key, type_ in self.__annotations__.items():
            if not isinstance(getattr(self, key), type_):
                raise ValueError(f'Expecting field {key} to be of type {type_}. Got {getattr(self, key)}')
        assert is_probably_cid(self.arrete_id), self.arrete_id


@dataclass
class FlatAlinea:
    id: str
    rank: int
    active: bool
    text: str
    table: str
    section_id: str

    def __post_init__(self):
        for key, type_ in self.__annotations__.items():
            if not isinstance(getattr(self, key), type_):
                raise ValueError(f'Expecting field {key} to be of type {type_}. Got {getattr(self, key)}')
        if self.table:
            Table.from_dict(json.loads(self.table))
