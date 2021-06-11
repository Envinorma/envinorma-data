![Envinorma Logo](assets/favicon.ico)

# Envinorma (en)

Envinorma is a project which aims at helping people find applicable regulations to French non-nuclear industries ([ICPE](https://fr.wikipedia.org/wiki/Installation_class%C3%A9e_pour_la_protection_de_l'environnement)).

Read the [project description](https://entrepreneur-interet-general.etalab.gouv.fr/defis/2020/envinorma.html) on the EIG Program website.

This repository is a library for manipulating enriched versions of regulation texts, in particular texts called _Arrêtés Ministériels_ (AM).

# Envinorma (fr)

Envinorma cherche à faciliter la préparation des inspections en simplifiant l'accès à la réglementation applicables aux industries en France (les [ICPE](https://fr.wikipedia.org/wiki/Installation_class%C3%A9e_pour_la_protection_de_l'environnement)).

Ce projet est réalisé dans le cadre du programme EIG, une page d'introduction est accessibile [ici](https://entrepreneur-interet-general.etalab.gouv.fr/defis/2020/envinorma.html).

Ce dépôt est permet de manipuler des _Arrêtés Ministériels_ (AM).

# Composants

- Schémas d'encodage d'un arrêté ministériel et de ses sections paramétrées
- Générateur des versions d'un arrêté ministériel à partir du texte d'origine et du paramétrage
- Modules d'enrichissement automatique d'un arrêté ministériel ICPE

# Usage

## Clone and install

```sh
git clone git@github.com:Envinorma/envinorma-data.git
cd envinorma-data
pip install -e .
```

## Install from git

```sh
pip install -e git+https://github.com/envinorma/envinorma-data.git
```

## Install for dev

```sh
git clone git@github.com:Envinorma/envinorma-data.git
cd envinorma-data
pip install -e .[dev] # or pip install -e .\[dev\] on MacOS
```

# Exemple

## 1. Download LegifranceText and print lines

```python
from envinorma.from_legifrance.legifrance_to_am import legifrance_to_arrete_ministeriel
from leginorma import LegifranceClient

legifrance_text = LegifranceClient(CLIENT_ID, CLIENT_SECRET).consult_law_decree('JORFTEXTTODO')
arrete_ministeriel = legifrance_to_arrete_ministeriel(legifrance_text)
print(arrete_ministeriel.to_text().text_lines())

# TODO
```

# Modules principaux

## [envinorma.models](envinorma/models/README.md)

Module contenant les schemas de données, en particulier la classe `StructuredText`, qui constitue la structure proposée pour représenter les textes réglementaires, permettant de représenter une structure suffisamment générale ainsi que le résultat de paramétrages, détection de thèmes et autres métadonnées.

## [envinorma.parametrization](envinorma/parametrization/README.md)

Module de gestion de la couche de parametrage d'un `StructuredText`.

## [envinorma.from_legifrance](envinorma/from_legifrance/README.md)

Module pour transformer un texte légifrance en `ArreteMinisteriel`.

## [envinorma.io](envinorma/io/README.md)

Ensemble de modules pour convertir des `StructuredText` en fichier `.docx`, `.odt`, `html` ou `markdown`.

## [envinorma.topics](envinorma/topics/README.md)

Module de détection de thème dans un `StructuredText`.
