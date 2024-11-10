import json
import responses
import base64
import json
from datetime import datetime, UTC
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch
from faker import Faker

from app import create_app
from models import Month, Client, Rate, Incident, Invoice, Channel, Plan, Role
from repositories import ClientRepository, IncidentRepository, InvoiceRepository, RateRepository
from blueprints.invoice import (
    get_billing_period,
    create_invoice,
    get_incidents_by_client_and_month,
    create_rate,
    invoice_result_to_dict,
)


class TestInvoice(TestCase):
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
            plan="basic",
            client_id=str(self.client_id),
            fixed_cost=100.0,
            cost_per_incident_web=10.0,
            cost_per_incident_mobile=15.0,
            cost_per_incident_email=5.0,
        )
        self.client = Client(id=str(self.client_id), plan="basic", name="Test Client")

    def gen_token_employee(self, *, client_id: str | None, role: Role, assigned: bool) -> dict[str, any]:
        return {
            'sub': str(self.faker.uuid4()),
            'cid': client_id,
            'role': role.value,
            'aud': ('' if assigned else 'unassigned_') + role.value,
        }

    def encode_token(self, token: dict[str, any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(token).encode()).decode()

    def generate_headers(self, token: dict[str, any]) -> dict[str, str]:
        token_encoded = self.encode_token(token)
        return {'X-Apigateway-Api-Userinfo': token_encoded}

    def get_request(self, url: str, headers: dict[str, str]) -> Mock:
        return self.test_client.get(url, headers=headers)

    def setup_firestore_mocks(self, mock_client_init, mock_collection):
        mock_client_init.return_value = None
        mock_collection.return_value = MagicMock()

    def test_get_billing_period(self) -> None:
        billing_month, billing_year = get_billing_period()
        now = datetime.now(UTC)
        expected_month = Month.from_int(now.month - 1 if now.month > 1 else 12)
        expected_year = now.year if now.month > 1 else now.year - 1

        self.assertEqual(billing_month, expected_month)
        self.assertEqual(billing_year, expected_year)

    def test_create_rate(self) -> None:
        self.client.plan = "EMPRENDEDOR"
        self.rate_repo.create = MagicMock()

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
                history=[MagicMock(date=datetime(2024, 11, 15, tzinfo=UTC))]
            ),
            Incident(
                id=str(self.faker.uuid4()),
                channel=Channel.MOBILE,
                history=[MagicMock(date=history_date)],
                name=self.faker.sentence(),
                reported_by=str(self.faker.uuid4()),
                created_by=str(self.faker.uuid4()),
                assigned_to=str(self.faker.uuid4()),
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

        self.assertEqual(result['billing_month'], "November")
        self.assertEqual(result['billing_year'], 2024)
        self.assertEqual(result['client_id'], self.client.id)
        self.assertEqual(result['total_cost'], 285.0)

    @patch("google.cloud.firestore_v1.client.Client.__init__", return_value=None)
    @patch("google.cloud.firestore_v1.client.Client.collection")
    def test_get_invoice_forbidden(self, mock_collection, mock_client_init):
        self.setup_firestore_mocks(mock_client_init, mock_collection)
        token = self.gen_token_employee(role=Role.AGENT, client_id="test-client-id", assigned=True)
        headers = self.generate_headers(token)

        resp = self.get_request('/api/v1/invoice', headers)

        self.assertEqual(resp.status_code, 403)
        self.assertIn("Forbidden", resp.get_json()["message"])

    @patch("google.cloud.firestore_v1.client.Client.__init__", return_value=None)
    @patch("google.cloud.firestore_v1.client.Client.collection")
    def test_get_invoice_client_not_found(self, mock_collection, mock_client_init):
        self.setup_firestore_mocks(mock_client_init, mock_collection)
        token = self.gen_token_employee(role=Role.ADMIN, client_id="invalid-client-id", assigned=True)
        headers = self.generate_headers(token)

        mock_client_repo = MagicMock()
        mock_client_repo.get.return_value = None

        with self.app.container.client_repo.override(mock_client_repo):
            resp = self.get_request('/api/v1/invoice', headers)

        self.assertEqual(resp.status_code, 404)
        self.assertIn("Client not found", resp.get_json()["message"])

    @patch("google.cloud.firestore_v1.client.Client.__init__", return_value=None)
    @patch("google.cloud.firestore_v1.client.Client.collection")
    def test_get_invoice_invalid_token(self, mock_collection, mock_client_init):
        self.setup_firestore_mocks(mock_client_init, mock_collection)
        headers = {'X-Apigateway-Api-Userinfo': "invalid-token"}

        resp = self.get_request('/api/v1/invoice', headers)

        self.assertEqual(resp.status_code, 401)
        self.assertIn("Token is missing", resp.get_json()["message"])

    @patch("google.cloud.firestore_v1.client.Client.__init__", return_value=None)
    @patch("google.cloud.firestore_v1.client.Client.collection")
    def test_get_invoice_invalid_role(self, mock_collection, mock_client_init):
        mock_client_init.return_value = None
        mock_collection.return_value = MagicMock()

        token = self.gen_token_employee(role=Role.AGENT, client_id=str(self.client_id), assigned=True)
        headers = {'X-Apigateway-Api-Userinfo': self.encode_token(token)}

        resp = self.test_client.get('/api/v1/invoice', headers=headers)

        self.assertEqual(resp.status_code, 403)
        self.assertIn("Forbidden", resp.get_json()["message"])

    @patch("google.cloud.firestore_v1.client.Client.__init__", return_value=None)
    @patch("google.cloud.firestore_v1.client.Client.collection")
    def test_get_invoice_client_not_found(self, mock_collection, mock_client_init):
        mock_client_init.return_value = None
        mock_collection.return_value = MagicMock()

        token = self.gen_token_employee(role=Role.ADMIN, client_id="invalid-client-id", assigned=True)
        headers = {'X-Apigateway-Api-Userinfo': self.encode_token(token)}

        mock_client_repo = MagicMock()
        mock_client_repo.get.return_value = None

        with self.app.container.client_repo.override(mock_client_repo):
            resp = self.test_client.get('/api/v1/invoice', headers=headers)

        self.assertEqual(resp.status_code, 404)
        self.assertIn("Client not found", resp.get_json()["message"])

    @patch("google.cloud.firestore_v1.client.Client.__init__", return_value=None)
    @patch("google.cloud.firestore_v1.client.Client.collection")
    def test_get_invoice_rate_not_found(self, mock_collection, mock_client_init):
        mock_client_init.return_value = None
        mock_collection.return_value = MagicMock()

        token = self.gen_token_employee(role=Role.ADMIN, client_id=str(self.client_id), assigned=True)
        headers = {'X-Apigateway-Api-Userinfo': self.encode_token(token)}

        mock_client_repo = MagicMock()
        mock_client_repo.get.return_value = self.client

        mock_rate_repo = MagicMock()
        mock_rate_repo.get_by_client_and_plan.return_value = None

        with self.app.container.client_repo.override(mock_client_repo), \
            self.app.container.rate_repo.override(mock_rate_repo):
            resp = self.test_client.get('/api/v1/invoice', headers=headers)

        self.assertEqual(resp.status_code, 500)



    @patch("google.cloud.firestore_v1.client.Client.__init__", return_value=None)
    @patch("google.cloud.firestore_v1.client.Client.collection")
    def test_get_invoice_rate_creation_failed(self, mock_collection, mock_client_init):
        mock_client_init.return_value = None
        mock_collection.return_value = MagicMock()

        token = self.gen_token_employee(role=Role.ADMIN, client_id=str(self.client_id), assigned=True)
        headers = {'X-Apigateway-Api-Userinfo': self.encode_token(token)}

        mock_client_repo = MagicMock()
        self.client.plan = Plan.EMPRENDEDOR.value
        mock_client_repo.get.return_value = self.client

        mock_rate_repo = MagicMock()
        mock_rate_repo.get_by_client_and_plan.return_value = None
        mock_rate_repo.create.side_effect = Exception("Failed to create rate")

        with self.app.container.client_repo.override(mock_client_repo), \
            self.app.container.rate_repo.override(mock_rate_repo):

            resp = self.test_client.get('/api/v1/invoice', headers=headers)

        self.assertEqual(resp.status_code, 500)

        if resp.get_json() is not None:
            self.assertIn("Rate could not be determined", resp.get_json().get("message", ""))


