![Envinorma Logo](https://raw.githubusercontent.com/Envinorma/envinorma.github.io/main/favicon.ico)

# Envinorma

Envinorma is a project which aims at helping people find applicable regulations to non-nuclear industries ([ICPE](https://fr.wikipedia.org/wiki/Installation_class%C3%A9e_pour_la_protection_de_l'environnement)).

This repository contains utils for manipulating texts called Arrêtés Ministériels (AM) and Arrêtés Préfectoraux (AP).

It generates the source code of:

- [https://envinorma.github.io/](https://envinorma.github.io/) which gathers main Arrêtes Ministériels and displays enriched versions of the texts
- [https://envinorma-dashboard.herokuapp.com/](https://envinorma-dashboard.herokuapp.com/) which gathers statistics on open data about ICPE and this project

It also features:

- A library for automatic structuration of regulation texts, based on title detection
- A library for detecting paragraph topics in a structured text
- A script for transforming an .odt document into a structured text
- A library for handling enriched texts: texts that are containing metadata, among which a parametrization that rules the applicability of paragraphs
- A small wrapper for LegifranceAPI
- A script for generating diffs between versions of a text depending on parameter values for parametrization checking via github UI, _e.g._: [https://github.com/Envinorma/arretes_ministeriels/compare/565eeb1f48caed785afe6d356e6a3116fd337fe1...e78dbfd5cd7a5c0f090eecb081dc52f8c5819663](https://github.com/Envinorma/arretes_ministeriels/compare/565eeb1f48caed785afe6d356e6a3116fd337fe1...e78dbfd5cd7a5c0f090eecb081dc52f8c5819663)
