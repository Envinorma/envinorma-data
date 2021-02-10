from enum import Enum
from typing import Any, Dict, Tuple
from werkzeug.routing import Map, Rule, MapAdapter


def build_am_page(am_id: str) -> str:
    return '/edit_am/' + am_id


class Endpoint(Enum):
    COMPARE = 'compare'
    EDIT_AM = 'edit_am'
    PARSE_AP = 'parse_ap'


ROUTER: MapAdapter = Map(
    [
        Rule('/compare', endpoint=Endpoint.COMPARE),
        Rule('/compare/id/<am_id>', endpoint=Endpoint.COMPARE),
        Rule('/compare/id/<am_id>/<date_before>/<date_after>', endpoint=Endpoint.COMPARE),
        Rule('/am/id/<id>/operation/<operation>', endpoint=Endpoint.EDIT_AM),
    ]
).bind('')


def route(pathname: str) -> Tuple[Endpoint, Dict[str, Any]]:
    return ROUTER.match(pathname)