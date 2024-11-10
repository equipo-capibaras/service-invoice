import logging
from datetime import datetime

import requests
from dacite import Config, from_dict

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

        return requests.get(url, timeout=3, headers=headers)

    def get_incidents_by_client_id(self, client_id: str) -> list[Incident]:
        url = f'{self.base_url}/api/v1/clients/{client_id}/incidents'
        resp = self.authenticated_get(url=url)

        if resp.status_code == requests.codes.ok:
            data = resp.json()
            incidents = []

            for incident_data in data:
                # Convert 'history' entries to HistoryEntry objects
                history_entries = []
                for history_entry_data in incident_data['history']:
                    history_entry_data['date'] = datetime.fromisoformat(history_entry_data['date'].replace('Z', '+00:00'))
                    history_entry = from_dict(data_class=HistoryEntry, data=history_entry_data, config=Config(cast=[Action]))
                    history_entries.append(history_entry)

                # Add 'history' to incident_data
                incident_data['history'] = history_entries

                # Convert the incident data to an Incident object
                incident = from_dict(data_class=Incident, data=incident_data, config=Config(cast=[Channel]))
                incidents.append(incident)

            return incidents

        if resp.status_code == requests.codes.not_found:
            return []

        resp.raise_for_status()
        raise requests.HTTPError('Unexpected response from server', response=resp)
