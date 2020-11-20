from collections import Counter
from typing import Dict, List, Optional, Set
from tqdm import tqdm

from lib.aida import transform_aida_links_to_github_markdown_links, add_links_to_am
from lib.data import (
    check_am,
    ArreteMinisteriel,
    AMStructurationLog,
    get_text_defined_id,
    AMState,
    AMData,
    Data,
    AMMetadata,
    AMProperties,
    TextProperties,
    LegifranceTextProperties,
    TitleInconsistency,
)
from lib.am_to_markdown import am_to_markdown, generate_text_md
from lib.compute_properties import handle_all_am
from lib.git_diffs_generator import AMCommits, compute_and_dump_am_git_diffs
from lib.parametrization import Parametrization, parametrization_to_markdown


def _score(log: AMStructurationLog) -> int:
    if log.legifrance_api_error:
        return 4
    if log.legifrance_text_format_error:
        return 3
    if log.structuration_error:
        return 2
    return 1


def magic_sort_texts(texts: List[AMMetadata], cid_to_log: Dict[str, AMStructurationLog]) -> List[AMMetadata]:
    return list(sorted(texts, key=lambda x: (_score(cid_to_log[x.cid]), -x.publication_date)))


def generate_metadata_md(am_data: AMData, cid_to_log: Dict[str, AMStructurationLog]) -> str:
    abrogated = [text for text in am_data.metadata if text.state == AMState.ABROGE]
    in_force = [text for text in am_data.metadata if text.state == AMState.VIGUEUR]
    return '\n\n---\n\n'.join(
        [
            '# Textes en vigueur',
            *[generate_text_md(text, cid_to_log[text.cid]) for text in magic_sort_texts(in_force, cid_to_log)],
            '# Textes abrogés',
            *[generate_text_md(text, cid_to_log[text.cid]) for text in magic_sort_texts(abrogated, cid_to_log)],
        ]
    )


def generate_index_header_md(metadata: List[AMMetadata], cid_to_log: Dict[str, AMStructurationLog]) -> str:
    cid_in_force = {md.cid for md in metadata if md.state == AMState.VIGUEUR}

    api_errors = [
        cid_to_log[cid].legifrance_api_error for cid in cid_in_force if cid_to_log[cid].legifrance_api_error is not None
    ]
    api_errors_cids = ', '.join([cid for cid in cid_in_force if cid_to_log[cid].legifrance_api_error is not None])
    status_codes = ', '.join(
        [f'{status} ({occs})' for status, occs in Counter([error.status_code for error in api_errors]).most_common()]
    )
    unhandled_schemas = [cid for cid in cid_in_force if cid_to_log[cid].legifrance_text_format_error is not None]
    unhandled_schemas_str = ', '.join(unhandled_schemas)
    structuration_errors = ', '.join([cid for cid in cid_in_force if cid_to_log[cid].structuration_error is not None])
    properties = [cid_to_log[cid].properties for cid in cid_in_force if cid_to_log[cid].properties]
    inconsistencies = Counter(
        [inc.inconsistency for prop in properties if prop.am for inc in prop.am.title_inconsistencies]
    )
    inconsistencies_str = [f' - {inc} ({occs})' for inc, occs in inconsistencies.most_common()]

    return '\n\n'.join(
        [
            '# Stats',
            '## Nombre d\'arrêtés.',
            f'- {len(cid_to_log)} arrêtés.',
            f'- {len(cid_in_force)} en vigueur.',
            f'- {len(cid_to_log) - len(cid_in_force)} abrogés.',
            'Seuls les arrêtés en vigueur sont gérés.',
            '## API Errors',
            f'- {len(api_errors)} erreur(s).',
            f'- Status codes (avec occurrences): {status_codes}',
            f'- CIDs: {api_errors_cids}',
            '## Schemas non supportés',
            f'- {len(unhandled_schemas)} erreur(s).',
            f'- CIDs: {unhandled_schemas_str}',
            '## Erreurs de structuration',
            f'- {len(structuration_errors)} erreur(s).',
            f'- CIDs: {structuration_errors}',
            '## Incohérences détectées',
            *inconsistencies_str,
        ]
    )


def generate_index(am_data: AMData, cid_to_log: Dict[str, AMStructurationLog]) -> str:
    header = generate_index_header_md(am_data.metadata, cid_to_log)
    metadata = generate_metadata_md(am_data, cid_to_log)
    return header + '\n\n---\n\n' + metadata


def lf_properties_to_markdown(properties: LegifranceTextProperties) -> str:
    return f'```\n{properties.structure}\n```'


def _join_strings(strs: List[str]) -> str:
    return '\n\n'.join(strs)


def title_inconsistencies_to_markdown(inconsistencies: List[TitleInconsistency]) -> str:
    return '\n\n'.join(
        [
            f'''
#### {inconsistency.parent_section_title}

##### Incohérence

{inconsistency.inconsistency}

##### Titres
{_join_strings(inconsistency.titles)}
'''
            for inconsistency in inconsistencies
        ]
    )


def am_properties_to_markdown(properties: AMProperties) -> str:
    return f'''
### Structure
```
{properties.structure}
```

### Incohérences

{title_inconsistencies_to_markdown(properties.title_inconsistencies)}
'''


def properties_to_markdown(properties: TextProperties) -> str:
    return f'''
## Legifrance

{lf_properties_to_markdown(properties.legifrance)}

## Arrêté structuré

{am_properties_to_markdown(properties.am) if properties.am else 'Not computed.'}

'''


