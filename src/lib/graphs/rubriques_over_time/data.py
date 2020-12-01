import pandas
from dataclasses import asdict, dataclass
from datetime import datetime
from lib.graphs.utils import check_same_lengths
from typing import Any, Dict, List


@dataclass
class RubriqueOverTimeDataset:
    rubriques: List[str]
    years: List[int]
    departments: List[str]
    occurrences: List[int]

    def __post_init__(self):
        check_same_lengths([self.rubriques, self.years, self.departments, self.occurrences])

    def to_dataframe(self) -> pandas.DataFrame:
        return pandas.DataFrame(self.to_dict())

    def to_csv(self, filename: str) -> None:
        self.to_dataframe().to_csv(filename, index=False)

    @staticmethod
    def load_csv(filename: str) -> pandas.DataFrame:
        return pandas.read_csv(filename, dtype={'departments': str, 'rubriques': str})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'RubriqueOverTimeDataset':
        return RubriqueOverTimeDataset(**dict_)
