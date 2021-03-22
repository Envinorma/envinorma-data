from typing import Any, Dict

from envinorma.parametrization.conditions import ParameterEnum


def new_text(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-new-text', 'rank': rank}


def new_text_title(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-new-text-title', 'rank': rank}


def new_text_content(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-new-text-content', 'rank': rank}


def target_section(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-target-section', 'rank': rank}


def target_section_store(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-target-section-store', 'rank': rank}


def target_alineas(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-target-alineas', 'rank': rank}


def delete_block_button(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-delete-block-button', 'rank': rank}


def delete_condition_button(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-delete-condition-button', 'rank': rank}


def target_section_block(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-target-section-block', 'rank': rank}


def condition_parameter(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-condition-parameter', 'rank': rank}


def condition_operation(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-condition-operation', 'rank': rank}


def condition_value(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-condition-value', 'rank': rank}


def condition_block(rank: int) -> Dict[str, Any]:
    return {'id': 'param-edition-condition-block', 'rank': rank}


DROPDOWN_OPTIONS = 'param-edition-dropdown-options'
TARGET_BLOCKS = 'param-edition-target-blocks'
ADD_TARGET_BLOCK = 'param-edition-add-target-block'
SOURCE = 'param-edition-source'
CONDITION_MERGE = 'param-edition-condition-merge'
ADD_CONDITION_BLOCK = 'param-edition-add-condition-block'
CONDITION_BLOCKS = 'param-edition-condition-blocks'
AM_ID = 'param-edition-am-id'
PARAMETER_RANK = 'param-edition-param-rank'
AM_OPERATION = 'param-edition-am-operation'
_AUTORISATION_DATE_FR = 'Date d\'autorisation'
_DECLARATION_DATE_FR = 'Date de déclaration'
_ENREGISTREMENT_DATE_FR = 'Date d\'enregistrement'
INSTALLATION_DATE_FR = 'Date de mise en service'
CONDITION_VARIABLES = {
    'Régime': ParameterEnum.REGIME,
    _AUTORISATION_DATE_FR: ParameterEnum.DATE_AUTORISATION,
    _DECLARATION_DATE_FR: ParameterEnum.DATE_DECLARATION,
    _ENREGISTREMENT_DATE_FR: ParameterEnum.DATE_ENREGISTREMENT,
    INSTALLATION_DATE_FR: ParameterEnum.DATE_INSTALLATION,
    'Alinéa': ParameterEnum.ALINEA,
    'Rubrique': ParameterEnum.RUBRIQUE,
    'Quantité associée à la rubrique': ParameterEnum.RUBRIQUE_QUANTITY,
}
