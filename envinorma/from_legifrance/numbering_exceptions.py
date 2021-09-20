MAX_PREFIX_LEN = 60
EXCEPTION_PREFIXES = {
    "1. Une attestation de la maîtrise foncière sur l'emprise de ": None,
    "2. Un plan de l'exploitation à une échelle adaptée à la supe": None,
    '3. Une note succincte indiquant la nature de la substance ex': None,
    '4. Pour les carrières visées à la rubrique 2510-6, la justif': None,
    "5. Une description des modalités d'extraction et de remise e": None,
    '6. Les documents et registres prévus aux articles 3.5 et 4.7': None,
    '7. Les résultats des dernières mesures sur les effluents et ': None,
    "1. Le démantèlement des installations de production d'électr": None,
    "2. L'excavation de la totalité des fondations, jusqu'à la ba": None,
    '3. La remise en état qui consiste en le décaissement des air': None,
    'I. ― Les aires de chargement et de déchargement des produits': 'caps',
    "1. Les zones d'effets Z1 et Z2 définies par l'arrêté du 20 a": None,
    "2. La zone d'effets Z3 définie par l'arrêté du 20 avril 2007": None,
    "3. La zone d'effets Z4 définie par l'arrêté du 20 avril 2007": None,
    "4. La zone d'effets Z5 (ou la zone d'effets Z4 dans le cas o": None,
    '5. Les effets dominos de toute installation, équipement ou b': None,
    "1. Lorsque les distances d'éloignement mentionnées au point ": None,
    "1. Le flux horaire maximal en COV à l'exclusion du méthane, ": None,
    "2. Le flux horaire maximal en COV à l'exclusion du méthane, ": None,
    '1. Le contrôleur vérifie la présence des documents listés ai': None,
    "2. L'effectif au jour du contrôle, selon le registre, l'extr": None,
    "1. L'installation est maintenue en parfait état d'entretien,": None,
    "2. L'exploitant justifie de la lutte contre la prolifération": None,
    "1. Lorsqu'un forage alimente en eau l'installation, il est m": None,
    "2. L'exploitant dispose d'un moyen pour surveiller sa consom": None,
    "1. Les effluents d'élevage issus des bâtiments d'élevage et ": None,
    "2. L'exploitant justifie que les capacités des équipements d": None,
    '3. Tout écoulement direct des boues ou eaux polluées vers le': None,
    "1. Le niveau sonore des bruits en provenance de l'élevage ne": None,
    "2. L'émergence due aux bruits engendrés par l'installation r": None,
    'Méthode acoustique pour le contrôle des réservoirs enterrés ': 'caps',
    'Méthode hydraulique pour le contrôle des réservoirs enterrés': 'caps',
    "1. Il existe un mode d'élimination des bidons de désinfectan": None,
    "2. Le contrôleur s'assure que :": None,
    '1. Les surfaces effectivement épandues ;': None,
    '2. Hors zone vulnérable aux pollutions par les nitrates, les': None,
    "3. Les dates d'épandage ;": None,
    '4. La nature des cultures ;': None,
    '5. Les rendements des cultures ;': None,
    "6. Les volumes par nature d'effluents et les quantités d'azo": None,
    "7. Le mode d'épandage et le délai d'enfouissement ;": None,
    "8. Le traitement mis en œuvre pour atténuer les odeurs (s'il": None,
    '1. Cas des turbines :': None,
    '1. Cas des turbines.': None,
    '2. Cas des moteurs.': None,
    '2. Cas des moteurs :': None,
    '3. Autres appareils de combustion :': None,
    '1. Lorsque la puissance est inférieure à 10 MW :': None,
    '2. Lorsque la puissance est supérieure ou égale à 10 MW :': None,
    '1. Réception :': None,
    '2. Expédition :': None,
    "1. - = Courant d'électrolyse, en A": None,
    "1. En ce qui concerne les reptiles, les sites d'implantation": 'caps',
    "2. En ce qui concerne les amphibiens, l'implantation des tra": 'caps',
    '1. La caractérisation des sous-produits ou effluents à épand': None,
    '2. La liste des parcelles avec, pour chacune, son emplacemen': None,
    "3. L'identification des contraintes liées au milieu naturel ": None,
    '4. La description des caractéristiques des sols ;': None,
    '5. Une analyse des sols portant sur les paramètres mentionné': None,
    "6. La justification des doses d'apport et des fréquences d'é": None,
    '7. La description des modalités techniques de réalisation de': None,
    '8. La description des modalités de surveillance des opératio': None,
    '9. La définition de la périodicité des analyses et sa justif': None,
    'a) Si leurs concentrations en éléments pathogènes sont supér': None,
    'b) Si les teneurs en éléments-traces métalliques dans les so': None,
    "c) Dès lors que l'une des teneurs en éléments ou composés in": None,
    'd) Dès lors que le flux, cumulé sur une durée de dix ans, ap': None,
    'e) En outre, lorsque les déchets ou effluents sont épandus s': None,
    'IV-1. Détail du cycle :': 'caps',
    "IV-1.1. Cas des machines munies d'un distillateur :": 'numeric-d2',
    'IV-1.2. Cas des machines sans distillateur :': 'numeric-d2',
    'IV-1.2.1. Machines en plein bain :': 'numeric-d3',
    'IV-1.2.2. Machines à pulvérisation :': 'numeric-d3',
    'IV-2. Température de séchage :': 'caps',
    'IV-3. Distillation :': 'caps',
    'IV-4. Capacité machine :': 'caps',
    'V-1. Concernant les charges textiles :': 'caps',
    'V-2. Concernant la machine en essais :': 'caps',
    'VI-1. Préparation de la machine :': 'caps',
    'VI-1.1. Les séparateurs :': 'numeric-d2',
    'VI-1.2. Pot à charbons actifs :': 'numeric-d2',
    'VI-1.3. Fixation de la machine :': 'numeric-d2',
    'VI-2. Pesée initiale (machine) :': 'caps',
    'VI-3. Pesée initiale (charge textile) :': 'caps',
    'VII-1. Déroulement :': 'caps',
    'VII-2. Utilisation des charges textiles :': 'caps',
    "VII-3. Renouvellement d'air :": 'caps',
    "VII-4. Opérations d'entretien :": 'caps',
    'VII-4.1. Nettoyage des filtres :': 'numeric-d2',
    'VII-4.2. Distillateur :': 'numeric-d2',
    'VIII-1. Séparateurs :': 'caps',
    'VIII-2. Pot à charbons actifs :': 'caps',
    'VIII-3. Pesée de la machine :': 'caps',
    'VIII-4. Prise en compte du solvant recueilli du distillateur': 'caps',
    'VIII-5. Prise en compte du solvant présent dans le pot à cha': 'caps',
    "2. Prescriptions spécifiques à l'emploi de l'ammoniac (insta": 'roman',
    '1. La surface maximale des îlots au sol est de 2 500 mètres ': None,
    "2. Pour les stockages couverts, une surface maximale d'îlots": None,
    "a) Sont des réservoirs à toit fixe reliés à l'URV conforméme": None,
    'b) Sont conçues avec un toit flottant (externe ou interne) d': None,
    "a) Reliés à une URV conformément aux dispositions de l'annex": None,
    "b) Equipés d'un toit flottant interne doté d'un joint primai": None,
    '1. Etre accrédité selon la norme NF EN ISO/CEI 17025 pour la': None,
    '1. Etre accrédité selon la norme NF EN ISO CEI 17025 pour la': None,
    "2. Respecter les limites de quantification listées à l'artic": None,
    'a) Turbine ou moteur destiné uniquement à alimenter des syst': None,
    'b) Turbine dont le fonctionnement est nécessaire pour assure': None,
    "a) Les produits composés d'une matière végétale agricole ou ": None,
    'b) Les déchets ci-après :': None,
    'i) Déchets végétaux agricoles et forestiers ;': None,
    "v) Déchets de bois, à l'exception des déchets de bois qui so": None,
    "1. Dispositions générales relatives à l'entretien préventif ": 'numeric-d3',
    "1. Dispositions générales relatives à l'entretien préventif": 'numeric-d3',
    "2. Entretien préventif de l'installation": 'numeric-d3',
    "3. Surveillance de l'installation": 'numeric-d3',
    '1. Actions à mener si les résultats provisoires confirmés ou': 'numeric-d3',
    "2. Actions à mener si les résultats d'analyse selon la norme": 'numeric-d3',
    '3. Actions à mener si le dénombrement des Legionella pneumop': 'numeric-d3',
    '4. En cas de dérives répétées, consécutives ou non, de la co': 'numeric-d3',
    "1. Vérification de l'installation": 'numeric-d3',
    '2. Carnet de suivi': 'numeric-d3',
    "a) Seul ou en association avec d'autres agents, sans subir d": None,
    'b) Comme agent de nettoyage pour dissoudre des salissures ;': None,
    'c) Comme dissolvant ;': None,
    'd) Comme dispersant ;': None,
    'e) Comme correcteur de viscosité ;': None,
    'f) Comme correcteur de tension superficielle ;': None,
    'g) Comme plastifiant ;': None,
    'h) Comme agent protecteur ;': None,
    '1. Si le flux horaire total de COV(1) dépasse 2 kg/h, la val': 'numeric-d3',
    '2. Si le flux horaire total des composés organiques listés c': 'numeric-d3',
    '3. Substances de mentions de danger H340, H350, H350i, H360D': 'numeric-d3',
    "4. Mise en œuvre d'un schéma de maîtrise des émissions de CO": 'numeric-d3',
    '1. Oxydes de soufre (exprimés en dioxyde de soufre) : si le ': 'numeric-d3',
    "2. Oxydes d'azote (exprimés en dioxyde d'azote) : si le flux": 'numeric-d3',
    "3. Chlorure d'hydrogène et autres composés inorganiques gaze": 'numeric-d3',
    '4. Fluor et composés inorganiques du fluor (gaz, vésicules e': 'numeric-d3',
    '5. Métaux :': 'numeric-d3',
    '1. Rejets de cadmium, mercure et thallium, et de leurs compo': None,
    "2. Rejets d'arsenic, sélénium et tellure, et de leurs compos": None,
    '3. Rejets de plomb et de ses composés : si le flux horaire t': None,
    "4. Rejets d'antimoine, chrome, cobalt, cuivre, étain, mangan": None,
    "1. Si la quantité d'explosif susceptible d'être présente dan": None,
    "2. Si la quantité d'explosif susceptible d'être présente est": None,
    '1. La surface des cellules peut dépasser 12 000 m2 si leurs ': None,
    '2. La hauteur des cellules peut dépasser 23 m si leurs surfa': None,
    '1. Soit des échantillonneurs monoflacons fixes ou portatifs ': None,
    '2. Soit des échantillonneurs multiflacons fixes ou portatifs': None,
    '1. Justesse et répétabilité du volume prélevé (volume minima': None,
    "2. Vitesse de circulation de l'effluent dans les tuyaux supé": None,
    'a) Aucune des moyennes arithmétiques de tous les relevés eff': None,
    "b) Aucune des moyennes horaires n'est supérieure à 1,5 fois ": None,
    'a) La moyenne de toutes les valeurs de mesure ne dépasse pas': None,
    'a) turbine ou moteur destiné uniquement à alimenter des syst': None,
    'b) turbine dont le fonctionnement est nécessaire pour assure': None,
    "a) les produits composés d'une matière végétale agricole ou ": None,
    'b) les déchets ci-après :': None,
    'i) déchets végétaux agricoles et forestiers ;': None,
    "v) déchets de bois, à l'exception des déchets de bois qui so": None,
    '1° Surface maximale des îlots au sol : 500 m2 ;': None,
    '2° Hauteur maximale de stockage : 8 mètres maximum ;': None,
    '3° Largeurs des allées entre îlots : 2 mètres minimum.': None,
    '1° Hauteur maximale de stockage : 10 mètres maximum ;': None,
    '2° Largeurs des allées entre ensembles de rayonnages ou de p': None,
    '7.7 Epandage': 'numeric-d2',
    'D.1. Les apports de phosphore et de potasse, organique et mi': 'caps',
    "D.2. Les cendres ne contiennent pas d'éléments ou substances": 'caps',
    "D.3. Un programme prévisionnel annuel d'épandage est établi,": 'caps',
    "D.4. L'épandage des cendres est mis en œuvre afin que les nu": 'caps',
    'D.5. Sous réserve des prescriptions fixées en application de': 'caps',
    "D.6. Les périodes d'épandage et les quantités épandues sont ": 'caps',
    'D.7. Toute anomalie constatée sur les sols, les cultures et ': 'caps',
    "E.1. Les ouvrages permanents d'entreposage des cendres sont ": 'caps',
    "E.2. Le dépôt temporaire de déchets, sur les parcelles d'épa": 'caps',
    'G.1. Des analyses sont effectuées, sur un échantillonnage re': 'caps',
    'G.2. Seuils en éléments-traces métalliques et en substances ': 'caps',
    "G.3. Les méthodes d'échantillonnage et d'analyse sont défini": 'caps',
    "G.3. Les méthodes d'échantillonnage et d'analyse s'appuient ": 'caps',
    '22-3. La hauteur des parois des rétentions est au minimum de': 'numeric-d3-dash',
    '22-4. La distance entre les parois de la rétention et la par': 'numeric-d3-dash',
    '22-5. Dans tous les cas, la surface nette (réservoirs déduit': 'numeric-d3-dash',
    "22-6. Les rétentions sont accessibles aux moyens d'extinctio": 'numeric-d3-dash',
    '22-8. Une pompe de liquides inflammables peut être placée da': 'numeric-d3-dash',
    "22-9. Lorsqu'une perte de confinement sur un réservoir peut ": 'numeric-d3-dash',
    "22-10. A l'exception du point 22-9 du présent arrêté, les di": 'numeric-d3-dash',
    'Art. 2.1. - Au sens du présent arrêté on entend par :': 'roman',
    "Art. 2.2. - I. - Le pétitionnaire et l'exploitant sont tenus": 'roman',
    "Art. 2.3. - I. - L'exploitant tient à la disposition de l'in": 'roman',
    'Art. 4-1.-I.-Afin de satisfaire au premier alinéa du présent': 'roman-dash',
    'Art. 4-2.-I.-Afin de satisfaire au premier alinéa du présent': 'roman-dash',
    'Art. 4-3.-Les règles applicables aux avis conformes du minis': 'roman-dash',
    'a) Dans tous les cas, avant rejet au milieu naturel ou dans ': None,
    "b) Dans le cas de rejet dans un réseau d'assainissement coll": None,
    'c) Dans le cas de rejet dans le milieu naturel (ou dans un r': None,
    "a) Des prises d'eau, poteaux ou bouches d'incendie normalisé": None,
    "b) Des réserves d'eau, réalimentées ou non, disponibles pour": None,
    "I. - Tout stockage d'un liquide susceptible de créer une pol": None,
    "II. - La capacité de rétention est étanche aux produits qu'e": None,
    "III. - Lorsque les stockages sont à l'air libre, les rétenti": None,
    'IV. - Le sol des aires et des locaux de stockage ou de manip': None,
    'V. - Les dispositions des points I à III ne sont pas applica': None,
    "I. - La vitesse d'éjection des effluents gazeux en marche co": None,
    'II. - Dans le cas de mesures périodiques, la moyenne de tout': None,
    '2.10 Cuvettes de rétention': 'numeric-d2',
}