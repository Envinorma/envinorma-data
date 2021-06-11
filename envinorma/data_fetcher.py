import json
from typing import Any, Dict, List, Optional, Set, Tuple, Type, TypeVar

import psycopg2

from envinorma.models.am_metadata import AMMetadata, AMState
from envinorma.models.arrete_ministeriel import ArreteMinisteriel
from envinorma.parametrization.models.parametrization import (
    AlternativeSection,
    AMWarning,
    InapplicableSection,
    ParameterObject,
    Parametrization,
)
from envinorma.utils import AMStatus


def _ensure_len(list_: List, min_len: int) -> None:
    if len(list_) < min_len:
        raise ValueError(f'Expecting len(list_) >= {min_len}, got {len(list_)}')


def _ensure_non_negative(int_: int) -> None:
    if int_ < 0:
        raise ValueError(f'Expecting non negative int, got {int_}')


def _ensure_one_variable(res: List[Tuple]) -> Any:
    if len(res) != 1 or len(res[0]) != 1:
        raise ValueError(f'Expecting only one value in res. Got :\n{str(res)[:280]}')
    return res[0][0]


def _load_am_str(str_: str) -> ArreteMinisteriel:
    return ArreteMinisteriel.from_dict(json.loads(str_))


def _recreate_with_removed_parameter(
    object_type: Type[ParameterObject], parameter_rank: int, parametrization: Parametrization
) -> Parametrization:
    new_sections = parametrization.alternative_sections.copy()
    new_conditions = parametrization.application_conditions.copy()
    new_warnings = parametrization.warnings.copy()
    if object_type == InapplicableSection:
        _ensure_len(parametrization.application_conditions, parameter_rank + 1)
        del new_conditions[parameter_rank]
    if object_type == AlternativeSection:
        _ensure_len(parametrization.alternative_sections, parameter_rank + 1)
        del new_sections[parameter_rank]
    if object_type == AMWarning:
        _ensure_len(parametrization.warnings, parameter_rank + 1)
        del new_warnings[parameter_rank]
    return Parametrization(new_conditions, new_sections, new_warnings)


T = TypeVar('T')


def _replace_element_in_list_or_append_if_negative_rank(element: T, list_: List[T], rank: int) -> List[T]:
    if rank < 0:
        return [*list_, element]
    if rank >= len(list_):
        raise ValueError(f'Cannot replace element of rank {rank} in a list of size {len(list_)}')
    return [elt if i != rank else element for i, elt in enumerate(list_)]


def _recreate_with_upserted_parameter(
    new_parameter: ParameterObject, parameter_rank: int, parametrization: Parametrization
) -> Parametrization:
    new_sections = parametrization.alternative_sections
    new_conditions = parametrization.application_conditions
    new_warnings = parametrization.warnings
    if isinstance(new_parameter, InapplicableSection):
        new_conditions = _replace_element_in_list_or_append_if_negative_rank(
            new_parameter, new_conditions, parameter_rank
        )
    elif isinstance(new_parameter, AlternativeSection):
        new_sections = _replace_element_in_list_or_append_if_negative_rank(new_parameter, new_sections, parameter_rank)
    else:
        new_warnings = _replace_element_in_list_or_append_if_negative_rank(new_parameter, new_warnings, parameter_rank)
    return Parametrization(new_conditions, new_sections, new_warnings)


def _create_table_queries() -> List[str]:
    queries = ['CREATE TABLE IF NOT EXISTS am_status (am_id VARCHAR(255) PRIMARY KEY, status VARCHAR(255));']
    type_1_tables = ['am_metadata', 'initial_am', 'parametrization', 'structured_am']
    for table in type_1_tables:
        queries.append(f'CREATE TABLE IF NOT EXISTS {table} (am_id VARCHAR(255) PRIMARY KEY, data TEXT);')
    return queries


def create_tables(psql_dsn: str) -> None:
    """
    Execute this function if you start the application from an empty database, or have missing tables.
    """
    connection = psycopg2.connect(psql_dsn)
    cursor = connection.cursor()
    for query in _create_table_queries():
        cursor.execute(query, ())
    connection.commit()
    cursor.close()
    connection.close()


