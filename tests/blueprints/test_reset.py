from unittest_parametrize import ParametrizedTestCase, parametrize

from app import create_app


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
        resp = self.client.post(self.API_ENDPOINT + (f'?demo={arg}' if arg is not None else ''))

        self.assertEqual(resp.status_code, 200)
