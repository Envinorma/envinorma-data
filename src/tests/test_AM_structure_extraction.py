import json
from lib.am_structure_extraction import (
    LegifranceArticle,
    _extract_links,
    _html_to_structured_text,
    transform_arrete_ministeriel,
    _extract_cell_data,
    _load_legifrance_text,
    _replace_weird_annexe_words,
    _compute_proximity,
    _group_articles_to_merge,
    _delete_or_merge_articles,
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


def test_weird_annexe_replacement():
    inputs_outputs = [
        ('A N N E X E S I I', 'ANNEXES I I'),
        ('A N N E X E I I I', 'ANNEXE III'),
        ('A N N E X E I V', 'ANNEXE IV'),
        ('A N N E X E I I', 'ANNEXE II'),
        ('A N N E X E V', 'ANNEXE V'),
        ('A N N E X E V I', 'ANNEXE VI'),
    ]
    for input_, output in inputs_outputs:
        assert output == _replace_weird_annexe_words(input_)


def test_compute_proximity():
    sentence_1 = 'l\'exploitant informera immédiatement l\'inspection des installations classées en cas d\'accident'
    sentence_2 = 'l\'exploitant informera immédiatement l\'inspection des installations classées en cas d\'accident !'
    assert _compute_proximity(sentence_1, '') == 0
    assert _compute_proximity(sentence_1, 'Bonjour, comment allez vous ?') <= 0.5
    assert _compute_proximity(sentence_1, sentence_2) >= 0.5


def test_group_articles_to_merge():
    article_0 = LegifranceArticle('0', '', 0, None)
    article_1 = LegifranceArticle('1', '', 1, '1')
    article_2 = LegifranceArticle('2', '', 2, '2')
    article_3 = LegifranceArticle('3', '', 3, None)

    groups = _group_articles_to_merge([article_0, article_1, article_2, article_3])
    assert len(groups) == 3
    group_1, group_2, group_3 = groups
    assert isinstance(group_1, LegifranceArticle) and group_1.id == article_0.id
    assert isinstance(group_2, LegifranceArticle) and group_2.id == article_1.id
    assert isinstance(group_3, tuple) and group_3[0].id == article_2.id
    assert isinstance(group_3, tuple) and group_3[1].id == article_3.id


def test_delete_or_merge_articles():
    sentence_1 = 'l\'exploitant informera immédiatement l\'inspection des installations classées en cas d\'accident'
    sentence_2 = 'l\'exploitant informera immédiatement l\'inspection des installations classées en cas d\'accident !'
    sentence_3 = 'Les VLE sont disponibles dans ce tableau:'
    sentence_4 = '<table><tr><td>CO <= 0.6 unités</table></tr></td>'
    articles = [
        LegifranceArticle('0', '', 0, None),
        LegifranceArticle('1', '', 1, '1'),
        LegifranceArticle('2', sentence_1, 2, '2'),
        LegifranceArticle('3', sentence_2, 3, None),
        LegifranceArticle('4', sentence_3, 4, '3'),
        LegifranceArticle('5', sentence_4, 5, None),
    ]
    new_articles = _delete_or_merge_articles(articles)
    assert len(new_articles) == 4
    assert [article.id for article in new_articles] == ['0', '1', '2', '4']
    assert new_articles[2].content == articles[2].content
    assert articles[4].content in new_articles[3].content and articles[4].content in new_articles[3].content
