import re
from typing import List

from envinorma.from_legifrance.numbering_exceptions import EXCEPTION_PREFIXES, MAX_PREFIX_LEN
from envinorma.title_detection import (
    INCREASING_PATTERNS,
    NUMBERING_PATTERNS,
    PATTERN_NAME_TO_LIST,
    SHOULD_HAVE_SEMICOLON_PATTERNS,
    NumberingPattern,
    _detect_longest_matched_pattern,
    _first_word,
    _smart_detect_pattern,
    detect_longest_matched_string,
    detect_patterns_if_exists,
    is_probably_title,
)


def _starts_with_prefix(string: str, prefix: str) -> bool:
    return string[: len(prefix)] == prefix


def _prefixes_are_increasing(prefixes: List[str], strings: List[str]) -> bool:
    i = 0
    for string in strings:
        while True:
            if i >= len(prefixes):
                return False
            if _starts_with_prefix(string, prefixes[i]):
                break
            i += 1
    if i >= len(prefixes):
        return False
    return True


def _pattern_is_increasing(pattern: NumberingPattern, strings: List[str]) -> bool:
    prefixes = PATTERN_NAME_TO_LIST[pattern]
    return _prefixes_are_increasing(prefixes, strings)


def _any_final_semicolon(strings: List[str]) -> bool:
    return any([':' in string[-2:] for string in strings])


def _is_valid(pattern: NumberingPattern, strings: List[str]) -> bool:
    checks: List[bool] = []
    if pattern in INCREASING_PATTERNS:
        checks.append(_pattern_is_increasing(pattern, strings))
    if pattern in SHOULD_HAVE_SEMICOLON_PATTERNS:
        checks.append(_any_final_semicolon(strings))
    return all(checks)


def test_pattern_is_increasing():
    assert _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'd) '])
    assert not _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'd) ', 'a) '])
    assert _pattern_is_increasing(NumberingPattern.LETTERS, ['a) ', 'b) ', 'c) ', 'x) ', 'y) '])


def test_regex():
    for key in PATTERN_NAME_TO_LIST:
        assert key in NUMBERING_PATTERNS
    for pattern_name, pattern in NUMBERING_PATTERNS.items():
        for elt in PATTERN_NAME_TO_LIST[pattern_name]:
            assert re.match(pattern, elt)


def test_is_valid():
    assert not _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar ;'])
    assert _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar :'])
    assert not _is_valid(NumberingPattern.LETTERS, ['a) Foo ;', 'b) Bar :', 'a) Pi', 'b) Pa'])


def test_detect_longest_matched_pattern():
    assert _detect_longest_matched_pattern('1. 1. bnjr') == NumberingPattern.NUMERIC_D2_SPACE
    assert _detect_longest_matched_pattern('1. 2. 3. bnjr') == NumberingPattern.NUMERIC_D3_SPACE
    assert _detect_longest_matched_pattern('1. 2.3. bnjr') == NumberingPattern.NUMERIC_D1
    assert _detect_longest_matched_pattern('1.') is None
    assert _detect_longest_matched_pattern('') is None


def test_exceptions():
    for exc in EXCEPTION_PREFIXES:
        assert len(exc) <= MAX_PREFIX_LEN


def test_smart_detect_pattern():
    pattern = _smart_detect_pattern(
        "1. Les zones d'effets Z1 et Z2 définies par l'arrêté du 20 a erez", (MAX_PREFIX_LEN, EXCEPTION_PREFIXES)
    )  # in EXCEPTION_PREFIXES
    assert pattern is None

    pattern = _smart_detect_pattern("1. Les zones d'effets Z1 et Z2 définies par l'arrêté du 20 a erez", None)
    assert pattern == NumberingPattern.NUMERIC_D1


def test_structure_extraction():
    patterns = detect_patterns_if_exists(
        [
            "1. Dispositions générales",
            "1. 1. Conformité de l'installation au dossier d'enregistrement",
            "1. 2. Dossier installation classée",
            "2. Risques",
            "2. 1. Généralités",
            "2. 1. 1. Surveillance de l'installation",
            "1. Les zones d'effets Z1 et Z2 définies par l'arrêté du 20 a erez",  # in EXCEPTION_PREFIXES
            "2. 1. 2. Clôture",
        ],
        (MAX_PREFIX_LEN, EXCEPTION_PREFIXES),
    )
    assert patterns[0] == NumberingPattern.NUMERIC_D1
    assert patterns[1] == NumberingPattern.NUMERIC_D2_SPACE
    assert patterns[6] is None


def test_structure_extraction_2():
    patterns = detect_patterns_if_exists(
        [
            "I. First title",
            "A. First section",
            "B. Second section",
            "H. H-th section",
            "I. ― Les aires de chargement et de déchargement des produits",  # must be letter (exception)
        ],
        (MAX_PREFIX_LEN, EXCEPTION_PREFIXES),
    )
    assert patterns == [
        NumberingPattern.ROMAN,
        NumberingPattern.CAPS,
        NumberingPattern.CAPS,
        NumberingPattern.CAPS,
        NumberingPattern.CAPS,
    ]


def test_detect_longest_matched_string():
    titles_to_target = {
        'I. First title': 'I. ',
        'A. First section': 'A. ',
        'B. Second section': 'B. ',
        'H. H-th section': 'H. ',
        'I. ― Les aires de chargement et de déchargement des produits': 'I. ',
        '1.1. Bonjour': '1.1. ',
        '1. 15. Bonjour': '1. 15. ',
    }

    for title, target in titles_to_target.items():
        assert detect_longest_matched_string(title) == target


