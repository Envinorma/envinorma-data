import json

from lib.am_to_markdown import (
    DataFormat,
    Link,
    _insert_links,
    table_to_markdown,
    _extract_sorted_links_to_display,
    am_to_markdown,
)
from lib.am_structure_extraction import _extract_table, transform_arrete_ministeriel, _load_legifrance_text


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


_SAMPLE_AM_NOR = ['DEVP1706393A', 'TREP1815737A', 'ATEP9870263A', 'DEVP1519168A', 'DEVP1430916A', 'DEVP1001990A']


def test_no_fail_in_markdown_extraction():
    for nor in _SAMPLE_AM_NOR:
        am_to_markdown(
            transform_arrete_ministeriel(_load_legifrance_text(json.load(open(f'data/AM/legifrance_texts/{nor}.json'))))
        )
