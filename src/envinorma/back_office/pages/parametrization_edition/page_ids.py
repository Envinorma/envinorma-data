from envinorma.parametrization.conditions import ParameterEnum

CONDITION_VARIABLE = 'param-edition-condition-parameter'
CONDITION_OPERATION = 'param-edition-condition-operation'
CONDITION_VALUE = 'param-edition-condition-value'
SOURCE = 'param-edition-source'
TARGET_SECTION = 'param-edition-target-section'
TARGET_SECTION_STORE = 'param-edition-target-section-store'
TARGET_ALINEAS = 'param-edition-target-alineas'
LOADED_NB_ALINEAS = 'param-edition-loaded-nb-alineas'
CONDITION_MERGE = 'param-edition-condition-merge'
NB_CONDITIONS = 'param-edition-nb-conditions'
NEW_TEXT = 'param-edition-new-text'
NEW_TEXT_TITLE = 'param-edition-new-text-title'
NEW_TEXT_CONTENT = 'param-edition-new-text-content'
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