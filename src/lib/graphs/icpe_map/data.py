import pandas
from dataclasses import asdict, dataclass
from lib.graphs.utils import check_same_lengths
from typing import Any, Dict, List, Optional


@dataclass
class RubriquePerDepartments:
    rubrique: List[str]
    regime: List[Optional[str]]
    department: List[str]
    count: List[int]

    def __post_init__(self):
        check_same_lengths([self.rubrique, self.department, self.count, self.regime])

    def to_dataframe(self) -> pandas.DataFrame:
        return pandas.DataFrame(self.to_dict())

    def to_csv(self, filename: str) -> None:
        self.to_dataframe().to_csv(filename, index=False)

    @staticmethod
    def load_csv(filename: str) -> pandas.DataFrame:
        return pandas.read_csv(filename, dtype={'department': str, 'rubrique': str, 'regime': str})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'RubriquePerDepartments':
        return RubriquePerDepartments(**dict_)
