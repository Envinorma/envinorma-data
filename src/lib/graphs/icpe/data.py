import pandas
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict, List, Optional


@dataclass
class ICPESStat:
    num_dep: str
    region: str
    city: str
    last_inspection: Optional[date]
    regime: str
    seveso: str
    family: str
    active: bool
    code_postal: str
    code_naf: str
    nb_documents: int
    nb_ap: int
    nb_reports: int
    nb_sanctions: int
    nb_med: int
    nb_active_classements: int
    nb_inactive_classements: int
    rubriques: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'ICPESStat':
        return ICPESStat(**dict_)


@dataclass
class ICPEDataset:
    rows: List[ICPESStat]

    def to_dataframe(self) -> pandas.DataFrame:
        res = {}
        ordered_keys = ['region']
        dict_ = self.to_pandas_dict()
        for key in ordered_keys + list(dict_.keys() - set(ordered_keys)):
            res[key] = dict_[key]
        return pandas.DataFrame(res)

    def to_csv(self, filename: str) -> None:
        self.to_dataframe().to_csv(filename, index=False)

    @staticmethod
    def load_csv(filename: str) -> pandas.DataFrame:
        return pandas.read_csv(
            filename,
            dtype={
                'num_dep': str,
                'region': str,
                'city': str,
                'regime': str,
                'seveso': str,
                'family': str,
                'code_postal': str,
                'code_naf': str,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_pandas_dict(self) -> Dict[str, List[Any]]:
        if not self.rows:
            return {}
        keys = self.rows[0].to_dict().keys()
        dicts = [row.to_dict() for row in self.rows]
        return {key: [dict_[key] for dict_ in dicts] for key in keys}

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'ICPEDataset':
        return ICPEDataset(**dict_)


# import json
# import requests
# from tqdm import tqdm

# data = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/icpe.geojson'))
# ids = [doc['properties']['code_s3ic'].replace('.', '-') for doc in data['features']]
# res = json.load(open('/Users/remidelbouys/EnviNorma/brouillons/data/georisques_documents.json'))
# for i, id_ in enumerate(tqdm(ids, bar_format='{l_bar}{r_bar}')):
#     if id_ in res:
#         continue
#     if i in {100, 500, 1000, 10000, 30000}:
#         json.dump(
#             res,
#             open('/Users/remidelbouys/EnviNorma/brouillons/data/georisques_documents.json', 'w'),
#             ensure_ascii=False,
#         )
#     try:
#         response = requests.get(
#             f'https://www.georisques.gouv.fr/webappReport/ws/installations/etablissement/{id_}/texte'
#         )
#         res[id_] = response.json()
#     except Exception as e:
#         print(id_, response.content.decode())

# json.dump(res, open('/Users/remidelbouys/EnviNorma/brouillons/data/georisques_documents.json', 'w'), ensure_ascii=False)