import dash
from enum import Enum
from typing import Any, Callable, Optional, Tuple
from werkzeug.routing import Map, MapAdapter, Rule


class Endpoint(Enum):
    AP_ODT = 'ap_odt'
    AP_PDF = 'ap_pdf'
    AP_IMAGE = 'ap_image'
    AP_IMAGE_V2 = 'ap_image_v2'
    ETABLISSEMENT = 'etablissement'
    INDEX = 'index'
    AP = 'ap'
    TMP = 'tmp'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


class APOperation(Enum):
    EDIT_PRESCRIPTIONS = 'edit_prescriptions'

    def __repr__(self):
        return self.value

    def __str__(self):
        return self.value


ROUTER: MapAdapter = Map(
    [
        Rule('/', endpoint=Endpoint.INDEX),
        Rule(f'/{Endpoint.AP_ODT}', endpoint=Endpoint.AP_ODT),
        Rule(f'/{Endpoint.AP_ODT}/id/<ap_id>', endpoint=Endpoint.AP_ODT),
        Rule(f'/{Endpoint.ETABLISSEMENT}', endpoint=Endpoint.ETABLISSEMENT),
        Rule(f'/{Endpoint.ETABLISSEMENT}/id/<etablissement_id>', endpoint=Endpoint.ETABLISSEMENT),
        Rule(f'/{Endpoint.AP}/id/<ap_id>', endpoint=Endpoint.AP),
        Rule(f'/{Endpoint.AP}/id/<ap_id>/<operation>', endpoint=Endpoint.AP),
        Rule(f'/{Endpoint.AP_PDF}', endpoint=Endpoint.AP_PDF),
        Rule(f'/{Endpoint.AP_IMAGE}', endpoint=Endpoint.AP_IMAGE),
        Rule(f'/{Endpoint.AP_IMAGE_V2}', endpoint=Endpoint.AP_IMAGE_V2),
        Rule(f'/{Endpoint.TMP}', endpoint=Endpoint.TMP),
    ]
).bind('')

CallbacksAdder = Optional[Callable[[dash.Dash], None]]
Page = Tuple[Callable[..., Any], CallbacksAdder]