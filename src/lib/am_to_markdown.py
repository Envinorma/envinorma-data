import json
from enum import Enum
from collections import Counter
from typing import Dict, List, Optional, TypeVar
from tqdm import tqdm

from lib.am_structure_extraction import (
    EnrichedString,
    Cell,
    Row,
    Table,
    Link,
    StructuredText,
    ArreteMinisteriel,
    transform_arrete_ministeriel,
    load_legifrance_text,
)
from lib.aida import transform_aida_links_to_github_markdown_links, add_links_to_am, _AIDA_URL
from lib.texts_properties import AMProperties, TextProperties, LegifranceTextProperties, TitleInconsistency
from lib.compute_properties import (
    AMStructurationLog,
    get_text_defined_id,
    Classement,
    AMState,
    AMData,
    Data,
    AMMetadata,
    handle_all_am,
)


def enriched_text_to_html(str_: EnrichedString, with_links: bool = False) -> str:
    if with_links:
        text = _insert_links(str_.text, str_.links, DataFormat.HTML)
    else:
        text = str_.text
    return text.replace('\n', '<br/>')


def cell_to_html(cell: Cell, is_header: bool, with_links: bool = False) -> str:
    tag = 'th' if is_header else 'td'
    return (
        f'<{tag} colspan="{cell.colspan}" rowspan="{cell.rowspan}">'
        f'{enriched_text_to_html(cell.content, with_links)}'
        f'</{tag}>'
    )


def cells_to_html(cells: List[Cell], is_header: bool, with_links: bool = False) -> str:
    return ''.join([cell_to_html(cell, is_header, with_links) for cell in cells])


def row_to_html(row: Row, with_links: bool = False) -> str:
    return f'<tr>{cells_to_html(row.cells, row.is_header, with_links)}</tr>'


def rows_to_html(rows: List[Row], with_links: bool = False) -> str:
    return ''.join([row_to_html(row, with_links) for row in rows])


def table_to_markdown(table: Table, with_links: bool = False) -> str:  # html required for merging cells
    return f'<table>{rows_to_html(table.rows, with_links)}</table>'


def _extract_sorted_links_to_display(links: List[Link]) -> List[Link]:
    if not links:
        return []
    sorted_links = sorted(links, key=lambda link: (link.position, -link.content_size))
    filtered_links = [sorted_links[0]]
    for link in sorted_links[1:]:
        if link.position >= filtered_links[-1].position + filtered_links[-1].content_size:
            filtered_links.append(link)
    return filtered_links


class DataFormat(Enum):
    MARKDOWN = 'MARKDOWN'
    HTML = 'HTML'


def _make_url(content: str, target: str, format_: DataFormat) -> str:
    if format_ == DataFormat.MARKDOWN:
        return f'[{content}]({target})'
    if format_ == DataFormat.HTML:
        return f'<a href="{target}">{content}</a>'
    raise NotImplementedError(f'URL outputting is not implemented for format {format_}')


TP = TypeVar('TP')


def _alternate_merge(even_elements: List[TP], odd_elements: List[TP]) -> List[TP]:
    if not 0 <= len(even_elements) - len(odd_elements) <= 1:
        raise ValueError(
            f'There should be the same number of elements or one extra even elements.'
            f' Even: {len(even_elements)}, Odd: {len(odd_elements)}'
        )
    res = [x for a, b in zip(even_elements, odd_elements) for x in [a, b]]
    if len(even_elements) > len(odd_elements):
        res.append(even_elements[-1])
    return res


def divide_string(str_: str, hyphenations: List[int]) -> List[str]:
    return [str_[start:end] for start, end in zip([0] + hyphenations, hyphenations + [len(str_)])]


def _add_links_to_relevant_pieces(pieces: List[str], links: List[Link], format_: DataFormat) -> List[str]:
    iso_pieces = pieces[0::2]
    changing_pieces = pieces[1::2]
    assert len(changing_pieces) == len(links)
    changed_pieces = [_make_url(str_, link.target, format_) for str_, link in zip(changing_pieces, links)]
    return _alternate_merge(iso_pieces, changed_pieces)


def _insert_links(str_: str, links: List[Link], format_: DataFormat) -> str:
    compatible_links = _extract_sorted_links_to_display(links)
    hyphenations = [hyph for link in compatible_links for hyph in (link.position, link.position + link.content_size)]
    pieces = divide_string(str_, hyphenations)
    return ''.join(_add_links_to_relevant_pieces(pieces, compatible_links, format_))


