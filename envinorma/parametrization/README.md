# Parametrization

Un arrêté ministériel peut être paramétré (schéma [Parametrization](https://envinorma.github.io/envinorma-data/envinorma.parametrization.models.html#envinorma.parametrization.models.parametrization.Parametrization)).

![Arrete Ministeriel et Parametrization](../../_static/parametrized_am.jpg)

À partir d'une _Parametrization_, d'un _ArreteMinisteriel_ et des valeurs des paramètres d'une installation, on peut générer la version de l'AM qui s'applique.

## Application d'un jeu de paramètres à un AM

Pour passer d'un triplet (ArreteMinisteriel, Parametrization, parameter_values) à la version correspondante de l'arrêté ministériel, on utilise la fonction [build_am_with_applicability](https://envinorma.github.io/envinorma-data/envinorma.parametrization.html?#envinorma.parametrization.apply_parameter_values.build_am_with_applicability), dont le principe est explicité ci dessous:

![Générateur des versions d'un arrêté ministériels](../../_static/versions_generator.jpg)
