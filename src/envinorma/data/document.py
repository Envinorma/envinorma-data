from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, Optional


class DocumentType(Enum):
    AP = 'Arrêté préfectoral'
    RAPPORT = 'Rapport'
    VISITE = 'Visite'
    APMED = 'Arrêté de mise en demeure'
    SANCTION = 'Arrêté de sanction'
    AUTRE = 'Autre'
    SUITE = "Suite d'inspection"
    INFO_PUBLIC = 'Information du public (DI Seveso art. 14)'


@dataclass
class Document:
    date: Optional[date]
    type: DocumentType
    description: str
    url: str
    s3ic_id: str

    @classmethod
    def from_georisques_dict(cls, dict_: Dict[str, Any], s3ic_id: str) -> 'Document':
        dict_['type'] = DocumentType(dict_['typeDoc'])
        dict_['date'] = date.fromisoformat(dict_['dateDoc']) if dict_['dateDoc'] else None
        return cls(
            date=dict_['date'],
            type=dict_['type'],
            description=dict_['descriptionDoc'],
            url=dict_['urlDoc'],
            s3ic_id=s3ic_id,
        )

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Document':
        dict_['type'] = DocumentType(dict_['type'])
        dict_['date'] = date.fromisoformat(dict_['date']) if dict_['date'] else None
        return cls(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['type'] = self.type.value
        if self.date:
            res['date'] = str(self.date)
        return res
