from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

from .condition import Condition, load_condition


@dataclass
class AMApplicability:
    warnings: List[str] = field(default_factory=list)
    condition_of_inapplicability: Optional[Condition] = None

    def to_dict(self) -> Dict[str, Any]:
        res = asdict(self)
        if self.condition_of_inapplicability:
            res['condition_of_inapplicability'] = self.condition_of_inapplicability.to_dict()
        return res

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'AMApplicability':
        dict_ = dict_.copy()
        if dict_.get('condition_of_inapplicability'):
            dict_['condition_of_inapplicability'] = load_condition(dict_['condition_of_inapplicability'])
        return cls(**dict_)