_IS_TITLE = {
    "La mise en œuvre des dispositions du présent arrêté fera l'objet d'une évaluation en 2007, notamment en ce qui concerne l'adéquation des valeurs limites pour les oxydes d'azote prévues à l'article 45 eu égard à l'évolution des meilleures techniques disponibles, aux références nationales ou étrangères et à l'évolution de techniques notamment en matière d'oxycombustion.": False,  # noqa: E501
    '(épandage)': True,  # noqa: E501
    'Stockage': True,  # noqa: E501
    "Dans les parties de l'installation recensées selon les dispositions de l'article 8 en raison des risques d'explosion, l'exploitant met en place des évents/surfaces soufflables dimensionnés selon les normes en vigueur.": False,  # noqa: E501
    'Stockage des déchets.': True,  # noqa: E501
    "L'épandage des boues, déchets, effluents et sous-produits est interdit.": False,  # noqa: E501
    'Définitions : au sens du présent arrêté, on entend par :': False,  # noqa: E501
    "Le directeur général de la prévention des risques est chargé de l'exécution du présent arrêté, qui sera publié au Journal officiel de la République française.": False,  # noqa: E501
    'Définitions.': True,  # noqa: E501
    "Les eaux pluviales non souillées ne présentant pas une altération de leur qualité d'origine sont évacuées par un réseau spécifique ou dans le milieu naturel si le réseau spécifique est inexistant et après justification par l'exploitant de l'absence de pollution créée par ce rejet.": False,  # noqa: E501
    "Dans le cas où l'atelier est installé dans un bâtiment où d'autres activités sont pratiquées, il est isolé par des parois (cloisons, plafond ou plancher) de classe REI 60 (coupe-feu de degré une heure). Si des ouvertures sont pratiquées, elles sont équipées de dispositifs appropriés permettant de prévenir la propagation d'un incendie d'un local à l'autre.": False,  # noqa: E501
    "En cas de traitement des effluents dans une station d'épuration propre à l'installation, une analyse de l'azote et du phosphore contenus dans les boues et les produits issus du traitement des effluents est réalisée annuellement.": False,  # noqa: E501
    'Les déchets radioactifs contenant des radionucléides de période supérieure à cent jours sont gérés dans des filières autorisées pour ce type de déchets.': False,  # noqa: E501
    "Chaque réservoir est équipé d'un dispositif permettant de connaître à tout moment le volume du liquide contenu.": False,  # noqa: E501
    "Le directeur général de l'énergie et du climat et le directeur général de la prévention des risques sont chargés, chacun en ce qui le concerne, de l'exécution du présent arrêté, qui sera publié au Journal officiel de la République française.": False,  # noqa: E501
    "Les points de mesure et les points de prélèvement d'échantillons sont aménagés conformément aux conditions fixées par les méthodes de référence précisées dans l'arrêté du 7 juillet 2009 susvisé et équipés des appareils nécessaires pour effectuer les mesures prévues par le présent arrêté dans des conditions représentatives.": False,  # noqa: E501
    "Il est interdit d'établir des liaisons directes entre les réseaux de collecte des effluents devant subir un traitement ou être détruits et le milieu récepteur, à l'exception des cas accidentels où la sécurité des personnes ou des installations serait compromise.": False,  # noqa: E501
    "Les dispositions du présent arrêté s'appliquent sans préjudice de prescriptions particulières les complétant ou les renforçant dont peut être assorti l'arrêté d'enregistrement dans les conditions fixées par les articles L. 512-7-3 et L. 512-7-5 du code de l'environnement.": False,  # noqa: E501
    "Les appareils de combustion consommant du biogaz produit par des installations de méthanisation classées sous la rubrique n° 2781-1 dans une installation de combustion de puissance thermique nominale totale supérieure ou égale à 1 MW et inférieure à 20 MW comprenant uniquement des appareils de combustion classés au titre du point 1 de la rubrique 2910-A sont soumis aux dispositions de l'annexe I.": False,  # noqa: E501
    "CALENDRIER D'APPLICATION": True,  # noqa: E501
    "Les réservoirs de liquides inflammables de catégories A, B, C1 et D1 situés dans une même rétention sont adjacents à une voie d'accès permettant l'intervention des moyens mobiles d'extinction.": False,  # noqa: E501
    "Les autorisations des installations existantes sont rendues compatibles, pour le domaine de l'eau, avec les dispositions du schéma directeur d'aménagement et de gestion des eaux et du schéma d'aménagement des eaux, lorsqu'il existe.": False,  # noqa: E501
    "Surveillance de l'impact sur l'environnement au voisinage de l'installation. - L'exploitant doit mettre en place un programme de surveillance de l'impact de l'installation sur l'environnement. Ce programme concerne au moins les dioxines et les métaux.": False,  # noqa: E501
    'A modifié les dispositions suivantes :': False,  # noqa: E501
    'Réception et traitement de certains sous-produits animaux de catégorie 2': True,  # noqa: E501
    "Le présent arrêté s'applique aux installations de stockage de chlore gazeux liquéfié sous pression, nouvelles ou existantes, lorsque la quantité totale susceptible d'être présente dans l'installation est supérieure ou égale à 18 tonnes, relevant de la rubrique 4710 de la Nomenclature des installations classées pour la protection de l'environnement.": False,  # noqa: E501
    "Les installations de prélèvement d'eau sont munies d'un dispositif de mesure totalisateur. Ce dispositif est relevé quotidiennement si le débit prélevé est susceptible de dépasser 100 m³/j, hebdomadairement si ce débit est inférieur. Ces résultats sont portés sur un registre éventuellement informatisé et conservés dans le dossier de l'installation.": False,  # noqa: E501
    'Pendant les opérations de transvasement, un dispositif de ventilation à débit réduit et le dispositif de neutralisation du chlore sont obligatoirement mis en service.': False,  # noqa: E501
    'Les points de rejet dans le milieu naturel sont en nombre aussi réduit que possible.': False,  # noqa: E501
    "L'installation est implantée, réalisée et exploitée conformément aux plans et autres documents joints à la demande d'enregistrement.": False,  # noqa: E501
    'Déchets non valorisables.': True,  # noqa: E501
    "A minima une fois par an, l'exploitant met à jour les relevés topographiques et évalue les capacités d'accueil de déchets disponibles restantes. Ces informations sont tenues à la disposition de l'inspection des installations classées et sont présentées dans le rapport annuel d'activité prévu à l'article 26 du présent arrêté.": False,  # noqa: E501
    "Les prescriptions fixées aux annexes du présent arrêté peuvent être adaptées par arrêté préfectoral aux circonstances locales, en application des dispositions de l'article L. 512-10 du code de l'environnement.": False,  # noqa: E501
    'Dispositions applicables aux installations existantes': True,  # noqa: E501
    "Pour les substances susceptibles d'être rejetées par l'installation, les effluents gazeux respectent, selon le flux horaire, les valeurs limites de concentration fixées dans le tableau ci-après.": False,  # noqa: E501
    "L'exploitant prend toutes les dispositions nécessaires dans la conception et l'exploitation de l'installation pour assurer une bonne gestion des déchets, notamment :": False,  # noqa: E501
    "Les dispositions de l'article 4 ne s'appliquent, dans le cas des extensions des installations en fonctionnement régulier, qu'aux nouveaux bâtiments d'élevage ou parcs d'élevage, ou à leurs annexes nouvelles. Elles ne s'appliquent pas lorsqu'un exploitant doit, pour mettre en conformité son installation autorisée avec les dispositions du présent arrêté, réaliser des annexes ou aménager ou reconstruire sur le même site un bâtiment de même capacité.": False,  # noqa: E501
    'Les canalisations de décharge des réservoirs et autres équipements (soupapes, etc.) ainsi que la ou les enceintes de confinement doivent être reliés à une installation de neutralisation du chlore.': False,  # noqa: E501
    "En cas de fuite d'un réservoir, les dispositions suivantes sont mises en œuvre :": False,  # noqa: E501
    "L'établissement dispose de réserves suffisantes de produits ou matières consommables utilisés de manière courante ou occasionnelle pour assurer le respect des valeurs limites d'émission et des autres dispositions du présent arrêté tels que manches de filtre, produits de neutralisation, liquides inhibiteurs, produits absorbants, etc.": False,  # noqa: E501
    "Un cahier d'épandage, tenu sous la responsabilité de l'exploitant et à la disposition de l'inspection de l'environnement, spécialité installations classées, pendant une durée de cinq ans, comporte pour chacune des surfaces réceptrices épandues exploitées en propre :": False,  # noqa: E501
    "(1) Les annexes sont publiées au Bulletin officiel du ministère de l'écologie et du développement durable.": False,  # noqa: E501
    'RÈGLES TECHNIQUES APPLICABLES AUX VIBRATIONS': True,  # noqa: E501
    "L'exploitant recense, sous sa responsabilité, les parties de l'installation qui, en raison de la présence de gaz (notamment en vue de chauffage) ou de liquides inflammables, sont susceptibles de prendre feu ou de conduire à une explosion.": False,  # noqa: E501
    "Les points de mesure et les points de prélèvement d'échantillons sont aménagés conformément aux conditions fixées par les méthodes de référence précisées dans l'arrêté du 7 juillet 2009 susvisé.": False,  # noqa: E501
    'Dans les parties de l\'installation recensées à l\'article 8, et notamment celles recensées comme locaux à risque incendie définis à l\'article 11.2, les travaux de réparation ou d\'aménagement ne peuvent être effectués qu\'après délivrance d\'un "permis d\'intervention" (pour une intervention sans flamme et sans source de chaleur) et éventuellement d\'un "permis de feu" (pour une intervention avec source de chaleur ou flamme) et en respectant une consigne particulière. Ces permis sont délivrés après analyse des risques liés aux travaux et définition des mesures appropriées.': False,  # noqa: E501
    "Le rejet respecte les dispositions de l'article 22 du 2 février 1998 modifié en matière de :": False,  # noqa: E501
    "Les dispositions de l'annexe I sont applicables :": False,  # noqa: E501
    'Eaux souterraines.': True,  # noqa: E501
    'Les véhicules de transport, les matériels de manutention et les engins de chantier utilisés sont conformes aux dispositions en vigueur en matière de limitation de leurs émissions sonores.': False,  # noqa: E501
    "Le surremplissage est prévenu par un contrôle du niveau de la surface libre de la phase liquide. Ce niveau est mesuré en continu. Le résultat de la mesure est mis à la disposition de l'exploitant et de la personne en charge du remplissage.": False,  # noqa: E501
    "Le directeur de la prévention des pollutions et des risques est chargé de l'exécution du présent arrêté, qui sera publié au Journal officiel de la République française.": False,  # noqa: E501
    'Compatibilité avec les objectifs de qualité du milieu.': True,  # noqa: E501
    "Lors de la réalisation de forages en nappe, toutes dispositions sont prises pour éviter de mettre en communication des nappes d'eau distinctes, sauf autorisation explicite dans l'arrêté d'autorisation, et pour prévenir toute introduction de pollution de surface, notamment par un aménagement approprié.": False,  # noqa: E501
    'Implantation.': True,  # noqa: E501
    'Vérification périodique et maintenance des équipements.': True,  # noqa: E501
    'VLE pour rejet dans le milieu naturel.': True,  # noqa: E501
    "Les hauteurs indiquées entre parenthèses correspondent aux hauteurs minimales des cheminées associées aux installations situées dans le périmètre d'un plan de protection de l'atmosphère tel que prévu à l'article R. 222-13 du code de l'environnement.": False,  # noqa: E501
    'Admission et sorties.': True,  # noqa: E501
    'Prévention des nuisances odorantes.': True,  # noqa: E501
    'Les établissements respectent, en plus des dispositions du présent arrêté, les dispositions propres :': False,  # noqa: E501
    'Vérification périodique et maintenance des équipements': True,  # noqa: E501
    "Les installations classées pour la protection de l'environnement soumises à déclaration sous la rubrique n° 2551 (Fonderie [fabrication de produits moulés] de métaux et alliages ferreux), la capacité de production étant supérieure à 1 tonne par jour mais inférieure ou égale à 10 tonnes par jour, sont soumises aux dispositions de l'annexe I . Les présentes dispositions s'appliquent sans préjudice des autres législations.": False,  # noqa: E501
    'Tuyauteries et opérations de chargement, déchargement.': True,  # noqa: E501
    "Les matériels importants pour la sécurité, définis par l'étude des dangers, font l'objet de spécifications précises, de procédures de qualification et d'essais en rapport avec leurs utilisations dans les conditions de fonctionnement normales et accidentelles. Les paramètres significatifs de la sécurité des installations définis dans l'étude des dangers sont mesurés et enregistrés en continu. La liste des équipements et paramètres importants pour la sécurité et éventuellement les informations faisant l'objet d'un enregistrement sont tenues à la disposition de l'inspecteur des installations classées.": False,  # noqa: E501
    "Hauteur des conduits d'extraction.": True,  # noqa: E501
    'Collecte des effluents.': True,  # noqa: E501
    'Le présent arrêté entre en vigueur le 1er juillet 2018.': False,  # noqa: E501
    'Conception du poste de surveillance.': True,  # noqa: E501
    "L'exploitant démontre que les valeurs limites d'émission fixées ci-après sont compatibles avec l'état du milieu.": False,  # noqa: E501
    'CONFORMITÉ DES SYSTÈMES DE RÉCUPÉRATION DES VAPEURS': True,  # noqa: E501
    "Les points de rejet sont en nombre aussi réduits que possible. Si plusieurs points de rejet sont nécessaires, l'exploitant le justifie dans son dossier de demande d'enregistrement.": False,  # noqa: E501
    'Information préalable sur les matières à traiter.': True,  # noqa: E501
    "Pour les équipements autres que les chaudières relevant de la rubrique 2910 de la nomenclature des installations classées, les rejets dans l'atmosphère, exprimés sur gaz secs après déduction de la vapeur d'eau et rapportés à une concentration de 11 % d'oxygène sur gaz secs contiendront moins de :": False,  # noqa: E501
    "L'exploitant tient une comptabilité régulière et précise des déchets produits par son établissement.": False,  # noqa: E501
    "Les rejets directs ou indirects d'effluents vers les eaux souterraines sont interdits.": False,  # noqa: E501
    "L'enceinte de confinement est conçue pour résister à la surpression due au flash thermodynamique dont l'hypothèse est décrite dans l'étude des dangers. L'étude des dangers estime les fuites dues aux ouvertures (accès pour le personnel, passages de tuyauterie ou de rails...) afin de s'assurer, en cas de survenance d'un accident majeur, qu'elles n'entraînent pas d'effets notables à l'extérieur du bâtiment sur les intérêts visés à l'article 1er de la loi du 19 juillet 1976 susvisée.": False,  # noqa: E501
    "La mise en oeuvre des dispositions du présent arrêté fait l'objet d'une évaluation périodique par le    Conseil supérieur de la prévention des risques technologiques. Ce dernier examine toute proposition utile de modification du présent arrêté, notamment au vu de l'adéquation des valeurs limites retenues au chapitre IV par rapport aux procédés et technologies disponibles et à leur évolution.": False,  # noqa: E501
    "Les rejets d'eaux pluviales canalisées respectent les valeurs limites de concentration suivantes, sous réserve de la compatibilité des rejets présentant les niveaux de pollution définis ci-dessous avec les objectifs de qualité et de quantité des eaux visés dans les SDAGE.": False,  # noqa: E501
    'Le préfet peut, pour une installation donnée, modifier par arrêté les dispositions des annexes I et II dans les conditions prévues aux articles 11 de la loi n° 76-663 du 19 juillet 1976 et 30 du décret n° 77-1133 du 21 septembre 1977 susvisés.': False,  # noqa: E501
    "Valeurs limites d'émission en cas de rejet dans le milieu naturel.": True,  # noqa: E501
    "La protection du sol, des eaux souterraines et de surface est assurée par une barrière géologique dite « barrière de sécurité passive » des casiers de stockage de déchets de sédiments non dangereux. Elle est constituée du terrain naturel en l'état répondant aux critères suivants :": False,  # noqa: E501
    "Les capacités techniques du système d'assainissement individuel des effluents de l'installation sont, qualitativement et quantitativement, compatibles avec l'ensemble des effluents reçus.": False,  # noqa: E501
    "L'annexe sera publiée au Bulletin officiel du ministère de l'écologie, du développement durable et de l'énergie.": False,  # noqa: E501
    "Les installations de charge d'au moins 10 véhicules de transport en commun de catégorie M2 ou M3, tels que définis à l'article R. 311-1 du code de la route, fonctionnant grâce à l'énergie électrique et soumises à déclaration sous la rubrique n° 2925 sont soumises aux dispositions du présent arrêté.": False,  # noqa: E501
    "Dans le cas où il est exercé dans le site une ou plusieurs des activités visées par les points 19 à 36 de l'article 30 de l'arrêté du 2 février 1998 susvisé, les valeurs limites d'émissions relatives aux COV définies aux points a et c de l'article 45 et dans l'article 48 du présent arrêté ne sont pas applicables aux rejets des installations.": False,  # noqa: E501
    "Le chauffage de l'atelier, s'il est indispensable, s'effectue par fluide chauffant (air, eau, vapeur d'eau basse pression) ou par tout autre procédé présentant des garanties de sécurité comparables empêchant l'apparition de sources d'ignition.": False,  # noqa: E501
    "Les points de rejet dans le milieu naturel sont en nombre aussi réduit que possible. Si plusieurs points de rejet sont nécessaires, l'exploitant le justifie.": False,  # noqa: E501
    "La présence à l'intérieur de l'enceinte de points chauds capables d'amorcer la réaction du fer avec le chlore doit faire l'objet de consignes particulières. La présence de soufre, de matières organiques, de matières combustibles, d'huiles et graisses dans l'enceinte ou à proximité de celle-ci est proscrite pour empêcher tout risque d'amorçage d'une combustion.": False,  # noqa: E501
    "L'exploitant démontre que, pour chaque polluant, le flux rejeté est inférieur à 10 % du flux admissible par le milieu.": False,  # noqa: E501
    "Valeurs limites d'émission dans l'air. - Les installations d'incinération sont conçues, équipées, construites et exploitées de manière à ce que les valeurs limites fixées à l'annexe 1 ne soient pas dépassées dans les rejets gazeux de l'installation.": False,  # noqa: E501
    "En cas de rejets dans l'environnement, les points de rejets des effluents gazeux des installations concernées sont en nombre aussi limité que possible.": False,  # noqa: E501
    "Les installations de prélèvement d'eau sont munies d'un dispositif de mesure totalisateur. Ce dispositif est relevé hebdomadairement. Ces résultats sont portés sur un registre éventuellement informatisé et conservés dans le dossier de l'installation.": False,  # noqa: E501
    "Sans préjudice des règlements d'urbanisme, l'exploitant adopte les dispositions suivantes, nécessaires pour prévenir les envols de poussières et matières diverses :": False,  # noqa: E501
    'Gestion des produits': True,  # noqa: E501
    'Dispositions générales.': True,  # noqa: E501
    "La quantité des peroxydes organiques ou des substances ou mélanges autoréactifs du groupe Gr4 n'est pas prise en considération dans le calcul des distances d'éloignement.": False,  # noqa: E501
    "Les tuyauteries transportant des fluides dangereux ou insalubres et de collecte d'effluents pollués ou susceptibles de l'être sont étanches et résistent à l'action physique et chimique des produits qu'elles sont susceptibles de contenir. Elles sont convenablement entretenues et font l'objet d'examens périodiques appropriés permettant de s'assurer de leur bon état.": False,  # noqa: E501
    'DISPOSITIONS APPLICABLES': True,  # noqa: E501
    "Le préfet peut, pour une installation donnée, adapter par arrêté les dispositions des annexes dans les conditions prévues aux articles L. 512-12 et R. 512-52 du code de l'environnement.": False,  # noqa: E501
    "Valeurs limites d'émission pour rejet dans le milieu naturel": True,  # noqa: E501
    'Les installations classées pour la protection de l\'environnement soumises à déclaration sous la rubrique n° 2710-1 "Installation de collecte de déchets apportés par le producteur initial de ces déchets, collecte de déchets dangereux" sont soumises aux dispositions de l\'annexe I. Les présentes dispositions s\'appliquent sans préjudice des autres législations.': False,  # noqa: E501
    "L'exploitant tient à la disposition de l'inspection des installations classées les éléments justifiant que ses installations électriques sont réalisées conformément aux règles en vigueur, entretenues en bon état et vérifiées.": False,  # noqa: E501
    'Les salles des machines doivent être conformes aux normes en vigueur.': False,  # noqa: E501
    "Une aire cimentée permet le stockage des fumiers. Elle est munie d'une fosse étanche pour la récupération des jus sauf dans le cas de fumière couverte ou de fumier compact pailleux. Cette aire est dégagée aussi souvent que nécessaire, sans préjudice des dispositions réglementaires relatives aux conditions d'épandage des fumiers.": False,  # noqa: E501
    "Le site dispose en permanence d'une voie d'accès carrossable au moins pour permettre l'intervention des services d'incendie et de secours.": False,  # noqa: E501
    "Dispositions relatives à la prévention des risques dans le cadre de l'exploitation.": True,  # noqa: E501
    "Les personnes étrangères à l'installation n'ont pas d'accès libre à l'intérieur des aérogénérateurs.": False,  # noqa: E501
    'Désenfumage.': True,  # noqa: E501
    'Déchets entrants.': True,  # noqa: E501
    "Pour chaque matière intermédiaire telle que définie à l'article 2, l'exploitant doit respecter au minimum les teneurs limites définies dans la norme NFU 44-051 concernant les éléments traces métalliques, composés traces organiques, inertes et impuretés. Il tient les justificatifs relatifs à la conformité de chaque lot à la disposition de l'inspection des installations classées et des autorités de contrôle chargées des articles L. 255-1 à L. 255-11 du code rural.": False,  # noqa: E501
    "DISPOSITIONS TECHNIQUES EN MATIÈRE D'ÉPANDAGE": True,  # noqa: E501
    "Concernant les dispositions générales pour la fixation des valeurs limites d'émissions dans l'eau, les dispositions de l'article 21 de l'arrêté du 2 février 1998 modifié s'appliquent.": False,  # noqa: E501
    "Déchets interdits dans l'installation.": True,  # noqa: E501
    "Captage et épuration des rejets à l'atmosphère.": True,  # noqa: E501
    'Hauteur de cheminées.': True,  # noqa: E501
    "PRESCRIPTIONS GÉNÉRALES ET FAISANT L'OBJET DU CONTRÔLE PÉRIODIQUE APPLICABLES AUX INSTALLATIONS CLASSÉES POUR LA PROTECTION DE L'ENVIRONNEMENT SOUMISES À DÉCLARATION SOUS LA RUBRIQUE No 2950": True,  # noqa: E501
    'Débit et mesures.': True,  # noqa: E501
    'Surveillance des émissions de gaz à effet de serre.': True,  # noqa: E501
    'Odeurs.': True,  # noqa: E501
    "L'exploitant tient une comptabilité régulière et précise des déchets produits par son site.": False,  # noqa: E501
    "Les dispositions des articles 10 et 11 de l'arrêté du 2 février 1998 susvisé relatives au stockage de liquides susceptibles de créer une pollution sont applicables aux installations visées à l'article 1er du présent arrêté si elles stockent de tels liquides.": False,  # noqa: E501
    'Points de prélèvements pour les contrôles.': True,  # noqa: E501
    'Sans préjudice des dispositions du code du travail, des consignes sont établies, tenues à jour et affichées dans les lieux fréquentés par le personnel.': False,  # noqa: E501
    'Le chargement de la citerne se fait soit par le bas (chargement dit "en source"), soit par le dôme par tube plongeur. Le chargement en pluie est interdit.': False,  # noqa: E501
    "Conformité de l'installation.": True,  # noqa: E501
    "Les installations classées pour la protection de l'environnement soumises à déclaration sous la rubrique n° 4731 sont soumises aux dispositions de l'annexe I. Les présentes dispositions s'appliquent sans préjudice des autres législations.": False,  # noqa: E501
    'Pour les casiers mono-déchets dédiés au stockage de déchets de matériaux de construction contenant de l\'amiante, la protection du sol, des eaux souterraines et de surface est assurée par une barrière géologique dite "barrière de sécurité passive" constituée du terrain naturel en l\'état répondant aux critères suivants :': False,  # noqa: E501
    'DISPOSITIONS APPLICABLES AUX INSTALLATIONS EXISTANTES': True,  # noqa: E501
    "Le préfet peut, pour une installation donnée, adapter par arrêté les présentes dispositions dans les conditions prévues par les articles L. 512-12 et R. 512-52 du code de l'environnement.": False,  # noqa: E501
    "Si le flux horaire total d'antimoine, de chrome total, de cuivre, d'étain, de manganèse, de vanadium et de leurs composés dépasse 25 g/h, la valeur limite de concentration des rejets d'antimoine, de chrome total, de cuivre, d'étain, de manganèse, de vanadium et de leurs composés est de 5 mg/Nm3 (exprimée en Sb + Cr total + Cu + Sn + Mn + V) à la fois en ce qui concerne les rejets des unités de fusion et des autres activités annexes.": False,  # noqa: E501
    "Les eaux de pluie provenant des toitures ne sont en aucun cas mélangées aux effluents d'élevage, ni rejetées sur les aires d'exercice en dur lorsqu'elles existent. Lorsque ce risque est présent, elles sont collectées par une gouttière ou tout autre dispositif équivalent. Elles sont alors soit stockées en vue d'une utilisation ultérieure, soit évacuées vers le milieu naturel ou un réseau particulier.": False,  # noqa: E501
    'Au sens du présent arrêté, on entend par :': False,  # noqa: E501
    "L'exploitant met en place un programme de surveillance de ses émissions dans les conditions fixées aux articles 60 à 63. Les mesures sont effectuées sous la responsabilité de l'exploitant et à ses frais.": False,  # noqa: E501
    'Normes de mesure.': True,  # noqa: E501
    "Les vannes et les tuyauteries doivent être d'accès facile et leur signalisation conforme aux normes applicables ou à une codification reconnue. Les vannes doivent porter de manière indélébile le sens de leur fermeture.": False,  # noqa: E501
    "FACTEURS D'ÉQUIVALENCE POUR LES DIBENZOPARADIOXINES ET LES DIBENZOFURANNES": True,  # noqa: E501
    "L'exploitant assure ou fait effectuer la vérification périodique et la maintenance des matériels de sécurité et de lutte contre l'incendie ainsi que des dispositifs permettant de prévenir les surpressions.": False,  # noqa: E501
    "Les sites disposant d'une capacité totale réelle de liquides inflammables (hors fioul lourd) supérieure ou égale à 1 500 mètres cubes sont munis au minimum d'un puits de contrôle (piézomètre) en amont et de deux puits de contrôle en aval du site par rapport au sens d'écoulement de la nappe.": False,  # noqa: E501
    "L'exploitation se fait sous la surveillance, directe ou indirecte, d'une personne nommément désignée par l'exploitant, ayant une connaissance de la conduite de l'installation, des dangers et inconvénients que l'exploitation induit, des produits utilisés ou stockés dans l'installation et des dispositions à mettre en œuvre en cas d'incident ou d'accident.": False,  # noqa: E501
    "Avant l'abandon de son exploitation, l'industriel remet le site dans un état tel qu'il ne s'y manifeste aucun des dangers ou inconvénients mentionnés à l'article 1er de la loi du 19 juillet 1976.": False,  # noqa: E501
    "Contrôle par l'inspection des installations classées.": True,  # noqa: E501
    "L'exploitant met en place les mesures de prévention adaptées aux installations et aux produits, permettant de limiter la probabilité d'occurrence d'une explosion ou d'un incendie, sans préjudice des dispositions du code du travail. Il assure le maintien dans le temps de leurs performances.": False,  # noqa: E501
    'Le présent arrêté fixe les prescriptions applicables aux installations classées soumises à enregistrement sous la rubrique 1532.': False,  # noqa: E501
    "Afin d'éviter le ruissellement des eaux extérieures aux aires de stockage de déchets d'extraction sur le site lui-même, un fossé extérieur de collecte, dimensionné pour capter au moins les ruissellements consécutifs à un événement pluvieux de fréquence décennale, est mis en place.": False,  # noqa: E501
    "Critères minimaux applicables aux rejets d'effluents liquides dans le milieu naturel": True,  # noqa: E501
    "Conformité de l'installation à la déclaration": True,  # noqa: E501
    "Les tuyauteries transportant des fluides dangereux ou insalubres et de collecte d'effluents pollués ou susceptibles de l'être sont étanches et résistent à l'action physique et chimique des produits qu'elles sont susceptibles de contenir. Elles sont convenablement repérées, entretenues et contrôlées.": False,  # noqa: E501
    'Échantillonnage.': True,  # noqa: E501
    'Matériels utilisables en atmosphères explosibles.': True,  # noqa: E501
    'Exécution.': True,  # noqa: E501
    "Les dispositions des annexes I, II et IV sont applicables aux installations déclarées postérieurement à la date de publication du présent arrêté au Journal officiel augmentée de quatre mois. Pour les installations nouvelles sises dans un bâtiment construit à la date de publication du présent arrêté, et nouvellement soumises à la rubrique n° 4735  suite à un changement de fluide frigorigène, et déclarées postérieurement à la date de publication du présent arrêté au Journal officiel augmentée de quatre mois, ces dispositions s'appliquent dans les conditions précisées en annexe III.": False,  # noqa: E501
    'Un modèle a été constitué pour la rédaction des arrêtés de prescriptions générales applicables aux installations soumises à déclaration. Certaines dispositions de ce modèle, qui ne se justifient pas pour les installations visées par la rubrique n° 1212, ont été supprimées. Néanmoins, la numérotation a été conservée pour permettre une homogénéité entre les arrêtés de prescriptions générales de toutes les rubriques de la nomenclature.': False,  # noqa: E501
    "Les installations de prélèvement d'eau dans le milieu naturel ou dans un réseau public sont munies de dispositifs de mesure totalisateurs de la quantité d'eau prélevée. Ces dispositifs sont relevés toutes les semaines si le débit moyen prélevé dans le milieu naturel est supérieur à 10 m³/j. Le résultat de ces mesures est enregistré et tenu à la disposition de l'inspecteur des installations classées pendant une durée minimale de cinq ans.": False,  # noqa: E501
    "L'exploitant prend les dispositions appropriées pour préserver la biodiversité végétale et animale sur son exploitation, notamment en implantant ou en garantissant le maintien d'infrastructures agro-écologiques de type haies d'espèces locales, bosquets, talus enherbés, points d'eau.": False,  # noqa: E501
    "Prélèvement d'eau.": True,  # noqa: E501
    "Lorsque l'établissement comporte plusieurs dépôts, plusieurs aires de stockage ou plusieurs cellules au sein d'un même dépôt, les distances mentionnées à l'article 7 peuvent être calculées par dépôt ou par aire de stockage ou par cellule, sur la base des capacités propres à chaque dépôt ou aire de stockage ou cellule si l'un des critères suivant au moins est respecté et justifié par l'exploitant :": False,  # noqa: E501
    "Le débit des effluents gazeux est exprimé en mètres cubes par heure rapportés à des conditions normalisées de température (273 kelvins) et de pression (101,3 kilopascals) après déduction de la vapeur d'eau (gaz secs). Le débit des effluents gazeux ainsi que les concentrations en polluants sont rapportés à une teneur en oxygène de référence établie en fonction du combustible (6 % en volume dans le cas des combustibles solides et de la biomasse, 3 % en volume dans le cas des combustibles liquides ou gazeux). Les concentrations en polluants sont exprimées en gramme(s) ou milligramme(s) par mètre cube rapporté(s) aux mêmes conditions normalisées.": False,  # noqa: E501
    "Le préfet peut, pour une installation donnée, adapter par arrêté les dispositions énumérées à l'annexe III (1) dans les conditions prévues à l'article L. 512-12 du code de l'environnement et à l'article 30 du décret du 21 septembre 1977 susvisés.": False,  # noqa: E501
    'Comportement au feu': True,  # noqa: E501
    "Les dispositions de l'article 9 s'appliquent :": False,  # noqa: E501
    'PRESCRIPTIONS GÉNÉRALES ET FAISANT L’OBJET DU CONTRÔLE PÉRIODIQUE APPLICABLES AUX': True,  # noqa: E501
    "PRESCRIPTIONS GÉNÉRALES APPLICABLES AUX INSTALLATIONS CLASSÉES POUR LA PROTECTION DE L'ENVIRONNEMENT SOUMISES À DÉCLARATION SOUS LA RUBRIQUE N° 2345": True,  # noqa: E501
    "L'exploitant déclare ses déchets conformément aux seuils et aux critères de l'arrêté du 31 janvier 2008 modifié relatif au registre et à la déclaration annuelle des émissions polluantes et des déchets.": False,  # noqa: E501
    "La mesure du débit d'odeur est effectuée, notamment à la demande du préfet, selon les méthodes normalisées en vigueur si l'installation fait l'objet de plaintes relatives aux nuisances olfactives.": False,  # noqa: E501
    "Les installations classées relevant du régime de la déclaration sous la rubrique n° 2518 relative aux installations de production de béton prêt à l'emploi équipées d'un dispositif d'alimentation en liants hydrauliques mécanisé sont soumises aux prescriptions générales du présent arrêté (1). Les présentes dispositions s'appliquent sans préjudice des autres législations.": False,  # noqa: E501
    "L'organisation de la circulation des véhicules à l'intérieur du site doit être conçue pour qu'aucun véhicule souillé ne quitte le site sans avoir reçu un lavage approprié.": False,  # noqa: E501
    'Les opérations sont surveillées en permanence depuis la salle de contrôle ou dispositif équivalent.': False,  # noqa: E501
    "Valeur limite d'émission.": True,  # noqa: E501
    "L'exploitant identifie, dans son dossier de demande d'enregistrement, les produits dangereux détenus sur le site.": False,  # noqa: E501
    "Pour les stations de traitement des effluents, le niveau de traitement minimal est fixé par l'arrêté préfectoral d'autorisation et, en cas de rejet dans les eaux superficielles d'effluents traités, le flux journalier maximal de pollution admissible est compatible avec les objectifs de qualité fixés pour le milieu récepteur.": False,  # noqa: E501
    "Les installations classées pour la protection de l'environnement soumises à déclaration sous la rubrique n° 2575 (Abrasives [emploi de matières] telles que sables, corindon, grenailles métalliques, etc., sur un matériau quelconque pour gravure, dépolissage, décapage, grainage), la puissance de l'ensemble des machines fixes concourant au fonctionnement de l'installation étant supérieure à 20 kW, sont soumises aux dispositions de l'annexe I. Les présentes dispositions s'appliquent sans préjudice des autres législations.": False,  # noqa: E501
    "Sur la base des éléments mentionnés dans le dossier de demande d'autorisation d'exploiter et sans préjudice des dispositions de l'article 13, les zones attenantes (locaux ou aires extérieures) aux locaux ou zones, où sont mises en œuvre des substances ou déchets radioactifs, sont conçues et réalisées de façon à ce que l'exposition des personnes aux rayonnements ionisants soit aussi basse que raisonnablement possible et de façon à ce que la dose susceptible d'être reçue en un an, exprimée en dose efficace, reste inférieure à 1 mSv. Lorsque cette disposition ne peut être mise en œuvre, des mesures compensatoires sont prévues dans l'arrêté préfectoral d'autorisation conformément aux dispositions du II de l'article 2.": False,  # noqa: E501
    'Le préfet peut, pour une installation donnée, modifier par arrêté les dispositions des annexes I et II dans les conditions prévues aux articles 11 de la loi du 19 juillet 1976 et 30 du décret du 21 septembre 1977 susvisés.': False,  # noqa: E501
    "Le préfet peut, pour une installation donnée, adapter par arrêté les dispositions des annexes I à IV dans les conditions prévues aux articles L. 512-12 et R. 512-52 du code de l'environnement.": False,  # noqa: E501
    "Le site est clôturé. La hauteur de la clôture n'est pas inférieure à 2,5 mètres.": False,  # noqa: E501
    "PRESCRIPTIONS GÉNÉRALES APPLICABLES AUX INSTALLATIONS CLASSÉES POUR LA PROTECTION DE L'ENVIRONNEMENT SOUMISES À DÉCLARATION SOUS LA RUBRIQUE N° 2794": True,  # noqa: E501
    "Systèmes de détection et d'extinction automatiques.": True,  # noqa: E501
    "Les émissions sonores de l'installation respectent les dispositions de l'arrêté du 23 janvier 1997 relatif à la limitation des bruits émis dans l'environnement par les installations classées pour la protection de l'environnement.": False,  # noqa: E501
    "Les canalisations de transport de fluides dangereux ou insalubres et de collecte d'effluents pollués ou susceptibles de l'être sont étanches et résistent à l'action physique et chimique des produits qu'elles sont susceptibles de contenir. Elles sont convenablement entretenues et font l'objet d'examens périodiques appropriés permettant de s'assurer de leur bon état. Les canalisations de transport de fluides dangereux à l'intérieur de l'établissement sont aériennes, sauf exception motivée par des raisons de sécurité ou d'hygiène dans le dossier d'enregistrement.": False,  # noqa: E501
    'Les installations sont implantées à une distance minimale de 5 mètres des limites de propriété du site où elles sont implantées.': False,  # noqa: E501
    "Sans préjudice des dispositions du code du travail, l'exploitant dispose des documents lui permettant de connaître la nature et les risques des produits dangereux présents dans l'installation, en particulier les fiches de données de sécurité.": False,  # noqa: E501
    "Les installations classées pour la protection de l'environnement soumises à déclaration sous la rubrique n° 2661 (Transformation de polymères matières plastiques, caoutchouc, élastomères, résines et adhésifs synthétiques par des procédés exigeant des conditions particulières de température ou de pression, la quantité de matière susceptible d'être traitée étant supérieure ou égale à 1 t/j, mais inférieure à 10 t/j ; par tout procédé exclusivement mécanique, la quantité de matière susceptible d'être traitée étant supérieure ou égale à 2 t/j, mais inférieure à 20 t/j) sont soumises aux dispositions de l'annexe I. Les présentes dispositions s'appliquent sans préjudice des autres législations.": False,  # noqa: E501
    "Le dossier de demande d'enregistrement comprend notamment :": False,  # noqa: E501
    'Dossier Installation classée.': True,  # noqa: E501
    'Règles techniques applicables en matière de vibrations': True,  # noqa: E501
    "L'exploitant prend toutes les dispositions nécessaires dans la conception et l'exploitation de ses installations pour assurer une bonne gestion des déchets de son entreprise, notamment :": False,  # noqa: E501
}


def test_is_title():
    for title, is_title in _IS_TITLE.items():
        assert is_probably_title(title) == is_title


def test_first_word():
    assert _first_word('Le chat est') == 'Le'
    assert _first_word('Foo bar foo') == 'Foo'
    assert _first_word('Foo\'bar foo') == 'Foo'
    assert _first_word('C\'est un') == 'C'
    assert _first_word('L\'amour est enfant') == 'L'
