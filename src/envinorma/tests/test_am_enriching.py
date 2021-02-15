import json

import pytest
from envinorma.am_enriching import (
    _extract_special_prefix,
    _extract_summary_elements,
    _is_prefix,
    _is_probably_section_number,
    _merge_prefix_list,
    _remove_html,
    _remove_last_word,
    _shorten_summary_text,
    add_inspection_sheet_in_table_rows,
    add_links_in_enriched_string,
    add_links_to_am,
    add_references,
    add_topics,
    extract_titles_and_reference_pairs,
    remove_prescriptive_power,
    remove_sections,
)
from envinorma.config import AM_DATA_FOLDER
from envinorma.data import ArreteMinisteriel, Cell, EnrichedString, Hyperlink, Link, Row, StructuredText, Table
from envinorma.topics.patterns import TopicName


def test_add_topics():
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None)
    section_2 = StructuredText(EnrichedString('Section 2'), [], [], None)
    am = ArreteMinisteriel(EnrichedString(''), [section_1, section_2], [], '', id='FAKE_ID')

    am_with_topics = add_topics(
        am, {(0,): TopicName.INCENDIE, (0, 0): TopicName.INCENDIE, (1,): TopicName.BRUIT_VIBRATIONS}
    )
    assert am_with_topics.sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_topics.sections[0].sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_topics.sections[1].annotations.topic == TopicName.BRUIT_VIBRATIONS

    am_with_non_prescriptive = remove_prescriptive_power(am_with_topics, {(1,)})
    assert am_with_non_prescriptive.sections[0].annotations.prescriptive
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.prescriptive
    assert not am_with_non_prescriptive.sections[1].annotations.prescriptive

    assert am_with_non_prescriptive.sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.topic == TopicName.INCENDIE
    assert am_with_non_prescriptive.sections[1].annotations.topic == TopicName.BRUIT_VIBRATIONS


def test_extract_special_prefix():
    assert _extract_special_prefix('Annexe I') == 'Annexe I'
    assert _extract_special_prefix('ANNEXE I') == 'Annexe I'
    assert _extract_special_prefix('ANNEXE') == 'Annexe'
    assert _extract_special_prefix('ANNEXE CONCERNANT LES DISPOSITIONS') == 'Annexe ?'
    assert _extract_special_prefix('Article fixant les dispositions') == 'Art. ?'
    assert _extract_special_prefix('Article 1') == 'Art. 1'
    assert _extract_special_prefix('Article 2.21') == 'Art. 2.21'
    assert _extract_special_prefix('Bonjour') is None


def test_is_probably_section_number():
    assert _is_probably_section_number('I.')
    assert _is_probably_section_number('1.1.')
    assert _is_probably_section_number('A.')
    assert _is_probably_section_number('III')
    assert _is_probably_section_number('a)')
    assert not _is_probably_section_number('Dispositions')
    assert not _is_probably_section_number('Bonjour')


def test_is_prefix():
    assert _is_prefix('1. ', '1.1.')
    assert _is_prefix('1. ', '1. 2.')
    assert _is_prefix('2. 4.', '2. 4. 1.')
    assert _is_prefix('1. ', '1. BONJOUR')
    assert not _is_prefix('1. ', '2. ')
    assert not _is_prefix('1. ', '2. 1. ')
    assert not _is_prefix('1. ', 'A.')


def test_merge_prefix_list():
    assert _merge_prefix_list(['1.', '2.', '3.', '4.']) == '1. 2. 3. 4.'
    assert _merge_prefix_list(['1.', '1.1.', '1.1.1.']) == '1.1.1.'
    assert _merge_prefix_list(['Art. 1.', '2.', '2. 1.']) == 'Art. 1. 2. 1.'
    assert _merge_prefix_list(['Section II', 'Chapitre 4', 'Art. 10']) == 'Section II Chapitre 4 Art. 10'


