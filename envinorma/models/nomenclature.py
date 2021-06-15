from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Tuple

from .am_metadata import AMMetadata
from .classement import Regime


def _is_increasing(list_: List[float]) -> bool:
    if not list_:
        return True
    for a, b in zip(list_, list_[1:]):
        if a >= b:
            return False
    return True


@dataclass(frozen=True)
class RubriqueSimpleThresholds:
    code: str
    thresholds: List[float]
    regimes: List[Regime]
    alineas: List[str]
    unit: str
    variable_name: str

    def __post_init__(self):
        if len(self.thresholds) != len(self.regimes):
            raise ValueError(
                f'Expecting thresholds and regimes to have same lengths, received {self.thresholds} and {self.regimes}'
            )
        if not _is_increasing(self.thresholds):
            raise ValueError(f'Expecting increasing thresholds, received {self.thresholds}')

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'RubriqueSimpleThresholds':
        dict_ = dict_.copy()
        dict_['regimes'] = [Regime(rg) for rg in dict_['regimes']]
        dict_['code'] = str(dict_['code'])
        return RubriqueSimpleThresholds(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        res['regimes'] = [rg.value for rg in self.regimes]
        return res


@dataclass
class Nomenclature:
    am_metadata_list: List[AMMetadata]
    simple_thresholds: Dict[str, RubriqueSimpleThresholds]
    rubrique_and_regime_to_am: Dict[Tuple[str, Regime], List[AMMetadata]] = field(init=False)

    def __post_init__(self):
        self.rubrique_and_regime_to_am = {}
        for md in self.am_metadata_list:
            for classement in md.classements:
                pair = (classement.rubrique, classement.regime)
                if pair not in self.rubrique_and_regime_to_am:
                    self.rubrique_and_regime_to_am[pair] = []
                self.rubrique_and_regime_to_am[pair].append(md)

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'Nomenclature':
        dict_ = dict_.copy()
        dict_['am_metadata_list'] = [AMMetadata.from_dict(dc) for dc in dict_['am_metadata_list']]
        dict_['simple_thresholds'] = {
            str(id_): RubriqueSimpleThresholds.from_dict(dc) for id_, dc in dict_['simple_thresholds'].items()
        }
        return Nomenclature(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        del res['rubrique_and_regime_to_am']
        res['am_metadata_list'] = [md.to_dict() for md in self.am_metadata_list]
        res['simple_thresholds'] = {id_: ts.to_dict() for id_, ts in self.simple_thresholds.items()}
        return res
