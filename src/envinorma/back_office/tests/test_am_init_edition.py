from envinorma.back_office.am_init_edition import _extract_elements, _extract_structured_text
from envinorma.data.text_elements import Table, Title


def test_extract_elements():
    assert _extract_elements('') == []
    assert _extract_elements('\n') == []
    res = _extract_elements('\n<table><tr><td></td></tr></table>')
    assert len(res) == 1
    assert isinstance(res[0], Table)

    res = _extract_elements('Test\n<table><tr><td></td></tr></table>')
    assert len(res) == 2
    assert res[0] == 'Test'
    assert isinstance(res[1], Table)

    res = _extract_elements('Test\nTest')
    assert len(res) == 2
    assert res[0] == 'Test'
    assert res[1] == 'Test'

    res = _extract_elements('Test\nTest\n#Test')
    assert len(res) == 3
    assert res[0] == 'Test'
    assert res[1] == 'Test'
    title = res[2]
    assert isinstance(title, Title)
    assert title.text == 'Test'
    assert title.level == 1


def test_extract_structured_text():
    am_str = '''


# Article 1 er

Les installations classées pour la protection de l'environnement soumises à déclaration sous la rubrique n° 2260 « broyage, concassage, criblage, déchiquetage, ensachage, pulvérisation, trituration, nettoyage, tamisage, blutage, mélange, épluchage et décortication des substances végétales et de tous produits organiques naturels, à l'exclusion des activités visées par les rubriques nos 2220, 2221, 2225 et 2226, mais y compris la fabrication d'aliments pour le bétail » sont soumises aux dispositions de l'annexe I. Les présentes dispositions s'appliquent sans préjudice des autres législations.


# Article 2

Les dispositions de l'annexe I sont applicables aux installations déclarées postérieurement à la date de publication du présent arrêté au Journal officiel, augmentée de quatre mois.

Les dispositions de cette annexe sont applicables aux installations existantes, déclarées avant la date de publication du présent arrêté au Journal officiel augmentée de quatre mois, dans les conditions précisées en annexe V. Les prescriptions auxquelles les installations existantes sont déjà soumises demeurent applicables jusqu'à l'entrée en vigueur de ces dispositions.

Les dispositions de l'annexe I sont applicables aux installations classées soumises à déclaration incluses dans un établissement qui comporte au moins une installation soumise au régime de l'autorisation dès lors que ces installations ne sont pas régies par l'arrêté préfectoral d'autorisation.


# Article 3

Le préfet peut adapter ou renforcer les dispositions suivantes, prévues à l'annexe I : 2.2. Intégration dans le paysage, 5.1. Prélèvements, 5.2. Consommation, 5.5. Valeurs limites de rejet, 5.8. Epandage, en fonction des circonstances locales et conformément à l'article L. 512-9 du code de l'environnement et l'article 29 du décret n° 77-1133 du 21 septembre 1977 susvisés.


# Article 4

Le préfet peut, pour une installation donnée, adapter par arrêté les dispositions des annexes I à IV dans les conditions prévues à l'article L. 512-12 du code de l'environnement et à l'article 30 du décret n° 77-1133 du 21 septembre 1977 susvisés.
'''

    text = _extract_structured_text(am_str)
    assert text.title.text == ''
    assert len(text.sections) == 4
    assert text.sections[0].title.text == 'Article 1 er'
    assert text.outer_alineas == []