def test_add_references():
    sub_sub_sections = [
        StructuredText(EnrichedString('1.1. azeaze'), [], [], None, None),
        StructuredText(EnrichedString('1. 2. azeaze'), [], [], None, None),
    ]
    sub_sections = [StructuredText(EnrichedString('1. azeaze'), [], sub_sub_sections, None, None)]
    lf_article_id = 'article_id'
    sections = [
        StructuredText(EnrichedString('Article 1. efzefz'), [], sub_sections, None, lf_article_id),
        StructuredText(EnrichedString('2. zefez'), [], [], None, lf_article_id),
        StructuredText(EnrichedString('A. zefze'), [], [], None, lf_article_id),
        StructuredText(EnrichedString('a) zefze'), [], [], None, lf_article_id),
        StructuredText(EnrichedString('V. zefze'), [], [], None, lf_article_id),
        StructuredText(EnrichedString('ANNEXE I zefze'), [], [], None, lf_article_id),
        StructuredText(EnrichedString('Article 18.1'), [], [], None, lf_article_id),
        StructuredText(EnrichedString('Article 1'), [], [], None, lf_article_id),
    ]
    am = ArreteMinisteriel(EnrichedString(''), sections, [], '', id='FAKE_ID')
    am_with_references = add_references(am)

    assert am_with_references.sections[0].reference_str == 'Art. 1.'
    assert am_with_references.sections[0].sections[0].reference_str == 'Art. 1. 1.'
    assert am_with_references.sections[0].sections[0].sections[0].reference_str == 'Art. 1. 1.1.'
    assert am_with_references.sections[0].sections[0].sections[1].reference_str == 'Art. 1. 1.2.'
    assert am_with_references.sections[1].reference_str == '2.'
    assert am_with_references.sections[2].reference_str == 'A.'
    assert am_with_references.sections[3].reference_str == 'a)'
    assert am_with_references.sections[4].reference_str == 'V.'
    assert am_with_references.sections[5].reference_str == 'Annexe I'
    assert am_with_references.sections[6].reference_str == 'Art. 18.1'
    assert am_with_references.sections[7].reference_str == 'Art. 1'


