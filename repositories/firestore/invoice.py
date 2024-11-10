import logging
from collections.abc import Generator
from dataclasses import asdict
from enum import Enum
from typing import Any, cast

import dacite
from google.cloud.firestore import Client as FirestoreClient  # type: ignore[import-untyped]
from google.cloud.firestore_v1 import DocumentSnapshot

from models import Invoice, Month
from repositories import InvoiceRepository


class FirestoreInvoiceRepository(InvoiceRepository):
    def __init__(self, database: str) -> None:
        self.db = FirestoreClient(database=database)
        self.logger = logging.getLogger(self.__class__.__name__)

    def doc_to_invoice(self, doc: DocumentSnapshot) -> Invoice:
        return dacite.from_dict(
            data_class=Invoice,
            data={
                **cast(dict[str, Any], doc.to_dict()),
                'id': doc.id,
            },
            config=dacite.Config(cast=[Enum]),
        )

    def get(self, invoice_id: str) -> Invoice | None:
        doc = self.db.collection('invoices').document(invoice_id).get()

        if not doc.exists:
            return None

        return self.doc_to_invoice(doc)

    def get_by_client_and_month(self, client_id: str, month: Month, year: int) -> Invoice | None:
        docs = (
            self.db.collection('invoices')
            .where('client_id', '==', client_id)
            .where('billing_month', '==', month.value)
            .where('billing_year', '==', year)
            .get()
        )

        if len(docs) == 0:
            return None

        if len(docs) > 1:
            self.logger.error('Multiple invoices found for client %s for %s %d', client_id, month, year)
            return None

        return self.doc_to_invoice(cast(DocumentSnapshot, docs[0]))

    def create(self, invoice: Invoice) -> None:
        invoice_dict = asdict(invoice)
        del invoice_dict['id']

        invoice_ref = self.db.collection('invoices').document(invoice.id)
        invoice_ref.set(invoice_dict)

    def update(self, invoice: Invoice) -> None:
        invoice_dict = asdict(invoice)

        del invoice_dict['id']

        self.db.collection('invoices').document(invoice.id).set(invoice_dict)

    def get_all(self) -> Generator[Invoice, None, None]:
        stream: Generator[DocumentSnapshot, None, None] = self.db.collection('invoices').stream()
        for doc in stream:
            yield self.doc_to_invoice(doc)
