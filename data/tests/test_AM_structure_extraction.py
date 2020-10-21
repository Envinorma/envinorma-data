import json
from AM_structure_extraction import _extract_links, _html_to_structured_text, transform_arrete_ministeriel


def test_link_extraction():
    text = 'Hello, how <a href="rf">are</a>'
    enriched_text = _extract_links(text)
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


def test_no_fail_in_structure_extraction():
    for filename in ['AM_1510.json', 'AM_2515.json', 'AM_2517.json', 'AM_2521.json']:
        transform_arrete_ministeriel(json.load(open(f'data/legifrance_AM/{filename}')))