def test_add_references_2():
    am = ArreteMinisteriel.from_dict(json.load(open('test_data/AM/minified_texts/DEVP1235896A.json')))
    expected = [
        ('Article 1', 'Art. 1'),
        ('Article 2', 'Art. 2'),
        ('Chapitre Ier : Dispositions générales', ''),
        ('Article 3', 'Art. 3'),
        ('Article 4', 'Art. 4'),
        ('Article 5', 'Art. 5'),
        ('Article 6', 'Art. 6'),
        ('Article 7', 'Art. 7'),
        ('Chapitre II : Prévention des accidents et des pollutions', ''),
        ('Section I : Généralités', ''),
        ('Article 8', 'Art. 8'),
        ('Article 9', 'Art. 9'),
        ('Article 10', 'Art. 10'),
        ('Article 11', 'Art. 11'),
        ('Article 12', 'Art. 12'),
        ('Section II : Tuyauteries de fluides', ''),
        ('Article 13', 'Art. 13'),
        ('Section III : Comportement au feu des locaux', ''),
        ('Article 14', 'Art. 14'),
        ('Section IV : Dispositions de sécurité', ''),
        ('Article 15', 'Art. 15'),
        ('Article 16', 'Art. 16'),
        ('Article 17', 'Art. 17'),
        ('Section V : Exploitation', ''),
        ('Article 18', 'Art. 18'),
        ('Article 19', 'Art. 19'),
        ('Article 20', 'Art. 20'),
        ('Section VI : Pollutions accidentelles', ''),
        ('Article 21', 'Art. 21'),
        ("I. ― Tout stockage d'un liquide susceptible", 'Art. 21 I.'),
        ("II. ― La capacité de rétention est étanche ", 'Art. 21 II.'),
        ('III. ― Rétention et confinement.', 'Art. 21 III.'),
        ("IV. ― Isolement des réseaux d'eau.", 'Art. 21 IV.'),
        ("Chapitre III : Emissions dans l'eau", ''),
        ('Section I : Principes généraux', ''),
        ('Article 22', 'Art. 22'),
        ("Section II : Prélèvements et consommation d'eau", ''),
        ('Article 23', 'Art. 23'),
        ('Article 24', 'Art. 24'),
        ('Article 25', 'Art. 25'),
        ('Section III : Collecte et rejet des effluents liquides', ''),
        ('Article 26', 'Art. 26'),
        ('Article 27', 'Art. 27'),
        ('Article 28', 'Art. 28'),
        ('Article 29', 'Art. 29'),
        ('Article 30', 'Art. 30'),
        ('Section IV : Valeurs limites de rejet', ''),
        ('Article 31', 'Art. 31'),
        ('Article 32', 'Art. 32'),
        ('Article 33', 'Art. 33'),
        ('Article 34', 'Art. 34'),
        ('Section V : Traitement des effluents', ''),
        ('Article 35', 'Art. 35'),
        ('Article 36', 'Art. 36'),
        ("Chapitre IV : Emissions dans l'air", ''),
        ('Section I : Généralités', ''),
        ('Article 37', 'Art. 37'),
        ("Section II : Rejets à l'atmosphère", ''),
        ('Article 38', 'Art. 38'),
        ('Article 39', 'Art. 39'),
        ("Section III : Valeurs limites d'émission", ''),
        ('Article 40', 'Art. 40'),
        ('Article 41', 'Art. 41'),
        ("a) Capacité d'aspiration supérieure à 7 000 m³/h.", 'Art. 41 a)'),
        ("b) Capacité d'aspiration inférieure ou égale à 7 000 m3/h.", 'Art. 41 b)'),
        ('Article 42', 'Art. 42'),
        ('Chapitre V : Emissions dans les sols', ''),
        ('Article 43', 'Art. 43'),
        ('Chapitre VI : Bruit et vibrations', ''),
        ('Article 44', 'Art. 44'),
        ('Article 45', 'Art. 45'),
        ('Article 46', 'Art. 46'),
        ('Article 47', 'Art. 47'),
        ('Article 48', 'Art. 48'),
        ('Article 49', 'Art. 49'),
        ('Article 50', 'Art. 50'),
        ('Article 51', 'Art. 51'),
        ('1. Eléments de base.', 'Art. 51 1.'),
        ('2. Appareillage de mesure.', 'Art. 51 2.'),
        ('3. Précautions opératoires.', 'Art. 51 3.'),
        ('Article 52', 'Art. 52'),
        ('1. Pour les établissements existants :', 'Art. 52 1.'),
        ('2. Pour les nouvelles installations :', 'Art. 52 2.'),
        ("3. Pour les installations fonctionnant sur une ", 'Art. 52 3.'),
        ('Chapitre VII : Déchets', ''),
        ('Article 53', 'Art. 53'),
        ('Article 54', 'Art. 54'),
        ('Article 55', 'Art. 55'),
        ('Chapitre VIII : Surveillance des émissions', ''),
        ('Section I : Généralités', ''),
        ('Article 56', 'Art. 56'),
        ("Section II : Emissions dans l'air", ''),
        ('Article 57', 'Art. 57'),
        ("Section III : Emissions dans l'eau", ''),
        ('Article 58', 'Art. 58'),
        ('Section VI : Impacts sur les eaux souterraines', ''),
        ('Article 59', 'Art. 59'),
        ('Chapitre IX : Exécution', ''),
        ('Article 60', 'Art. 60'),
        ('Annexes', ''),
        ('Article Annexe I', 'Annexe I'),
        ('1. Définitions.', 'Annexe I 1.'),
        ('1.1. Niveau de pression acoustique continu équivalent pondéré A " court ", LAeq, t.', 'Annexe I 1.1.'),
        ('1.2. Niveau acoustique fractile, LAN, t.', 'Annexe I 1.2.'),
        ('1.3. Intervalle de mesurage.', 'Annexe I 1.3.'),
        ("1.4. Intervalle d'observation.", 'Annexe I 1.4.'),
        ('1.5. Intervalle de référence.', 'Annexe I 1.5.'),
        ('1.6. Bruit ambiant.', 'Annexe I 1.6.'),
        ('1.7. Bruit particulier (1).', 'Annexe I 1.7.'),
        ('1.8. Bruit résiduel.', 'Annexe I 1.8.'),
        ('1.9. Tonalité marquée.', 'Annexe I 1.9.'),
        ("2. Méthode d'expertise (point 6 de la norme).", 'Annexe I 2.'),
        ('2.1. Appareillage de mesure (point 6.1 de la norme).', 'Annexe I 2.1.'),
        ('2.2. Conditions de mesurage (point 6.2 de la norme).', 'Annexe I 2.2.'),
        ('2.3. Gamme de fréquence (point 6.3 de la norme).', 'Annexe I 2.3.'),
        ('2.4. Conditions météorologiques (point 6.4 de la norme).', 'Annexe I 2.4.'),
        ('2.5. Indicateurs (point 6.5 de la norme).', 'Annexe I 2.5.'),
        ('a) Contrôle des niveaux de bruit admissibles en limites de propriété.', 'Annexe I 2.5. a)'),
        ("b) Contrôle de l'émergence.", 'Annexe I 2.5. b)'),
        ("2.6. Acquisitions des données, choix ", 'Annexe I 2.6.'),
        ('3. Méthode de contrôle (point 5 de la norme).', 'Annexe I 3.'),
        ('4. Rapport de mesurage (point 7 de la norme).', 'Annexe I 4.'),
        ('Article Annexe II', 'Annexe II'),
    ]
    res = extract_titles_and_reference_pairs(add_references(am))
    for exp, computed in zip(expected, res):
        assert exp[0][:10] == computed[0][:10]
        assert exp[1][:10] == computed[1][:10]


