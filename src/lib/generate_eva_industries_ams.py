import json
from typing import List

from lib.data import ArreteMinisteriel, load_arrete_ministeriel
from lib.compute_properties import AMMetadata, handle_am, load_data, get_legifrance_client


def _find_metadata_with_nor(metadata: List[AMMetadata], nor: str) -> AMMetadata:
    for md in metadata:
        if md.nor == nor:
            return md
    raise ValueError(f'Could not find AM with nor {nor}')


def _generate_structured_am(nor: str) -> ArreteMinisteriel:
    data = load_data()
    metadata = _find_metadata_with_nor(data.arretes_ministeriels.metadata, nor)
    handle_am(metadata, get_legifrance_client(), True)
    return load_arrete_ministeriel(json.load(open(f'data/AM/structured_texts/{nor}.json')))


def _handle_nor(nor: str,):
    _generate_structured_am(nor)


_NORS = ['TREP1900331A', 'DEVP1329353A', 'ATEP9760290A', 'ATEP9760292A', 'DEVP1235896A', 'DEVP1706393A']
if __name__ == '__main__':
    for NOR in _NORS:
        _handle_nor(NOR)
