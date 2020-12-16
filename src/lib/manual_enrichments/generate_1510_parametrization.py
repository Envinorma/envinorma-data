from dataclasses import replace
from datetime import datetime
from lib.parametrization import ConditionSource, EntityReference, SectionReference
from typing import Dict, List, Optional, Tuple

from lib.data import ArreteMinisteriel, EnrichedString, Regime, StructuredText
from lib.parametrization import (
    AlternativeSection,
    AndCondition,
    NonApplicationCondition,
    Equal,
    Littler,
    OrCondition,
    Condition,
    Parameter,
    ParameterEnum,
    ParameterType,
    Parametrization,
    Range,
    Combinations,
)
from lib.am_enriching import remove_sections


def _build_simple_structured_text(title: str, alineas: List[str]) -> StructuredText:
    return StructuredText(
        title=EnrichedString(title),
        outer_alineas=[EnrichedString(x) for x in alineas],
        sections=[],
        legifrance_article=None,
        applicability=None,
    )


def _build_alternative_13_for_autorisation() -> StructuredText:
    title = "13. Moyens de lutte contre l\'incendie"
    alineas = [
        "L\'installation est dotée de moyens de lutte contre l\'incendie appropriés aux risques, notamment :",
        "- d\'un ou de plusieurs points d\'eau incendie, tels que :",
        "a. Des prises d\'eau, poteaux ou bouches d\'incendie normalisés, d\'un diamètre nominal adapté au débit à fournir, alimentés par un réseau public ou privé, sous des pressions minimale et maximale permettant la mise en œuvre des pompes des engins de lutte contre l\'incendie ;",
        "b. Des réserves d\'eau, réalimentées ou non, disponibles pour le site et dont les organes de manœuvre sont accessibles en permanence aux services d\'incendie et de secours.",
        "Les prises de raccordement sont conformes aux normes en vigueur pour permettre aux services d\'incendie et de secours de s\'alimenter sur ces points d\'eau incendie.",
        "L\'accès extérieur de chaque cellule est à moins de 100 mètres d\'un point d\'eau incendie:",
        "- d\'extincteurs répartis à l\'intérieur de l\'entrepôt, sur les aires extérieures et dans les lieux présentant des risques spécifiques, à proximité des dégagements, bien visibles et facilement accessibles. Les agents d\'extinction sont appropriés aux risques à combattre et compatibles avec les matières stockées ;",
        "- de robinets d\'incendie armés, situés à proximité des issues. Ils sont disposés de telle sorte qu\'un foyer puisse être attaqué simultanément par deux lances sous deux angles différents. Ils sont utilisables en période de gel ; ce point n\'est pas applicable pour les cellules ou parties de cellules dont le stockage est totalement automatisé ;",
        "- le cas échéant, les colonnes sèches ou les moyens fixes d\'aspersion d\'eau prévus au point 6 de cette annexe.",
        "Les points d\'eau incendie sont en mesure de fournir un débit minimum de 60 mètres cubes par heure durant deux heures.",
        "Le débit et la quantité d\'eau nécessaires sont calculés conformément au document technique D9 (guide pratique pour le dimensionnement des besoins en eau de l\'Institut national d\'études de la sécurité civile, la Fédération française des sociétés d\'assurances et le Centre national de prévention et de protection, édition septembre 2001, sans toutefois dépasser 720 m3/h durant 2 heures.",
        "Le débit et la quantité d\'eau nécessaires peuvent toutefois être inférieurs à ceux calculés par l\'application du document technique D9, sous réserve qu\'une étude spécifique démontre leur caractère suffisant au regard des objectifs visés à l\'article 1er. La justification pourra prévoir un recyclage d\'une partie des eaux d\'extinction d\'incendie, sous réserve de l\'absence de stockage de produits dangereux ou corrosifs dans la zone concernée par l\'incendie. A cet effet, des aires de stationnement des engins d\'incendie, accessibles en permanence aux services d\'incendie et de secours, respectant les dispositions prévues au 3.3.2, sont disposées aux abords immédiats de la capacité de rétention des eaux d\'extinction d\'incendie.",
        "L\'exploitant joint au dossier prévu à l\'article 1.2 de la présente annexe la justification de la disponibilité effective des débits et le cas échéant des réserves d\'eau, au plus tard trois mois après la mise en service de l\'installation.",
        "En cas d\'installation de systèmes d\'extinction automatique d\'incendie, ceux-ci sont conçus, installés et entretenus régulièrement conformément aux référentiels reconnus. L\'efficacité de cette installation est qualifiée et vérifiée par des organismes reconnus compétents dans le domaine de l\'extinction automatique ; la qualification précise que l\'installation est adaptée aux produits stockés et à leurs conditions de stockage.",
        "L\'installation est dotée d\'un moyen permettant d\'alerter les services d\'incendie et de secours.",
        "Dans le trimestre qui suit le début de l\'exploitation de tout entrepôt soumis à enregistrement ou à autorisation, l\'exploitant organise un exercice de défense contre l\'incendie. Cet exercice est renouvelé au moins tous les trois ans.",
    ]
    return _build_simple_structured_text(title, alineas)


def _build_alternative_12_for_autorisation() -> StructuredText:
    title = "12. Détection automatique d\'incendie"
    alineas = [
        'La détection automatique d\'incendie avec transmission, en tout temps, de l\'alarme à l\'exploitant est obligatoire pour les cellules, les locaux techniques et pour les bureaux à proximité des stockages. Cette détection actionne une alarme perceptible en tout point du bâtiment permettant d\'assurer l\'alerte précoce des personnes présentes sur le site.',
        'Le type de détecteur est déterminé en fonction des produits stockés. Cette détection peut être assurée par le système d\'extinction automatique s\'il est conçu pour cela, à l\'exclusion du cas des cellules comportant au moins une mezzanine, pour lesquelles un système de détection dédié et adapté doit être prévu.',
        'Dans tous les cas, l\'exploitant s\'assure que le système permet une détection de tout départ d\'incendie tenant compte de la nature des produits stockés et du mode de stockage.',
        'Sauf pour les installations soumises à déclaration, l\'exploitant inclut dans le dossier prévu au point 1.2 de la présente annexe les documents démontrant la pertinence du dimensionnement retenu pour les dispositifs de détection.',
    ]
    return _build_simple_structured_text(title, alineas)


def _build_alternative_2_I_for_autorisation() -> StructuredText:
    title = "I. - Pour les installations soumises à enregistrement ou à autorisation, les parois extérieures de l\'entrepôt (ou les éléments de structure dans le cas d\'un entrepôt ouvert) sont suffisamment éloignées :"

    alineas = [
        "- des constructions à usage d\'habitation, des immeubles habités ou occupés par des tiers et des zones destinées à l\'habitation, à l\'exclusion des installations connexes à l\'entrepôt, et des voies de circulation autres que celles nécessaires à la desserte ou à l\'exploitation de l\'entrepôt, d\'une distance correspondant aux effets létaux en cas d\'incendie (seuil des effets thermiques de 5 kW/m2) ;",
        "- des immeubles de grande hauteur, des établissements recevant du public (ERP) autres que les guichets de dépôt et de retrait des marchandises conformes aux dispositions du point 4. de la présente annexe sans préjudice du respect de la réglementation en matière d\'ERP, des voies ferrées ouvertes au trafic de voyageurs, des voies d\'eau ou bassins exceptés les bassins de rétention ou d\'infiltration d\'eaux pluviales et de réserve d\'eau incendie, et des voies routières à grande circulation autres que celles nécessaires à la desserte ou à l\'exploitation de l\'entrepôt, d\'une distance correspondant aux effets irréversibles en cas d\'incendie (seuil des effets thermiques de 3 kW/m2)",
        "Ces distances résultent de l'instruction de la demande d'autorisation et de l'examen de l'étude des dangers. Les parois extérieures de l\'entrepôt ou les éléments de structure dans le cas d\'un entrepôt ouvert, sont implantées à une distance au moins égale à 20 mètres de l\'enceinte de l\'établissement, à moins que l\'exploitant justifie que les effets létaux (seuil des effets thermiques de 5 kW/m2) restent à l\'intérieur du site au moyen, si nécessaire, de la mise en place d\'un dispositif séparatif E120.",
    ]
    return _build_simple_structured_text(title, alineas)


