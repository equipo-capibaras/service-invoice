import contextlib
import os
from dataclasses import asdict
from datetime import datetime
from typing import cast
from unittest import skipUnless

import requests
from faker import Faker
from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore import Client as FirestoreClient  # type: ignore[import-untyped]
from unittest_parametrize import ParametrizedTestCase, parametrize

from models import Invoice, Month
from repositories.firestore import FirestoreInvoiceRepository

FIRESTORE_DATABASE = '(default)'

@skipUnless('FIRESTORE_EMULATOR_HOST' in os.environ, 'Firestore emulator not available')
class TestInvoiceRepository(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()

        # Reset Firestore emulator before each test
        requests.delete(
            f'http://{os.environ["FIRESTORE_EMULATOR_HOST"]}/emulator/v1/projects/google-cloud-firestore-emulator/databases/{FIRESTORE_DATABASE}/documents',
            timeout=5,
        )

        self.repo = FirestoreInvoiceRepository(FIRESTORE_DATABASE)
        self.client = FirestoreClient(database=FIRESTORE_DATABASE)

    def add_random_invoices(self, n: int) -> list[Invoice]:
        invoices: list[Invoice] = []

        # Add n invoices to Firestore
        for _ in range(n):
            invoice = Invoice(
                id=cast(str, self.faker.uuid4()),
                client_id=cast(str, self.faker.uuid4()),
                rate_id=cast(str, self.faker.uuid4()),
                generation_date=self.faker.date_time_this_year(),
                billing_month=self.faker.random_element(list(Month)),
                billing_year=int(self.faker.year()),
                payment_due_date=datetime.now(),
                total_incidents_web=self.faker.random_int(min=0, max=100),
                total_incidents_mobile=self.faker.random_int(min=0, max=100),
                total_incidents_email=self.faker.random_int(min=0, max=100),
            )

            invoices.append(invoice)
            invoice_dict = asdict(invoice)
            del invoice_dict['id']
            self.client.collection('invoices').document(invoice.id).set(invoice_dict)

        return invoices

    def test_get_existing_invoice(self) -> None:
        invoice = self.add_random_invoices(1)[0]

        invoice_repo = self.repo.get(invoice.id)

        self.assertEqual(invoice_repo, invoice)

    def test_get_missing_invoice(self) -> None:
        invoice_repo = self.repo.get(cast(str, self.faker.uuid4()))

        self.assertIsNone(invoice_repo)

    def test_get_by_client_and_month(self) -> None:
        invoice = self.add_random_invoices(1)[0]

        invoice_repo = self.repo.get_by_client_and_month(invoice.client_id, invoice.month, invoice.year)

        self.assertEqual(invoice_repo, invoice)

    def test_get_by_client_and_month_not_found(self) -> None:
        client_id = cast(str, self.faker.uuid4())
        month = self.faker.random_element(list(Month))
        year = self.faker.year()

        invoice_repo = self.repo.get_by_client_and_month(client_id, month, year)

        self.assertIsNone(invoice_repo)

    def test_create_invoice(self) -> None:
        invoice = Invoice(
            id=cast(str, self.faker.uuid4()),
            client_id=cast(str, self.faker.uuid4()),
            rate_id=cast(str, self.faker.uuid4()),
            generation_date=self.faker.date_time_this_year(),
            billing_month=self.faker.random_element(list(Month)),
            billing_year=int(self.faker.year()),
            payment_due_date=datetime.now(),
            total_incidents_web=self.faker.random_int(min=0, max=100),
            total_incidents_mobile=self.faker.random_int(min=0, max=100),
            total_incidents_email=self.faker.random_int(min=0, max=100),
        )

        self.repo.create(invoice)

        doc = self.client.collection('invoices').document(invoice.id).get()
        self.assertTrue(doc.exists)
        invoice_dict = asdict(invoice)
        del invoice_dict['id']
        self.assertEqual(doc.to_dict(), invoice_dict)

    def test_update_invoice(self) -> None:
        invoice = self.add_random_invoices(1)[0]

        # Update some fields in the invoice
        invoice.total_web_incidents = self.faker.random_int(min=0, max=100)
        invoice.total_mobile_incidents = self.faker.random_int(min=0, max=100)
        invoice.total_email_incidents = self.faker.random_int(min=0, max=100)

        self.repo.update(invoice)

        doc = self.client.collection('invoices').document(invoice.id).get()
        self.assertTrue(doc.exists)
        invoice_dict = asdict(invoice)
        del invoice_dict['id']
        self.assertEqual(doc.to_dict(), invoice_dict)

    def test_get_all_invoices(self) -> None:
        invoices = self.add_random_invoices(5)

        retrieved_invoices = list(self.repo.get_all())

        for invoice in invoices:
            self.assertIn(invoice, retrieved_invoices)
