![Envinorma Logo](./_static/favicon.ico)

[![Documentation](https://github.com/envinorma/envinorma-data/workflows/Documentation/badge.svg)](https://envinorma.github.io/envinorma-data/)

# Envinorma (en)

Envinorma is a project which aims at helping people find applicable regulations to French non-nuclear industries ([ICPE](https://fr.wikipedia.org/wiki/Installation_class%C3%A9e_pour_la_protection_de_l'environnement)).

Read the [project description](https://entrepreneur-interet-general.etalab.gouv.fr/defis/2020/envinorma.html) on the EIG Program website.

This repository is a library for manipulating enriched versions of regulation texts, in particular texts called _Arrêtés Ministériels_ (AM).

# Envinorma (fr)

Envinorma cherche à faciliter la préparation des inspections en simplifiant l'accès à la réglementation applicable aux industries en France (les [ICPE](https://fr.wikipedia.org/wiki/Installation_class%C3%A9e_pour_la_protection_de_l'environnement)).

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

Testing

```sh
pytest --mypy-ignore-missing-imports
```

Linting

```sh
isort . --profile black -l 120
flake8 --count --verbose --show-source --statistics
black . --check --exclude venv -S -l 120
```

# Exemples d'utilisation

## 1. Télécharger, structurer et afficher un texte depuis Légifrance

```python

from envinorma.from_legifrance.legifrance_to_am import legifrance_to_arrete_ministeriel
from leginorma import LegifranceClient, LegifranceText

legifrance_text = LegifranceText.from_dict(LegifranceClient(CLIENT_ID, CLIENT_SECRET).consult_law_decree('JORFTEXT000034429274'))
arrete_ministeriel = legifrance_to_arrete_ministeriel(legifrance_text)
print('\n'.join(arrete_ministeriel.to_text().text_lines()))

```

Output

```markdown
Arrêté du 11/04/17 relatif aux prescriptions générales applicables aux entrepôts couverts soumis à la rubrique 1510

# Article 1

Le présent arrêté s'applique aux entrepôts couverts déclarés, enregistrés ou autorisés au titre de la rubrique n° 1510 de la nomenclature des installations classées.
[...]
```

## 2. Appliquer un jeu de paramètres à un arrêté ministériel paramétré

Ce script peut être exécuté à partir des arrêtés ministériels contenus dans le dépôt [arretes-ministeriels](https://github.com/Envinorma/arretes-ministeriels).

```python
from datetime import date

from envinorma.models import ArreteMinisteriel
from envinorma.parametrization import Parametrization, ParameterEnum
from envinorma.parametrization.apply_parameter_values import apply_parameter_values_to_am

am_folder = 'TODO' # Replace with the folder containing AMs
am_id = 'JORFTEXT000018332514'
parametrization = Parametrization.from_dict(json.load(open(f'{am_folder}/parametrizations/{am_id}.json')))
base_am = ArreteMinisteriel.from_dict(json.load(open(f'{am_folder}/base_ams/{am_id}.json')))

parameter_values = {ParameterEnum.DATE_AUTORISATION.value: date.today()}
am_with_warnings = apply_parameter_values_to_am(base_am, parametrization, parameter_values)


```

# Modules principaux

## [envinorma.models](envinorma/models/README.md)

Module contenant les schemas de données, en particulier la classe `StructuredText`, qui constitue la structure proposée pour représenter les textes réglementaires, permettant de représenter une structure suffisamment générale ainsi que le résultat de paramétrages, détection de thèmes et autres métadonnées.

## [envinorma.parametrization](envinorma/parametrization/README.md)

Module de gestion de la couche de parametrage d'un `StructuredText`.

## [envinorma.from_legifrance](https://envinorma.github.io/envinorma-data/envinorma.from_legifrance)

Module pour transformer un texte légifrance en `ArreteMinisteriel`.

## [envinorma.io](https://envinorma.github.io/envinorma-data/envinorma.io)

Ensemble de modules pour convertir des `StructuredText` en fichier `.docx`, `.odt`, `html` ou `markdown`.

## [envinorma.topics](https://envinorma.github.io/envinorma-data/envinorma.topics)

Module de détection de thème dans un `StructuredText`.
