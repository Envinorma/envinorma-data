from copy import copy

from envinorma.models import AMMetadata, ArreteMinisteriel
from envinorma.models.classement import group_classements_by_alineas
from envinorma.utils import AIDA_URL, LEGIFRANCE_LODA_BASE_URL

from .remove_null_attributes import remove_null_attributes
from .title_reference import add_references


def _build_legifrance_url(cid: str) -> str:
    return LEGIFRANCE_LODA_BASE_URL + cid


def _build_aida_url(page: str) -> str:
    return AIDA_URL + page


def add_metadata(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    am = copy(am)
    am.legifrance_url = _build_legifrance_url(metadata.cid)
    am.aida_url = _build_aida_url(metadata.aida_page)
    am.classements = metadata.classements
    am.classements_with_alineas = group_classements_by_alineas(metadata.classements)
    am.is_transverse = metadata.is_transverse
    am.nickname = metadata.nickname
    return am


def enrich(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    return remove_null_attributes(add_references(add_metadata(am, metadata)))
