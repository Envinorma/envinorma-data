import time
from datetime import datetime
from typing import Dict, Optional

import requests
from requests_oauthlib import OAuth2Session

_API_HOST = 'https://api.aife.economie.gouv.fr/dila/legifrance-beta/lf-engine-app'
_TOKEN_URL = 'https://oauth.aife.economie.gouv.fr/api/oauth/token'
_NOR_URL = f'{_API_HOST}/consult/getJoWithNor'


def _get_legifrance_client(client_id: str, client_secret: str) -> OAuth2Session:
    data = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'openid',
    }
    response = requests.post(_TOKEN_URL, data=data)
    if 200 <= response.status_code < 300:
        token = response.json()
        client = OAuth2Session(client_id, token=token)
        return client
    raise LegifranceRequestError(f'Error when retrieving token: {response.json()}')


_LAST_COMPUTE_TIME = time.time()
HOUR = 60 * 60
_RES: Optional[OAuth2Session] = None


def get_legifrance_client(client_id: str, client_secret: str) -> OAuth2Session:
    global _RES, _LAST_COMPUTE_TIME
    elapsed = time.time() - _LAST_COMPUTE_TIME
    if not _RES or elapsed >= HOUR:
        _LAST_COMPUTE_TIME = time.time()
        _RES = _get_legifrance_client(client_id, client_secret)
    return _RES


class LegifranceRequestError(Exception):
    pass


def _extract_response_content(response: requests.Response) -> Dict:
    if 200 <= response.status_code < 300:
        return response.json()
    raise LegifranceRequestError(
        f'Request has status_code {response.status_code} and content {response.content.decode()}'
    )


def get_arrete_by_nor(nor: str, client: OAuth2Session) -> Dict:
    json_ = {'nor': nor}
    response = client.post(_NOR_URL, json=json_)
    return _extract_response_content(response)


def get_loda_list(nor: str, client: OAuth2Session) -> Dict:
    url = _API_HOST + '/list/loda'
    json_ = {'nor': nor}
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