def _build_alternative_3_2_for_autorisation() -> StructuredText:
    title = "3.2. "
    alineas = [
        "L'entrepôt est en permanence accessible pour permettre l'intervention des services d'incendie et de secours. Une voie au moins est maintenue dégagée pour la circulation sur le périmètre de l'entrepôt. Cette voie permet l'accès des engins de secours des sapeurs-pompiers et les croisements de ces engins.",
        "A partir de cette voie, les sapeurs-pompiers peuvent accéder à toutes les issues de l'entrepôt par un chemin stabilisé de 1,40 mètres de large au minimum.",
        "Pour tout bâtiment de hauteur supérieure à 15 mètres, des aires de mise en station des moyens aériens sont prévus pour chaque façade. Cette disposition est également applicable aux entrepôts de plusieurs niveaux possédant au moins un plancher situé à une hauteur supérieure à 8 mètres par rapport au niveau d'accès des secours.",
        "Les véhicules dont la présence est liée à l'exploitation de l'entrepôt peuvent stationner sans occasionner de gêne sur les voies de circulation externe à l'entrepôt tout en laissant dégagés les accès nécessaires aux secours, même en dehors des heures d'exploitation et d'ouverture de l'entrepôt.",
    ]
    return _build_simple_structured_text(title, alineas)


def _build_alternative_4_for_autorisation() -> StructuredText:
    title = "4. Dispositions constructives"
    alineas = [
        "Les dispositions constructives visent à ce que la cinétique d\'incendie soit compatible avec l\'évacuation des personnes, l\'intervention des services de secours et la protection de l\'environnement. Elles visent notamment à ce que la ruine d\'un élément de structure (murs, toiture, poteaux, poutres par exemple) suite à un sinistre n\'entraîne pas la ruine en chaîne de la structure du bâtiment, notamment les cellules de stockage avoisinantes, ni de leurs dispositifs de recoupement, et ne conduit pas à l\'effondrement de la structure vers l\'extérieur de la cellule en feu.",
        "Les murs extérieurs sont construits en matériaux de classe A2 s1 d0, sauf si le bâtiment est doté d\'un dispositif d\'extinction automatique d\'incendie.",
        "Les éléments de support de la toiture sont réalisés en matériaux A2 s1 d0. Cette disposition n\'est pas applicable si la structure porteuse est en lamellé-collé, en bois massif ou en matériaux reconnus équivalents par rapport au risque incendie, par la direction générale de la sécurité civile et de la gestion des crises du ministère chargé de l\'intérieur.",
        "En ce qui concerne la toiture, ses éléments de support sont réalisés en matériaux A2 s1 d0 et l'isolant thermique (s'il existe) est réalisé en matériaux A2 s1 d0 ou B s1 d0 de pouvoir calorifique supérieur (pcs) inférieur ou égal à 8,4 mj/kg. cette disposition n'est pas applicable si la structure porteuse est en lamellé-collé, en bois massif ou en matériaux reconnus équivalents par rapport au risque incendie, par la direction générale de la sécurité civile et de la gestion des crises du ministère chargé de l'intérieur.",
        "Le système de couverture de toiture satisfait la classe BROOF (t3).",
        "Les matériaux utilisés pour l\'éclairage naturel satisfont à la classe d0.",
        "Pour les entrepôts de deux niveaux ou plus, les planchers sont au moins EI 120 et les structures porteuses des planchers au moins R120 et la stabilité au feu de la structure est au moins R 60 pour ceux dont le plancher du dernier niveau est situé à plus de 8 mètres du sol intérieur. Pour les entrepôts à simple rez-de-chaussée de plus de 13,70 m de hauteur, la stabilité au feu de la structure est au moins R 60.",
        "Les escaliers intérieurs reliant des niveaux séparés, dans le cas de planchers situés à plus de 8 mètres du sol intérieur et considérés comme issues de secours, sont encloisonnés par des parois au moins REI 60 et construits en matériaux de classe A2 s1 d0. Ils débouchent soit directement à l\'air libre, soit dans un espace protégé. Les blocs-portes intérieurs donnant sur ces escaliers sont au moins E 60 C2.",
        "Les ateliers d\'entretien du matériel sont isolés par une paroi et un plafond au moins REI 120 ou situés dans un local distant d\'au moins 10 mètres des cellules de stockage. Les portes d\'intercommunication présentent un classement au moins EI2 120 C (classe de durabilité C2 pour les portes battantes).",
        "A l\'exception des bureaux dits de quais destinés à accueillir le personnel travaillant directement sur les stockages, des zones de préparation ou de réception, des quais eux-mêmes, les bureaux et les locaux sociaux ainsi que les guichets de retrait et dépôt des marchandises sont situés dans un local clos distant d\'au moins 10 mètres des cellules de stockage ou isolés par une paroi au moins REI 120. Ils ne peuvent être contigus aux cellules où sont présentes des matières dangereuses. Ils sont également isolés par un plafond au moins REI 120 et des portes d\'intercommunication munies d\'un ferme-porte présentant un classement au moins EI2 120 C (classe de durabilité C2). Ce plafond n\'est pas obligatoire si le mur séparatif au moins REI 120 entre le local bureau et la cellule de stockage dépasse au minimum d\'un mètre, conformément au point 6, ou si le mur séparatif au moins REI 120 arrive jusqu\'en sous-face de toiture de la cellule de stockage, et que le niveau de la toiture du local bureau est située au moins à 4 mètres au-dessous du niveau de la toiture de la cellule de stockage). De plus, lorsqu\'ils sont situés à l\'intérieur d\'une cellule, le plafond est au moins REI 120, et si les bureaux sont situés en étage le plancher est également au moins REI 120.",
        "Les justificatifs attestant du respect des prescriptions du présent point sont conservés et intégrés au dossier prévu au point 1.2. de la présente annexe.",
    ]
    return _build_simple_structured_text(title, alineas)


def _build_alternative_5_for_autorisation() -> StructuredText:
    title = "5. Désenfumage"
    alineas = [
        "Les cellules de stockage sont divisées en cantons de désenfumage d\'une superficie maximale de 1 650 mètres carrés et d\'une longueur maximale de 60 mètres. Les cantons sont délimités par des écrans de cantonnement, réalisés en matériaux A2 s1 d0 (y compris leurs fixations) et stables au feu de degré un quart d'heure, ou par la configuration de la toiture et des structures du bâtiment.",
        "Les cantons de désenfumage sont équipés en partie haute de dispositifs d\'évacuation des fumées, gaz de combustion, chaleur et produits imbrûlés.",
        "Des exutoires à commande automatique et manuelle font partie des dispositifs d\'évacuation des fumées. La surface utile de l\'ensemble de ces exutoires n\'est pas inférieure à 2 % de la superficie de chaque canton de désenfumage.",
        "Le déclenchement du désenfumage n\'est pas asservi à la même détection que celle à laquelle est asservi le système d\'extinction automatique. Les dispositifs d\'ouverture automatique des exutoires sont réglés de telle façon que l\'ouverture des organes de désenfumage ne puisse se produire avant le déclenchement de l\'extinction automatique.",
        "Il faut prévoir au moins quatre exutoires pour 1 000 mètres carrés de superficie de toiture. La surface utile d\'un exutoire n\'est pas inférieure à 0,5 mètre carré ni supérieure à 6 mètres carrés. Les dispositifs d\'évacuation ne sont pas implantés sur la toiture à moins de 7 mètres des murs coupe-feu séparant les cellules de stockage. Cette distance peut être réduite pour les cellules dont une des dimensions est inférieure à 15 m.",
        "La commande manuelle des exutoires est au minimum installée en deux points opposés de l\'entrepôt de sorte que l\'actionnement d\'une commande empêche la manœuvre inverse par la ou les autres commandes. Ces commandes manuelles sont facilement accessibles aux services d\'incendie et de secours depuis les issues du bâtiment ou de chacune des cellules de stockage. Elles doivent être manœuvrables en toutes circonstances.",
        "Des amenées d\'air frais d\'une superficie au moins égale à la surface utile des exutoires du plus grand canton, cellule par cellule, sont réalisées soit par des ouvrants en façade, soit par des bouches raccordées à des conduits, soit par les portes des cellules à désenfumer donnant sur l\'extérieur.",
        "En cas d\'entrepôt à plusieurs niveaux, les niveaux autres que celui sous toiture sont désenfumés par des ouvrants en façade asservis à la détection conformément à la réglementation applicable aux établissements recevant du public.",
        "Les dispositions de ce point ne s\'appliquent pas pour un stockage couvert ouvert.",
    ]
    return _build_simple_structured_text(title, alineas)


def _build_alternative_7_for_autorisation() -> StructuredText:
    title = "7. Dimensions des cellules"
    alineas = [
        "La surface des cellules de stockage est limitée de façon à réduire la quantité de matières combustibles en feu et d'éviter la propagation du feu d'une cellule à l'autre.",
        "La surface maximale des cellules est égale à 3 000 mètres carrés en l'absence de système d'extinction automatique d'incendie ou 6 000 mètres carrés en présence de système d'extinction automatique d'incendie.",
    ]
    return _build_simple_structured_text(title, alineas)


