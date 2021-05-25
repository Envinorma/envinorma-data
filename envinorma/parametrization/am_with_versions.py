from dataclasses import dataclass, replace
from datetime import date
from typing import Dict, Optional, Tuple

from envinorma.am_enriching import (
    add_references,
    add_summary,
    add_table_inspection_sheet_data,
    detect_and_add_topics,
    remove_null_applicabilities,
)
from envinorma.data import AMMetadata, ArreteMinisteriel, ClassementWithAlineas, Regime, add_metadata
from envinorma.parametrization import Combinations, Parametrization
from envinorma.parametrization.conditions import ParameterEnum
from envinorma.parametrization.parametric_am import generate_all_am_versions
from envinorma.topics.topics import TOPIC_ONTOLOGY
from envinorma.utils import AM1510_IDS, ensure_not_none

AMVersions = Dict[Tuple[str, ...], ArreteMinisteriel]


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


def apply_parametrization(
    am_id: str, am: Optional[ArreteMinisteriel], parametrization: Parametrization, metadata: AMMetadata
) -> Optional[AMVersions]:
    if not am:
        return None
    enriched_am = remove_null_applicabilities(am)
    manual_combinations = _get_manual_combinations(am_id)  # For AM 1510 mainly, none otherwise
    all_versions = generate_all_am_versions(enriched_am, parametrization, True, manual_combinations)
    return {
        name: _post_process(am_id, _add_enrichments(am_, metadata), _extract_regime(am_id, name))
        for name, am_ in all_versions.items()
    }


def _add_enrichments(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    return add_summary(
        remove_null_applicabilities(
            add_table_inspection_sheet_data(
                detect_and_add_topics(add_references(add_metadata(am, metadata)), TOPIC_ONTOLOGY)
            )
        )
    )


def enrich_am(am: Optional[ArreteMinisteriel], metadata: AMMetadata) -> Optional[ArreteMinisteriel]:
    if not am:
        return None
    return _add_enrichments(am, metadata)


@dataclass
class AMWithVersions:
    base_am: Optional[ArreteMinisteriel]
    am_versions: Optional[AMVersions]


def generate_am_with_versions(
    base_am: ArreteMinisteriel, parametrization: Parametrization, metadata: AMMetadata
) -> AMWithVersions:
    cid = metadata.cid
    base_am = ensure_not_none(enrich_am(base_am, metadata))
    am_versions = apply_parametrization(cid, base_am, parametrization, metadata)
    return AMWithVersions(base_am=base_am, am_versions=am_versions)
