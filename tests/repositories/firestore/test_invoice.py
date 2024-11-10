import os
import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import cast
from unittest import skipUnless

import requests
from faker import Faker
from google.cloud.firestore import Client as FirestoreClient  # type: ignore[import-untyped]
from unittest_parametrize import ParametrizedTestCase

from models import Invoice, Month
from repositories.firestore import FirestoreInvoiceRepository

FIRESTORE_DATABASE = '(default)'


@skipUnless('FIRESTORE_EMULATOR_HOST' in os.environ, 'Firestore emulator not available')
class TestInvoiceRepository(ParametrizedTestCase):
    def setUp(self) -> None:
        self.faker = Faker()

        requests.delete(
            f'http://{os.environ["FIRESTORE_EMULATOR_HOST"]}/emulator/v1/projects/google-cloud-firestore-emulator/databases/{FIRESTORE_DATABASE}/documents',
            timeout=5,
        )

        self.repo = FirestoreInvoiceRepository(FIRESTORE_DATABASE)
        self.client = FirestoreClient(database=FIRESTORE_DATABASE)

    def get_one_random_invoice(self, client_id: str | None = None, billing_year: int | None = None) -> Invoice:
        if not client_id:
            client_id = cast(str, self.faker.uuid4())

        if not billing_year:
            billing_year = int(self.faker.year())

        return Invoice(
            id=str(uuid.uuid4()),
            client_id=client_id,
            rate_id=cast(str, self.faker.uuid4()),
            generation_date=self.faker.date_time_this_year(),
            billing_month=Month.NOVEMBER.value,
            billing_year=billing_year,
            payment_due_date=self.faker.past_datetime(start_date='-30d', tzinfo=UTC),
            total_incidents_web=self.faker.random_int(min=0, max=100),
            total_incidents_mobile=self.faker.random_int(min=0, max=100),
            total_incidents_email=self.faker.random_int(min=0, max=100),
        )

    def add_random_invoices(self, n: int, client_id: str | None = None, billing_year: int | None = None) -> list[Invoice]:
        invoices = []
        for _ in range(n):
            invoice = self.get_one_random_invoice(client_id, billing_year)
            invoices.append(invoice)
            invoice_dict = asdict(invoice)
            del invoice_dict['id']
            self.client.collection('invoices').document(invoice.id).set(invoice_dict)
        return invoices

    def convert_datetime_fields(self, invoice: Invoice) -> Invoice:
        if hasattr(invoice.generation_date, 'timestamp'):
            invoice.generation_date = datetime.fromtimestamp(
                invoice.generation_date.timestamp(), tz=invoice.generation_date.tzinfo
            )
        if hasattr(invoice.payment_due_date, 'timestamp'):
            invoice.payment_due_date = datetime.fromtimestamp(
                invoice.payment_due_date.timestamp(), tz=invoice.payment_due_date.tzinfo
            )
        return invoice

    def normalize_datetime(self, dt: datetime) -> datetime:
        return dt.replace(tzinfo=UTC) if not hasattr(dt, 'nanosecond') else dt.replace(tzinfo=UTC)

    def test_doc_to_invoice(self) -> None:
        invoice = self.get_one_random_invoice()
        invoice_dict = asdict(invoice)
        del invoice_dict['id']

        doc_ref = self.client.collection('invoices').document(invoice.id)
        doc_ref.set(invoice_dict)
        doc_snapshot = doc_ref.get()

        result = self.repo.doc_to_invoice(doc_snapshot)

        result.generation_date = self.normalize_datetime(result.generation_date)
        result.payment_due_date = self.normalize_datetime(result.payment_due_date)
        invoice.generation_date = self.normalize_datetime(invoice.generation_date)
        invoice.payment_due_date = self.normalize_datetime(invoice.payment_due_date)

        result.billing_month = Month(result.billing_month) if isinstance(result.billing_month, str) else result.billing_month
        invoice.billing_month = Month(invoice.billing_month)

        self.assertEqual(result, invoice)

    def test_get_existing_invoice(self) -> None:
        invoice = self.add_random_invoices(1)[0]

        result = self.repo.get(invoice.id)

        if result is not None:
            result = self.convert_datetime_fields(result)
            invoice = self.convert_datetime_fields(invoice)
            self.assertEqual(result.id, invoice.id)

    def test_get_missing_invoice(self) -> None:
        result = self.repo.get(str(uuid.uuid4()))
        self.assertIsNone(result)

    def test_get_by_client_and_month(self) -> None:
        invoice = self.add_random_invoices(1)[0]

        doc = self.client.collection('invoices').document(invoice.id).get()
        self.assertTrue(doc.exists)

        result = self.repo.get_by_client_and_month(invoice.client_id, Month.NOVEMBER, invoice.billing_year)

        self.assertIsNotNone(result, 'No se encontró el invoice con los datos proporcionados.')

    def test_get_by_client_and_month_not_found(self) -> None:
        client_id = str(uuid.uuid4())
        month: Month = self.faker.random_element(list(Month))
        year = int(self.faker.year())

        result = self.repo.get_by_client_and_month(client_id, month, year)
        self.assertIsNone(result)

    def test_create_invoice(self) -> None:
        invoice = self.get_one_random_invoice()

        self.repo.create(invoice)

        doc = self.client.collection('invoices').document(invoice.id).get()
        self.assertTrue(doc.exists)

        doc_data = doc.to_dict()
        doc_data['billing_month'] = Month(doc_data['billing_month'])
        doc_data['generation_date'] = doc_data['generation_date'].replace(tzinfo=UTC)
        doc_data['payment_due_date'] = doc_data['payment_due_date'].replace(tzinfo=UTC)

        invoice_dict = asdict(invoice)
        del invoice_dict['id']
        invoice_dict['generation_date'] = invoice_dict['generation_date'].replace(tzinfo=UTC)
        invoice_dict['payment_due_date'] = invoice_dict['payment_due_date'].replace(tzinfo=UTC)

        self.assertEqual(doc_data, invoice_dict)

    def test_update_invoice(self) -> None:
        invoice = self.add_random_invoices(1)[0]

        invoice.total_incidents_web = self.faker.random_int(min=0, max=100)
        invoice.total_incidents_mobile = self.faker.random_int(min=0, max=100)
        invoice.total_incidents_email = self.faker.random_int(min=0, max=100)

        self.repo.update(invoice)

        doc = self.client.collection('invoices').document(invoice.id).get()
        self.assertTrue(doc.exists)

        invoice_dict = asdict(invoice)
        del invoice_dict['id']

        doc_data = doc.to_dict()

        self.assertEqual(doc_data['total_incidents_web'], invoice_dict['total_incidents_web'])
        self.assertEqual(doc_data['total_incidents_mobile'], invoice_dict['total_incidents_mobile'])
        self.assertEqual(doc_data['total_incidents_email'], invoice_dict['total_incidents_email'])

    def test_get_all_invoices(self) -> None:
        invoices = self.add_random_invoices(5)
        retrieved_invoices = list(self.repo.get_all())

        for invoice in invoices:
            invoice.generation_date = self.normalize_datetime(invoice.generation_date)
            invoice.payment_due_date = self.normalize_datetime(invoice.payment_due_date)

        for retrieved_invoice in retrieved_invoices:
            retrieved_invoice.generation_date = self.normalize_datetime(retrieved_invoice.generation_date)
            retrieved_invoice.payment_due_date = self.normalize_datetime(retrieved_invoice.payment_due_date)

        for invoice in invoices:
            self.assertIn(invoice, retrieved_invoices)

    def test_multiple_invoices_error(self) -> None:
        client_id = cast(str, self.faker.uuid4())
        billing_year = int(self.faker.year())

        invoices = self.add_random_invoices(2, client_id=client_id, billing_year=billing_year)

        result = self.repo.get_by_client_and_month(invoices[0].client_id, Month.NOVEMBER, invoices[0].billing_year)

        self.assertIsNone(result)
