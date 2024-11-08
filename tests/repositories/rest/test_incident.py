from datetime import datetime
from typing import cast
from unittest.mock import Mock

import responses
from faker import Faker
from requests import HTTPError
from unittest_parametrize import ParametrizedTestCase, parametrize

from models import Action, Channel, HistoryEntry, Incident
from repositories.rest import RestIncidentRepository, TokenProvider


class TestIncident(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()
        self.base_url = self.faker.url().rstrip('/')
        self.repo = RestIncidentRepository(self.base_url, None)

    def test_authenticated_get_without_token_provider(self) -> None:
        repo = RestIncidentRepository(self.base_url, None)

        with responses.RequestsMock() as rsps:
            rsps.get(self.base_url)
            repo.authenticated_get(self.base_url)
            self.assertNotIn('Authorization', rsps.calls[0].request.headers)

    def test_authenticated_get_with_token_provider(self) -> None:
        token = self.faker.pystr()
        token_provider = Mock(TokenProvider)
        cast(Mock, token_provider.get_token).return_value = token

        repo = RestIncidentRepository(self.base_url, token_provider)

        with responses.RequestsMock() as rsps:
            rsps.get(self.base_url)
            repo.authenticated_get(self.base_url)
            self.assertEqual(rsps.calls[0].request.headers['Authorization'], f'Bearer {token}')

    def test_get_incidents_by_client_id_with_incidents(self) -> None:
        client_id = cast(str, self.faker.uuid4())

        incidents_data = [
            {
                'id': cast(str, self.faker.uuid4()),
                'name': 'Internet no funciona',
                'channel': 'web',
                'reported_by': cast(str, self.faker.uuid4()),
                'created_by': cast(str, self.faker.uuid4()),
                'assigned_to': cast(str, self.faker.uuid4()),
                'history': [
                    {
                        'seq': 0,
                        'date': '2024-10-23T22:46:40Z',
                        'action': 'created',
                        'description': 'El servicio de Internet está interrumpido.',
                    }
                ],
            }
        ]

        with responses.RequestsMock() as rsps:
            # Simulando la respuesta del endpoint de incident-query
            rsps.get(f'{self.base_url}/api/v1/clients/{client_id}/incidents', json=incidents_data, status=200)

            incidents = self.repo.get_incidents_by_client_id(client_id)

        # Crear objetos Incident y HistoryEntry para la validación
        history_entry = HistoryEntry(
            seq=0,
            date=datetime.fromisoformat('2024-10-23T22:46:40+00:00'),
            action=Action.CREATED,
            description='El servicio de Internet está interrumpido.',
        )

        expected_incident = Incident(
            id=incidents_data[0]['id'],
            name='Internet no funciona',
            channel=Channel.WEB,
            reported_by=incidents_data[0]['reported_by'],
            created_by=incidents_data[0]['created_by'],
            assigned_to=incidents_data[0]['assigned_to'],
            history=[history_entry],
        )

        self.assertEqual(incidents, [expected_incident])

    def test_get_incidents_by_client_id_not_found(self) -> None:
        client_id = cast(str, self.faker.uuid4())

        with responses.RequestsMock() as rsps:
            # Simulando respuesta cuando no se encuentran incidentes
            rsps.get(f'{self.base_url}/api/v1/clients/{client_id}/incidents', status=404)

            incidents = self.repo.get_incidents_by_client_id(client_id)

        self.assertEqual(incidents, [])

    @parametrize(
        'status',
        [
            (500,),  # Internal Server Error
            (400,),  # Bad Request
        ],
    )
    def test_get_incidents_by_client_id_error(self, status: int) -> None:
        client_id = cast(str, self.faker.uuid4())

        with responses.RequestsMock() as rsps:
            # Simulando error del servidor
            rsps.get(f'{self.base_url}/api/v1/clients/{client_id}/incidents', status=status)

            with self.assertRaises(HTTPError):
                self.repo.get_incidents_by_client_id(client_id)