def _build_alternative_11_for_autorisation() -> StructuredText:
    title = "11. Eaux d\'extinction incendie"
    alineas = [
        "Toutes mesures sont prises pour recueillir l\'ensemble des eaux et écoulements susceptibles d\'être pollués lors d\'un sinistre, y compris les eaux utilisées pour l\'extinction d\'un incendie et le refroidissement, afin que celles-ci soient récupérées ou traitées afin de prévenir toute pollution des sols, des égouts, des cours d\'eau ou du milieu naturel. Ce confinement peut être réalisé par des dispositifs internes ou externes aux cellules de stockage. Les dispositifs internes sont interdits lorsque des matières dangereuses sont stockées.",
        "Dans le cas d\'un confinement externe, les matières canalisées sont collectées, de manière gravitaire ou grâce à des systèmes de relevage autonomes, puis convergent vers une rétention extérieure au bâtiment. En cas de recours à des systèmes de relevage autonomes, l\'exploitant est en mesure de justifier à tout instant d\'un entretien et d\'une maintenance rigoureux de ces dispositifs. Des tests réguliers sont par ailleurs menés sur ces équipements.",
        "En cas de confinement interne, les orifices d\'écoulement sont en position fermée par défaut.",
        "En cas de confinement externe, les orifices d\'écoulement issus de ces dispositifs sont munis d\'un dispositif automatique d\'obturation pour assurer ce confinement lorsque des eaux susceptibles d\'être polluées y sont portées. Tout moyen est mis en place pour éviter la propagation de l\'incendie par ces écoulements.",
        "Le volume nécessaire à ce confinement est déterminé notamment au vu de l'étude de dangers en fonction de la rapidité d'intervention et des moyens d'intervention ainsi que de la nature des matières stockées, et mentionné dans l'arrêté préfectoral.",
        "Les réseaux de collecte des effluents et des eaux pluviales de l\'établissement sont équipés de dispositifs d\'isolement visant à maintenir toute pollution accidentelle, en cas de sinistre, sur le site. Ces dispositifs sont maintenus en état de marche, signalés et actionnables en toute circonstance localement et à partir d\'un poste de commande. Leur entretien et leur mise en fonctionnement sont définis par consigne.",
    ]
    return _build_simple_structured_text(title, alineas)


def _build_alternative_7_for_enregistrement() -> StructuredText:
    return _build_simple_structured_text(
        '7. Dimensions des cellules',
        [
            "La surface maximale des cellules est égale à 3 000 mètres carrés en l'absence de système d'extinction automatique d'incendie et à 6 000 mètres carrés en présence d'un système d'extinction automatique d'incendie adapté à la nature des produits stockés.",
            "La surface d'une mezzanine occupe au maximum 50 % de la surface du niveau inférieur de la cellule. Dans le cas où, dans une cellule, un niveau comporte plusieurs mezzanines, l'exploitant démontre, par une étude, que ces mezzanines n'engendrent pas de risque supplémentaire, et notamment qu'elles ne gênent pas le désenfumage en cas d'incendie.",
            "Pour les entrepôts textile, la surface peut être portée à 85 % sous réserve que l'exploitant démontre, par une étude, que cette mezzanine n'engendre pas de risque supplémentaire, et notamment qu'elle ne gêne pas le désenfumage en cas d'incendie.",
        ],
    )


def _build_alternative_3_2_for_enr_after_2010() -> StructuredText:
    return _build_simple_structured_text(
        '3.2. Voie engins',
        [
            "Une voie \"engins\", dans l'enceinte de l'établissement, au moins est maintenue dégagée pour la circulation et le croisement sur le périmètre de l'installation et est positionnée de façon à ne pas être obstruée par l'effondrement de cette installation et par les eaux d'extinction.",
            "Cette voie \"engins\" respecte les caractéristiques suivantes : - la largeur utile est au minimum de 6 mètres, la hauteur libre au minimum de 4,5 mètres et la pente inférieure à 15 % ; - dans les virages de rayon intérieur inférieur à 50 mètres, un rayon intérieur R minimal de 13 mètres est maintenu et une sur largeur de S = 15/R mètres est ajoutée ; - la voie résiste à la force portante calculée pour un véhicule de 320 kN avec un maximum de 130 kN par essieu, ceux-ci étant distants de 3,6 mètres au minimum ; - chaque point du périmètre de l'installation est à une distance maximale de 60 mètres de cette voie ; - aucun obstacle n'est disposé entre la voie engins et les accès à l'installation ou aux aires de mise en station des moyens aériens.",
            "En cas d'impossibilité de mise en place d'une voie engin permettant la circulation sur l'intégralité du périmètre de l'installation et si tout ou partie de la voie est en impasse, les quarante derniers mètres de la partie de la voie en impasse sont d'une largeur utile minimale de 7 mètres et une aire de retournement comprise dans un cercle de 20 mètres de diamètre est prévue à son extrémité.",
        ],
    )


def _build_alternative_3_3_for_enr_after_2010() -> StructuredText:
    return _build_simple_structured_text(
        '3.3. Aires de stationnement',
        [
            "Chaque cellule a au moins une façade accessible desservie par une voie permettant la circulation et la mise en station des échelles et bras élévateurs articulés. Cette aire de mise en station des moyens aériens est directement accessible depuis la voie engin définie au 3.2.",
            "Depuis cette aire, une un moyen aérien (par exemple une échelle ou un bras élévateur articulé) peut être mis en station pour accéder à au moins toute la hauteur du bâtiment et défendre chaque mur séparatif coupe-feu. L'aire respecte par ailleurs les caractéristiques suivantes :",
            "- la largeur utile est au minimum de 4 mètres, la longueur de l'aire de stationnement au minimum de 15 mètres, la pente au maximum de 10 % ;",
            "- dans les virages de rayon intérieur inférieur à 50 mètres, un rayon intérieur R minimal de 13 mètres est maintenu et une sur largeur de S = 15/R mètres est ajoutée ;",
            "- aucun obstacle aérien ne gêne la manœuvre de ces moyens aériens à la verticale de cette aire ;",
            "- la distance par rapport à la façade est de 1 mètre minimum et 8 mètres maximum pour un stationnement parallèle au bâtiment et inférieure à 1 mètre pour un stationnement perpendiculaire au bâtiment ;",
            "- la voie résiste à la force portante calculée pour un véhicule de 320 kN avec un maximum de 130 kN par essieu, ceux-ci étant distants de 3,6 mètres au minimum, et présente une résistance minimale au poinçonnement de 88 N/cm2.",
            "Par ailleurs, pour tout bâtiment de plusieurs niveaux possédant au moins un plancher situé à une hauteur supérieure à 8 mètres par rapport au niveau d'accès des secours, sur au moins deux façades, cette aire de mise en station des moyens aériens permet d'accéder à des ouvertures.",
            "Ces ouvertures qui demeurent accessibles de l'extérieur et de l'intérieur permettent au moins deux accès par étage pour chacune des façades disposant d'aires de mise en station des moyens aériens et présentent une hauteur minimale de 1,8 mètre et une largeur minimale de 0,9 mètre. Elles sont aisément repérables de l'extérieur par les services de secours.",
            "Les dispositions du présent point ne sont pas exigées si la cellule a une surface de moins de 2 000 mètres carrés respectant les dispositions suivantes :",
            "- au moins un de ses murs séparatifs se situe à moins de 23 mètres d'une façade accessible ;",
            "- la cellule comporte un dispositif d'extinction automatique d'incendie ;",
            "- la cellule ne comporte pas de mezzanine.",
        ],
    )


