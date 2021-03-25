import json
from datetime import date
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel

from envinorma.data import Regime


class State(Enum):
    EN_PROJET = 'En projet'
    EN_FONCTIONNEMENT = 'En fonctionnement'
    A_L_ARRET = 'A l\'arrêt'
    REPRISE = 'Reprise'


_UNKNOWN_REGIME = 'unknown'


class DetailedRegime(Enum):
    NC = 'NC'
    D = 'D'
    DC = 'DC'
    A = 'A'
    S = 'S'
    _1 = '1'
    _2 = '2'
    _3 = '3'
    E = 'E'
    UNKNOWN = _UNKNOWN_REGIME

    def to_regime(self) -> Optional[Regime]:
        try:
            return Regime(self.value)
        except ValueError:
            return None

    def to_simple_regime(self) -> str:
        if self.value in ('A', 'E', 'D', 'NC'):
            return self.value
        if self == self.DC:
            return 'D'
        return DetailedRegime.UNKNOWN.value

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


class DetailedClassement(BaseModel):
    s3ic_id: str
    rubrique: str
    regime: DetailedRegime
    alinea: Optional[str]
    date_autorisation: Optional[date]
    state: Optional[State]
    regime_acte: Optional[DetailedRegime]
    alinea_acte: Optional[str]
    rubrique_acte: Optional[str]
    activite: Optional[str]
    volume: str
    unit: Optional[str]
    date_mise_en_service: Optional[date] = None
    last_substantial_modif_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.json())
