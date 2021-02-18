'''
Script for detecting differences between remote texts and envinorma texts.
'''
import pathlib
import random
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from dash_text_components.diff import (
    AddedLine,
    ModifiedLine,
    RemovedLine,
    TextDifferences,
    UnchangedLine,
    build_text_differences,
)
from envinorma.back_office.fetch_data import load_initial_am
from envinorma.back_office.utils import ID_TO_AM_MD
from envinorma.config import config
from envinorma.data import AMSource, ArreteMinisteriel, extract_text_lines, load_legifrance_text
from envinorma.structure.am_structure_extraction import transform_arrete_ministeriel
from legifrance.legifrance_API import get_current_loda_via_cid, get_legifrance_client
from tqdm import tqdm


def _load_legifrance_version(am_id: str) -> ArreteMinisteriel:
    client = get_legifrance_client(config.legifrance.client_id, config.legifrance.client_secret)
    legifrance_current_version = load_legifrance_text(get_current_loda_via_cid(am_id, client))
    random.seed(legifrance_current_version.title)
    return transform_arrete_ministeriel(legifrance_current_version, am_id=am_id)


def _extract_lines(am: ArreteMinisteriel) -> List[str]:
    return [line for section in am.sections for line in extract_text_lines(section, 0)]


def _compute_am_diff(am_before: ArreteMinisteriel, am_after: ArreteMinisteriel) -> TextDifferences:
    lines_before = _extract_lines(am_before)
    lines_after = _extract_lines(am_after)
    return build_text_differences(lines_before, lines_after)


def _compute_modification_ratio(diff: TextDifferences) -> float:
    nb_modified_lines = len([0 for dl in diff.diff_lines if not isinstance(dl, UnchangedLine)])
    modification_ratio = nb_modified_lines / len(diff.diff_lines)
    return modification_ratio


def _seems_too_big(diff: TextDifferences) -> bool:
    return _compute_modification_ratio(diff) >= 0.03


def _am_has_changed(am_id: str) -> Tuple[bool, Optional[TextDifferences]]:
    envinorma_version = load_initial_am(am_id)
    if not envinorma_version:
        return False, None
    legifrance_version = _load_legifrance_version(am_id)
    diff = _compute_am_diff(envinorma_version, legifrance_version)
    if _seems_too_big(diff):
        return True, diff
    return False, diff


def _pretty_print_diff(diff: TextDifferences):
    for line in diff.diff_lines:
        if isinstance(line, UnchangedLine):
            continue
        if isinstance(line, AddedLine):
            print(f'+{line.content}')
        if isinstance(line, RemovedLine):
            print(f'-{line.content}')
        if isinstance(line, ModifiedLine):
            print(f'M-{line.content_before}')
            print(f'M+{line.content_after}')


def _write_diff_description(am_id_to_diff: Dict[str, TextDifferences]) -> None:
    lines = [
        line
        for am_id, diff in am_id_to_diff.items()
        for line in [am_id, f'ratio : {_compute_modification_ratio(diff)}']
    ]
    date_ = datetime.now().strftime('%Y-%m-%d-%H-%M')
    destination = pathlib.Path(__file__).parent.parent.joinpath(f'data/legifrance_diffs/{date_}.txt')
    open(destination, 'w').write('\n'.join(lines))


def run() -> None:
    changed = {}
    for am_id, md in tqdm(ID_TO_AM_MD.items()):
        if md.source != AMSource.LEGIFRANCE:
            continue
        am_id = str(am_id)
        try:
            am_has_changed, diff = _am_has_changed(am_id)
        except Exception as exc:
            print(am_id, str(exc))
            continue
        if am_has_changed:
            changed[am_id] = diff
            print(f'AM {am_id} seems to have changed.')
    _write_diff_description(changed)
    for am_id, diff in changed.items():
        print(am_id)
        _pretty_print_diff(diff)


def _dump_before_after(am_id: str):
    envinorma_version = load_initial_am(am_id)
    if not envinorma_version:
        return
    legifrance_version = _load_legifrance_version(am_id)
    open('tmp_before.txt', 'w').write('\n'.join(_extract_lines(envinorma_version)))
    open('tmp_after.txt', 'w').write('\n'.join(_extract_lines(legifrance_version)))


if __name__ == '__main__':
    run()
