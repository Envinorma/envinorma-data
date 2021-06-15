import json
from typing import List, Tuple

from envinorma.enriching.title_reference import (
    _extract_prefix,
    _extract_special_prefix,
    _is_prefix,
    _is_probably_section_number,
    _merge_prefixes,
    _merge_titles,
    add_references,
)
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.models.structured_text import StructuredText
from envinorma.models.text_elements import estr


def test_extract_special_prefix():
    assert _extract_special_prefix('Annexe I') == 'Annexe I'
    assert _extract_special_prefix('ANNEXE I') == 'Annexe I'
    assert _extract_special_prefix('ANNEXE') == 'Annexe'
    assert _extract_special_prefix('ANNEXE CONCERNANT LES DISPOSITIONS') == 'Annexe ?'
    assert _extract_special_prefix('Article fixant les dispositions') == 'Art. ?'
    assert _extract_special_prefix('Article 1') == 'Art. 1'
    assert _extract_special_prefix('Article 2.21') == 'Art. 2.21'
    assert _extract_special_prefix('Bonjour') is None


def test_extract_prefix():
    assert _extract_prefix('Article 9') == 'Art. 9'
    assert _extract_prefix('Article 9.3') == 'Art. 9.3'
    assert _extract_prefix('9.3. Pollution') == '9.3.'
    assert _extract_prefix('9. 3. Pollution') == '9.3.'
    assert _extract_prefix('Dispositions') is None


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
    assert _merge_prefixes(['1.', '2.', '3.', '4.']) == '1. 2. 3. 4.'
    assert _merge_prefixes(['1.', '1.1.', '1.1.1.']) == '1.1.1.'
    assert _merge_prefixes(['Art. 1.', '2.', '2. 1.']) == 'Art. 1. 2. 1.'
    assert _merge_prefixes(['Annexe II', 'a)']) == 'Annexe II a)'
    assert _merge_prefixes(['Section II', 'Chapitre 4', 'Art. 10']) == 'Section II Chapitre 4 Art. 10'


def test_merge_titles():
    tuples = [
        (
            [
                'TITRE III : RÉSERVOIRS DE STOCKAGE ET POSTES DE CHARGEMENT/DÉCHARGEMENT',
                'Chapitre Ier : Réservoirs et équipements associés.',
                'Article 4',
            ],
            'Art. 4',
        ),
        (
            ["Chapitre III : Emissions dans l'eau", 'Section 3 : Collecte et rejet des effluents', 'Article 29'],
            'Art. 29',
        ),
        (
            [
                "Annexe II - ANNEXE À L'ARRÊTÉ DU 29 MAI 2000 AUX PRESCRIPTIONS GÉNÉRALES APPLIC"
                "ABLES AUX INSTALLATIONS CLASSÉES POUR LA PROTECTION DE L'ENVIRONNEMENT"
                " SOUMISES À DÉCLARATION SOUS LA RUBRIQUE N° 2925"
            ],
            'Annexe II',
        ),
        (
            [
                'Chapitre II : Prévention des accidents et des pollutions',
                'Section 2 : Dispositions constructives',
                'Article 12',
                'I. ― Accessibilité :',
            ],
            'Art. 12 I.',
        ),
        (["Chapitre III : Prélèvement et consommation d'eau.", 'Article 21'], 'Art. 21'),
        (['Article 4'], 'Art. 4'),
        (['Annexes', 'Annexe I', '4. Risques', '4.1. Localisation des risques'], 'Annexe I 4.1.'),
        (
            [
                'Titre II : PRÉVENTION DE LA POLLUTION ATMOSPHÉRIQUE',
                "Chapitre V : Surveillance des rejets atmosphériques et de l'impact sur l'environnement",
                'Section 3 : Conditions de respect des valeurs limites',
            ],
            '',
        ),
        (
            [
                'Annexe I : Prescriptions générales applicables aux installations classées pour la protection'
                ' de l’environnement soumises à déclaration sous la rubrique n° 2560',
                '2.Implantation - aménagement',
                '2.4.Comportement au feu des locaux',
                '2.4.4.Désenfumage',
            ],
            'Annexe I',
        ),
        (
            [
                'Annexe I : Prescriptions générales applicables et faisant l’objet du contrôle périodique '
                'applicables aux installations classées soumises à déclaration sous la rubrique n°2930',
                '1. Dispositions générales',
                "1.7. Cessation d'activité",
            ],
            'Annexe I 1.7.',
        ),
        (["Chapitre IV : Émissions dans l'eau et les sols"], ''),
        (
            [
                'Annexes',
                'Annexe I',
                '2. Implantation aménagement',
                '2.4. Comportement au feu des bâtiments',
                '2.4.1. Réaction au feu',
            ],
            'Annexe I 2.4.1.',
        ),
        (
            ['Annexe', '1. Dispositions générales', "1.5. Déclaration d'accident ou de pollution accidentelle"],
            'Annexe 1.5.',
        ),
        (['Annexes'], 'Annexe'),
        (
            [
                'Annexes',
                'Annexe I - PRESCRIPTIONS GÉNÉRALES APPLICABLES AUX INSTALLATIONS CLASSÉES SOUMISES À DÉCLARATION'
                ' SOUS LA RUBRIQUE N° 2921',
                '8. Bruit et vibrations',
                '8.3. Vibrations',
            ],
            'Annexe I 8.3.',
        ),
        (["TITRE VIII : RISQUES INDUSTRIELS LORS D'UN DYSFONCTIONNEMENT DE L'INSTALLATION.", 'Article 50'], 'Art. 50'),
        (
            ['Chapitre VII : Bruit et vibrations', 'Article 7.3 - Vibrations.', '7.3.2. Sources impulsionnelles :'],
            'Art. 7.3 7.3.2.',
        ),
        (['Annexe I', '7. Déchets'], 'Annexe I 7.'),
        (
            [
                'Annexes',
                "Annexe II - PRESCRIPTIONS GÉNÉRALES APPLICABLES AUX INSTALLATIONS CLASSÉES POUR LA PROTECTION DE"
                " L'ENVIRONNEMENT SOUMISES À LA RUBRIQUE 1510",
                '1. Dispositions générales',
                '1.8. Dispositions générales pour les installations soumises à déclaration',
                '1.8.3. Contenu de la déclaration',
            ],
            'Annexe II 1.8.3.',
        ),
        (['Article 4'], 'Art. 4'),
        (
            [
                'Annexe I : Prescriptions générales et faisant l’objet du contrôle périodique applicables aux '
                'installations classées soumises à déclaration sous la rubrique 2940',
                '5. Eau',
                '5.6 . Interdiction des rejets en nappe',
            ],
            'Annexe I 5.',
        ),
    ]
    for titles, expected in tuples:
        assert _merge_titles(titles) == expected


