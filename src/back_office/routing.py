from typing import Any, Dict, Tuple
from werkzeug.routing import Map, Rule, MapAdapter


def build_am_page(am_id: str) -> str:
    return '/edit_am/' + am_id


# TODO : improve routing via werkzeug. Example below :
_url_map = Map(
    [
        Rule('/', endpoint=''),
        Rule('/am', endpoint='am'),
        Rule('/am/id/<id>', endpoint='am'),
        Rule('/am/id/<id>/operation/<operation>', endpoint='am'),
    ]
)


def application(pathname: str) -> Tuple[str, Dict[str, Any]]:
    urls: MapAdapter = _url_map.bind('')
    return urls.match(pathname)