def generate_header_md(title: str, nor: str, is_param: bool = False) -> str:
    if not is_param:
        return f'''
# {title}

[Versions paramétrées](parametrization/{nor}.md)
'''
    return f'''
# {title}

[Retour à l'arrêté]({nor}.md)
'''


def am_and_properties_to_markdown(
    am: ArreteMinisteriel, properties: Optional[TextProperties], metadata: AMMetadata
) -> str:
    header_md = generate_header_md(am.title.text, metadata.nor or metadata.cid)
    props_md = properties_to_markdown(properties) if properties else ''
    am_md = am_to_markdown(am, with_links=True)
    return '\n\n'.join([header_md, props_md, am_md])


def dump_md(markdown: str, filename: str) -> None:
    open(filename, 'w').write(markdown)


def add_aida_links_to_am(metadata: AMMetadata, am: ArreteMinisteriel, data: Data) -> ArreteMinisteriel:
    if metadata.nor is None or metadata.nor not in data.arretes_ministeriels.nor_to_aida:
        return am
    aida_page = data.arretes_ministeriels.nor_to_aida[metadata.nor]
    if aida_page not in data.aida.page_id_to_links or aida_page not in data.aida.page_id_to_anchors:
        return am
    internal_links = transform_aida_links_to_github_markdown_links(
        data.aida.page_id_to_links[aida_page],
        data.aida.page_id_to_anchors[aida_page],
        metadata.nor,
        data.arretes_ministeriels.aida_to_nor,
    )
    return add_links_to_am(am, internal_links)


def generate_am_markdown(
    data: Data, metadata: AMMetadata, log: AMStructurationLog, am: Optional[ArreteMinisteriel]
) -> str:
    if not am:
        return f"# {metadata.short_title}\n\nError in computation"
    am = add_aida_links_to_am(metadata, am, data)
    check_am(am)
    return am_and_properties_to_markdown(am, log.properties, metadata)


def _parametrization_section(parametrization: Parametrization) -> str:
    return f'''
# Paramétrisation

{parametrization_to_markdown(parametrization)}
'''


def _diff_md(diff: List[str]) -> str:
    code = '\n'.join(diff) or 'Pas de différences.'
    return f'```\n{code}\n```'


def _diffs_section(diffs: Dict[str, List[str]]) -> str:
    return '\n\n'.join(
        [
            '# Différences par rapport à l\'arrêté d\'origine',
            *[f'## {title}\n\n{_diff_md(diff)}' for title, diff in diffs.items()],
        ]
    )


def _generate_diff_url(main_commit_id: str, commit_id: str) -> str:
    return f'https://github.com/Envinorma/arretes_ministeriels/compare/{commit_id}...{main_commit_id}'


def generate_commits_md(am_commits: AMCommits) -> str:
    commit_lines = [
        f'[{version_name}]({_generate_diff_url(am_commits.main_commit_id, commit_id)})'
        for version_name, commit_id in am_commits.version_commit_ids.items()
    ]
    return '\n\n'.join(['## Differences'] + commit_lines)


def generate_parametric_am_markdown(
    am: ArreteMinisteriel,
    metadata: AMMetadata,
    parametrization: Parametrization,
    diffs: Dict[str, List[str]],
    am_commits: AMCommits,
) -> str:
    header_md = generate_header_md(am.title.text, metadata.nor or metadata.cid, True)
    commits = generate_commits_md(am_commits)
    parametrization_md = _parametrization_section(parametrization)
    diffs_md = _diffs_section(diffs)
    return '\n\n'.join([header_md, commits, parametrization_md, diffs_md])


_GITHUB_IO = '/Users/remidelbouys/EnviNorma/envinorma.github.io'


def generate_all_markdown(output_folder: str = _GITHUB_IO, am_cids: Optional[Set[str]] = None) -> None:
    am_cids = am_cids or set()
    data, cid_to_log, cid_to_am, cid_to_param = handle_all_am(
        am_cids=am_cids, dump_am=len(am_cids) != 0, with_manual_enrichments=len(am_cids) != 0
    )
    if not am_cids:  # We just want to generate specific pages
        dump_md(generate_index(data.arretes_ministeriels, cid_to_log), f'{output_folder}/index.md')
    for metadata in tqdm(data.arretes_ministeriels.metadata, 'Generating markdown'):
        if metadata.cid not in am_cids:
            continue
        id_ = get_text_defined_id(metadata)
        cid = metadata.cid
        dump_md(generate_am_markdown(data, metadata, cid_to_log[cid], cid_to_am.get(cid)), f'{output_folder}/{id_}.md')
        if cid in cid_to_am and cid in cid_to_param:
            am_commits = compute_and_dump_am_git_diffs(id_, am_to_markdown)
            dump_md(
                generate_parametric_am_markdown(
                    cid_to_am[cid], metadata, cid_to_param[cid][0], cid_to_param[cid][1], am_commits
                ),
                f'{output_folder}/parametrization/{id_}.md',
            )


if __name__ == '__main__':
    generate_all_markdown(
        am_cids={
            'JORFTEXT000026694913',
            'JORFTEXT000034429274',
            'JORFTEXT000028379599',
            'JORFTEXT000038358856',
            'JORFTEXT000000552021',
            'JORFTEXT000000369330',
        }
    )
