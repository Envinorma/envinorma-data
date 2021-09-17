from dataclasses import dataclass
from typing import List

from envinorma.topics.patterns import TopicName


@dataclass
class LostTopic:
    topic: TopicName
    section_titles: List[str]
    section_id: str