def _build_alternative_4_for_enr_after_2010() -> StructuredText:
    return _build_simple_structured_text(
        '4. Dispositions constructives',
        [
            "L'exploitant réalise une étude technique démontrant que les dispositions constructives visent à ce que la ruine d'un élément (murs, toiture, poteaux, poutres, mezzanines) suite à un sinistre n'entraîne pas la ruine en chaîne de la structure du bâtiment, notamment les cellules de stockage avoisinantes, ni de leurs dispositifs de compartimentage, ni l'effondrement de la structure vers l'extérieur de la cellule en feu. Cette étude est réalisée avec la construction de l'entrepôt et est tenue à disposition de l'inspection des installations classées.",
            "Les locaux abritant l'installation présentent les caractéristiques de réaction et de résistance au feu minimales suivantes : ",
            "- les parois extérieures des bâtiments sont construites en matériaux A2 s1 d0 ; ",
            "- l'ensemble de la structure est a minima R 15 ; ",
            "- pour les entrepôts à simple rez-de-chaussée de plus de 12,50 mètres de hauteur, la structure est R 60, sauf si le bâtiment est doté d'un dispositif d'extinction automatique d'incendie ; ",
            "- pour les entrepôts de deux niveaux ou plus, les planchers (hors mezzanines) sont au moins EI 120 et les structures porteuses des planchers R 120 au moins ; ",
            "- les murs séparatifs entre deux cellules sont au moins REI 120 ; ces parois sont prolongées latéralement le long du mur extérieur sur une largeur de 1 mètre ou sont prolongées perpendiculairement au mur extérieur de 0,50 mètre en saillie de la façade ; ",
            "- les éléments séparatifs entre cellules dépassent d'au moins 1 mètre la couverture du bâtiment au droit du franchissement. La toiture est recouverte d'une bande de protection sur une largeur minimale de 5 mètres de part et d'autre des parois séparatives. Cette bande est en matériaux A2 s1 d0 ou comporte en surface une feuille métallique A2 s1 d0 ; ",
            "- les murs séparatifs entre une cellule et un local technique (hors chaufferie) sont au moins REI 120 jusqu'en sous-face de toiture ou une distance libre de 10 mètres est respectée entre la cellule et le local technique ; ",
            "- les bureaux et les locaux sociaux, à l'exception des bureaux dits de quais destinés à accueillir le personnel travaillant directement sur les stockages et les quais, sont situés dans un local clos distant d'au moins 10 mètres des cellules de stockage.",
            "Cette distance peut être inférieure à 10 mètres si les bureaux et locaux sociaux sont : ",
            "- isolés par une paroi jusqu'en sous-face de toiture et des portes d'intercommunication munies d'un ferme-porte, qui sont tous au moins REI 120 ; ",
            "- sans être contigus avec les cellules où sont présentes des matières dangereuses.",
            "De plus, lorsque les bureaux sont situés à l'intérieur d'une cellule : ",
            "- le plafond est au moins REI 120 ; ",
            "- le plancher est également au moins REI 120 si les bureaux sont situés en étage ; ",
            "- les escaliers intérieurs reliant des niveaux séparés, dans le cas de planchers situés à plus de 8 mètres du sol intérieur, sont encloisonnés par des parois REI 60 et construits en matériaux A2 s1 d0. Ils débouchent directement à l'air libre, sinon sur des circulations encloisonnées de même degré coupe-feu y conduisant. Les blocs-portes intérieurs donnant sur ces escaliers sont E 60 C2 ; ",
            "- le sol des aires et locaux de stockage est de classe A1fl ; ",
            "- les ouvertures effectuées dans les parois séparatives (baies, convoyeurs, passages de gaines, câbles électriques et canalisations, portes, etc.) sont munies de dispositifs de fermeture ou de calfeutrement assurant un degré de résistance au feu équivalent à celui exigé pour ces parois. Les fermetures sont associées à un dispositif asservi à la détection automatique d'incendie assurant leur fermeture automatique, mais ce dispositif est aussi manœuvrable à la main, que l'incendie soit d'un côté ou de l'autre de la paroi. Ainsi les portes situées dans un mur au moins REI 120 présentent un classement EI2 120 C et les portes satisfont une classe de durabilité C2 ; ",
            "- les éléments de support de couverture de toiture, hors isolant, sont réalisés en matériaux A2 s1 d0 ; ",
            "- en ce qui concerne les isolants thermiques (ou l'isolant s'il n'y en a qu'un) : ",
            "- soit ils sont de classe A2 s1 d0 ; ",
            "- soit le système support + isolants est de classe B s1 d0 et respecte l'une des conditions ci-après : ",
            "- l'isolant, unique, a un PCS inférieur ou égal à 8,4 MJ/kg ; ",
            "- l'isolation thermique est composée de plusieurs couches dont la première (en contact avec le support de couverture), d'une épaisseur d'au moins 30 mm, de masse volumique supérieure à 110 kg/m3 et fixée mécaniquement, a un PCS inférieur ou égal à 8,4 MJ/kg et les couches supérieures sont constituées d'isolants, justifiant en épaisseur de 60 millimètres d'une classe D s3 d2. Ces couches supérieures sont recoupées au droit de chaque écran de cantonnement par un isolant de PCS inférieur ou égal à 8,4 MJ/kg ; ",
            "- le système de couverture de toiture satisfait la classe et l'indice BROOF (t3) ; ",
            "- les matériaux utilisés pour l'éclairage naturel satisfont à la classe d0.",
        ],
    )


def _build_alternative_5_for_enr_after_2010() -> StructuredText:
    return _build_simple_structured_text(
        '5. Désenfumage',
        [
            "Les cellules de stockage sont divisées en cantons de désenfumage d\'une superficie maximale de 1 650 mètres carrés et d\'une longueur maximale de 60 mètres. Les cantons sont délimités par des écrans de cantonnement, réalisés en matériaux A2 s1 d0 (y compris leurs fixations) et stables au feu de degré un quart d'heure. Leur hauteur est calculée conformément à la réglementation applicable aux établissements recevant du public.",
            "Les cantons de désenfumage sont équipés en partie haute de dispositifs d\'évacuation des fumées, gaz de combustion, chaleur et produits imbrûlés.",
            "Des exutoires à commande automatique et manuelle font partie des dispositifs d\'évacuation des fumées. La surface utile de l\'ensemble de ces exutoires n\'est pas inférieure à 2 % de la superficie de chaque canton de désenfumage.",
            "Le déclenchement du désenfumage n\'est pas asservi à la même détection que celle à laquelle est asservi le système d\'extinction automatique. Les dispositifs d\'ouverture automatique des exutoires sont réglés de telle façon que l\'ouverture des organes de désenfumage ne puisse se produire avant le déclenchement de l\'extinction automatique.",
            "Il faut prévoir au moins quatre exutoires pour 1 000 mètres carrés de superficie de toiture. La surface utile d\'un exutoire n\'est pas inférieure à 0,5 mètre carré ni supérieure à 6 mètres carrés. Les dispositifs d\'évacuation ne sont pas implantés sur la toiture à moins de 7 mètres des murs coupe-feu séparant les cellules de stockage. Cette distance peut être réduite pour les cellules dont une des dimensions est inférieure à 15 m.",
            "La commande manuelle des exutoires est au minimum installée en deux points opposés de l\'entrepôt de sorte que l\'actionnement d\'une commande empêche la manœuvre inverse par la ou les autres commandes. Ces commandes manuelles sont facilement accessibles aux services d\'incendie et de secours depuis les issues du bâtiment ou de chacune des cellules de stockage. Elles doivent être manœuvrables en toutes circonstances.",
            "Des amenées d\'air frais d\'une superficie au moins égale à la surface utile des exutoires du plus grand canton, cellule par cellule, sont réalisées soit par des ouvrants en façade, soit par des bouches raccordées à des conduits, soit par les portes des cellules à désenfumer donnant sur l\'extérieur.",
            "En cas d\'entrepôt à plusieurs niveaux, les niveaux autres que celui sous toiture sont désenfumés par des ouvrants en façade asservis à la détection conformément à la réglementation applicable aux établissements recevant du public.",
            "Les dispositions de ce point ne s\'appliquent pas pour un stockage couvert ouvert.",
        ],
    )


def _build_alternative_7_for_enr_after_2010() -> StructuredText:
    return _build_simple_structured_text(
        '7. Dimensions des cellules',
        [
            "La surface maximale des cellules est égale à 3 000 mètres carrés en l'absence de système d'extinction automatique d'incendie et à 6 000 mètres carrés en présence d'un système d'extinction automatique d'incendie adapté à la nature des produits stockés.",
            "La surface d'une mezzanine occupe au maximum 50 % de la surface du niveau inférieur de la cellule. Dans le cas où, dans une cellule, un niveau comporte plusieurs mezzanines, l'exploitant démontre, par une étude, que ces mezzanines n'engendrent pas de risque supplémentaire, et notamment qu'elles ne gênent pas le désenfumage en cas d'incendie.",
            "Pour les entrepôts textile, la surface peut être portée à 85 % sous réserve que l'exploitant démontre, par une étude, que cette mezzanine n'engendre pas de risque supplémentaire, et notamment qu'elle ne gêne pas le désenfumage en cas d'incendie.",
        ],
    )


