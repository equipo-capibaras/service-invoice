import os
import uuid
from dataclasses import asdict
from unittest import skipUnless

from faker import Faker
from google.cloud.firestore import Client as FirestoreClient  # type: ignore[import-untyped]
from unittest_parametrize import ParametrizedTestCase

from models import Plan, Rate
from repositories.firestore import FirestoreRateRepository

FIRESTORE_DATABASE = '(default)'


@skipUnless('FIRESTORE_EMULATOR_HOST' in os.environ, 'Firestore emulator not available')
class TestFirestoreRateRepository(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()
        self.repo = FirestoreRateRepository(FIRESTORE_DATABASE)
        self.client = FirestoreClient(database=FIRESTORE_DATABASE)

    def get_one_random_rate(self, client_id: str | None = None, plan: Plan | None = None) -> Rate:
        if not client_id:
            client_id = str(uuid.uuid4())

        if not plan:
            plan = Plan.EMPRENDEDOR

        return Rate(
            id=str(uuid.uuid4()),
            client_id=client_id,
            plan=plan,
            fixed_cost=self.faker.random_number(),
            cost_per_incident_web=self.faker.random_number(),
            cost_per_incident_mobile=self.faker.random_number(),
            cost_per_incident_email=self.faker.random_number(),
        )

    def add_random_rates(self, n: int, client_id: str | None = None, plan: Plan | None = None) -> list[Rate]:
        rates = []
        for _ in range(n):
            rate = self.get_one_random_rate(client_id, plan)
            rates.append(rate)
            rate_dict = asdict(rate)
            del rate_dict['id']
            self.client.collection('rates').document(rate.id).set(rate_dict)
        return rates

    def test_get_by_id(self) -> None:
        rate = self.add_random_rates(1)[0]

        result = self.repo.get_by_id(rate.id)

        if result is not None:
            self.assertEqual(result.id, rate.id)

    def test_get_by_id_not_found(self) -> None:
        result = self.repo.get_by_id(str(uuid.uuid4()))
        self.assertIsNone(result)

    def test_get_by_client_and_plan(self) -> None:
        rate = self.add_random_rates(1, client_id='client123', plan=Plan.EMPRENDEDOR)[0]

        result = self.repo.get_by_client_and_plan('client123', Plan.EMPRENDEDOR)

        if result is not None:
            self.assertEqual(result.id, rate.id)

    def test_get_by_client_and_plan_not_found(self) -> None:
        result = self.repo.get_by_client_and_plan('nonexistent_client', 'premium')
        self.assertIsNone(result)

    def test_create(self) -> None:
        rate = self.get_one_random_rate()

        self.repo.create(rate)

        doc = self.client.collection('rates').document(rate.id).get()
        self.assertTrue(doc.exists)

    def test_update(self) -> None:
        rate = self.add_random_rates(1)[0]
        new_fixed_cost = self.faker.random_number()
        rate.fixed_cost = new_fixed_cost

        self.repo.update(rate)

        doc = self.client.collection('rates').document(rate.id).get()
        self.assertTrue(doc.exists)
        self.assertEqual(doc.to_dict()['fixed_cost'], new_fixed_cost)

    def test_multiple_rates_error(self) -> None:
        self.add_random_rates(2, client_id='client123', plan=Plan.EMPRENDEDOR)

        result = self.repo.get_by_client_and_plan('client123', Plan.EMPRENDEDOR)
        self.assertIsNone(result)
