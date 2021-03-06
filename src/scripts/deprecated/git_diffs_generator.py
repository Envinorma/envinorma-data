'''
Script for generating commits with AM version in ordre to use version control features for AM db.
Deprecated.
'''
import json
import os
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List

from git import Repo
from git.objects.commit import Commit

from envinorma.config import AM_DATA_FOLDER
from envinorma.data import ArreteMinisteriel
from envinorma.utils import write_json

_AM_DIFF_REPO_PATH = '/Users/remidelbouys/EnviNorma/arretes_ministeriels'


def get_repo() -> Repo:
    repo = Repo(_AM_DIFF_REPO_PATH)
    return repo


def get_absolute_path_with_repo(repo: Repo, relative_path: str) -> str:
    if not repo.working_tree_dir:
        raise ValueError('Expecting non null working tree dir')
    return os.path.join(repo.working_tree_dir, relative_path)


def commit_file(repo: Repo, relative_path: str, commit_message: str) -> Commit:
    new_file_path = get_absolute_path_with_repo(repo, relative_path)
    repo.index.add([new_file_path])
    return repo.index.commit(commit_message)


@dataclass
class AMCommits:
    main_commit_id: str
    version_commit_ids: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(dict_: Dict[str, Any]) -> 'AMCommits':
        return AMCommits(**dict_)


def _write_file(content: str, path: str):
    open(path, 'w').write(content)


def _write_file_and_commit(repo: Repo, filename: str, file_content, commit_detail: str) -> str:
    _write_file(file_content, get_absolute_path_with_repo(repo, filename))
    commit_message = f'{filename} {commit_detail}'
    return str(commit_file(repo, filename, commit_message).hexsha)


def commit_ams(
    filename: str,
    main_am: ArreteMinisteriel,
    all_am_versions: Dict[str, ArreteMinisteriel],
    am_stringifier: Callable[[ArreteMinisteriel], str],
) -> AMCommits:
    main_am_str = am_stringifier(main_am)
    all_am_versions_str = {name: am_stringifier(am) for name, am in all_am_versions.items()}
    repo = get_repo()
    version_commit_ids: Dict[str, str] = {}
    for version_name, am_str in all_am_versions_str.items():
        version_commit_ids[version_name] = _write_file_and_commit(repo, filename, am_str, 'version ' + version_name)
    main_commit_id = _write_file_and_commit(repo, filename, main_am_str, 'main commit')
    return AMCommits(main_commit_id, version_commit_ids)


def _get_parametric_ams_folder(id_: str) -> str:
    return f'{AM_DATA_FOLDER}/parametric_texts/{id_}'


def _get_enriched_am_filename(id_: str) -> str:
    return f'{AM_DATA_FOLDER}/enriched_texts/{id_}.json'


def _load_main_am(nor: str) -> ArreteMinisteriel:
    return ArreteMinisteriel.from_dict(json.load(open(_get_enriched_am_filename(nor))))


def _read_folder(folder: str) -> List[str]:
    return [filename for filename in os.listdir(folder) if filename[0] != '.']


def _load_versions(nor: str) -> Dict[str, ArreteMinisteriel]:
    folder = _get_parametric_ams_folder(nor)
    return {
        filename: ArreteMinisteriel.from_dict(json.load(open(os.path.join(folder, filename))))
        for filename in _read_folder(folder)
    }


def get_am_commits_filename(nor: str) -> str:
    return os.path.join(_get_parametric_ams_folder(nor), '.am_diffs_commits.json')


def _dump_am_commits(nor: str, am_commits: AMCommits) -> None:
    write_json(am_commits.to_dict(), get_am_commits_filename(nor))


def compute_and_dump_am_git_diffs(nor: str, am_stringifier: Callable[[ArreteMinisteriel], str]) -> AMCommits:
    main_am = _load_main_am(nor)
    versions = _load_versions(nor)
    am_commits = commit_ams(f'{nor}.md', main_am, versions, am_stringifier)
    _dump_am_commits(nor, am_commits)
    return am_commits
