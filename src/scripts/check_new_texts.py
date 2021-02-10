import random
from dataclasses import dataclass
from typing import List, Union

from back_office.fetch_data import load_initial_am
from back_office.utils import ID_TO_AM_MD
from lib.am_structure_extraction import transform_arrete_ministeriel
from lib.data import ArreteMinisteriel, load_legifrance_text
from lib.legifrance_API import get_current_loda_via_cid, get_legifrance_client
from tqdm import tqdm


@dataclass
class RemovedLine:
    content: str


@dataclass
class AddedLine:
    content: str


@dataclass
class ModifiedLine:
    content: str
    mask: List[bool]


DiffLine = Union[RemovedLine, AddedLine, ModifiedLine]


@dataclass
class TextDifferences:
    diff_lines: List[DiffLine]


def _load_legifrance_version(am_id: str) -> ArreteMinisteriel:
    client = get_legifrance_client()
    legifrance_current_version = load_legifrance_text(get_current_loda_via_cid(am_id, client))
    random.seed(legifrance_current_version.title)
    return transform_arrete_ministeriel(legifrance_current_version)


def _compute_am_diff(am_before: ArreteMinisteriel, am_after: ArreteMinisteriel) -> TextDifferences:
    return TextDifferences([])  # TODO


def _seems_too_big(diff: TextDifferences) -> bool:
    return False  # TODO


def _am_has_changed(am_id: str) -> bool:
    envinorma_version = load_initial_am(am_id)
    if not envinorma_version:
        return False
    legifrance_version = _load_legifrance_version(am_id)
    diff = _compute_am_diff(envinorma_version, legifrance_version)
    if _seems_too_big(diff):
        return True
    return False


def run() -> None:
    for am_id in tqdm(ID_TO_AM_MD):
        am_id = str(am_id)
        if _am_has_changed(am_id):
            raise ValueError(f'AM {am_id} seems to have changed.')


if __name__ == '__main__':
    run()
