import json
import random
import string
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, TypeVar, Union

import requests

from envinorma.config import config


def jsonify(obj: Union[Dict, List]) -> str:
    return json.dumps(obj, indent=4, sort_keys=True, ensure_ascii=False)


def write_file(text: str, filename: str) -> None:
    with open(filename, 'w') as file_:
        file_.write(text)


def write_json(obj: Union[Dict, List], filename: str, safe: bool = False, pretty: bool = True) -> None:
    indent = 4 if pretty else None
    with open(filename, 'w') as file_:
        if not safe:
            json.dump(obj, file_, indent=indent, sort_keys=True, ensure_ascii=False)
        else:
            try:
                json.dump(obj, file_, indent=indent, sort_keys=True, ensure_ascii=False)
            except Exception:  # pylint: disable=broad-except
                print(traceback.format_exc())


def random_string(size: int = 6) -> str:
    return ''.join([random.choice(string.ascii_letters) for _ in range(size)])


class SlackChannel(Enum):
    ENRICHMENT_NOTIFICATIONS = 'ENRICHMENT_NOTIFICATIONS'

    def slack_url(self) -> str:
        if self == self.ENRICHMENT_NOTIFICATIONS:
            return config.slack.enrichment_notification_url
        raise NotImplementedError(f'Missing slack channel url {self}.')


def send_slack_notification(message: str, channel: SlackChannel) -> None:
    url = channel.slack_url()
    answer = requests.post(url, json={'text': message})
    if not (200 <= answer.status_code < 300):
        print('Error with status code', answer.status_code)
        print(answer.content.decode())


T = TypeVar('T')


def ensure_not_none(candidate: Optional[T]) -> T:
    if not candidate:
        raise ValueError('Expecting non None argument')
    return candidate


def date_to_str(date: datetime) -> str:
    return date.strftime('%Y-%m-%d')


def str_to_date(date_str: str) -> datetime:
    return datetime.strptime(date_str, '%Y-%m-%d')
