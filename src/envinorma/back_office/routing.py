from enum import Enum
from typing import Any, Dict, Tuple
from werkzeug.routing import Map, Rule, MapAdapter


def build_am_page(am_id: str) -> str:
    return '/edit_am/' + am_id


class Endpoint(Enum):
    COMPARE = 'compare'
    AM = 'am'
    EDIT_AM = 'edit_am'


ROUTER: MapAdapter = Map(
    [
        Rule('/compare', endpoint=Endpoint.COMPARE),
        Rule('/compare/id/<am_id>', endpoint=Endpoint.COMPARE),
        Rule('/compare/id/<am_id>/<date_before>/<date_after>', endpoint=Endpoint.COMPARE),
        Rule('/am/<am_id>', endpoint=Endpoint.AM),
        Rule('/am/<am_id>/compare/<compare_with>', endpoint=Endpoint.AM),
        # Rule('/edit_am/id/<id>/operation/<operation>', endpoint=Endpoint.EDIT_AM),
    ]
).bind('')


def route(pathname: str) -> Tuple[Endpoint, Dict[str, Any]]:
    return ROUTER.match(pathname)