def _7_replace_3_2() -> StructuredText:
    return _build_simple_structured_text(
        '3.2. Voie engins',
        [
            "Une voie \"engins\" au moins est maintenue dégagée pour la circulation sur le périmètre de l'entrepôt et des bâtiments accolés et est positionnée de façon à ne pouvoir être obstruée par l'effondrement de tout ou partie du stockage.",
            "Cette voie engins respecte les caractéristiques suivantes : ",
            "- la largeur utile est au minimum de 3 mètres, la hauteur libre au minimum de 3,5 mètres et la pente inférieure à 15 % ; ",
            "- dans les virages de rayon intérieur inférieur à 50 mètres, un rayon intérieur R minimal de 11 mètres est maintenu et une surlargeur de S = 15/R mètres est ajoutée ; ",
            "- la voie résiste à la force portante calculée pour un véhicule de 160 kN, avec un maximum de 90 kN par essieu, ceux-ci étant distants de 3,6 mètres au maximum ; ",
            "- chaque point du périmètre du stockage est à une distance maximale de 60 mètres de cette voie ; ",
            "- aucun obstacle n'est disposé entre la voie engins et les accès au bâtiment, les aires de mise en station des moyens aériens et les aires de stationnement des engins.",
            "En cas d'impossibilité de mise en place d'une voie engins permettant la circulation sur l'intégralité du périmètre de l'entrepôt et des bâtiments accolés et si tout ou partie de la voie est en impasse, les 40 derniers mètres de la partie de la voie en impasse sont d'une largeur utile minimale de 7 mètres et une aire de retournement de 10 mètres de diamètre est prévue à son extrémité.",
            "Pour permettre le croisement des engins de secours, tout tronçon de voie engins de plus de 100 mètres linéaires dispose d'au moins deux aires dites de croisement, judicieusement positionnées, dont les caractéristiques sont : ",
            "- largeur utile minimale de 3 mètres en plus de la voie engins ; ",
            "- longueur minimale de 10 mètres, présentant a minima les mêmes qualités de pente, de force portante et de hauteur libre que la voie engins.",
        ],
    )


def _7_replace_3_3() -> StructuredText:
    return _build_simple_structured_text(
        '3.3. Aires de stationnement',
        [
            "Pour tout stockage en bâtiment de hauteur supérieure à 8 mètres, au moins une façade est desservie par au moins une aire de mise en station des moyens aériens. Chaque aire de mise en station des moyens aériens est directement accessible depuis la voie engins définie au 3.2.",
            "Depuis cette aire, un moyen aérien (par exemple une échelle ou un bras élévateur articulé) accédant à au moins toute la hauteur du bâtiment peut être disposé.",
            "Chaque aire respecte par ailleurs les caractéristiques suivantes : ",
            "- la largeur utile est au minimum de 4 mètres, la longueur de l'aire de stationnement au minimum de 10 mètres, la pente au maximum de 10 % ; ",
            "- dans les virages de rayon intérieur inférieur à 50 mètres, un rayon intérieur R minimal de 11 mètres est maintenu et une surlargeur de S = 15/R mètres est ajoutée ; ",
            "- aucun obstacle aérien ne gêne la manœuvre de ces moyens aériens à la verticale de l'ensemble de la voie ; ",
            "- la distance par rapport à la façade est de 1 mètre minimum et 8 mètres maximum pour un stationnement parallèle au bâtiment et inférieure à 1 mètre pour un stationnement perpendiculaire au bâtiment ; ",
            "- la voie résiste à la force portante calculée pour un véhicule de 160 kN avec un maximum de 90 kN par essieu, ceux-ci étant distants de 3,6 mètres au maximum, et présente une résistance au poinçonnement minimale de 80 N/cm2.",
            "Par ailleurs, pour tout entrepôt de plusieurs niveaux possédant au moins un plancher situé à une hauteur supérieure à 8 mètres par rapport au niveau d'accès des secours, sur au moins deux façades, une aire de mise en station des moyens aériens permet d'accéder à des ouvertures.",
            "Ces ouvertures permettent au moins un accès par étage pour chacune des façades disposant de voie échelles et présentent une hauteur minimale de 1,8 mètre et une largeur minimale de 0,9 mètre.",
            "Les panneaux d'obturation ou les châssis composant ces accès s'ouvrent et demeurent toujours accessibles de l'extérieur et de l'intérieur. Ils sont aisément repérables de l'extérieur par les services de secours.",
        ],
    )


def _7_replace_3_4() -> StructuredText:
    return _build_simple_structured_text(
        '3.4. Accès aux issues et quais de déchargement',
        [
            "A partir de chaque voie engins ou échelles est prévu un accès à toutes les issues du bâtiment par un chemin stabilisé de 1,40 mètre de large au minimum."
        ],
    )


def _7_replace_4() -> StructuredText:
    return _build_simple_structured_text(
        '4. Dispositions constructives',
        [
            "Les locaux abritant l'installation présentent les caractéristiques de réaction et de résistance au feu minimales suivantes : ",
            "- les parois extérieures sont construites en matériaux A2 s1 d0 ou en matériaux reconnus équivalents par rapport au risque incendie, par la direction générale de la sécurité civile et de la gestion des crises du ministère chargé de l'intérieur ; ",
            "- l'ensemble de la structure présente les caractéristiques au moins R.15 ; ",
            "- en ce qui concerne la toiture, les poutres et les pannes sont au minimum R15 ; les autres éléments porteurs sont réalisés au minimum en matériaux A2 s1 d0 et l'isolant thermique (s'il existe) est réalisé en matériaux au minimum B S3 d0 avec pouvoir calorifique supérieur (PCS) inférieur ou égal à 8,4 MJ/kg, ou bien l'isolation thermique est composée de plusieurs couches, dont la première (en contact avec le support de couverture), d'une épaisseur d'au moins 30 millimètres, de masse volumique supérieure à 110 kg/m3 et fixée mécaniquement, a un PCS inférieur ou égal à 8,4 MJ/kg et les couches supérieures sont constituées d'isolants justifiant une en épaisseur de 60 millimètres d'une classe D s3 d2. Ces couches supérieures sont recoupées au droit de chaque écran de cantonnement par un isolant de PCS inférieur ou égal à 8,4 MJ/kg, ou bien il est protégé par un écran thermique disposé sur la ou les faces susceptibles d'être exposées à un feu intérieur au bâtiment. Cet écran doit jouer un rôle protecteur vis-à-vis de l'action du programme thermique normalisé durant au moins une demi-heure. L'ensemble de la toiture hors poutres et pannes satisfait la classe et l'indice BROOF (t3) ; ",
            "- planchers hauts (hors mezzanines) au moins REI 120 ; en outre, la stabilité au feu des structures porteuses des planchers, pour les entrepôts de deux niveaux et plus, est de degré deux heures au moins ; ",
            "- portes et fermetures des murs séparatifs au moins EI 120 (y compris celles comportant des vitrages et des quincailleries). Ces portes et fermetures sont munies d'un ferme-porte, ou d'un dispositif assurant leur fermeture automatique, également au moins EI 120 ; ",
            "- murs séparatifs au moins REI 120 entre deux cellules ; ces parois sont prolongées latéralement aux murs extérieurs sur une largeur de 1 mètre ou 0,50 mètre en saillie de la façade, dans la continuité de la paroi. Elles doivent être construites de façon à ne pas être entraînées en cas de ruine de la structure ;",
            " - murs séparatifs au moins REI 120 ou une distance libre de 10 mètres entre une cellule et un local technique (hors chaufferie) ; ",
            "- portes et fermetures des murs séparatifs résistantes au feu (y compris celles comportant des vitrages et des quincailleries) et leurs dispositifs de fermeture au moins EI 120.",
            "Les dispositions constructives visent à ce que la ruine d'un élément de structure n'entraîne pas la ruine en chaîne de la structure du bâtiment, notamment les cellules de stockage avoisinantes, ni de leur dispositif de recoupement et ne favorise pas l'effondrement de la structure vers l'extérieur de la première cellule en feu.",
            "Les éléments séparatifs entre cellules dépassent d'au moins 1 mètre la couverture du bâtiment au droit du franchissement. La toiture est recouverte d'une bande de protection sur une largeur minimale de 5 mètres de part et d'autre des parois séparatives.",
            "Les ouvertures effectuées dans les éléments séparatifs (passage de gaines et canalisations, de convoyeurs) sont munies de dispositifs assurant un degré coupe-feu équivalent à celui exigé pour ces éléments séparatifs.",
            "Le sol des aires et locaux de stockage est incombustible (de classe A1).",
            "Les matériaux utilisés pour l'éclairage naturel ne produisent pas, lors d'un incendie, de gouttes enflammées.",
            "Une étude spécifique visant à évaluer les risques particuliers, notamment pour les personnes, et à déterminer les mesures spécifiques à mettre en place est réalisée pour toute mezzanine de surface supérieure à 50 % (85 % pour les entrepôts de textile) de la surface en cellule située en rez-de-chaussée.",
        ],
    )


