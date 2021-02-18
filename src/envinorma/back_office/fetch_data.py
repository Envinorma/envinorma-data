import json
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from envinorma.back_office.utils import AMOperation, AMStatus, ID_TO_AM_MD
from envinorma.config import config
from envinorma.data import ArreteMinisteriel
from envinorma.parametrization import (
    NonApplicationCondition,
    ParameterObject,
    Parametrization,
    check_parametrization_consistency,
)


def _ensure_len(list_: List, min_len: int) -> None:
    if len(list_) < min_len:
        raise ValueError(f'Expecting len(list_) >= {min_len}, got {len(list_)}')


def _ensure_non_negative(int_: int) -> None:
    if int_ < 0:
        raise ValueError(f'Expecting non negative int, got {int_}')


def _exectute_select_query(query: str, values: Tuple) -> List[Tuple]:
    connection = psycopg2.connect(config.storage.psql_dsn)
    cursor = connection.cursor()
    cursor.execute(query, values)
    res = list(cursor.fetchall())
    cursor.close()
    connection.close()
    return res


def _exectute_update_query(query: str, values: Tuple) -> None:
    connection = psycopg2.connect(config.storage.psql_dsn)
    cursor = connection.cursor()
    cursor.execute(query, values)
    connection.commit()
    cursor.close()
    connection.close()


def _exectute_delete_query(query: str, values: Tuple) -> None:
    connection = psycopg2.connect(config.storage.psql_dsn)
    cursor = connection.cursor()
    cursor.execute(query, values)
    connection.commit()
    cursor.close()
    connection.close()


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


def remove_parameter(am_id: str, operation: AMOperation, parameter_rank: int) -> None:
    _ensure_non_negative(parameter_rank)
    previous_parametrization = _load_parametrization(am_id)
    if not previous_parametrization:
        raise ValueError('Expecting a non null parametrization.')
    parametrization = _recreate_with_removed_parameter(operation, parameter_rank, previous_parametrization)
    upsert_new_parametrization(am_id, parametrization)


def upsert_new_parametrization(am_id: str, parametrization: Parametrization) -> None:
    data = json.dumps(parametrization.to_dict())
    query = (
        'INSERT INTO parametrization(am_id, data) VALUES(%s, %s) ON CONFLICT (am_id)'
        ' DO UPDATE SET data = %s WHERE parametrization.am_id = %s;'
    )
    _exectute_update_query(query, (am_id, data, data, am_id))


def _load_parametrization(am_id: str) -> Optional[Parametrization]:
    query = 'SELECT data FROM parametrization where am_id = %s LIMIT 1;'
    tuples = _exectute_select_query(query, (am_id,))
    if len(tuples) > 1:
        raise ValueError('Parametrization not found, which should not happen.')
    if not tuples:
        return None
    if len(tuples[0]) != 1:
        raise ValueError(f'Expecting one value, received {len(tuples[0])}.')
    return Parametrization.from_dict(json.loads(tuples[0][0]))


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
    previous_parametrization = _load_parametrization(am_id) or Parametrization([], [])
    parametrization = _recreate_with_upserted_parameter(new_parameter, parameter_rank, previous_parametrization)
    check_parametrization_consistency(parametrization)
    upsert_new_parametrization(am_id, parametrization)


def _ensure_one_variable(res: List[Tuple]) -> Any:
    if len(res) != 1 or len(res[0]) != 1:
        raise ValueError(f'Expecting only one value in res. Got :\n{str(res)[:280]}')
    return res[0][0]


def load_parametrization(am_id: str) -> Optional[Parametrization]:
    query = 'SELECT data FROM parametrization WHERE am_id = %s;'
    json_am = _exectute_select_query(query, (am_id,))
    if json_am:
        return Parametrization.from_dict(json.loads(_ensure_one_variable(json_am)))
    return None


def load_structured_am(am_id: str) -> Optional[ArreteMinisteriel]:
    query = 'SELECT data FROM structured_am WHERE am_id = %s;'
    json_am = _exectute_select_query(query, (am_id,))
    if json_am:
        return _load_am_str(_ensure_one_variable(json_am))
    return None


def delete_structured_am(am_id: str) -> None:
    query = "DELETE FROM structured_am WHERE am_id = %s;"
    _exectute_delete_query(query, (am_id,))


def upsert_structured_am(am_id: str, am: ArreteMinisteriel) -> None:
    query = (
        'INSERT INTO structured_am(am_id, data) VALUES(%s, %s) ON CONFLICT (am_id)'
        ' DO UPDATE SET data = %s WHERE structured_am.am_id =%s;'
    )
    data = json.dumps(am.to_dict())
    _exectute_update_query(query, (am_id, data, data, am_id))


def _load_am_str(str_: str) -> ArreteMinisteriel:
    return ArreteMinisteriel.from_dict(json.loads(str_))


def load_initial_am(am_id: str) -> Optional[ArreteMinisteriel]:
    query = 'SELECT data FROM initial_am WHERE am_id = %s;'
    json_am = _exectute_select_query(query, (am_id,))
    if json_am:
        return _load_am_str(_ensure_one_variable(json_am))
    return None


def delete_initial_am(am_id: str) -> None:
    query = "DELETE FROM initial_am WHERE am_id = %s;"
    _exectute_delete_query(query, (am_id,))


def upsert_initial_am(am_id: str, am: ArreteMinisteriel) -> None:
    query = (
        'INSERT INTO initial_am(am_id, data) VALUES(%s, %s) ON CONFLICT (am_id)'
        ' DO UPDATE SET data = %s WHERE initial_am.am_id =%s;'
    )
    data = json.dumps(am.to_dict())
    _exectute_update_query(query, (am_id, data, data, am_id))


def load_am_status(am_id: str) -> AMStatus:
    query = 'SELECT status FROM am_status WHERE am_id = %s;'
    status = _ensure_one_variable(_exectute_select_query(query, (am_id,)))
    return AMStatus(status)


def load_all_am_statuses() -> Dict[str, AMStatus]:
    query = 'SELECT am_id, status FROM am_status'
    return {am_id: AMStatus(status) for am_id, status in _exectute_select_query(query, ())}


def upsert_am_status(am_id: str, new_status: AMStatus) -> None:
    query = (
        'INSERT INTO am_status(am_id, status) VALUES(%s, %s) ON CONFLICT (am_id)'
        ' DO UPDATE SET status = %s WHERE am_status.am_id =%s;'
    )
    _exectute_update_query(query, (am_id, new_status.value, new_status.value, am_id))


def load_all_structured_am() -> List[ArreteMinisteriel]:
    ids = list(ID_TO_AM_MD)
    query = 'SELECT am_id, data FROM structured_am'
    tuples = _exectute_select_query(query, ())
    return [_load_am_str(json_am) for id_, json_am in tuples if id_ in ids]


def load_all_initial_am() -> List[ArreteMinisteriel]:
    ids = list(ID_TO_AM_MD)
    query = 'SELECT am_id, data FROM initial_am'
    tuples = _exectute_select_query(query, ())
    return [_load_am_str(json_am) for id_, json_am in tuples if id_ in ids]
