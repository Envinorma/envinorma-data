import json

from envinorma.data.document import DocumentType
from envinorma.data.load import load_aps
from envinorma.data_build.filenames import GEORISQUES_IDS_FILENAME


def dump_georisques_ids() -> None:
    ids = list(sorted([doc.georisques_id for doc in load_aps('all') if doc.type == DocumentType.AP]))
    json.dump(ids, open(GEORISQUES_IDS_FILENAME, 'w'))