def enriched_string_to_markdown(str_: EnrichedString, with_links: bool = False) -> str:
    if str_.table:
        return table_to_markdown(str_.table, with_links)
    return str_.text if not with_links else _insert_links(str_.text, str_.links, DataFormat.MARKDOWN)


def extract_markdown_title(title: EnrichedString, with_links: bool = False) -> List[str]:
    return [f'# {enriched_string_to_markdown(title, with_links)}']


def extract_markdown_visa(visa: List[EnrichedString], with_links: bool = False) -> List[str]:
    return ['## Visa'] + [enriched_string_to_markdown(vu, with_links) for vu in visa]


def extract_markdown_text(text: StructuredText, level: int, with_links: bool = False) -> List[str]:
    return [
        '#' * level + f' {enriched_string_to_markdown(text.title, with_links)}' if text.title else ' -',
        *[enriched_string_to_markdown(alinea, with_links) for alinea in text.outer_alineas],
        *[line for section in text.sections for line in extract_markdown_text(section, level + 1, with_links)],
    ]


def am_to_markdown(am: ArreteMinisteriel, with_links: bool = False) -> str:
    lines = [
        *extract_markdown_title(am.title, with_links),
        *extract_markdown_visa(am.visa, with_links),
        *[line for section in am.sections for line in extract_markdown_text(section, 2, with_links)],
    ]
    return '\n\n'.join(lines)


def markdown_transform_and_write_am(input_filename: str, output_filename: str):
    input_ = load_legifrance_text(json.load(open(input_filename)))
    output = am_to_markdown(transform_arrete_ministeriel(input_))
    open(output_filename, 'w').write(output)


def classement_to_md(classements: List[Classement]) -> str:
    if not classements:
        return ''
    rows = [f"{clss.rubrique} | {clss.regime.value} | {clss.alinea or ''}" for clss in classements]
    return '\n'.join(['Rubrique | Régime | Alinea', '---|---|---'] + rows)


_LEGIFRANCE_URL = 'https://www.legifrance.gouv.fr/jorf/id/{}'


def log_to_md(log: AMStructurationLog) -> str:
    if log.legifrance_api_error:
        return 'erreur-lf-api'
    if log.legifrance_text_format_error:
        return 'erreur-structure-entrante'
    if log.structuration_error:
        return 'erreur-structuration'
    return 'pas-d-erreur'


def generate_text_md(text: AMMetadata, log: AMStructurationLog) -> str:
    page_name = get_text_defined_id(text)
    table = classement_to_md(text.classements)
    return '\n\n'.join(
        [
            f'## [{text.short_title}](/{page_name}.md)',
            f'Etat: {text.state.value}',
            f'NOR: {text.nor or "non défini"}',
            f'CID: {text.cid}',
            f'Statut de structuration: {log_to_md(log)}',
            f'_{page_name.strip()}_',
            f'- [sur Légifrance]({_LEGIFRANCE_URL.format(text.cid)})',
            f'- [sur AIDA]({_AIDA_URL.format(text.aida_page)})',
            *([table] if table else []),
        ]
    )


def _make_collapsible(details: str, hidden: str) -> str:
    return f'''
        <details>
            <summary>
                {details}
            </summary>

            {hidden}
        </details>

    '''


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


def generate_header_md(title: str) -> str:
    return f'''
# {title}

'''


def am_and_properties_to_markdown(am: ArreteMinisteriel, properties: Optional[TextProperties]) -> str:
    header_md = generate_header_md(am.title.text)
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
    return am_and_properties_to_markdown(am, log.properties)


def generate_all_markdown(output_folder: str = '/Users/remidelbouys/EnviNorma/envinorma.github.io') -> None:
    data, cid_to_log, cid_to_am = handle_all_am()
    dump_md(generate_index(data.arretes_ministeriels, cid_to_log), f'{output_folder}/index.md')
    for metadata in tqdm(data.arretes_ministeriels.metadata, 'Genrating markdown'):
        id_ = get_text_defined_id(metadata)
        cid = metadata.cid
        dump_md(generate_am_markdown(data, metadata, cid_to_log[cid], cid_to_am.get(cid)), f'{output_folder}/{id_}.md')