class DataFetcher:
    def __init__(self, psql_dsn: str) -> None:
        self.psql_dsn: str = psql_dsn

    def _exectute_select_query(self, query: str, values: Tuple) -> List[Tuple]:
        connection = psycopg2.connect(self.psql_dsn)
        cursor = connection.cursor()
        cursor.execute(query, values)
        res = list(cursor.fetchall())
        cursor.close()
        connection.close()
        return res

    def _exectute_update_query(self, query: str, values: Tuple) -> None:
        connection = psycopg2.connect(self.psql_dsn)
        cursor = connection.cursor()
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
        connection.close()

    def _exectute_delete_query(self, query: str, values: Tuple) -> None:
        connection = psycopg2.connect(self.psql_dsn)
        cursor = connection.cursor()
        cursor.execute(query, values)
        connection.commit()
        cursor.close()
        connection.close()

    def load_am_metadata(self, am_id: str) -> Optional[AMMetadata]:
        query = 'SELECT data FROM am_metadata WHERE am_id = %s;'
        json_am = self._exectute_select_query(query, (am_id,))
        if json_am:
            return AMMetadata.from_dict(json.loads(_ensure_one_variable(json_am)))
        return None

    def load_all_am_metadata(self, with_deleted_ams: bool = False) -> Dict[str, AMMetadata]:
        query = 'SELECT am_id, data FROM am_metadata;'
        tuples = self._exectute_select_query(query, ())
        result = {am_id: AMMetadata.from_dict(json.loads(json_)) for am_id, json_ in tuples or {}}
        if with_deleted_ams:
            return result
        return {am_id: am for am_id, am in result.items() if am.state == am.state.VIGUEUR}

    def upsert_am(self, am_md: AMMetadata) -> None:
        data = json.dumps(am_md.to_dict())
        query = (
            'INSERT INTO am_metadata(am_id, data) VALUES(%s, %s) ON CONFLICT (am_id)'
            ' DO UPDATE SET data = %s WHERE am_metadata.am_id = %s;'
        )
        self._exectute_update_query(query, (am_md.cid, data, data, am_md.cid))

    def delete_am(self, am_id: str, reason_deleted: str) -> None:
        am_metadata = self.load_am_metadata(am_id)
        if not am_metadata:
            raise ValueError(f'AM with id {am_id} does not exist, cannot delete it.')
        am_metadata.state = AMState.DELETED
        am_metadata.reason_deleted = reason_deleted
        self.upsert_am(am_metadata)

    def remove_parameter(self, am_id: str, parameter_type: Type[ParameterObject], parameter_rank: int) -> None:
        _ensure_non_negative(parameter_rank)
        previous_parametrization = self._load_parametrization(am_id)
        if not previous_parametrization:
            raise ValueError('Expecting a non null parametrization.')
        parametrization = _recreate_with_removed_parameter(parameter_type, parameter_rank, previous_parametrization)
        self.upsert_new_parametrization(am_id, parametrization)

    def upsert_new_parametrization(self, am_id: str, parametrization: Parametrization) -> None:
        data = json.dumps(parametrization.to_dict())
        query = (
            'INSERT INTO parametrization(am_id, data) VALUES(%s, %s) ON CONFLICT (am_id)'
            ' DO UPDATE SET data = %s WHERE parametrization.am_id = %s;'
        )
        self._exectute_update_query(query, (am_id, data, data, am_id))

    def _load_parametrization(self, am_id: str) -> Optional[Parametrization]:
        query = 'SELECT data FROM parametrization where am_id = %s LIMIT 1;'
        tuples = self._exectute_select_query(query, (am_id,))
        if len(tuples) > 1:
            raise ValueError('Parametrization not found, which should not happen.')
        if not tuples:
            return None
        if len(tuples[0]) != 1:
            raise ValueError(f'Expecting one value, received {len(tuples[0])}.')
        return Parametrization.from_dict(json.loads(tuples[0][0]))

    def load_or_init_parametrization(self, am_id: str) -> Parametrization:
        return self.load_parametrization(am_id) or Parametrization([], [], [])

    def upsert_parameter(self, am_id: str, new_parameter: ParameterObject, parameter_rank: int) -> None:
        previous_parametrization = self.load_or_init_parametrization(am_id)
        parametrization = _recreate_with_upserted_parameter(new_parameter, parameter_rank, previous_parametrization)
        parametrization.check_consistency()
        self.upsert_new_parametrization(am_id, parametrization)

    def load_parametrization(self, am_id: str) -> Optional[Parametrization]:
        query = 'SELECT data FROM parametrization WHERE am_id = %s;'
        json_am = self._exectute_select_query(query, (am_id,))
        if json_am:
            return Parametrization.from_dict(json.loads(_ensure_one_variable(json_am)))
        return None

    def load_all_parametrizations(self) -> Dict[str, Parametrization]:
        query = 'SELECT am_id, data FROM parametrization;'
        tuples = self._exectute_select_query(query, ())
        return {am_id: Parametrization.from_dict(json.loads(json_)) for am_id, json_ in tuples or {}}

    def load_structured_am(self, am_id: str) -> Optional[ArreteMinisteriel]:
        query = 'SELECT data FROM structured_am WHERE am_id = %s;'
        json_am = self._exectute_select_query(query, (am_id,))
        if json_am:
            return _load_am_str(_ensure_one_variable(json_am))
        return None

    def delete_structured_am(self, am_id: str) -> None:
        query = "DELETE FROM structured_am WHERE am_id = %s;"
        self._exectute_delete_query(query, (am_id,))

    def upsert_structured_am(self, am_id: str, am: ArreteMinisteriel) -> None:
        query = (
            'INSERT INTO structured_am(am_id, data) VALUES(%s, %s) ON CONFLICT (am_id)'
            ' DO UPDATE SET data = %s WHERE structured_am.am_id =%s;'
        )
        data = json.dumps(am.to_dict())
        self._exectute_update_query(query, (am_id, data, data, am_id))

    def load_initial_am(self, am_id: str) -> Optional[ArreteMinisteriel]:
        query = 'SELECT data FROM initial_am WHERE am_id = %s;'
        json_am = self._exectute_select_query(query, (am_id,))
        if json_am:
            return _load_am_str(_ensure_one_variable(json_am))
        return None

    def delete_initial_am(self, am_id: str) -> None:
        query = "DELETE FROM initial_am WHERE am_id = %s;"
        self._exectute_delete_query(query, (am_id,))

    def upsert_initial_am(self, am_id: str, am: ArreteMinisteriel) -> None:
        query = (
            'INSERT INTO initial_am(am_id, data) VALUES(%s, %s) ON CONFLICT (am_id)'
            ' DO UPDATE SET data = %s WHERE initial_am.am_id =%s;'
        )
        data = json.dumps(am.to_dict())
        self._exectute_update_query(query, (am_id, data, data, am_id))

    def load_most_advanced_am(self, am_id: str) -> Optional[ArreteMinisteriel]:
        return self.load_structured_am(am_id) or self.load_initial_am(am_id)

    def load_am_status(self, am_id: str) -> AMStatus:
        query = 'SELECT status FROM am_status WHERE am_id = %s;'
        query_result = self._exectute_select_query(query, (am_id,))
        if not query_result:
            return AMStatus.PENDING_INITIALIZATION
        status = _ensure_one_variable(query_result)
        return AMStatus(status)

    def load_all_am_statuses(self) -> Dict[str, AMStatus]:
        query = 'SELECT am_id, status FROM am_status'
        return {am_id: AMStatus(status) for am_id, status in self._exectute_select_query(query, ())}

    def upsert_am_status(self, am_id: str, new_status: AMStatus) -> None:
        query = (
            'INSERT INTO am_status(am_id, status) VALUES(%s, %s) ON CONFLICT (am_id)'
            ' DO UPDATE SET status = %s WHERE am_status.am_id =%s;'
        )
        self._exectute_update_query(query, (am_id, new_status.value, new_status.value, am_id))

    def load_structured_ams(self, am_ids: Set[str]) -> List[ArreteMinisteriel]:
        query = 'SELECT am_id, data FROM structured_am'
        tuples = self._exectute_select_query(query, ())
        return [_load_am_str(json_am) for id_, json_am in tuples if id_ in am_ids]

    def load_initial_ams(self, am_ids: Set[str]) -> List[ArreteMinisteriel]:
        query = 'SELECT am_id, data FROM initial_am'
        tuples = self._exectute_select_query(query, ())
        return [_load_am_str(json_am) for id_, json_am in tuples if id_ in am_ids]

    def safe_load_most_advanced_am(self, am_id: str) -> ArreteMinisteriel:
        am = self.load_most_advanced_am(am_id)
        if not am:
            raise ValueError('Expecting one AM to proceed.')
        return am
