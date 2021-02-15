import json
import random

import pytest
from envinorma.config import AM_DATA_FOLDER
from envinorma.data import LegifranceSection, LegifranceText, load_legifrance_text
from envinorma.structure.am_structure_extraction import (
    _BASE_LEGIFRANCE_URL,
    ArreteMinisteriel,
    ArticleStatus,
    EnrichedString,
    LegifranceArticle,
    Link,
    LinkReference,
    StructuredText,
    _add_links_if_any,
    _compute_proximity,
    _delete_or_merge_articles,
    _extract_links,
    _find_references,
    _generate_article_title,
    _group_articles_to_merge,
    _html_to_structured_text,
    _remove_abrogated,
    _remove_links,
    _replace_weird_annexe_words,
    _structure_text,
    remove_empty,
    remove_summaries,
    split_alineas_in_sections,
    transform_arrete_ministeriel,
)
from envinorma.structure.texts_properties import (
    _extract_section_inconsistencies,
    count_articles_in_am,
    count_sections,
    count_tables,
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


def test_remove_links():
    random.seed(0)
    text = 'Hello, how <a href="/rf1">are</a> you <a href="/rf2">now</a> ?'
    rf1 = '$$REF_L$$CD18FC$$REF_R$$'
    rf2 = '$$REF_L$$9FB649$$REF_R$$'
    text, link_references = _remove_links(text)
    assert len(link_references) == 2
    assert link_references[0].target == f'{_BASE_LEGIFRANCE_URL}/rf1'
    assert link_references[0].reference == rf1
    assert link_references[1].target == f'{_BASE_LEGIFRANCE_URL}/rf2'
    assert link_references[1].reference == rf2
    assert text == f'Hello, how {rf1} you {rf2} ?'


def test_find_references():
    links = [LinkReference('RF1', 'rf1', 'are'), LinkReference('RF2', 'rf2', 'now')]
    text = EnrichedString('Hello, how RF1 you RF2 ?', [])
    matches = _find_references(text, links)
    assert len(matches) == 2
    assert matches[0] == links[0]
    assert matches[1] == links[1]


def test_add_links_if_any():
    links = [LinkReference('RF1', 'rf1', 'are'), LinkReference('RF2', 'rf2', 'now')]
    text = EnrichedString('Hello, how RF1 you RF2 ?', [Link('rf0', 0, 5)])
    result = _add_links_if_any(text, links)
    assert len(result.links) == 3
    assert result.links[1].content_size == 3
    assert result.links[2].content_size == 3
    assert result.links[1].target == 'rf1'
    assert result.links[2].target == 'rf2'
    assert result.table is None
    assert result.text == 'Hello, how are you now ?'


def test_structure_extraction():
    text = '''
        <p>Holà</p>
        <p>
            <div>
                <table>
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
                </table>
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


@pytest.mark.filterwarnings('ignore')
def test_no_fail_in_structure_extraction():
    for nor in _SAMPLE_AM_NOR:
        transform_arrete_ministeriel(
            load_legifrance_text(json.load(open(f'{AM_DATA_FOLDER}/legifrance_texts/{nor}.json')))
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
    article_0 = LegifranceArticle('0', '', 0, None, ArticleStatus('VIGUEUR'))
    article_1 = LegifranceArticle('1', '', 1, '1', ArticleStatus('VIGUEUR'))
    article_2 = LegifranceArticle('2', '', 2, '2', ArticleStatus('VIGUEUR'))
    article_3 = LegifranceArticle('3', '', 3, None, ArticleStatus('VIGUEUR'))

    groups = _group_articles_to_merge([article_0, article_1, article_2, article_3])
    assert len(groups) == 3
    first_elt = groups[0]
    assert isinstance(first_elt, LegifranceArticle) and first_elt.id == article_0.id
    second_elt = groups[1]
    assert isinstance(second_elt, LegifranceArticle) and second_elt.id == article_1.id
    third_group = groups[2]
    assert isinstance(third_group, tuple)
    assert third_group[0].id == article_2.id
    assert third_group[1].id == article_3.id


def test_delete_or_merge_articles():
    sentence_1 = 'l\'exploitant informera immédiatement l\'inspection des installations classées en cas d\'accident'
    sentence_2 = 'l\'exploitant informera immédiatement l\'inspection des installations classées en cas d\'accident !'
    sentence_3 = 'Les VLE sont disponibles dans ce tableau:'
    sentence_4 = '<table><tr><td>CO <= 0.6 unités</table></tr></td>'
    articles = [
        LegifranceArticle('0', '', 0, None, ArticleStatus('VIGUEUR')),
        LegifranceArticle('1', '', 1, '1', ArticleStatus('VIGUEUR')),
        LegifranceArticle('2', sentence_1, 2, '2', ArticleStatus('VIGUEUR')),
        LegifranceArticle('3', sentence_2, 3, None, ArticleStatus('VIGUEUR')),
        LegifranceArticle('4', sentence_3, 4, '3', ArticleStatus('VIGUEUR')),
        LegifranceArticle('5', sentence_4, 5, None, ArticleStatus('VIGUEUR')),
    ]
    new_articles = _delete_or_merge_articles(articles)
    assert len(new_articles) == 4
    assert [article.id for article in new_articles] == ['0', '1', '2', '4']
    assert new_articles[2].content == articles[2].content
    assert articles[4].content in new_articles[3].content and articles[4].content in new_articles[3].content

    articles = [
        LegifranceArticle('1', '', 1, None, ArticleStatus('VIGUEUR')),
        LegifranceArticle('0', '', 0, None, ArticleStatus('VIGUEUR')),
    ]
    new_articles = _delete_or_merge_articles(articles)
    assert len(new_articles) == 1
    assert new_articles[0].id == '0'
    assert new_articles[0].content == '\n<br/>\n'


def _get_am(filename: str) -> ArreteMinisteriel:
    raw_text = load_legifrance_text(json.load(open(filename)))
    return transform_arrete_ministeriel(raw_text, am_id=f'FAKE_ID_{filename}')


@pytest.mark.filterwarnings('ignore')
def test_structuration():
    am_1 = _get_am('test_data/AM/legifrance_texts/DEVP1706393A.json')
    assert count_sections(am_1) == 93
    assert count_tables(am_1) == 5
    assert count_articles_in_am(am_1) == 14
    assert len(am_1.sections) == 14


@pytest.mark.filterwarnings('ignore')
def test_structuration_2():
    am_2 = _get_am('test_data/AM/legifrance_texts/TREP1835514A.json')
    assert count_sections(am_2) == 89
    assert count_tables(am_2) == 9
    assert count_articles_in_am(am_2) == 60
    assert len(am_2.sections) == 6


def test_structuration_3():
    am_3 = _get_am('test_data/AM/legifrance_texts/fake_am.json')
    assert count_sections(am_3) == 101
    assert count_tables(am_3) == 1
    assert count_articles_in_am(am_3) == 1
    assert len(am_3.sections) == 1


def test_inconsistency_detection():
    subsections = [
        StructuredText(EnrichedString('1. Foo'), [], [], None),
        StructuredText(EnrichedString('2. Bar'), [], [], None),
        StructuredText(EnrichedString('3. Pi'), [], [], None),
        StructuredText(EnrichedString('4. Pa'), [], [], None),
    ]
    section = StructuredText(EnrichedString(''), [], subsections, None)
    inconsistencies = _extract_section_inconsistencies(section)
    assert len(inconsistencies) == 0

    subsections_err = [*subsections, StructuredText(EnrichedString('4. Pou'), [], [], None)]
    section_err = StructuredText(EnrichedString(''), [], subsections_err, None)
    inconsistencies_err = _extract_section_inconsistencies(section_err)
    assert len(inconsistencies_err) == 1


def test_structure_text():
    alineas = ['I. Foo', 'A. pi', 'hola', 'B. pa', 'quetal', 'C. po', 'II. Bar']
    text = _structure_text('', alineas)
    assert len(text.sections) == 2
    assert len(text.outer_alineas) == 0
    assert text.sections[0].title.text == 'I. Foo'
    assert text.sections[1].title.text == 'II. Bar'
    assert len(text.sections[0].sections) == 3
    assert text.sections[0].sections[0].title.text == 'A. pi'
    assert text.sections[0].sections[1].title.text == 'B. pa'
    assert text.sections[0].sections[2].title.text == 'C. po'


# def test_structure_text_2():
#     alineas = ['I. Foo', 'a) pi', 'hola', 'b) pa', 'quetal', 'c) po', 'II. Bar']
#     text = _structure_text('', alineas)
#     assert len(text.sections) == 2
#     assert len(text.outer_alineas) == 0
#     assert text.sections[0].title.text == 'I. Foo'
#     assert text.sections[1].title.text == 'II. Bar'
#     assert len(text.sections[0].sections) == 0


def test_remove_summaries():
    alineas_str = '''
PRESCRIPTIONS GÉNÉRALES APPLICABLES AUX INSTALLATIONS CLASSÉES POUR LA PROTECTION DE L'ENVIRONNEMENT [...]

SOMMAIRE

Annexe I.
1. Dispositions générales.
1.1. Conformité de l'installation.
1.2. Modifications.
1.3. Contenu de la déclaration.
2. Implantation. ― Aménagement.
2.1. Règles d'implantation.
2.2. Intégration dans le paysage.

Annexe II.
Modalités de calcul du dimensionnement du plan d'épandage.

Définitions

Au sens du présent arrêté, on entend par :
"Habitation" : un local destiné à servir de résidence permanente ou temporaire à des personnes, [...]
"Local habituellement occupé par des tiers" : un local destiné à être utilisé couramment par des [...]
'''
    alineas = remove_empty(alineas_str.split('\n'))
    filtered_alineas = remove_summaries(alineas)
    assert filtered_alineas == alineas[:1] + alineas[-4:]


def test_generate_article_title():
    article_1 = LegifranceArticle('', '', 0, 'Annexe I', ArticleStatus.VIGUEUR)
    outer_alineas_1 = [
        EnrichedString('DISPOSITIONS GENERALES'),
        EnrichedString('APPLICABLES AUX INSTALLATIONS EXISTANTES'),
        EnrichedString('Cf ci-dessous'),
    ]
    expected = 'Annexe I - DISPOSITIONS GENERALES APPLICABLES AUX INSTALLATIONS EXISTANTES'
    assert _generate_article_title(article_1, outer_alineas_1)[0].text == expected
    assert _generate_article_title(article_1, outer_alineas_1)[1][0].text == 'Cf ci-dessous'
    assert _generate_article_title(article_1, outer_alineas_1[:1])[0].text == 'Annexe I - DISPOSITIONS GENERALES'
    assert _generate_article_title(article_1, [])[0].text == 'Annexe I'

    article_2 = LegifranceArticle('', '', 0, 'Annexes', ArticleStatus.VIGUEUR)
    outer_alineas_2 = [
        EnrichedString('Dispositions generales applicables aux installations existantes:'),
        EnrichedString('Cf ci-dessous'),
    ]
    assert _generate_article_title(article_2, outer_alineas_2)[0].text == 'Annexes'
    assert _generate_article_title(article_2, outer_alineas_2)[1][0] == outer_alineas_2[0]
    assert _generate_article_title(article_2, outer_alineas_2)[1][1] == outer_alineas_2[1]

    article_3 = LegifranceArticle('', '', 0, '1', ArticleStatus.VIGUEUR)
    outer_alineas_3 = [EnrichedString('Valeurs limites d\'émission.'), EnrichedString('Cf ci-dessous')]
    assert _generate_article_title(article_3, outer_alineas_3)[0].text == 'Article 1 - Valeurs limites d\'émission.'
    assert _generate_article_title(article_3, outer_alineas_3)[1][0] == outer_alineas_3[1]

    article_4 = LegifranceArticle('', '', 0, '1', ArticleStatus.VIGUEUR)
    outer_alineas_4 = [
        EnrichedString('L\'exploitant doit respecter les valeurs limites d\'émission suivantes:'),
        EnrichedString('CO2: 403'),
    ]
    assert _generate_article_title(article_4, outer_alineas_4)[0].text == 'Article 1'
    assert _generate_article_title(article_4, outer_alineas_4)[1][0] == outer_alineas_4[0]
    assert _generate_article_title(article_4, outer_alineas_4)[1][1] == outer_alineas_4[1]


def test_split_alineas_in_sections():
    lines = list('abcdefghijklmnopqrst')
    matches = [False] * len(lines)
    alineas, sections = split_alineas_in_sections(lines, matches)
    assert len(sections) == 0
    assert len(alineas) == len(lines)

    lines = list('abcdefghijklmnopqrst')
    matches = [False] * len(lines)
    matches[1] = True
    alineas, sections = split_alineas_in_sections(lines, matches)
    assert alineas == ['a']
    assert len(sections) == 1
    assert sections[0] == lines[1:]

    lines = list('abcdefghijklmnopqrst')
    matches = [False] * len(lines)
    matches[1] = True
    matches[3] = True
    matches[4] = True
    alineas, sections = split_alineas_in_sections(lines, matches)
    assert alineas == ['a']
    assert len(sections) == 3
    assert sections[0] == lines[1:3]
    assert sections[1] == [lines[3]]
    assert sections[2] == lines[4:]


def test_remove_abrogated():
    empty_text = LegifranceText('visa', 'title', [], [])
    assert _remove_abrogated(empty_text) == empty_text

    empty_section = LegifranceSection(0, 'visa', [], [], ArticleStatus.ABROGE)
    assert _remove_abrogated(empty_section) == empty_section

    empty_section = LegifranceSection(0, 'visa', [], [], ArticleStatus.ABROGE)
    text = LegifranceText('visa', 'title', [], [empty_section])
    assert _remove_abrogated(text) == empty_text

    article = LegifranceArticle('id', 'content', 0, '1er', ArticleStatus.ABROGE)
    empty_section = LegifranceSection(0, 'visa', [], [], ArticleStatus.ABROGE)
    text = LegifranceText('visa', 'title', [article], [empty_section])
    assert _remove_abrogated(text) == empty_text

    article = LegifranceArticle('id', 'content', 0, '1er', ArticleStatus.VIGUEUR)
    empty_section = LegifranceSection(0, 'visa', [], [], ArticleStatus.ABROGE)
    text = LegifranceText('visa', 'title', [article], [empty_section])
    assert _remove_abrogated(text) == LegifranceText('visa', 'title', [article], [])

    article = LegifranceArticle('id', 'content', 0, '1er', ArticleStatus.VIGUEUR)
    empty_section = LegifranceSection(0, 'visa', [], [], ArticleStatus.VIGUEUR)
    text = LegifranceText('visa', 'title', [article], [empty_section])
    assert _remove_abrogated(text) == LegifranceText('visa', 'title', [article], [empty_section])

    article = LegifranceArticle('id', 'content', 0, '1er', ArticleStatus.VIGUEUR)
    section = LegifranceSection(0, 'visa', [], [], ArticleStatus.ABROGE)
    section_2 = LegifranceSection(0, 'visa', [article], [section], ArticleStatus.VIGUEUR)
    text = LegifranceText('visa', 'title', [article], [section_2])
    assert _remove_abrogated(text) == LegifranceText(
        'visa', 'title', [article], [LegifranceSection(0, 'visa', [article], [], ArticleStatus.VIGUEUR)]
    )
