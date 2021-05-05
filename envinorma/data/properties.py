from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LegifranceTextProperties:
    structure: str
    nb_articles: int
    nb_non_numbered_articles: int
    nb_lost_vu_lines: int


@dataclass
class TitleInconsistency:
    titles: List[str]
    parent_section_title: str
    inconsistency: str


@dataclass
class AMProperties:
    structure: str
    nb_sections: int
    nb_articles: int
    nb_tables: int
    nb_empty_articles: int
    title_inconsistencies: List[TitleInconsistency]


@dataclass
class TextProperties:
    legifrance: LegifranceTextProperties
    am: Optional[AMProperties]