def test_link_addition():
    input_str = EnrichedString('This cat is called Pipa. Yes this cat.', [Link('example.com', 0, 4)])
    new_str = add_links_in_enriched_string(input_str, {'cat': 'example.com/cat', 'Pipa.': 'example.com/pipa'})
    assert len(new_str.links) == 4
    assert sum([link.content_size == 3 for link in new_str.links]) == 2
    assert sum([link.content_size == 4 for link in new_str.links]) == 1
    assert sum([link.content_size == 5 for link in new_str.links]) == 1
    assert sum([link.target == 'example.com' for link in new_str.links]) == 1
    assert sum([link.target == 'example.com/cat' for link in new_str.links]) == 2
    assert sum([link.target == 'example.com/pipa' for link in new_str.links]) == 1


_SAMPLE_AM_NOR = ['DEVP1706393A', 'ATEP9760292A', 'DEVP1235896A', 'DEVP1329353A', 'TREP1900331A', 'TREP2013116A']


@pytest.mark.filterwarnings('ignore')
def test_no_fail_in_aida_links_addition():
    for nor in _SAMPLE_AM_NOR:
        links_json = json.load(open(f'data/aida/hyperlinks/{nor}.json'))
        links = [Hyperlink(**link_doc) for link_doc in links_json]
        add_links_to_am(
            ArreteMinisteriel.from_dict(json.load(open(f'{AM_DATA_FOLDER}/structured_texts/{nor}.json'))), links
        )


def test_compute_summary():
    text = StructuredText(EnrichedString('Test_D2', []), [], [], None)
    parent_text = StructuredText(EnrichedString('Test_D1', []), [], [text] * 2, None)
    grand_parent_text = StructuredText(EnrichedString('Test_D0', []), [], [parent_text] * 2, None)
    summary_elements = _extract_summary_elements(grand_parent_text, 0)
    assert len(summary_elements) == 7
    assert summary_elements[0].depth == 0
    assert summary_elements[1].depth == 1
    assert summary_elements[2].depth == 2
    assert summary_elements[3].depth == 2
    assert summary_elements[4].depth == 1
    assert summary_elements[5].depth == 2
    assert summary_elements[6].depth == 2
    assert summary_elements[-1].section_title == 'Test_D2'
    assert summary_elements[-1].section_id == text.id


def test_remove_last_word():
    assert _remove_last_word('Hello Pipa!') == 'Hello'
    assert _remove_last_word('Hello Pipa, how are you ?') == 'Hello Pipa, how are you'


