import random
from dataclasses import asdict, dataclass, field
from string import ascii_letters
from typing import Any, Dict, List, Optional, Union


@dataclass
class Link:
    target: str
    position: int
    content_size: int

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Link':
        dict_ = dict_.copy()
        return cls(**dict_)


@dataclass
class Cell:
    content: 'EnrichedString'
    colspan: int
    rowspan: int

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Cell':
        dict_ = dict_.copy()
        dict_['content'] = EnrichedString.from_dict(dict_['content'])
        return cls(**dict_)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': self.content.to_dict(),
            'colspan': self.colspan,
            'rowspan': self.rowspan,
        }

    def to_html(self, is_header: bool, with_links: bool = False) -> str:
        tag = 'th' if is_header else 'td'
        colspan_attr = f' colspan="{self.colspan}"' if self.colspan != 1 else ''
        rowspan_attr = f' rowspan="{self.rowspan}"' if self.rowspan != 1 else ''
        return f'<{tag}{colspan_attr}{rowspan_attr}>' f'{_enriched_text_to_html(self.content, with_links)}' f'</{tag}>'


def _cells_to_html(cells: List[Cell], is_header: bool, with_links: bool = False) -> str:
    return ''.join([cell.to_html(is_header, with_links) for cell in cells])


@dataclass
class Row:
    cells: List[Cell]
    is_header: bool

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Row':
        return cls(cells=[Cell.from_dict(cell) for cell in dict_['cells']], is_header=dict_['is_header'])

    def to_dict(self) -> Dict[str, Any]:
        return {
            'cells': [cell.to_dict() for cell in self.cells],
            'is_header': self.is_header,
        }

    def to_html(self, with_links: bool = False) -> str:
        return f'<tr>{_cells_to_html(self.cells, self.is_header, with_links)}</tr>'


def _rows_to_html(rows: List[Row], with_links: bool = False) -> str:
    return ''.join([row.to_html(with_links) for row in rows])


@dataclass
class Table:
    rows: List[Row]

    def to_dict(self) -> Dict[str, Any]:
        return {'rows': [row.to_dict() for row in self.rows]}

    @classmethod
    def from_dict(cls, dict_: Dict) -> 'Table':
        return cls([Row.from_dict(row) for row in dict_['rows']])

    def to_html(self, with_links: bool = False) -> str:
        return f'<table>{_rows_to_html(self.rows, with_links)}</table>'


def empty_link_list() -> List[Link]:
    return []


def _split_html_in_lines(html: str) -> List[str]:
    html = html.replace('<br/>', '').replace('>', '>\n').replace('<', '\n<')
    return [x.strip() for x in html.split('\n')]


@dataclass
class EnrichedString:
    """Model for enriched strings.

    It can represent strings potentially decorated with links and tables and
    potentially inapplicably in a certain context.

    Args:
        text (str):
            content of the string
        links (List[Link] = field(default_factory=empty_link_list)):
            list of links decorating text
        table (Optional[Table] = None):
            if not None, the string actually is a table
        inactive (bool = False):
            if True, the string is inactive in the context of its usage
            (example : inapplicable alinea in an AM)

    """

    text: str
    links: List[Link] = field(default_factory=empty_link_list)
    table: Optional[Table] = None
    inactive: bool = False

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'EnrichedString':
        return cls(
            text=dict_['text'],
            links=[Link.from_dict(link) for link in dict_.get('links', [])],
            table=Table.from_dict(dict_['table']) if dict_.get('table') else None,
            inactive=dict_.get('inactive', False),
        )

    def to_dict(self) -> Dict[str, Any]:
        dict_ = asdict(self)
        dict_['table'] = self.table.to_dict() if self.table else None
        if not dict_['table']:
            del dict_['table']
        if not self.links:
            del dict_['links']
        if not self.inactive:
            del dict_['inactive']
        return dict_

    def text_lines(self) -> List[str]:
        if self.table:
            return _split_html_in_lines(self.table.to_html())
        return self.text.split('\n')


def _random_string(size: int = 9) -> str:
    return ''.join([random.choice(ascii_letters) for _ in range(size)])  # noqa: S311


def _random_enriched_string() -> EnrichedString:
    return EnrichedString(_random_string(), [], None)


def estr(text: Optional[str] = None) -> EnrichedString:
    return EnrichedString(text) if text else _random_enriched_string()


def _enriched_text_to_html(str_: EnrichedString, with_links: bool = False) -> str:
    if with_links:
        raise NotImplementedError()  # see markdown if required
    else:
        text = str_.text
    return text.replace('\n', '<br/>')


@dataclass(eq=True)
class Linebreak:
    pass


@dataclass
class Title:
    text: str
    level: int
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'Title':
        return cls(**dict_)


TextElement = Union[Table, str, Title, Linebreak]
TextElements = (Table, str, Title, Linebreak)


def load_text_element(json_: Any) -> TextElement:
    if isinstance(json_, str):
        return json_
    if 'rows' in json_:
        return Table.from_dict(json_)
    if 'level' in json_:
        return Title.from_dict(json_)
    if json_:
        raise ValueError(f'Expected empty dict, got {json_}')
    return Linebreak()


def _count_nb_cols_in_each_row(table: Table) -> List[int]:
    nb_cols_in_each_row: List[int] = [0] * len(table.rows)
    for row_rank, row in enumerate(table.rows):
        for cell in row.cells:
            nb_cols_in_each_row[row_rank] += cell.colspan
            for i in range(1, cell.rowspan):
                if row_rank + i < len(nb_cols_in_each_row):
                    nb_cols_in_each_row[row_rank + i] += cell.colspan
    return nb_cols_in_each_row


def _find_next_index_none(start_index: int, list_: List[Optional[str]]) -> Optional[int]:
    while start_index < len(list_) and list_[start_index] is not None:
        start_index += 1
    if start_index >= len(list_):
        return None
    return start_index


def table_to_list(table: Table) -> List[List[str]]:
    nb_cols_in_each_row = _count_nb_cols_in_each_row(table)
    rows: List[List[Optional[str]]] = [[None for _ in range(size)] for size in nb_cols_in_each_row]
    for row_rank, row in enumerate(table.rows):
        dest_row = rows[row_rank]
        col_index: int = 0
        for cell in row.cells:
            new_col_index = _find_next_index_none(col_index, dest_row)
            if new_col_index is None:
                break
            col_index = new_col_index
            for i in range(cell.rowspan):
                if row_rank + i < len(rows):
                    for j in range(cell.colspan):
                        rows[row_rank + i][col_index + j] = cell.content.text
    return [[x or '' for x in xs] for xs in rows]
