import json
from typing import Tuple

from .am_metadata import AMMetadata, AMSource, AMState  # noqa: F401
from .arrete_ministeriel import (  # noqa: F401
    ArreteMinisteriel,
    DateParameterDescriptor,
    VersionDescriptor,
    add_metadata,
    extract_date_of_signature,
)
from .classement import Classement, ClassementWithAlineas, Regime, ensure_rubrique  # noqa: F401
from .installation_classement import DetailedClassement, DetailedClassementState, DetailedRegime  # noqa: F401
from .structured_text import Annotations, Applicability, StructuredText  # noqa: F401
from .text_elements import EnrichedString, Linebreak, Link, Table  # noqa: F401

DELETE_REASON_MIN_NB_CHARS = 10


Ints = Tuple[int, ...]


def dump_path(path: Ints) -> str:
    return json.dumps(path)


def load_path(path_str: str) -> Ints:
    return tuple(json.loads(path_str))