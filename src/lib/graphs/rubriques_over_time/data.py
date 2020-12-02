import pandas
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass
class RubriqueStat:
    rubrique: str
    year: int
    s3ic_base: str
    department: str
    active: str
    famille_nomenclature: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'RubriqueStat':
        return RubriqueStat(**dict_)


@dataclass
class RubriquesDataset:
    rows: List[RubriqueStat]

    def to_dataframe(self) -> pandas.DataFrame:
        return pandas.DataFrame(self.to_pandas_dict())

    def to_csv(self, filename: str) -> None:
        self.to_dataframe().to_csv(filename, index=False)

    @staticmethod
    def load_csv(filename: str) -> pandas.DataFrame:
        return pandas.read_csv(filename, dtype={'department': str, 'rubrique': str, 's3ic_base': str})

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_pandas_dict(self) -> Dict[str, List[Any]]:
        if not self.rows:
            return {}
        keys = self.rows[0].to_dict().keys()
        dicts = [row.to_dict() for row in self.rows]
        return {key: [dict_[key] for dict_ in dicts] for key in keys}

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'RubriquesDataset':
        return RubriquesDataset(**dict_)