def test_add_references():
    sub_sub_sections = [
        StructuredText(estr('1.1. azeaze'), [], [], None, None),
        StructuredText(estr('1. 2. azeaze'), [], [], None, None),
    ]
    sub_sections = [StructuredText(estr('1. azeaze'), [], sub_sub_sections, None, None)]
    sections = [
        StructuredText(estr('Article 1. efzefz'), [], sub_sections, None),
        StructuredText(estr('2. zefez'), [], [], None),
        StructuredText(estr('A. zefze'), [], [], None),
        StructuredText(estr('a) zefze'), [], [], None),
        StructuredText(estr('V. zefze'), [], [], None),
        StructuredText(estr('ANNEXE I zefze'), [], [], None),
        StructuredText(estr('Article 18.1'), [], [], None),
        StructuredText(estr('Article 1'), [], [], None),
    ]
    am = ArreteMinisteriel(estr('Arrete du 10/10/10'), sections, [], None, id='FAKE_ID')
    am_with_references = add_references(am)

    assert am_with_references.sections[0].reference_str == 'Art. 1.'
    assert am_with_references.sections[0].sections[0].reference_str == 'Art. 1. 1.'
    assert am_with_references.sections[0].sections[0].sections[0].reference_str == 'Art. 1. 1.1.'
    assert am_with_references.sections[0].sections[0].sections[1].reference_str == 'Art. 1. 1.2.'
    assert am_with_references.sections[1].reference_str == ''
    assert am_with_references.sections[2].reference_str == ''
    assert am_with_references.sections[3].reference_str == ''
    assert am_with_references.sections[4].reference_str == ''
    assert am_with_references.sections[5].reference_str == 'Annexe I'
    assert am_with_references.sections[6].reference_str == 'Art. 18.1'
    assert am_with_references.sections[7].reference_str == 'Art. 1'


def _extract_titles_and_reference_pairs_from_section(text: StructuredText) -> List[Tuple[str, str]]:
    return [(text.title.text, text.reference_str or '')] + [
        pair for section in text.sections for pair in _extract_titles_and_reference_pairs_from_section(section)
    ]


def extract_titles_and_reference_pairs(am: ArreteMinisteriel) -> List[Tuple[str, str]]:
    return [pair for section in am.sections for pair in _extract_titles_and_reference_pairs_from_section(section)]


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
        ('Annexes', 'Annexe'),
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
