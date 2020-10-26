import json
from enum import Enum
from typing import List, TypeVar
from lib.am_structure_extraction import (
    EnrichedString,
    Cell,
    Row,
    Table,
    Link,
    StructuredText,
    StructuredArreteMinisteriel,
    transform_arrete_ministeriel,
    _load_legifrance_text,
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


def am_to_markdown(am: StructuredArreteMinisteriel, with_links: bool = False) -> str:
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