def _7_replace_5() -> StructuredText:
    return _build_simple_structured_text(
        '5. Désenfumage',
        [
            "Les cellules de stockage sont divisées en cantons de désenfumage d\'une superficie maximale de 1 650 mètres carrés et d\'une longueur maximale de 60 mètres. Les cantons sont délimités par des écrans de cantonnement, réalisés en matériaux A2 s1 d0 (y compris leurs fixations) et stables au feu de degré un quart d'heure, ou par la configuration de la toiture et des structures du bâtiment.",
            "Les cantons de désenfumage sont équipés en partie haute de dispositifs d\'évacuation des fumées, gaz de combustion, chaleur et produits imbrûlés.",
            "Des exutoires à commande automatique et manuelle font partie des dispositifs d\'évacuation des fumées. La surface utile de l\'ensemble de ces exutoires n\'est pas inférieure à 2 % de la superficie de chaque canton de désenfumage.",
            "Le déclenchement du désenfumage n\'est pas asservi à la même détection que celle à laquelle est asservi le système d\'extinction automatique. Les dispositifs d\'ouverture automatique des exutoires sont réglés de telle façon que l\'ouverture des organes de désenfumage ne puisse se produire avant le déclenchement de l\'extinction automatique.",
            "Il faut prévoir au moins quatre exutoires pour 1 000 mètres carrés de superficie de toiture. La surface utile d\'un exutoire n\'est pas inférieure à 0,5 mètre carré ni supérieure à 6 mètres carrés. Les dispositifs d\'évacuation ne sont pas implantés sur la toiture à moins de 7 mètres des murs coupe-feu séparant les cellules de stockage. Cette distance peut être réduite pour les cellules dont une des dimensions est inférieure à 15 m.",
            "La commande manuelle des exutoires est au minimum installée en deux points opposés de l\'entrepôt de sorte que l\'actionnement d\'une commande empêche la manœuvre inverse par la ou les autres commandes. Ces commandes manuelles sont facilement accessibles aux services d\'incendie et de secours depuis les issues du bâtiment ou de chacune des cellules de stockage. Elles doivent être manœuvrables en toutes circonstances.",
            "Des amenées d\'air frais d\'une superficie au moins égale à la surface utile des exutoires du plus grand canton, cellule par cellule, sont réalisées soit par des ouvrants en façade, soit par des bouches raccordées à des conduits, soit par les portes des cellules à désenfumer donnant sur l\'extérieur.",
            "En cas d\'entrepôt à plusieurs niveaux, les niveaux autres que celui sous toiture sont désenfumés par des ouvrants en façade asservis à la détection conformément à la réglementation applicable aux établissements recevant du public.",
            "Les dispositions de ce point ne s\'appliquent pas pour un stockage couvert ouvert.",
        ],
    )


def _7_replace_7() -> StructuredText:
    return _build_simple_structured_text(
        "7. Dimensions des cellules",
        [
            "La taille des surfaces des cellules de stockage est limitée de façon à réduire la quantité de matières combustibles en feu et d'éviter la propagation du feu d'une cellule à l'autre.",
            "La surface maximale des cellules est égale à 3 000 mètres carrés en l'absence de système d'extinction automatique d'incendie, ou 6 000 mètres carrés en présence d'un système d'extinction automatique d'incendie et d'une étude démontrant que les zones d'effets thermiques supérieurs à 5 kW/m2 générés par l'incendie d'une cellule restent à l'intérieur du site. Dans le cas des cellules de surface maximale de 3 000 mètres carrés, la plus grande longueur des cellules est limitée à 75 mètres.",
        ],
    )


def _7_replace_11() -> StructuredText:
    return _build_simple_structured_text(
        "11. Eaux d\'extinction incendie",
        [
            "Toutes mesures sont prises pour recueillir l\'ensemble des eaux et écoulements susceptibles d\'être pollués lors d\'un sinistre, y compris les eaux utilisées pour l\'extinction d\'un incendie et le refroidissement, afin que celles-ci soient récupérées ou traitées afin de prévenir toute pollution des sols, des égouts, des cours d\'eau ou du milieu naturel. Ce confinement peut être réalisé par des dispositifs internes ou externes aux cellules de stockage. Les dispositifs internes sont interdits lorsque des matières dangereuses sont stockées.",
            "Dans le cas d\'un confinement externe, les matières canalisées sont collectées, de manière gravitaire ou grâce à des systèmes de relevage autonomes, puis convergent vers une rétention extérieure au bâtiment. En cas de recours à des systèmes de relevage autonomes, l\'exploitant est en mesure de justifier à tout instant d\'un entretien et d\'une maintenance rigoureux de ces dispositifs. Des tests réguliers sont par ailleurs menés sur ces équipements.",
            "En cas de confinement interne, les orifices d\'écoulement sont en position fermée par défaut.",
            "En cas de confinement externe, les orifices d\'écoulement issus de ces dispositifs sont munis d\'un dispositif automatique d\'obturation pour assurer ce confinement lorsque des eaux susceptibles d\'être polluées y sont portées. Tout moyen est mis en place pour éviter la propagation de l\'incendie par ces écoulements.",
            "Le volume nécessaire à ce confinement est calculé : ",
            "- sur la base du volume d'eau d'extinction nécessaire à la lutte contre l'incendie, d'une part ; ",
            "- sur le volume de produits libéré par cet incendie, d'autre part, ce volume total correspondant à la plus grande valeur obtenue pour un incendie sur la plus grande cellule ou pour un incendie sur la cellule, présentant le plus fort potentiel calorifique."
            "Le volume nécessaire au confinement peut également être déterminé conformément au document technique D9a (guide pratique pour le dimensionnement des rétentions des eaux d\'extinction de l\'Institut national d\'études de la sécurité civile, la Fédération française des sociétés d\'assurances et le Centre national de prévention et de protection, édition août 2004).",
            "Les réseaux de collecte des effluents et des eaux pluviales de l\'établissement sont équipés de dispositifs d\'isolement visant à maintenir toute pollution accidentelle, en cas de sinistre, sur le site. Ces dispositifs sont maintenus en état de marche, signalés et actionnables en toute circonstance localement et à partir d\'un poste de commande. Leur entretien et leur mise en fonctionnement sont définis par consigne.",
        ],
    )


def _7_replace_12() -> StructuredText:
    return _build_simple_structured_text(
        "12. Détection automatique d\'incendie",
        [
            "La détection automatique d\'incendie avec transmission, en tout temps, de l\'alarme à l\'exploitant est obligatoire pour les cellules, les locaux techniques et pour les bureaux à proximité des stockages. Cette détection actionne une alarme perceptible en tout point du bâtiment permettant d\'assurer l\'alerte précoce des personnes présentes sur le site.",
            "Le type de détecteur est déterminé en fonction des produits stockés. Cette détection peut être assurée par le système d\'extinction automatique s\'il est conçu pour cela, à l\'exclusion du cas des cellules comportant au moins une mezzanine, pour lesquelles un système de détection dédié et adapté doit être prévu.",
            "Dans tous les cas, l\'exploitant s\'assure que le système permet une détection de tout départ d\'incendie tenant compte de la nature des produits stockés et du mode de stockage.",
            "Sauf pour les installations soumises à déclaration, l\'exploitant inclut dans le dossier prévu au point 1.2 de la présente annexe les documents démontrant la pertinence du dimensionnement retenu pour les dispositifs de détection.",
        ],
    )


def _7_replace_13() -> StructuredText:
    return _build_simple_structured_text(
        "13. Moyens de lutte contre l\'incendie",
        [
            "Le stockage est doté de moyens de lutte contre l'incendie appropriés aux risques et conformes aux normes en vigueur, notamment : ",
            "- d'un ou plusieurs appareils d'incendie (prises d'eau, poteaux, par exemple) d'un réseau public ou privé, implantés de telle sorte que, d'une part, tout point de la limite du stockage se trouve à moins de 100 mètres d'un appareil et que, d'autre part, tout point de la limite du stockage se trouve à moins de 200 mètres d'un ou plusieurs appareils permettant de fournir un débit minimal de 60 mètres cubes par heure pendant une durée d'au moins deux heures et dont les prises de raccordement sont conformes aux normes en vigueur pour permettre au service d'incendie et de secours de s'alimenter sur ces appareils. A défaut, une réserve d'eau destinée à l'extinction est accessible en toutes circonstances et à une distance du stockage ayant recueilli l'avis des services départementaux d'incendie et de secours ; ",
            "- d'extincteurs répartis à l'intérieur de l'entrepôt, sur les aires extérieures et dans les lieux présentant des risques spécifiques, à proximité des dégagements, bien visibles et facilement accessibles. Les agents d'extinction sont appropriés aux risques à combattre et compatibles avec les matières stockées ; ",
            "- de robinets d'incendie armés, répartis dans l'entrepôt en fonction de ses dimensions et situés à proximité des issues. Ils sont disposés de telle sorte qu'un foyer puisse être attaqué simultanément par deux lances sous deux angles différents. Ils sont utilisables en période de gel.",
            "L'exploitant est en mesure de justifier au préfet la disponibilité effective des débits d'eau ainsi que le dimensionnement de l'éventuelle réserve d'eau prévu au deuxième alinéa du présent point. En cas d'installation de systèmes d'extinction automatique d'incendie, ceux-ci sont conçus, installés et entretenus régulièrement conformément aux référentiels reconnus.",
        ],
    )


