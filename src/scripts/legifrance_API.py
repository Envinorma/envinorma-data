import requests
from typing import Dict
from requests_oauthlib import OAuth2Session

_API_HOST = "https://sandbox-api.aife.economie.gouv.fr"
_TOKEN_URL = 'https://sandbox-oauth.aife.economie.gouv.fr/api/oauth/token'
_NOR_URL = f'{_API_HOST}/dila/legifrance-beta/lf-engine-app/consult/getJoWithNor'


def get_legifrance_client() -> OAuth2Session:
    data = {
        "grant_type": "client_credentials",
        "client_id": '45a5cd6b-e9f3-445d-8a62-efa56b68c8ec',
        "client_secret": CLIENT_SECRET,
        "scope": "openid",
    }
    response = requests.post(_TOKEN_URL, data=data)
    token = response.json()
    client = OAuth2Session('45a5cd6b-e9f3-445d-8a62-efa56b68c8ec', token=token)
    return client


def _extract_response_content(response: requests.Response) -> Dict:
    if 200 <= response.status_code < 300:
        return response.json()
    raise ValueError(f'Requests has status_code {response.status_code} and content {response.content.decode()}')


def get_arrete_by_nor(nor: str, client: OAuth2Session) -> Dict:
    json_ = {'nor': nor}  # ex: nor = 'DEVP1706393A'
    response = client.post(_NOR_URL, json=json_)
    return _extract_response_content(response)
