from envinorma.models import AMMetadata, ArreteMinisteriel, add_metadata

from .remove_null_attributes import remove_null_attributes
from .table_row_inline_content import add_table_row_inline_content
from .title_reference import add_references


def enrich(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    return remove_null_attributes(add_table_row_inline_content(add_references(add_metadata(am, metadata))))