def build_1510_parametrization() -> Parametrization:
    application_conditions = []
    alternative_texts = []

    regime = Parameter('regime', ParameterType.REGIME)
    is_autorisation = Equal(regime, Regime.A)
    is_enregistrement = Equal(regime, Regime.E)
    is_declaration = Equal(regime, Regime.D)
    date = ParameterEnum.DATE_INSTALLATION.value
    date_2003 = datetime(2003, 7, 1)
    date_2009 = datetime(2009, 4, 30)
    date_2010 = datetime(2010, 4, 16)
    date_2017 = datetime(2017, 7, 1)
    is_before_2003 = Littler(date, date_2003, True)
    is_before_2009 = Littler(date, date_2009, True)
    is_between_2003_and_2017 = Range(date, date_2003, date_2017, False, True)
    is_between_2003_and_2010 = Range(date, date_2003, date_2010, False, True)
    is_between_2010_2017 = Range(date, date_2010, date_2017, False, True)
    is_between_2009_2017 = Range(date, date_2009, date_2017, False, True)

    Ints = Tuple[int, ...]
    _NotApplicable = List[Tuple[Tuple[int, ...], Optional[List[int]]]]
    tuples_: List[
        Tuple[
            Condition, ConditionSource, _NotApplicable, Dict[Ints, StructuredText], Tuple[Optional[datetime], datetime]
        ]
    ] = []
    all_warnings: List[Dict[Ints, str]] = []
    condition_1 = AndCondition([is_autorisation, is_before_2003])
    condition_source_A = ConditionSource(
        'Annexe IV décrivant les cas d\'application', EntityReference(SectionReference(tuple([8, 3])), None)
    )
    condition_source_E = ConditionSource(
        'Annexe V décrivant les cas d\'application', EntityReference(SectionReference(tuple([8, 4])), None)
    )
    condition_source_D = ConditionSource(
        'Annexe VI décrivant les cas d\'application', EntityReference(SectionReference(tuple([8, 5])), None)
    )
    not_applicable_1 = [
        ((8, 1, 1), None),
        ((8, 1, 2), None),
        ((8, 1, 2, 1), None),
        ((8, 1, 2, 2), None),
        ((8, 1, 2, 3), None),
        ((8, 1, 3), None),
        ((8, 1, 4), None),
        ((8, 1, 5), None),
        ((8, 1, 6), None),
        ((8, 1, 7), None),
        ((8, 1, 8), [6, 7, 8]),
        ((8, 1, 9), None),
        ((8, 1, 10), None),
        ((8, 1, 13), [0, 1, 2]),
        ((8, 1, 14), [1, 3]),
        ((8, 1, 16), None),
        ((8, 1, 17), None),
    ]
    new_articles_1 = {
        tuple((8, 1, 11)): _build_alternative_12_for_autorisation(),
        tuple((8, 1, 12)): _build_alternative_13_for_autorisation(),
    }
    description_1 = (None, date_2003)
    tuples_.append((condition_1, condition_source_A, not_applicable_1, new_articles_1, description_1))

    condition_2 = AndCondition([is_autorisation, is_between_2003_and_2017])
    not_applicable_2 = [((8, 1, 2, 2), None), ((8, 1, 2, 3), None)]
    new_articles_2 = {
        tuple((8, 1, 1, 0)): _build_alternative_2_I_for_autorisation(),
        tuple((8, 1, 2, 1)): _build_alternative_3_2_for_autorisation(),
        tuple((8, 1, 3)): _build_alternative_4_for_autorisation(),
        tuple((8, 1, 4)): _build_alternative_5_for_autorisation(),
        tuple((8, 1, 6)): _build_alternative_7_for_autorisation(),
        tuple((8, 1, 10)): _build_alternative_11_for_autorisation(),
        tuple((8, 1, 11)): _build_alternative_12_for_autorisation(),
        tuple((8, 1, 12)): _build_alternative_13_for_autorisation(),
    }
    warnings_2 = {
        tuple(
            (8, 1, 5)
        ): "Le deuxième alinéa n'est pas applicable aux installations existantes ; le franchissement du seuil mentionné par cet alinéa est soumis à l'application de l'article R. 181-46 du code de l'environnement."
    }
    all_warnings.append(warnings_2)
    description_2 = (date_2003, date_2017)
    tuples_.append((condition_2, condition_source_A, not_applicable_2, new_articles_2, description_2))

    condition_3 = AndCondition([is_enregistrement, is_before_2003])
    description_3 = (None, date_2003)

    not_applicable_3 = [
        ((8, 1, 1), None),
        ((8, 1, 2), None),
        ((8, 1, 2, 1), None),
        ((8, 1, 2, 2), None),
        ((8, 1, 2, 3), None),
        ((8, 1, 3), None),
        ((8, 1, 4), None),
        ((8, 1, 5), None),
        ((8, 1, 6), None),
        ((8, 1, 8), [6, 7, 8]),
        ((8, 1, 9), None),
        ((8, 1, 10), None),
        ((8, 1, 13), [0, 1, 2]),
        ((8, 1, 14), [1, 3]),
        ((8, 1, 16), None),
        ((8, 1, 17), None),
        ((8, 1, 22), None),
    ]
    new_articles_3 = {
        tuple((8, 1, 11)): _build_alternative_12_for_autorisation(),
        tuple((8, 1, 12)): _build_alternative_13_for_autorisation(),
    }
    tuples_.append((condition_3, condition_source_E, not_applicable_3, new_articles_3, description_3))

    condition_4 = AndCondition([is_enregistrement, is_between_2003_and_2010])
    description_4 = (date_2003, date_2010)
    new_articles_4 = {
        tuple((8, 1, 1, 0)): _build_alternative_2_I_for_autorisation(),
        tuple((8, 1, 2, 1)): _build_alternative_3_2_for_autorisation(),
        tuple((8, 1, 3)): _build_alternative_4_for_autorisation(),
        tuple((8, 1, 4)): _build_alternative_5_for_autorisation(),
        tuple((8, 1, 6)): _build_alternative_7_for_enregistrement(),
        tuple((8, 1, 10)): _build_alternative_11_for_autorisation(),
        tuple((8, 1, 11)): _build_alternative_12_for_autorisation(),
        tuple((8, 1, 12)): _build_alternative_13_for_autorisation(),
    }
    tuples_.append((condition_4, condition_source_E, [], new_articles_4, description_4))

    condition_5 = AndCondition([is_enregistrement, is_between_2010_2017])
    description_5 = (date_2010, date_2017)
    not_applicable_5: List[Tuple[Ints, Optional[List[int]]]] = [((8, 1, 5), None)]
    new_articles_5 = {
        tuple((8, 1, 2, 1)): _build_alternative_3_2_for_enr_after_2010(),
        tuple((8, 1, 2, 2)): _build_alternative_3_3_for_enr_after_2010(),
        tuple((8, 1, 3)): _build_alternative_4_for_enr_after_2010(),
        tuple((8, 1, 4)): _build_alternative_5_for_enr_after_2010(),
        tuple((8, 1, 6)): _build_alternative_7_for_enr_after_2010(),
    }
    tuples_.append((condition_5, condition_source_E, not_applicable_5, new_articles_5, description_5))

    condition_6 = AndCondition([is_declaration, is_before_2009])
    description_6 = (None, date_2009)

    not_applicable_6 = [
        ((8, 1, 1), None),
        ((8, 1, 2, 1), None),
        ((8, 1, 2, 2), None),
        ((8, 1, 3), None),
        ((8, 1, 4), None),
        ((8, 1, 5), None),
        ((8, 1, 6), None),
        ((8, 1, 10), None),
        ((8, 1, 16), None),
        ((8, 1, 17), None),
        ((8, 1, 22), None),
        ((8, 1, 8), [6, 7, 8]),
        ((8, 1, 13), [0, 1, 2]),
        ((8, 1, 14), [1, 3]),
    ]
    new_articles_6 = {
        tuple([8, 1, 2, 3]): _build_simple_structured_text(
            '3.4. Accès aux issues et quais de déchargement',
            [
                "A partir de chaque voie engins ou échelles est prévu un accès à toutes les issues du bâtiment par un chemin stabilisé de 1,40 mètre de large au minimum."
            ],
        ),
        tuple([8, 1, 9]): _build_simple_structured_text(
            '10. Stockage de matières susceptibles de créer une pollution du sol ou des eaux',
            [
                'Tout stockage de matières liquides susceptibles de créer une pollution de l\'eau ou du sol est associé à une capacité de rétention interne ou externe dont le volume est au moins égal à la plus grande des deux valeurs suivantes :',
                '100 % de la capacité du plus grand réservoir ;',
                '50 % de la capacité globale des réservoirs associés.',
                'Toutefois, lorsque le stockage est constitué exclusivement de récipients de capacité unitaire inférieure ou égale à 250 litres, admis au transport, le volume minimal de la rétention est égal soit à la capacité totale des récipients si cette capacité est inférieure à 800 litres, soit à 20 % de la capacité totale avec un minimum de 800 litres si cette capacité excède 800 litres. Cet alinéa ne s\'applique pas aux stockages de liquides inflammables.',
                'Des réservoirs ou récipients contenant des matières susceptibles de réagir dangereusement ensemble ne sont pas associés à la même cuvette de rétention.',
            ],
        ),
        tuple((8, 1, 11)): _build_alternative_12_for_autorisation(),
        tuple((8, 1, 12)): _build_simple_structured_text(
            '12. Détection automatique d\'incendie',
            [
                "Le stockage est doté de moyens de lutte contre l'incendie appropriés aux risques et conformes aux normes en vigueur, notamment : ",
                "- d'un ou plusieurs appareils d'incendie (prises d'eau, poteaux, par exemple) d'un réseau public ou privé, implantés de telle sorte que, d'une part, tout point de la limite du stockage se trouve à moins de 100 mètres d'un appareil et que, d'autre part, tout point de la limite du stockage se trouve à moins de 200 mètres d'un ou plusieurs appareils permettant de fournir un débit minimal de 60 mètres cubes par heure pendant une durée d'au moins deux heures et dont les prises de raccordement sont conformes aux normes en vigueur pour permettre au service d'incendie et de secours de s'alimenter sur ces appareils. A défaut, une réserve d'eau destinée à l'extinction est accessible en toutes circonstances et à une distance du stockage ayant recueilli l'avis des services départementaux d'incendie et de secours ; ",
                "- d'extincteurs répartis à l'intérieur de l'entrepôt, sur les aires extérieures et dans les lieux présentant des risques spécifiques, à proximité des dégagements, bien visibles et facilement accessibles. Les agents d'extinction sont appropriés aux risques à combattre et compatibles avec les matières stockées ; ",
                "- de robinets d'incendie armés, répartis dans l'entrepôt en fonction de ses dimensions et situés à proximité des issues. Ils sont disposés de telle sorte qu'un foyer puisse être attaqué simultanément par deux lances sous deux angles différents. Ils sont utilisables en période de gel.",
                "L'exploitant est en mesure de justifier au préfet la disponibilité effective des débits d'eau ainsi que le dimensionnement de l'éventuelle réserve d'eau prévu au deuxième alinéa du présent point. En cas d'installation de systèmes d'extinction automatique d'incendie, ceux-ci sont conçus, installés et entretenus régulièrement conformément aux référentiels reconnus.",
                "Pour les installations déclarées avant le 30 avril 2009, les points autres que celui relatif aux extincteurs au deuxième tiret ci-dessus ne sont applicables qu'à compter du 1er juillet 2020.",
            ],
        ),
    }
    warnings_6 = {
        tuple(
            (8, 1, 0)
        ): "Applicable à l\'exception des points 1.1. et 1.2. pour les installations bénéficiant des droits acquis."
    }
    tuples_.append((condition_6, condition_source_D, not_applicable_6, new_articles_6, description_6))
    all_warnings.append(warnings_6)

    condition_7 = AndCondition([is_declaration, is_between_2009_2017])
    description_7 = (date_2009, date_2017)
    not_applicable_7 = [(tuple([8, 1, 5]), None), ((8, 1, 13), [0, 1, 2]), ((8, 1, 14), [1]), ((8, 1, 16), None)]
    new_articles_7 = {
        tuple([8, 1, 2, 1]): _7_replace_3_2(),
        tuple([8, 1, 2, 2]): _7_replace_3_3(),
        tuple([8, 1, 2, 3]): _7_replace_3_4(),
        tuple([8, 1, 3]): _7_replace_4(),
        tuple([8, 1, 4]): _7_replace_5(),
        tuple([8, 1, 6]): _7_replace_7(),
        tuple([8, 1, 10]): _7_replace_11(),
        tuple([8, 1, 11]): _7_replace_12(),
        tuple([8, 1, 12]): _7_replace_13(),
    }
    warnings_7 = {tuple((8, 1, 11)): "L'article 12 est applicable à compter du 1er janvier 2021."}
    tuples_.append((condition_7, condition_source_D, not_applicable_7, new_articles_7, description_7))
    all_warnings.append(warnings_7)

    for condition, condition_source, not_applicable, new_articles, (dt_l, dt_r) in tuples_:
        if not dt_l:
            dt_str_r = dt_r.strftime('%d-%m-%Y')
            description_modif = f'Le paragraphe est modifié pour les sites installés avant le {dt_str_r}'
            description_app = f'Le paragraphe n\'est pas applicable pour les sites installés avant le {dt_str_r}'
        else:
            dt_str_l = dt_l.strftime('%d-%m-%Y')
            dt_str_r = dt_r.strftime('%d-%m-%Y')
            description_modif = (
                f'Le paragraphe est modifié pour les sites installés entre le {dt_str_l} et le {dt_str_r}'
            )
            description_app = (
                f'Le paragraphe n\'est pas applicable pour les sites installés entre le {dt_str_l} et le {dt_str_r}'
            )
        alternative_texts.extend(
            [
                AlternativeSection(SectionReference(sec), new_text, condition, condition_source, description_modif)
                for sec, new_text in new_articles.items()
            ]
        )
        application_conditions.extend(
            [
                NonApplicationCondition(
                    EntityReference(SectionReference(section), alineas), condition, condition_source, description_app
                )
                for section, alineas in not_applicable
            ]
        )

    condition_8 = OrCondition([is_enregistrement, is_autorisation])
    not_applicable_8 = [(tuple([8, 1, 0, 7]), None), (tuple([8, 1, 1, 1]), None)]
    for na_sec, na_als in not_applicable_8:
        _ref = EntityReference(SectionReference(na_sec), na_als)
        application_conditions.append(
            NonApplicationCondition(
                _ref,
                condition_8,
                ConditionSource('Mentionné dans l\'article.', _ref),
                description='''Le paragraphe ne s\'applique qu'aux installations soumises à déclaration.''',
            )
        )

    condition_9 = is_declaration
    not_applicable_9 = [(tuple([8, 1, 23, 2]), None), (tuple([8, 1, 1, 0]), None)]
    for na_sec, na_als in not_applicable_9:
        _ref = EntityReference(SectionReference(na_sec), na_als)
        application_conditions.append(
            NonApplicationCondition(
                _ref,
                condition_9,
                ConditionSource('Mentionné dans l\'article.', _ref),
                description='''Le paragraphe ne s\'applique qu'aux installations soumises à enregistrement ou à autorisation.''',
            )
        )

    return Parametrization(application_conditions, alternative_texts)


