import json
import os
from datetime import datetime
from functools import lru_cache
from typing import Dict, Optional

import requests
from requests_oauthlib import OAuth2Session
from tqdm import tqdm

from lib.config import AM_DATA_FOLDER, LEGIFRANCE_CLIENT_SECRET

_API_HOST = 'https://api.aife.economie.gouv.fr/dila/legifrance-beta/lf-engine-app'
_TOKEN_URL = 'https://oauth.aife.economie.gouv.fr/api/oauth/token'
_NOR_URL = f'{_API_HOST}/consult/getJoWithNor'


@lru_cache
def get_legifrance_client() -> OAuth2Session:
    secret = os.environ.get('CLIENT_SECRET', LEGIFRANCE_CLIENT_SECRET)
    if not secret:
        raise ValueError('Provide CLIENT_SECRET in environment variables')
    data = {
        'grant_type': 'client_credentials',
        'client_id': 'a5b0a4be-9406-4481-925d-e1bfb784f691',
        'client_secret': secret,
        'scope': 'openid',
    }
    response = requests.post(_TOKEN_URL, data=data)
    token = response.json()
    client = OAuth2Session('a5b0a4be-9406-4481-925d-e1bfb784f691', token=token)
    return client


class LegifranceRequestError(Exception):
    pass


def _extract_response_content(response: requests.Response) -> Dict:
    if 200 <= response.status_code < 300:
        return response.json()
    raise LegifranceRequestError(
        f'Request has status_code {response.status_code} and content {response.content.decode()}'
    )


def get_arrete_by_nor(nor: str, client: OAuth2Session) -> Dict:
    json_ = {'nor': nor}  # ex: nor = 'DEVP1706393A'
    response = client.post(_NOR_URL, json=json_)
    return _extract_response_content(response)


def get_loda_list(nor: str, client: OAuth2Session) -> Dict:
    url = _API_HOST + '/list/loda'
    json_ = {'nor': nor}  # ex: nor = 'DEVP1706393A'
    response = client.post(url, json=json_)
    return _extract_response_content(response)


def search(nor: str, client: OAuth2Session) -> Dict:
    url = _API_HOST + '/search'
    json_ = {
        'fond': 'LODA_DATE',
        'recherche': {
            # 'champs': [
            #     {
            #         'criteres': [{'typeRecherche': 'EXACTE', 'valeur': f'{nor}', 'operateur': 'ET'}],
            #         'operateur': 'ET',
            #         'typeChamp': 'NOR',
            #     }
            # ],
            'champs': [
                {
                    'typeChamp': 'NOR',
                    'criteres': [{'typeRecherche': 'EXACTE', 'valeur': nor, 'operateur': 'ET'}],
                    'operateur': 'ET',
                }
            ],
            # 'filtres': [{'valeur': f'{nor}', 'facette': 'NOR'}],
            'operateur': 'ET',
            'pageNumber': 1,
            'pageSize': 10,
            'sort': 'CONFORME',
            'typePagination': 'DEFAUT',
        },
    }
    response = client.post(url, json=json_)
    return _extract_response_content(response)


def get_current_loda_via_cid_response(cid: str, client: OAuth2Session) -> requests.Response:
    return get_loda_via_cid_response(cid, datetime.now(), client)


def get_current_loda_via_cid(cid: str, client: OAuth2Session) -> Dict:
    return _extract_response_content(get_current_loda_via_cid_response(cid, client))


def get_loda_via_cid_response(cid: str, date: datetime, client: OAuth2Session) -> requests.Response:
    json_ = {'date': int(date.timestamp()) * 1000, 'textId': cid}
    url = _API_HOST + '/consult/lawDecree'
    return client.post(url, json=json_)


def get_loda_via_cid(cid: str, date: datetime, client: OAuth2Session) -> Dict:
    return _extract_response_content(get_loda_via_cid_response(cid, date, client))


def get_article_by_id(cid: str, client: OAuth2Session) -> Dict:
    json_ = {'id': cid}
    url = _API_HOST + '/consult/getArticle'
    response = client.post(url, json=json_)
    return _extract_response_content(response)


def download_text(cid: str, output_filename: str, client: Optional[OAuth2Session]) -> None:
    if not client:
        client = get_legifrance_client()
    res = get_current_loda_via_cid(cid, client)
    json.dump(res, open(f'{AM_DATA_FOLDER}/legifrance_texts/{output_filename}', 'w'), ensure_ascii=False)


def download_all_lf_texts() -> None:
    texts = json.load(open(f'data/arretes_ministeriels.json'))
    client = get_legifrance_client()
    for text in tqdm(texts):
        if 'nor' in text and 'cid' in text:
            try:
                download_text(text['cid'], text['nor'] + '.json', client)
            except Exception as exc:  # pylint: disable=broad-except
                print(text['cid'], text['nor'], str(exc))
