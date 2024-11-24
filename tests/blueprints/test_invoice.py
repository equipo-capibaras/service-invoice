import base64
import json
from datetime import UTC, datetime
from typing import Any, cast
from unittest.mock import MagicMock, Mock, patch

import responses
from faker import Faker
from unittest_parametrize import ParametrizedTestCase, parametrize

from app import create_app
from blueprints.invoice import (
    create_invoice,
    create_rate,
    get_billing_period,
    get_incidents_by_client_and_month,
    invoice_result_to_dict,
)
from models import Channel, Client, Incident, Invoice, Month, Plan, Rate, Role
from repositories import ClientRepository, IncidentRepository, InvoiceRepository, RateRepository


class TestInvoice(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()
        self.app = create_app()
        self.test_client = self.app.test_client()

        self.client_repo = MagicMock(spec=ClientRepository)
        self.incident_repo = MagicMock(spec=IncidentRepository)
        self.invoice_repo = MagicMock(spec=InvoiceRepository)
        self.rate_repo = MagicMock(spec=RateRepository)

        self.client_id = self.faker.uuid4()
        self.rate = Rate(
            id=str(self.faker.uuid4()),
            plan=Plan.EMPRENDEDOR,
            client_id=str(self.client_id),
            fixed_cost=100.0,
            cost_per_incident_web=10.0,
            cost_per_incident_mobile=15.0,
            cost_per_incident_email=5.0,
        )
        self.client = Client(id=str(self.client_id), plan=Plan.EMPRENDEDOR, name='Test Client')

    def gen_token_employee(self, *, client_id: str | None, role: Role, assigned: bool) -> dict[str, Any]:
        return {
            'sub': str(self.faker.uuid4()),
            'cid': client_id,
            'role': role.value,
            'aud': ('' if assigned else 'unassigned_') + role.value,
        }

    def encode_token(self, token: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(token).encode()).decode()

    def test_get_billing_period(self) -> None:
        billing_month, billing_year = get_billing_period()
        now = datetime.now(UTC)
        expected_month = Month.from_int(now.month - 1 if now.month > 1 else 12)
        expected_year = now.year if now.month > 1 else now.year - 1

        self.assertEqual(billing_month, expected_month)
        self.assertEqual(billing_year, expected_year)

    @parametrize(
        ('plan', 'expect_error'),
        [
            (Plan.EMPRENDEDOR, False),
            (Plan.EMPRESARIO, False),
            (Plan.EMPRESARIO_PLUS, False),
            ('unknown', True),
        ],
    )
    def test_create_rate(self, *, plan: str, expect_error: bool) -> None:
        self.client.plan = cast(Plan, plan)
        self.rate_repo.create = MagicMock()

        if expect_error:
            with self.assertRaises(ValueError):
                create_rate(self.client, self.rate_repo)
        else:
            rate = create_rate(self.client, self.rate_repo)

            self.assertEqual(rate.client_id, self.client.id)
            self.assertEqual(rate.plan, self.client.plan)
            self.rate_repo.create.assert_called_once_with(rate)

    def test_get_incidents_by_client_and_month(self) -> None:
        mock_incident = MagicMock(spec=Incident)
        mock_incident.history = [MagicMock(date=datetime(2024, 11, 1, tzinfo=UTC))]
        self.incident_repo.get_incidents_by_client_id.return_value = [mock_incident]

        incidents = get_incidents_by_client_and_month(
            client_id=str(self.client_id),
            month=Month.NOVEMBER,
            year=2024,
            incident_repo=self.incident_repo,
        )

        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0], mock_incident)

    def test_create_invoice(self) -> None:
        self.invoice_repo.create = MagicMock()
        month_year = (Month.NOVEMBER, 2024)

        history_date = datetime(2024, 11, 15, tzinfo=UTC)

        incidents = [
            Incident(
                id=str(self.faker.uuid4()),
                channel=Channel.WEB,
                name=self.faker.sentence(),
                reported_by=str(self.faker.uuid4()),
                created_by=str(self.faker.uuid4()),
                assigned_to=str(self.faker.uuid4()),
                history=[MagicMock(date=history_date)],
            ),
            Incident(
                id=str(self.faker.uuid4()),
                channel=Channel.MOBILE,
                name=self.faker.sentence(),
                reported_by=str(self.faker.uuid4()),
                created_by=str(self.faker.uuid4()),
                assigned_to=str(self.faker.uuid4()),
                history=[MagicMock(date=history_date)],
            ),
        ]

        self.incident_repo.get_incidents_by_client_id.return_value = incidents

        invoice = create_invoice(
            month_year=month_year,
            client_id=str(self.client_id),
            rate=self.rate,
            incident_repo=self.incident_repo,
            invoice_repo=self.invoice_repo,
        )

        self.assertEqual(invoice.billing_month, Month.NOVEMBER)
        self.assertEqual(invoice.billing_year, 2024)
        self.assertEqual(invoice.total_incidents_web, 1)
        self.assertEqual(invoice.total_incidents_mobile, 1)
        self.invoice_repo.create.assert_called_once_with(invoice)

    def test_invoice_result_to_dict(self) -> None:
        invoice = Invoice(
            id=str(self.faker.uuid4()),
            client_id=str(self.client_id),
            rate_id=self.rate.id,
            generation_date=datetime.now(UTC),
            billing_month=Month.NOVEMBER,
            billing_year=2024,
            payment_due_date=datetime(2024, 11, 27, tzinfo=UTC),
            total_incidents_web=10,
            total_incidents_mobile=5,
            total_incidents_email=2,
        )

        result = invoice_result_to_dict(invoice, self.rate, self.client)

        self.assertEqual(result['billing_month'], 'November')
        self.assertEqual(result['billing_year'], 2024)
        self.assertEqual(result['client_id'], self.client.id)
        self.assertEqual(result['client_name'], self.client.name)
        self.assertEqual(result['total_cost'], 285.0)
        self.assertEqual(result['total_incidents']['web'], 10)

    @responses.activate
    def test_get_invoice_success(self) -> None:
        mock_client_repo = Mock()
        mock_rate_repo = Mock()
        mock_invoice_repo = Mock()
        mock_incidentquery_repo = Mock()

        mock_client_repo.get.return_value = self.client
        mock_rate_repo.get_by_client_and_plan.return_value = self.rate
        mock_invoice_repo.get_by_client_and_month.return_value = None
        mock_incidentquery_repo.get_incidents_by_client_id.return_value = []

        token = {'sub': 'uuid-del-usuario', 'cid': str(self.client_id), 'role': 'admin', 'aud': 'admin'}
        token_encoded = base64.urlsafe_b64encode(json.dumps(token).encode()).decode()

        with (
            self.app.container.client_repo.override(mock_client_repo),
            self.app.container.rate_repo.override(mock_rate_repo),
            self.app.container.invoice_repo.override(mock_invoice_repo),
            self.app.container.incidentquery_repo.override(mock_incidentquery_repo),
            self.app.test_client() as client,
        ):
            resp = client.get('/api/v1/invoice', headers={'X-Apigateway-Api-Userinfo': token_encoded})

            self.assertEqual(resp.status_code, 200)

    @responses.activate
    def test_get_invoice_failure(self) -> None:
        mock_client_repo = Mock()
        mock_rate_repo = Mock()
        mock_invoice_repo = Mock()
        mock_incidentquery_repo = Mock()

        client = Client(id=str(self.client_id), name='Test Client', plan=Plan.EMPRENDEDOR)
        mock_client_repo.get.return_value = client

        mock_invoice_repo.get_by_client_and_month.side_effect = Exception('Internal Server Error')

        token = {
            'sub': 'uuid-del-usuario',
            'cid': str(self.client_id),
            'role': 'admin',
            'aud': 'admin',
        }
        token_encoded = base64.urlsafe_b64encode(json.dumps(token).encode()).decode()

        with (
            self.app.container.client_repo.override(mock_client_repo),
            self.app.container.rate_repo.override(mock_rate_repo),
            self.app.container.invoice_repo.override(mock_invoice_repo),
            self.app.container.incidentquery_repo.override(mock_incidentquery_repo),
            self.app.test_client() as test_client,
        ):
            resp = test_client.get('/api/v1/invoice', headers={'X-Apigateway-Api-Userinfo': token_encoded})

            self.assertEqual(resp.status_code, 500)
            self.assertIn('Internal Server Error', resp.get_data(as_text=True))

    @patch('google.cloud.firestore_v1.client.Client.__init__', return_value=None)
    @patch('google.cloud.firestore_v1.client.Client.collection')
    def test_get_invoice_forbidden(self, mock_collection: Any, mock_client_init: Any) -> None:  # noqa: ANN401
        mock_client_init.return_value = None
        mock_collection.return_value = MagicMock()

        token = self.gen_token_employee(role=Role.AGENT, client_id='test-client-id', assigned=True)
        headers = {'X-Apigateway-Api-Userinfo': self.encode_token(token)}

        resp = self.test_client.get('/api/v1/invoice', headers=headers)

        self.assertEqual(resp.status_code, 403)
        self.assertIn('Forbidden', resp.get_json()['message'])

    @patch('google.cloud.firestore_v1.client.Client.__init__', return_value=None)
    @patch('google.cloud.firestore_v1.client.Client.collection')
    def test_get_invoice_client_not_found(self, mock_collection: Any, mock_client_init: Any) -> None:  # noqa: ANN401
        mock_client_init.return_value = None
        mock_collection.return_value = MagicMock()

        token = self.gen_token_employee(role=Role.ADMIN, client_id='invalid-client-id', assigned=True)
        headers = {'X-Apigateway-Api-Userinfo': self.encode_token(token)}

        mock_client_repo = MagicMock()
        mock_client_repo.get.return_value = None

        with self.app.container.client_repo.override(mock_client_repo):
            resp = self.test_client.get('/api/v1/invoice', headers=headers)

        self.assertEqual(resp.status_code, 404)
        self.assertIn('Client not found', resp.get_json()['message'])

    @patch('google.cloud.firestore_v1.client.Client.__init__', return_value=None)
    @patch('google.cloud.firestore_v1.client.Client.collection')
    def test_get_invoice_invalid_token(self, mock_collection: Any, mock_client_init: Any) -> None:  # noqa: ANN401
        mock_client_init.return_value = None
        mock_collection.return_value = MagicMock()

        headers = {'X-Apigateway-Api-Userinfo': 'invalid-token'}

        resp = self.test_client.get('/api/v1/invoice', headers=headers)

        self.assertEqual(resp.status_code, 401)
        self.assertIn('Token is missing', resp.get_json()['message'])
