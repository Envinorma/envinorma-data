from dataclasses import dataclass, replace
from datetime import date
from typing import Dict, List, Optional, Set, Tuple

from envinorma.enriching import enrich
from envinorma.enriching.remove_null_applicabilities import remove_null_applicabilities
from envinorma.models.am_metadata import AMMetadata
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.classement import Classement, ClassementWithAlineas, Regime
from envinorma.parametrization.combinations import generate_exhaustive_combinations
from envinorma.utils import AM1510_IDS, ensure_not_none

from .apply_parameter_values import apply_parameter_values_to_am
from .models.parameter import ParameterEnum
from .models.parametrization import Combinations, Parametrization

AMVersions = Dict[Tuple[str, ...], ArreteMinisteriel]


def _extract_am_regime(classements: List[Classement]) -> Optional[Regime]:
    regimes: Set[Regime] = {classement.regime for classement in classements}
    if len(regimes) != 1:
        return None
    return list(regimes)[0]


def generate_versions(
    am: ArreteMinisteriel,
    parametrization: Parametrization,
    date_only: bool,
    combinations: Optional[Combinations] = None,
) -> Dict[Tuple[str, ...], ArreteMinisteriel]:
    if combinations is None:
        combinations = generate_exhaustive_combinations(parametrization, date_only, _extract_am_regime(am.classements))
    if not combinations:
        combinations = {(): {}}
    return {
        combination_name: apply_parameter_values_to_am(am, parametrization, parameter_values)
        for combination_name, parameter_values in combinations.items()
    }


def _manual_1510_post_process(am: ArreteMinisteriel, regime: str) -> ArreteMinisteriel:
    classements = am.classements
    new_classements = [cl for cl in classements if cl.regime.value == regime]
    if len(new_classements) != 1:
        raise ValueError(new_classements)
    classement = new_classements[0]
    new_classements_with_alineas = [ClassementWithAlineas(classement.rubrique, classement.regime, [])]
    new_id = f'{am.id}_{regime}'  # to avoid having duplicate ids
    return replace(am, classements=new_classements, classements_with_alineas=new_classements_with_alineas, id=new_id)


def _extract_regime(am_id: str, name: Tuple[str, ...]) -> Optional[str]:
    if am_id in AM1510_IDS:  # Hack for this very special AM
        assert name[0][:4] == 'reg_'
        return name[0][4]
    return None


def _post_process(am_id: str, am: ArreteMinisteriel, regime_str: Optional[str]) -> ArreteMinisteriel:
    if am_id in AM1510_IDS:  # Hack for this very special AM
        if regime_str is None:
            raise ValueError('Cannot add 1510 metadata: need regime but got None.')
        am = _manual_1510_post_process(am, regime_str)
    return am


def _generate_1510_combinations() -> Combinations:
    regime = ParameterEnum.REGIME.value
    date_ = ParameterEnum.DATE_INSTALLATION.value
    return {
        ('reg_A_no_date',): {regime: Regime.A},
        ('reg_A', 'date_before_2003'): {regime: Regime.A, date_: date(2000, 1, 1)},
        ('reg_A', 'date_between_2003_and_2017'): {regime: Regime.A, date_: date(2010, 1, 1)},
        ('reg_A', 'date_after_2017'): {regime: Regime.A, date_: date(2020, 1, 1)},
        ('reg_E_no_date',): {regime: Regime.E},
        ('reg_E', 'date_before_2003'): {regime: Regime.E, date_: date(2000, 1, 1)},
        ('reg_E', 'date_between_2003_and_2010'): {regime: Regime.E, date_: date(2006, 1, 1)},
        ('reg_E', 'date_between_2010_and_2017'): {regime: Regime.E, date_: date(2015, 1, 1)},
        ('reg_E', 'date_after_2017'): {regime: Regime.E, date_: date(2020, 1, 1)},
        ('reg_D_no_date',): {regime: Regime.D},
        ('reg_D', 'date_before_2009'): {regime: Regime.D, date_: date(2000, 1, 1)},
        ('reg_D', 'date_between_2009_and_2017'): {regime: Regime.D, date_: date(2010, 1, 1)},
        ('reg_D', 'date_after_2017'): {regime: Regime.D, date_: date(2020, 1, 1)},
    }


def _get_manual_combinations(am_id: str) -> Optional[Combinations]:
    if am_id in AM1510_IDS:
        return _generate_1510_combinations()
    return None


def _generate_versions_and_postprocess(
    am_id: str, am: Optional[ArreteMinisteriel], parametrization: Parametrization, metadata: AMMetadata
) -> Optional[AMVersions]:
    if not am:
        return None
    enriched_am = remove_null_applicabilities(am)
    manual_combinations = _get_manual_combinations(am_id)  # For AM 1510 mainly, none otherwise
    all_versions = generate_versions(enriched_am, parametrization, True, manual_combinations)
    return {
        name: _post_process(am_id, enrich(am_, metadata), _extract_regime(am_id, name))
        for name, am_ in all_versions.items()
    }


@dataclass
class AMWithVersions:
    base_am: Optional[ArreteMinisteriel]
    am_versions: Optional[AMVersions]


def generate_am_with_versions(
    base_am: ArreteMinisteriel, parametrization: Parametrization, metadata: AMMetadata
) -> AMWithVersions:
    cid = metadata.cid
    base_am = ensure_not_none(enrich(ensure_not_none(base_am), metadata))
    am_versions = _generate_versions_and_postprocess(cid, base_am, parametrization, metadata)
    return AMWithVersions(base_am=base_am, am_versions=am_versions)
