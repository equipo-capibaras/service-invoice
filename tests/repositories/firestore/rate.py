import os
from dataclasses import asdict
from typing import cast
from unittest import skipUnless

import requests
from faker import Faker
from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore import Client as FirestoreClient  # type: ignore[import-untyped]
from unittest_parametrize import ParametrizedTestCase

from models import Plan, Rate
from repositories.firestore import FirestoreRateRepository

FIRESTORE_DATABASE = '(default)'


@skipUnless('FIRESTORE_EMULATOR_HOST' in os.environ, 'Firestore emulator not available')
class TestRateRepository(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()

        # Reset Firestore emulator before each test
        requests.delete(
            f'http://{os.environ["FIRESTORE_EMULATOR_HOST"]}/emulator/v1/projects/google-cloud-firestore-emulator/databases/{FIRESTORE_DATABASE}/documents',
            timeout=5,
        )

        self.repo = FirestoreRateRepository(FIRESTORE_DATABASE)
        self.client = FirestoreClient(database=FIRESTORE_DATABASE)

    def add_random_rates(self, n: int) -> list[Rate]:
        rates: list[Rate] = []

        # Add n rates to Firestore
        for _ in range(n):
            rate = Rate(
                id=cast(str, self.faker.uuid4()),
                plan=self.faker.random_element(list(Plan)),
                client_id=cast(str, self.faker.uuid4()),
                fixed_cost=self.faker.pyfloat(min_value=1.0, max_value=10.0),
                cost_per_incident_web=self.faker.pyfloat(min_value=0.01, max_value=1.0),
                cost_per_incident_mobile=self.faker.pyfloat(min_value=0.01, max_value=1.0),
                cost_per_incident_email=self.faker.pyfloat(min_value=0.01, max_value=1.0),
            )

            rates.append(rate)
            rate_dict = asdict(rate)
            del rate_dict['id']
            self.client.collection('rates').document(rate.id).set(rate_dict)

        return rates

    def test_create_rate(self) -> None:
        rate = Rate(
            id=cast(str, self.faker.uuid4()),
            plan=self.faker.random_element(list(Plan)),
            client_id=cast(str, self.faker.uuid4()),
            fixed_cost=self.faker.pyfloat(min_value=1.0, max_value=10.0),
            cost_per_incident_web=self.faker.pyfloat(min_value=0.01, max_value=1.0),
            cost_per_incident_mobile=self.faker.pyfloat(min_value=0.01, max_value=1.0),
            cost_per_incident_email=self.faker.pyfloat(min_value=0.01, max_value=1.0),
        )

        self.repo.create(rate)

        doc = self.client.collection('rates').document(rate.id).get()
        self.assertTrue(doc.exists)
        rate_dict = asdict(rate)
        del rate_dict['id']
        self.assertEqual(doc.to_dict(), rate_dict)

    def test_get_rate_by_id(self) -> None:
        rate = self.add_random_rates(1)[0]

        rate_repo = self.repo.get_by_id(rate.id)

        self.assertEqual(rate_repo, rate)

    def test_get_rate_by_client_and_plan(self) -> None:
        rate = self.add_random_rates(1)[0]

        rate_repo = self.repo.get_by_client_and_plan(rate.client_id, rate.plan.value)

        self.assertEqual(rate_repo, rate)

    def test_get_rate_by_client_and_plan_not_found(self) -> None:
        rate_repo = self.repo.get_by_client_and_plan(cast(str, self.faker.uuid4()), Plan.EMPRENDEDOR.value)

        self.assertIsNone(rate_repo)

    def test_update_rate(self) -> None:
        rate = self.add_random_rates(1)[0]

        rate.fixed_cost = self.faker.pyfloat(min_value=1.0, max_value=10.0)
        self.repo.update(rate)

        doc = self.client.collection('rates').document(rate.id).get()
        self.assertTrue(doc.exists)
        rate_dict = asdict(rate)
        del rate_dict['id']
        self.assertEqual(doc.to_dict(), rate_dict)

    def test_create_duplicate_rate(self) -> None:
        rate = Rate(
            id=cast(str, self.faker.uuid4()),
            plan=self.faker.random_element(list(Plan)),
            client_id=cast(str, self.faker.uuid4()),
            fixed_cost=self.faker.pyfloat(min_value=1.0, max_value=10.0),
            cost_per_incident_web=self.faker.pyfloat(min_value=0.01, max_value=1.0),
            cost_per_incident_mobile=self.faker.pyfloat(min_value=0.01, max_value=1.0),
            cost_per_incident_email=self.faker.pyfloat(min_value=0.01, max_value=1.0),
        )

        self.repo.create(rate)

        with self.assertRaises(AlreadyExists):
            self.repo.create(rate)

    def test_get_rate_not_found(self) -> None:
        rate_repo = self.repo.get_by_id(cast(str, self.faker.uuid4()))

        self.assertIsNone(rate_repo)
