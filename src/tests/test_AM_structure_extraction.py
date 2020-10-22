import json
from scripts.AM_structure_extraction import (
    DataFormat,
    Link,
    _extract_links,
    _insert_links,
    _html_to_structured_text,
    am_to_markdown,
    table_to_markdown,
    transform_arrete_ministeriel,
    _extract_table,
    _extract_cell_data,
    _extract_sorted_links_to_display,
)


def test_link_extraction():
    text = 'Hello, how <a href="rf">are</a>'
    enriched_text = _extract_links(text, False)
    assert enriched_text.table is None
    assert '<' not in enriched_text.text
    assert len(enriched_text.links) == 1
    assert enriched_text.links[0].target == 'rf'
    assert enriched_text.links[0].content_size == 3
    assert enriched_text.links[0].position == 11


def test_structure_extraction():
    text = '''
        <p>Holà</p>
        <p>
            <div>
                <tr>
                    <th>A</th>
                    <th>B</th>
                    <th>C</th>
                </tr>
                <tr>
                    <td>D</td>
                    <td>E</td>
                    <td>F</td>
                </tr>
            </div>
        </p>
        Hello, how <a href="rf">are</a><br/>
    '''
    structured_text = _html_to_structured_text(text)
    assert structured_text.title.text == '' and structured_text.title.table is None
    assert len(structured_text.sections) == 0
    assert len(structured_text.outer_alineas) == 3
    assert structured_text.outer_alineas[0].text == 'Holà'
    assert structured_text.outer_alineas[1].table is not None
    assert len(structured_text.outer_alineas[2].links) == 1


_SAMPLE_AM_NOR = ['DEVP1706393A', 'TREP1815737A', 'ATEP9870263A', 'DEVP1519168A', 'DEVP1430916A', 'DEVP1001990A']


def test_no_fail_in_structure_extraction():
    for nor in _SAMPLE_AM_NOR:
        transform_arrete_ministeriel(json.load(open(f'data/AM/legifrance_texts/{nor}.json')))


def test_no_fail_in_markdown_extraction():
    for nor in _SAMPLE_AM_NOR:
        am_to_markdown(transform_arrete_ministeriel(json.load(open(f'data/AM/legifrance_texts/{nor}.json'))))


def test_cell_data_extraction():
    input_ = (
        "<br/>NIVEAU DE BRUIT AMBIANT EXISTANT \n      <br/>\n"
        "    dans les zones à émergence réglementée \n      <br/>\n"
        "    (incluant le bruit de l'installation)"
    )
    assert _extract_cell_data(input_).text == (
        "NIVEAU DE BRUIT AMBIANT EXISTANT\n"
        "dans les zones à émergence réglementée\n"
        "(incluant le bruit de l'installation)"
    )


def test_markdown_to_html():
    table_html = '''
        <div>
            <tr>
                <th>A</th>
                <th>B</th>
                <th>C</th>
            </tr>
            <tr>
                <td colspan="2">D</td>
                <td>F</td>
            </tr>
        </div>
    '''
    table = _extract_table(table_html)
    generated_html_table = table_to_markdown(table)
    assert generated_html_table == (
        '<table><tr><th colspan="1" rowspan="1">A</th>'
        '<th colspan="1" rowspan="1">B</th>'
        '<th colspan="1" rowspan="1">C</th></tr>'
        '<tr><td colspan="2" rowspan="1">D</td>'
        '<td colspan="1" rowspan="1">F</td></tr></table>'
    )


def test_markdown_to_html_with_rowspan():
    table_html = '''
        <div>
            <tr>
                <th>A</th>
                <th>B</th>
                <th>C</th>
            </tr>
            <tr>
                <td rowspan="2">D</td>
                <td>E</td>
                <td>F</td>
            </tr>
            <tr>
                <td>G</td>
                <td>H</td>
            </tr>
        </div>
    '''
    table = _extract_table(table_html)
    generated_html_table = table_to_markdown(table)
    assert generated_html_table == (
        '<table><tr><th colspan="1" rowspan="1">A</th><th colspan="1" rowspan="1">B</th>'
        '<th colspan="1" rowspan="1">C</th></tr><tr><td colspan="1" rowspan="2">D</td>'
        '<td colspan="1" rowspan="1">E</td><td colspan="1" rowspan="1">F</td></tr>'
        '<tr><td colspan="1" rowspan="1">G</td><td colspan="1" rowspan="1">H</td></tr></table>'
    )


def test_compatible_links_extraction():
    links = [Link('', 0, 5), Link('', 0, 4), Link('', 6, 2), Link('', 8, 2)]
    filtered_links = _extract_sorted_links_to_display(links)
    assert len(filtered_links) == 3
    assert filtered_links[0].content_size == 5
    assert filtered_links[1].position == 6
    assert filtered_links[2].position == 8


def test_links_inclusion():
    links = [Link('A', 0, 5), Link('B', 0, 4), Link('C', 6, 2), Link('D', 8, 2)]
    assert _insert_links('Hello PiPa!', links, DataFormat.MARKDOWN) == '[Hello](A) [Pi](C)[Pa](D)!'
    html = _insert_links('Hello PiPa!', links, DataFormat.HTML)
    assert html == '<a href="A">Hello</a> <a href="C">Pi</a><a href="D">Pa</a>!'