def generate_1510_combinations() -> Combinations:
    regime = ParameterEnum.REGIME.value
    date = ParameterEnum.DATE_INSTALLATION.value
    return {
        ('reg_A_no_date',): {regime: Regime.A},
        ('reg_A', 'date_before_2003'): {regime: Regime.A, date: datetime(2000, 1, 1)},
        ('reg_A', 'date_between_2003_and_2017'): {regime: Regime.A, date: datetime(2010, 1, 1)},
        ('reg_A', 'date_after_2017'): {regime: Regime.A, date: datetime(2020, 1, 1)},
        ('reg_E_no_date',): {regime: Regime.E},
        ('reg_E', 'date_before_2003'): {regime: Regime.E, date: datetime(2000, 1, 1)},
        ('reg_E', 'date_between_2003_and_2010'): {regime: Regime.E, date: datetime(2006, 1, 1)},
        ('reg_E', 'date_between_2010_and_2017'): {regime: Regime.E, date: datetime(2015, 1, 1)},
        ('reg_E', 'date_after_2017'): {regime: Regime.E, date: datetime(2020, 1, 1)},
        ('reg_D_no_date',): {regime: Regime.D},
        ('reg_D', 'date_before_2009'): {regime: Regime.D, date: datetime(2000, 1, 1)},
        ('reg_D', 'date_between_2009_and_2017'): {regime: Regime.D, date: datetime(2010, 1, 1)},
        ('reg_D', 'date_after_2017'): {regime: Regime.D, date: datetime(2020, 1, 1)},
    }


def manual_1510_enricher(raw_am: ArreteMinisteriel) -> ArreteMinisteriel:
    return remove_sections(raw_am, {(8, 3), (8, 4), (8, 5)})


def _guess_regime(version_descriptor: Tuple[str, ...]) -> str:
    for desc in version_descriptor:
        if 'reg_' in desc:
            return desc.split('reg_')[1][0]
    raise ValueError(f'Expecting one descriptor to contain "reg_", received: {version_descriptor}')


def manual_1510_post_process(am: ArreteMinisteriel, version_descriptor: Tuple[str, ...]) -> ArreteMinisteriel:
    classements = am.classements
    regime = _guess_regime(version_descriptor)
    new_classements = [cl for cl in classements if cl.regime.value == regime]
    return replace(am, classements=new_classements)