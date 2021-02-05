from lib.parametrization import ParameterEnum
from back_office.display_am import _extract_name, _build_parameter_input, _extract_parameter_and_value


def test_extract_name():
    for value in ParameterEnum:
        _extract_name(value.value)


def test_build_parameter_input():
    for value in ParameterEnum:
        _build_parameter_input(value.value)


def test_extract_parameter_and_value():
    for value in ParameterEnum:
        _extract_parameter_and_value(value.value.id, None, None)