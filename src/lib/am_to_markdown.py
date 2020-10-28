import json
from enum import Enum
from dataclasses import dataclass
from typing import List, TypeVar, Dict, Any
from lib.am_structure_extraction import (
    EnrichedString,
    Cell,
    Row,
    Table,
    Link,
    StructuredText,
    ArreteMinisteriel,
    transform_arrete_ministeriel,
    _load_legifrance_text,
    _check_legifrance_dict,
)
from lib.aida import transform_aida_links_to_github_markdown_links, add_links_to_am, Hyperlink, _AIDA_URL, Anchor
from lib.texts_properties import (
    AMProperties,
    ComputeProperties,
    LegifranceTextProperties,
    TitleInconsistency,
    compute_properties,
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
    input_ = _load_legifrance_text(json.load(open(input_filename)))
    output = am_to_markdown(transform_arrete_ministeriel(input_))
    open(output_filename, 'w').write(output)


@dataclass
class AMData:
    content: List[Dict[str, Any]]
    nor_to_aida: Dict[str, str]
    aida_to_nor: Dict[str, str]


@dataclass
class AidaData:
    page_id_to_links: Dict[str, List[Hyperlink]]
    page_id_to_anchors: Dict[str, List[Anchor]]


@dataclass
class Data:
    aida: AidaData
    arretes_ministeriels: AMData


def load_am_data() -> AMData:
    arretes_ministeriels = json.load(open('data/AM/arretes_ministeriels.json'))
    nor_to_aida = {doc['nor']: doc['aida_page'] for doc in arretes_ministeriels if 'nor' in doc and 'aida_page' in doc}
    aida_to_nor = {doc['aida_page']: doc['nor'] for doc in arretes_ministeriels if 'nor' in doc and 'aida_page' in doc}
    return AMData(arretes_ministeriels, nor_to_aida, aida_to_nor)


def load_aida_data() -> AidaData:
    page_id_to_links = json.load(open('data/aida/hyperlinks/page_id_to_links.json'))
    page_id_to_anchors = json.load(open('data/aida/hyperlinks/page_id_to_anchors.json'))
    links = {
        aida_page: [Hyperlink(**link_doc) for link_doc in link_docs]
        for aida_page, link_docs in page_id_to_links.items()
    }
    anchors = {
        aida_page: [Anchor(**anchor_doc) for anchor_doc in anchor_docs]
        for aida_page, anchor_docs in page_id_to_anchors.items()
    }
    return AidaData(links, anchors)


def load_data() -> Data:
    return Data(load_aida_data(), load_am_data())


def classement_to_md(classements: List[Dict]) -> str:
    if not classements:
        return ''
    rows = [f"{clss['rubrique']} | {clss['regime']} | {clss.get('alinea') or ''}" for clss in classements]
    return '\n'.join(['Rubrique | Régime | Alinea', '---|---|---'] + rows)


def generate_text_md(text: Dict[str, Any]) -> str:
    nor = text.get('nor')
    page_name = text.get('page_name') or ''
    aida = text.get('aida_page')
    table = classement_to_md(text['classements'])
    return '\n\n'.join(
        [
            f'## [{nor}](/{nor}.md)',
            f'_{page_name.strip()}_',
            f'[sur AIDA]({_AIDA_URL.format(aida)})',
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


def generate_index(am_data: AMData) -> str:
    return '\n\n---\n\n'.join(
        [generate_text_md(text) for text in sorted(am_data.content, key=lambda x: x.get('nor', 'zzzzz'))]
    )


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


def properties_to_markdown(page_title: str, properties: ComputeProperties) -> str:
    return f'''
# {page_title}

## Legifrance

{lf_properties_to_markdown(properties.legifrance)}

## Arrêté structuré

{am_properties_to_markdown(properties.am)}

'''


def generate_nor_markdown(nor: str, data: Data, output_folder: str):
    aida_page = data.arretes_ministeriels.nor_to_aida[nor]
    internal_links = transform_aida_links_to_github_markdown_links(
        data.aida.page_id_to_links[aida_page],
        data.aida.page_id_to_anchors[aida_page],
        nor,
        data.arretes_ministeriels.aida_to_nor,
    )

    legifrance_text_json = json.load(open(f'data/AM/legifrance_texts/{nor}.json'))
    _check_legifrance_dict(legifrance_text_json)
    lf_text = _load_legifrance_text(legifrance_text_json)
    am = transform_arrete_ministeriel(lf_text)
    properties = compute_properties(lf_text, am)
    open(f'{output_folder}/{nor}.md', 'w').write(am_to_markdown(add_links_to_am(am, internal_links), with_links=True))
    open(f'{output_folder}/props/{nor}.md', 'w').write(properties_to_markdown(am.title.text, properties))


def generate_1510_markdown() -> None:
    data = load_data()
    magic_nor = 'DEVP1706393A'
    generate_nor_markdown(magic_nor, data, 'data/AM/markdown_texts')


def generate_all_markdown(output_folder: str = '/Users/remidelbouys/EnviNorma/envinorma.github.io') -> None:
    from tqdm import tqdm

    data = load_data()
    open(f'{output_folder}/index.md', 'w').write(generate_index(data.arretes_ministeriels))

    nors = data.arretes_ministeriels.nor_to_aida.keys()
    for nor in tqdm(nors):
        try:
            generate_nor_markdown(nor, data, output_folder)
        except Exception as exc:  # pylint: disable = broad-except
            print(nor, type(exc), str(exc))
