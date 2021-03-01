from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, Tuple

import dash
from werkzeug.routing import Map, MapAdapter, Rule


def build_am_page(am_id: str) -> str:
    return '/edit_am/' + am_id


class Endpoint(Enum):
    INDEX = ''
    COMPARE = 'compare'
    AM = 'am'
    EDIT_AM = 'edit_am'
    LOGIN = 'login'
    LOGOUT = 'logout'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


ROUTER: MapAdapter = Map(
    [
        Rule(f'/{Endpoint.INDEX}', endpoint=Endpoint.INDEX),
        Rule(f'/{Endpoint.COMPARE}', endpoint=Endpoint.COMPARE),
        Rule(f'/{Endpoint.COMPARE}/id/<am_id>', endpoint=Endpoint.COMPARE),
        Rule(f'/{Endpoint.COMPARE}/id/<am_id>/<date_before>/<date_after>', endpoint=Endpoint.COMPARE),
        Rule(f'/{Endpoint.AM}/<am_id>', endpoint=Endpoint.AM),
        Rule(f'/{Endpoint.AM}/<am_id>/compare/<compare_with>', endpoint=Endpoint.AM),
        Rule(f'/{Endpoint.LOGIN}', endpoint=Endpoint.LOGIN),
        Rule(f'/{Endpoint.LOGOUT}', endpoint=Endpoint.LOGOUT),
        # Rule('/edit_am/id/<id>/operation/<operation>', endpoint=Endpoint.EDIT_AM),
    ]
).bind('')


@dataclass
class Page:
    layout: Callable[..., Any]
    callbacks_adder: Optional[Callable[[dash.Dash], None]]
