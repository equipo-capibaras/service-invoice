from unittest.mock import Mock

from unittest_parametrize import ParametrizedTestCase, parametrize

from app import create_app
from repositories import InvoiceRepository


class TestReset(ParametrizedTestCase):
    API_ENDPOINT = '/api/v1/reset/invoice'

    def setUp(self) -> None:
        self.app = create_app()
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        self.app.container.unwire()

    @parametrize(
        'arg',
        [
            (None,),
            ('true',),
            ('false',),
            ('foo',),
        ],
    )
    def test_reset(self, arg: str | None) -> None:
        invoice_repo_mock = Mock(InvoiceRepository)

        with self.app.container.invoice_repo.override(invoice_repo_mock):
            resp = self.client.post(self.API_ENDPOINT + (f'?demo={arg}' if arg is not None else ''))

        invoice_repo_mock.delete_all.assert_called_once()

        self.assertEqual(resp.status_code, 200)
