from dataclasses import asdict, dataclass
from typing import Any, Dict, List

import pandas


@dataclass
class TableStat:
    nb_rows: int
    max_nb_cols: int
    nb_headers: int
    has_headers_not_at_the_top: bool
    am_cid: str
    max_colspan: int
    max_rowspan: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'TableStat':
        return TableStat(**dict_)


@dataclass
class TablesDataset:
    tables: List[TableStat]

    def to_dataframe(self) -> pandas.DataFrame:
        return pandas.DataFrame(self.to_pandas_dict())

    def to_csv(self, filename: str) -> None:
        self.to_dataframe().to_csv(filename, index=False)

    @staticmethod
    def load_csv(filename: str) -> pandas.DataFrame:
        return pandas.read_csv(filename, dtype={'departments': str, 'rubriques': str})

    def to_dict(self) -> Dict[str, Any]:
        return {'tables': table.to_dict() for table in self.tables}

    def to_pandas_dict(self) -> Dict[str, List[Any]]:
        if not self.tables:
            return {}
        keys = self.tables[0].to_dict().keys()
        dicts = [table.to_dict() for table in self.tables]
        return {key: [dict_[key] for dict_ in dicts] for key in keys}

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'TablesDataset':
        return TablesDataset(**dict_)
