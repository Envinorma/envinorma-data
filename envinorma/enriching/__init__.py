from envinorma.models import AMMetadata, ArreteMinisteriel, add_metadata

from .remove_null_attributes import remove_null_attributes
from .title_reference import add_references


def enrich(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    return remove_null_attributes(add_references(add_metadata(am, metadata)))
