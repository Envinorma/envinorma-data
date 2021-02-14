import json

import pytest
from envinorma.config import AM_DATA_FOLDER
from envinorma.data import load_legifrance_text
from envinorma.io.markdown import (
    DataFormat,
    Link,
    _extract_sorted_links_to_display,
    _insert_links,
    am_to_markdown,
    extract_markdown_text,
    table_to_markdown,
)
from envinorma.structure.am_structure_extraction import (
    ArticleStatus,
    LegifranceArticle,
    LegifranceSection,
    _extract_sections,
    _structure_text,
    extract_table,
    transform_arrete_ministeriel,
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
    table = extract_table(table_html)
    generated_html_table = table_to_markdown(table)
    assert generated_html_table == (
        '<table><tr><th>A</th><th>B</th><th>C</th></tr><tr><td colspan="2">D</td><td>F</td></tr></table>'
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
    table = extract_table(table_html)
    generated_html_table = table_to_markdown(table)
    assert generated_html_table == (
        '<table><tr><th>A</th><th>B</th>'
        '<th>C</th></tr><tr><td rowspan="2">D</td>'
        '<td>E</td><td>F</td></tr>'
        '<tr><td>G</td><td>H</td></tr></table>'
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


@pytest.mark.filterwarnings('ignore')
def test_no_fail_in_markdown_extraction():
    for nor in _SAMPLE_AM_NOR:
        am_to_markdown(
            transform_arrete_ministeriel(
                load_legifrance_text(json.load(open(f'{AM_DATA_FOLDER}/legifrance_texts/{nor}.json')))
            )
        )


def test_structure_via_markdown():
    strs = [
        "1. Dispositions générales",
        "1. 1. Conformité de l'installation au dossier d'enregistrement",
        "1. 2. Dossier installation classée",
        "1. 3. Intégration dans le paysage",
        "2. Risques",
        "2. 1. Généralités",
        "2. 1. 1. Surveillance de l'installation",
        "1. Les zones d'effets Z1 et Z2 définies par l'arrêté du 20 a erez",  # in EXCEPTION_PREFIXES
        "2. 1. 2. Clôture",
        "2. 1. 3. Entretien de l'installation",
        "2. 2. Implantation",
        "2. 2. 1. Distances d'éloignement",
        "2. 2. 1. 1. Installations nouvelles",
    ]
    text = _structure_text('', strs)
    res = extract_markdown_text(text, 0)
    assert res[1][:2] == '# '
    assert res[2][:3] == '## '
    assert res[3][:3] == '## '
    assert res[4][:3] == '## '
    assert res[5][:2] == '# '
    assert res[6][:3] == '## '
    assert res[7][:4] == '### '
    assert res[8][:4] == '1. L'


def test_existing_installations():
    alineas_strs = [
        '''
1. Dispositions générales.
1.1. Conformité de l'installation.
1.2. Modifications.
1.3. Contenu de la déclaration.
2. Implantation. ― Aménagement.
2.1. Règles d'implantation.
2.2. Intégration dans le paysage.
    ''',
        '''
1. Dispositions générales.
1.1. Conformité de l'installation.
1.2. Modifications.
1.3. Contenu de la déclaration.
2. Implantation. ― Aménagement.
2.1. Règles d'implantation.
2.2. Intégration dans le paysage.
    ''',
    ]
    titles = ['A. First title', 'B. Dispositions applicables aux installations existantes.']
    alineas_html = [str_.replace('\n', '<br/>') for str_ in alineas_strs]
    sections = [
        LegifranceSection(
            i,
            title,
            [LegifranceArticle('', html, i, f'Annexe {i}', ArticleStatus('VIGUEUR'))],
            [],
            ArticleStatus('VIGUEUR'),
        )
        for i, (title, html) in enumerate(zip(titles, alineas_html))
    ]
    res = [extract_markdown_text(sec, 1) for sec in _extract_sections([], sections, [])]

    expected_res = [
        [
            "# A. First title",
            "## Annexe 0",
            "### 1. Dispositions générales.",
            "#### 1.1. Conformité de l'installation.",
            "#### 1.2. Modifications.",
            "#### 1.3. Contenu de la déclaration.",
            "### 2. Implantation. ― Aménagement.",
            "#### 2.1. Règles d'implantation.",
            "#### 2.2. Intégration dans le paysage.",
        ],
        [
            "# B. Dispositions applicables aux installations existantes.",
            "## Annexe 1",
            "1. Dispositions générales.",
            "1.1. Conformité de l'installation.",
            "1.2. Modifications.",
            "1.3. Contenu de la déclaration.",
            "2. Implantation. ― Aménagement.",
            "2.1. Règles d'implantation.",
            "2.2. Intégration dans le paysage.",
        ],
    ]

    for true, expected in zip(res, expected_res):
        assert len(true) == len(expected)
        for true_elt, expected_elt in zip(true, expected):
            assert true_elt == expected_elt
