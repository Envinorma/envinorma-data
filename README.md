![Envinorma Logo](assets/favicon.ico)

# Envinorma

Envinorma is a project which aims at helping people find applicable regulations to French non-nuclear industries ([ICPE](https://fr.wikipedia.org/wiki/Installation_class%C3%A9e_pour_la_protection_de_l'environnement)).

Read the [project description](https://entrepreneur-interet-general.etalab.gouv.fr/defis/2020/envinorma.html) on the EIG Program website.

This repository contains utils for manipulating texts called _Arrêtés Ministériels_ (AM) and _Arrêtés Préfectoraux_ (AP).

# Features

## envinorma/data.py

Data classes, among which StructuredText, the proposed structure for representing regulation texts with, compatible with features like parametrization and topic detection.

## envinorma/io

Utils for parsing and generating StructuredText instances from/to .docx file, .odt file, html, markdown.

## envinorma/structure

A set of functions for automatic detection of text structure, mainly based on title detection.

## envinorma/topics

An ontology and a parser for topic detection in StructuredTexts.

## envinorma/parametrization

Algorithm for managing the parametrization layer of StructuredText instances.

## envinorma/back_office

Web app for managing the database of AM, manually structuring, parametrization layer declaration and enriching AM.
[Back office screenshot](assets/back_office_screenshot.png)

## envinorma/dashboard

Dash app for ICPE data exploration, deployed here [https://envinorma-dashboard.herokuapp.com/](https://envinorma-dashboard.herokuapp.com/) which gathers statistics on open data about ICPE and this project

## legifrance/

A wrapper for Legifrance API.