def test_shorten_summary_text():
    assert _shorten_summary_text('Pipa is a cat', 8) == 'Pipa is [...]'
    title = (
        "c) Dans le cas de rejet dans le milieu naturel (ou "
        "dans un réseau d'assainissement collectif dépourvu de stati"
    )
    assert _shorten_summary_text(title) == 'c) Dans le cas de rejet dans le milieu naturel (ou dans un [...]'


def test_remove_sections():
    sub_sub_sections = [
        StructuredText(EnrichedString('1.1. azeaze'), [], [], None),
        StructuredText(EnrichedString('1. 2. azeaze'), [], [], None),
    ]
    sub_sections = [StructuredText(EnrichedString('1. azeaze'), [], sub_sub_sections, None)]
    sections = [
        StructuredText(EnrichedString('Article 1. efzefz'), [], sub_sections, None),
        StructuredText(EnrichedString('2. zefez'), [], [], None),
        StructuredText(EnrichedString('A. zefze'), [], [], None),
    ]
    am = ArreteMinisteriel(EnrichedString(''), sections, [], '', id='FAKE_ID')

    am_1 = remove_sections(am, {(0,)})
    assert len(am_1.sections) == 2
    assert len(am_1.sections[0].sections) == 0
    am_2 = remove_sections(am, {(1,)})
    assert len(am_2.sections) == 2
    assert len(am_2.sections[0].sections) == 1
    am_3 = remove_sections(am, {(0, 0)})
    assert len(am_3.sections) == 3
    assert len(am_3.sections[0].sections) == 0
    am_4 = remove_sections(am, {(0, 0, 1), (0, 0, 0)})
    assert len(am_4.sections) == 3
    assert len(am_4.sections[0].sections) == 1
    assert len(am_4.sections[0].sections[0].sections) == 0


def test_add_inspection_sheet_in_table_rows():
    string = EnrichedString('Hello')
    assert not add_inspection_sheet_in_table_rows(string).table
    assert add_inspection_sheet_in_table_rows(string).text == string.text

    header_cells = [Cell(EnrichedString('Header 1'), 1, 1), Cell(EnrichedString('Header 2'), 1, 1)]
    content_cells = [Cell(EnrichedString('content 1'), 1, 1), Cell(EnrichedString('content 2'), 1, 1)]
    string = EnrichedString('', table=Table([Row(header_cells, True), Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[0].text_in_inspection_sheet is None
    assert transformed_string.table.rows[1].text_in_inspection_sheet == 'Header 1\ncontent 1\nHeader 2\ncontent 2'

    header_cells = [Cell(EnrichedString('Header 1'), 2, 1), Cell(EnrichedString('Header 2'), 1, 1)]
    content_cells = [
        Cell(EnrichedString('content 1'), 1, 1),
        Cell(EnrichedString('content 2'), 1, 1),
        Cell(EnrichedString('content 3'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(header_cells, True), Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[0].text_in_inspection_sheet is None
    expected = 'Header 1\ncontent 1\nHeader 1\ncontent 2\nHeader 2\ncontent 3'
    assert transformed_string.table.rows[1].text_in_inspection_sheet == expected

    content_cells = [
        Cell(EnrichedString('content 1'), 1, 1),
        Cell(EnrichedString('content 2'), 1, 1),
        Cell(EnrichedString('content 3'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[0].text_in_inspection_sheet == 'content 1\ncontent 2\ncontent 3'

    content_cells = [
        Cell(EnrichedString('\n\n\ncontent\n\n 1'), 1, 1),
        Cell(EnrichedString('content\n\n 2'), 1, 1),
        Cell(EnrichedString('content 3\n\n'), 1, 1),
    ]
    string = EnrichedString('', table=Table([Row(content_cells, False)]))
    transformed_string = add_inspection_sheet_in_table_rows(string)
    assert transformed_string.table.rows[0].text_in_inspection_sheet == 'content\n 1\ncontent\n 2\ncontent 3'


def test_remove_html():
    assert _remove_html('Hello<br/>How are you ?') == 'Hello\nHow are you ?'
    assert _remove_html('Hello    How are you ?') == 'Hello    How are you ?'
    assert _remove_html('') == ''
    assert _remove_html('<div></div>') == ''
    assert _remove_html('<a>URL</a>\n<p>P</p>') == 'URL\nP'
