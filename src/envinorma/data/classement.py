from datetime import date
from enum import Enum
from typing import Optional

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
