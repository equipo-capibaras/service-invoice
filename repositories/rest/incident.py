import logging

import dacite
import requests

from models import Action, Channel, HistoryEntry, Incident
from repositories import IncidentRepository

from .util import TokenProvider


class RestIncidentRepository(IncidentRepository):
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

    def get_incidents_by_client_id(self, client_id: str) -> list[Incident] | None:
        url = f'{self.base_url}/api/v1/clients/{client_id}/incidents'
        resp = self.authenticated_get(url=url)

        if resp.status_code == requests.codes.ok:
            data = resp.json()
            incidents = []

            for incident_data in data:
                # Convert the history entries in HistoryEntry objects
                history_entries = [
                    dacite.from_dict(data_class=HistoryEntry, data=history_entry_data, config=dacite.Config(cast=[Action]))
                    for history_entry_data in incident_data.get('history', [])
                ]

                # Convert the incident data in an Incident object
                incident = dacite.from_dict(
                    data_class=Incident,
                    data={**incident_data, 'channel': Channel(incident_data['channel']), 'history': history_entries},
                    config=dacite.Config(cast=[Channel]),
                )
                incidents.append(incident)

            return incidents

        if resp.status_code == requests.codes.not_found:
            return None

        resp.raise_for_status()
        raise requests.HTTPError(f'Unexpected status code: {resp.status_code}', response=resp)
