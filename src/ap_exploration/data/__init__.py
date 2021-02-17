from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

from envinorma.structure import TextElement, TextElements, load_text_element


class PrescriptionStatus(Enum):
    EN_VIGUEUR = 'En vigueur'
    MODIFIEE = 'Modifiée'
    SUPPRIMEE = 'Supprimée'

    def __repr__(self) -> str:
        return self.value

    def __str__(self) -> str:
        return self.value


@dataclass
class Prescription:
    ap_id: str
    title: str
    content: List[TextElement]
    status: PrescriptionStatus
    modifier_ap_id: Optional[str] = None
    reason_modified: Optional[str] = None

    def __post_init__(self):
        for element in self.content:
            assert isinstance(element, TextElements)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['status'] = self.status.value
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Prescription':
        dict_ = dict_.copy()
        dict_['content'] = [load_text_element(element) for element in dict_['content']]
        dict_['status'] = PrescriptionStatus(dict_['status'])
        return cls(**dict_)


class ActeState(Enum):
    EN_PROJET = 'En projet'
    EN_VIGUEUR = 'En vigueur'
    ABROGE = 'Abrogé'
    ANNULE = 'Annulé'
    ABANDONNE = 'Abandonné'
    PARTIELLEMENT_ABROGE = 'Partiellement abrogé'

    def __repr__(self):
        return self.value


class ActeType(Enum):
    AP_AUTORISATION_AVEC_ENQUETE_PUBLIQUE = "Arrêtés préfectoraux d'autorisation avec enquête publique"
    AP_A_DUREE_LIMITEE_AVEC_ENQUETE_PUBLIQUE = "Arrêtés préfectoraux à durée limitée avec enquête publique"
    AP_D_AUTORISATION_TEMPORAIRE = "Arrêtés préfectoraux d'autorisation temporaire"
    AP_DE_PRESCRIPTIONS_COMPLEMENTAIRES = "Arrêtés préfectoraux de prescriptions complémentaires"
    AP_DE_PRESCRIPTIONS_SPECIALES = "Arrêtés préfectoraux de prescriptions spéciales"
    DECISIONS_PRENANT_ACTE_DU_BENEFICE_DE_L_ANTERIORITE = "Décisions prenant acte du bénéfice de l'antériorité"
    NOTIFICATION_CESSATION_ACTIVITE = "Notification de la cessation d'activité"
    ELEMENTS_CONCERNANT_EXISTENCE_D_UNE_ACTIVITE = "Eléments concernant l'existence d'une activité"
    ARRETES_PREFECTORAUX_D_URGENCE = "Arrêtés préfectoraux d'urgence"
    RECEPISSE_DE_DECLARATION = "Récépissé de déclaration"
    ACTE_FICTIF_D_IMPORTATION = "Acte fictif d'importation"
    ARRETES_PREFECTORAUX_D_ENREGISTREMENT = "Arrêtés préfectoraux d'enregistrement"

    def __repr__(self):
        return self.value

    def short(self) -> str:
        if self == self.AP_AUTORISATION_AVEC_ENQUETE_PUBLIQUE:
            return 'AP (EP)'
        if self == self.AP_A_DUREE_LIMITEE_AVEC_ENQUETE_PUBLIQUE:
            return 'AP durée limitée (EP)'
        if self == self.AP_D_AUTORISATION_TEMPORAIRE:
            return 'AP autor. temp.'
        if self == self.AP_DE_PRESCRIPTIONS_COMPLEMENTAIRES:
            return 'APC'
        if self == self.AP_DE_PRESCRIPTIONS_SPECIALES:
            return 'AP prescriptions spéciales'
        if self == self.DECISIONS_PRENANT_ACTE_DU_BENEFICE_DE_L_ANTERIORITE:
            return 'AP bénéfice antériorité'
        if self == self.NOTIFICATION_CESSATION_ACTIVITE:
            return 'Notif. cess. activité'
        if self == self.ELEMENTS_CONCERNANT_EXISTENCE_D_UNE_ACTIVITE:
            return 'Elements existence activité'
        if self == self.ARRETES_PREFECTORAUX_D_URGENCE:
            return 'AP urgence'
        if self == self.RECEPISSE_DE_DECLARATION:
            return 'Récépissé déclaration'
        if self == self.ACTE_FICTIF_D_IMPORTATION:
            return 'Acte fictif importation'
        if self == self.ARRETES_PREFECTORAUX_D_ENREGISTREMENT:
            return 'AP, enregistrement'
        raise NotImplementedError(self)


def _build_s3ic_id(code_base: int, code_etablissement: int) -> str:
    return '.'.join([('0' * 5 + str(code_base))[-4:], ('0' * 5 + str(code_etablissement))[-5:]])


@dataclass(eq=True, unsafe_hash=True)
class Etablissement:
    id: str
    nom_usuel: str
    code_base: int
    code_etab: int
    code_s3ic: str = field(init=False)

    def __post_init__(self):
        self.code_s3ic = _build_s3ic_id(self.code_base, self.code_etab)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Etablissement':
        if 'code_s3ic' in dict_:
            del dict_['code_s3ic']
        return cls(**dict_)


@dataclass
class Acte:
    id: str
    date_abrogation: Optional[date]
    date_acte: Optional[date]
    date_annulation: Optional[date]
    date_application: Optional[date]
    date_fin_validite: Optional[date]
    date_modification: Optional[date]
    reference_acte: str
    state: ActeState
    type: ActeType
    affaire_liee_id: str
    etablissement: Etablissement

    def __post_init__(self):
        assert isinstance(self.state, ActeState)
        assert isinstance(self.type, ActeType)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        date_keys = (
            'date_abrogation',
            'date_acte',
            'date_annulation',
            'date_application',
            'date_fin_validite',
            'date_modification',
        )
        for key in date_keys:
            res[key] = res[key].toordinal() if res[key] else None
        res['state'] = res['state'].value
        res['type'] = res['type'].value
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Acte':
        date_keys = (
            'date_abrogation',
            'date_acte',
            'date_annulation',
            'date_application',
            'date_fin_validite',
            'date_modification',
        )
        for key in date_keys:
            dict_[key] = date.fromordinal(dict_[key]) if dict_[key] else None
        dict_['state'] = ActeState(dict_['state'])
        dict_['type'] = ActeType(dict_['type'])
        dict_['etablissement'] = Etablissement.from_dict(dict_['etablissement'])
        return cls(**dict_)
