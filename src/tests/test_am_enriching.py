import json

import pytest
from lib.data import (
    ArreteMinisteriel,
    ArticleStatus,
    EnrichedString,
    Hyperlink,
    LegifranceArticle,
    Link,
    StructuredText,
    Topic,
    load_arrete_ministeriel,
)
from lib.am_enriching import (
    add_links_in_enriched_string,
    add_links_to_am,
    extract_titles_and_reference_pairs,
    remove_prescriptive_power,
    add_topics,
    add_references,
    _extract_special_prefix,
    _is_probably_section_number,
    _is_prefix,
    _merge_prefix_list,
)


def test_add_topics():
    sub_section_1 = StructuredText(EnrichedString('Section 1.1'), [], [], None, None)
    section_1 = StructuredText(EnrichedString('Section 1'), [], [sub_section_1], None, None)
    section_2 = StructuredText(EnrichedString('Section 2'), [], [], None, None)
    am = ArreteMinisteriel(EnrichedString(''), [section_1, section_2], [], '', None)

    am_with_topics = add_topics(am, {(0,): Topic.INCENDIE, (0, 0): Topic.INCENDIE, (1,): Topic.BRUIT})
    assert am_with_topics.sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_topics.sections[0].sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_topics.sections[1].annotations.topic == Topic.BRUIT

    am_with_non_prescriptive = remove_prescriptive_power(am_with_topics, {(1,)})
    assert am_with_non_prescriptive.sections[0].annotations.prescriptive
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.prescriptive
    assert not am_with_non_prescriptive.sections[1].annotations.prescriptive

    assert am_with_non_prescriptive.sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_non_prescriptive.sections[0].sections[0].annotations.topic == Topic.INCENDIE
    assert am_with_non_prescriptive.sections[1].annotations.topic == Topic.BRUIT


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
    article = LegifranceArticle('', '', 0, '', ArticleStatus.VIGUEUR)
    sections = [
        StructuredText(EnrichedString('Article 1. efzefz'), [], sub_sections, article, None),
        StructuredText(EnrichedString('2. zefez'), [], [], article, None),
        StructuredText(EnrichedString('A. zefze'), [], [], article, None),
        StructuredText(EnrichedString('a) zefze'), [], [], article, None),
        StructuredText(EnrichedString('V. zefze'), [], [], article, None),
        StructuredText(EnrichedString('ANNEXE I zefze'), [], [], article, None),
        StructuredText(EnrichedString('Article 18.1'), [], [], article, None),
        StructuredText(EnrichedString('Article 1'), [], [], article, None),
    ]
    am = ArreteMinisteriel(EnrichedString(''), sections, [], '', None)
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
    am = load_arrete_ministeriel(json.load(open('test_data/AM/minified_texts/DEVP1235896A.json')))
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
        add_links_to_am(load_arrete_ministeriel(json.load(open(f'data/AM/structured_texts/{nor}.json'))), links)

