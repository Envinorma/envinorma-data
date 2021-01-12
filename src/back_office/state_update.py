import os
from datetime import datetime
from typing import List

from lib.parametrization import NonApplicationCondition, ParameterObject, Parametrization
from lib.utils import get_parametrization_wip_folder, jsonify

from back_office.utils import AMOperation, dump_am_state, load_am_state, load_parametrization, write_file


def _ensure_len(list_: List, min_len: int) -> None:
    if len(list_) < min_len:
        raise ValueError(f'Expecting len(list_) >= {min_len}, got {len(list_)}')


def _ensure_non_negative(int_: int) -> None:
    if int_ < 0:
        raise ValueError(f'Expecting non negative int, got {int_}')


def _recreate_with_removed_parameter(
    operation: AMOperation, parameter_rank: int, parametrization: Parametrization
) -> Parametrization:
    new_sections = parametrization.alternative_sections.copy()
    new_conditions = parametrization.application_conditions.copy()
    if operation == AMOperation.ADD_CONDITION:
        _ensure_len(parametrization.application_conditions, parameter_rank + 1)
        del new_conditions[parameter_rank]
    if operation == AMOperation.ADD_ALTERNATIVE_SECTION:
        _ensure_len(parametrization.alternative_sections, parameter_rank + 1)
        del new_sections[parameter_rank]
    return Parametrization(new_conditions, new_sections)


def _compute_filename() -> str:
    new_version = datetime.now().strftime('%y%m%d_%H%M')
    filename = new_version + '.json'
    return filename


def _add_filename_to_state(am_id: str, filename: str) -> None:
    am_state = load_am_state(am_id)
    am_state.parametrization_draft_filenames.append(filename)
    dump_am_state(am_id, am_state)


def remove_parameter(am_id: str, operation: AMOperation, parameter_rank: int) -> None:
    _ensure_non_negative(parameter_rank)
    previous_parametrization = _safe_load_parametrization(am_id)
    parametrization = _recreate_with_removed_parameter(operation, parameter_rank, previous_parametrization)
    _save_new_parametrization(am_id, parametrization)


def _save_new_parametrization(am_id: str, parametrization: Parametrization) -> None:
    filename = _compute_filename()
    full_filename = os.path.join(get_parametrization_wip_folder(am_id), filename)
    json_ = jsonify(parametrization.to_dict())
    write_file(json_, full_filename)
    _add_filename_to_state(am_id, filename)


def _safe_load_parametrization(am_id: str) -> Parametrization:
    parametrization = load_parametrization(am_id, load_am_state(am_id))
    if not parametrization:
        raise ValueError('Parametrization not found, which should not happen.')
    return parametrization


def _recreate_with_upserted_parameter(
    new_parameter: ParameterObject, parameter_rank: int, parametrization: Parametrization
) -> Parametrization:
    new_sections = parametrization.alternative_sections
    new_conditions = parametrization.application_conditions
    if isinstance(new_parameter, NonApplicationCondition):
        if parameter_rank >= 0:
            _ensure_len(parametrization.application_conditions, parameter_rank + 1)
            new_conditions[parameter_rank] = new_parameter
        else:
            new_conditions.append(new_parameter)
    else:
        if parameter_rank >= 0:
            _ensure_len(parametrization.alternative_sections, parameter_rank + 1)
            new_sections[parameter_rank] = new_parameter
        else:
            new_sections.append(new_parameter)
    return Parametrization(new_conditions, new_sections)


def upsert_parameter(am_id: str, new_parameter: ParameterObject, parameter_rank: int) -> None:
    previous_parametrization = _safe_load_parametrization(am_id)
    parametrization = _recreate_with_upserted_parameter(new_parameter, parameter_rank, previous_parametrization)
    _save_new_parametrization(am_id, parametrization)
