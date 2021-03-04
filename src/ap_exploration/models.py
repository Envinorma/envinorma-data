from dataclasses import asdict, dataclass
from typing import Any, Dict, List

from envinorma.data.text_elements import TextElement, load_text_element


@dataclass
class ArretePrefectoral:
    id: str
    title: str
    visas_considerant: List[str]
    content: List[TextElement]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, dict_: Dict[str, Any]) -> 'ArretePrefectoral':
        dict_ = dict_.copy()
        dict_['content'] = [load_text_element(el) for el in dict_['content']]
        return ArretePrefectoral(**dict_)
