from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, Optional

from envinorma.data import Regime


class Seveso(Enum):
    NON_SEVESO = 'NS'
    SEUIL_HAUT = 'SH'
    SEUIL_BAS = 'SB'
    AS = 'AS'
    EMPTY = ''


class InstallationFamily(Enum):
    BOVINS = 'Bovins'
    INDUSTRIES = 'Industries'
    CARRIERES = 'Carrières'
    PORCS = 'Porcs'
    VOLAILLES = 'Volailles'


class ActivityStatus(Enum):
    EN_FONCTIONNEMENT = 'En fonctionnement'
    EN_CONSTRUCTION = 'En construction'
    CESSATION_DECLAREE = 'Cessation déclarée'
    A_L_ARRET = 'A l\'arrêt'
    RECOLEMENT_FAIT = 'Récolement fait'
    EMPTY = ''


@dataclass
class Installation:
    s3ic_id: str
    num_dep: str
    region: Optional[str]
    department: Optional[str]
    city: str
    name: str
    lat: float
    lon: float
    last_inspection: Optional[date]
    regime: Regime
    seveso: Seveso
    family: InstallationFamily
    active: ActivityStatus
    code_postal: str
    code_insee: str
    code_naf: str

    def __post_init__(self) -> None:
        assert len(self.num_dep) <= 4
        assert isinstance(self.s3ic_id, str)
        if self.last_inspection:
            if not isinstance(self.last_inspection, (date, datetime)):
                print(self.last_inspection)
            assert isinstance(self.last_inspection, (date, datetime))

    @staticmethod
    def from_georisques_dict(dict_: Dict[str, Any]) -> 'Installation':
        return Installation(
            s3ic_id=dict_['properties']['code_s3ic'],
            num_dep=dict_['properties']['num_dep'],
            region=dict_['regionInst'],
            department=dict_['departementInst'],
            city=dict_['communeInst'],
            name=dict_['nomInst'],
            lat=dict_['geometry']['coordinates'][1],
            lon=dict_['geometry']['coordinates'][0],
            last_inspection=datetime.strptime(dict_['derInspection'], '%Y-%m-%d').date()
            if dict_['derInspection']
            else None,
            regime=Regime(dict_['properties']['regime']),
            seveso=Seveso(dict_['properties']['seveso']),
            family=InstallationFamily(dict_['properties']['famille_ic']),
            active=ActivityStatus(dict_['etatActiviteInst']),
            code_postal=dict_['codePostal'],
            code_insee=dict_['codeInsee'],
            code_naf=dict_['properties']['code_naf'],
        )

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.last_inspection:
            res['last_inspection'] = self.last_inspection.strftime('%Y-%m-%d')
        res['regime'] = self.regime.value
        res['seveso'] = self.seveso.value
        res['family'] = self.family.value
        res['active'] = self.active.value
        return res
