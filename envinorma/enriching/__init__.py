from envinorma.enriching.remove_null_applicabilities import remove_null_applicabilities
from envinorma.enriching.table_row_inline_content import add_table_row_inline_content
from envinorma.enriching.title_reference import add_references
from envinorma.enriching.topic_detection import detect_and_add_topics
from envinorma.models.am_metadata import AMMetadata
from envinorma.models.arrete_ministeriel import ArreteMinisteriel, add_metadata
from envinorma.topics.topics import TOPIC_ONTOLOGY


def enrich(am: ArreteMinisteriel, metadata: AMMetadata) -> ArreteMinisteriel:
    return remove_null_applicabilities(
        add_table_row_inline_content(detect_and_add_topics(add_references(add_metadata(am, metadata)), TOPIC_ONTOLOGY))
    )
