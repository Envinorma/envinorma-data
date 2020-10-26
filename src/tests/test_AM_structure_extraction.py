import json
from lib.am_structure_extraction import (
    _extract_links,
    _html_to_structured_text,
    transform_arrete_ministeriel,
    _extract_cell_data,
    _load_legifrance_text,
    _load_legifrance_text,
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
        transform_arrete_ministeriel(_load_legifrance_text(json.load(open(f'data/AM/legifrance_texts/{nor}.json'))))


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

