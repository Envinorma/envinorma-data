from envinorma.data import Table
from envinorma.structure.texts_properties import extract_tables
from envinorma.dashboard.tables_in_am.data import TablesDataset, TableStat
from envinorma.back_office.fetch_data import load_all_structured_am


def _extract_max_nb_cols(table: Table) -> int:
    return max([sum([cell.colspan for cell in row.cells]) for row in table.rows])


def _extract_nb_headers(table: Table) -> int:
    return sum([row.is_header for row in table.rows])


def _has_headers_not_at_the_top(table: Table) -> bool:
    i = 0
    for i, row in enumerate(table.rows):
        if not row.is_header:
            break
    if i == len(table.rows) - 1:  # no more rows can be header
        return False
    for j in range(i + 1, len(table.rows)):
        if table.rows[j].is_header:
            return True
    return False


def _max_colspan(table: Table) -> int:
    return max([cell.colspan for row in table.rows for cell in row.cells])


def _max_rowspan(table: Table) -> int:
    return max([cell.rowspan for row in table.rows for cell in row.cells])


def extract_stats(am_cid: str, table: Table) -> TableStat:
    return TableStat(
        nb_rows=len(table.rows),
        max_nb_cols=_extract_max_nb_cols(table),
        nb_headers=_extract_nb_headers(table),
        has_headers_not_at_the_top=_has_headers_not_at_the_top(table),
        am_cid=am_cid,
        max_colspan=_max_colspan(table),
        max_rowspan=_max_rowspan(table),
    )


def build(output_filename: str):
    all_enriched_am = load_all_structured_am()
    all_tables = [(am.id, table) for am in all_enriched_am for table in extract_tables(am)]
    all_stats = [extract_stats(am_cid or '', table) for am_cid, table in all_tables]
    TablesDataset(all_stats).to_csv(output_filename)
