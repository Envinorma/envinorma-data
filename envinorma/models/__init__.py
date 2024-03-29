import json
from typing import Tuple

from .am_applicability import AMApplicability  # noqa: F401
from .am_metadata import AMMetadata, AMSource, AMState  # noqa: F401
from .arrete_ministeriel import ArreteMinisteriel, extract_date_of_signature  # noqa: F401
from .classement import Classement, ClassementWithAlineas, Regime, ensure_rubrique  # noqa: F401
from .condition import (  # noqa: F401
    AndCondition,
    Condition,
    Conditions,
    ConditionType,
    Equal,
    Greater,
    LeafCondition,
    LeafConditions,
    Littler,
    MergeCondition,
    MergeConditions,
    MergeType,
    MonoCondition,
    OrCondition,
    Range,
    ensure_mono_conditions,
)
from .helpers.date_helpers import standardize_title_date  # noqa: F401
from .installation_classement import DetailedClassement, DetailedClassementState, DetailedRegime  # noqa: F401
from .parameter import Parameter, ParameterEnum, ParameterType, parameter_value_to_str  # noqa: F401
from .structured_text import Annotations, Applicability, Reference, StructuredText  # noqa: F401
from .text_elements import Cell, EnrichedString, Linebreak, Link, Row, Table, TextElement, Title  # noqa: F401

DELETE_REASON_MIN_NB_CHARS = 10


Ints = Tuple[int, ...]


def dump_path(path: Ints) -> str:
    return json.dumps(path)


def load_path(path_str: str) -> Ints:
    return tuple(json.loads(path_str))
