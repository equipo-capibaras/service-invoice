import logging

import dacite
import requests

from models import Client, Plan
from repositories import ClientRepository

from .util import TokenProvider


class RestClientRepository(ClientRepository):
    def __init__(self, base_url: str, token_provider: TokenProvider | None) -> None:
        self.base_url = base_url
        self.token_provider = token_provider
        self.logger = logging.getLogger(self.__class__.__name__)

    def authenticated_get(self, url: str) -> requests.Response:
        if self.token_provider is None:
            headers = None
        else:
            id_token = self.token_provider.get_token()
            headers = {'Authorization': f'Bearer {id_token}'}

        return requests.get(url, timeout=2, headers=headers)

    def get(self, client_id: str) -> Client | None:
        url = f'{self.base_url}/api/v1/clients/{client_id}?include_plan=true'
        resp = self.authenticated_get(url=url)

        if resp.status_code == requests.codes.ok:
            data = resp.json()
            return dacite.from_dict(data_class=Client, data=data, config=dacite.Config(cast=[Plan]))

        if resp.status_code == requests.codes.not_found:
            return None

        resp.raise_for_status()

        raise requests.HTTPError('Unexpected response from server', response=resp)
