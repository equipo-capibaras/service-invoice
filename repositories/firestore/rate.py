import logging
from collections.abc import Generator  # pragma: no cover
from dataclasses import asdict
from enum import Enum
from typing import Any, cast

import dacite
from google.cloud.firestore import Client as FirestoreClient  # type: ignore[import-untyped]
from google.cloud.firestore_v1 import DocumentSnapshot, Query
from google.cloud.firestore_v1.base_query import FieldFilter

from models import Rate
from repositories import RateRepository


class FirestoreRateRepository(RateRepository):
    def __init__(self, database: str) -> None:
        self.db = FirestoreClient(database=database)
        self.logger = logging.getLogger(self.__class__.__name__)

    def doc_to_rate(self, doc: DocumentSnapshot) -> Rate:
        return dacite.from_dict(
            data_class=Rate,
            data={
                **cast(dict[str, Any], doc.to_dict()),
                'id': doc.id,
            },
            config=dacite.Config(cast=[Enum]),
        )

    def get_by_id(self, rate_id: str) -> Rate | None:
        rate_doc = self.db.collection('rates').document(rate_id).get()

        if not rate_doc.exists:
            return None

        return self.doc_to_rate(rate_doc)

    def get_by_client_and_plan(self, client_id: str, plan: str) -> Rate | None:
        query: Query = (
            self.db.collection('rates')
            .where(filter=FieldFilter('client_id', '==', client_id))  # type: ignore[no-untyped-call]
            .where(filter=FieldFilter('plan', '==', plan))  # type: ignore[no-untyped-call]
        )

        docs = query.get()

        if len(docs) == 0:
            return None

        if len(docs) > 1:
            self.logger.error('Multiple rates found with client_id %s and plan %s', client_id, plan)
            return None

        return self.doc_to_rate(cast(DocumentSnapshot, docs[0]))

    def create(self, rate: Rate) -> None:
        rate_dict = asdict(rate)
        del rate_dict['id']

        self.db.collection('rates').document(rate.id).create(rate_dict)

    def update(self, rate: Rate) -> None:
        rate_dict = asdict(rate)
        del rate_dict['id']

        self.db.collection('rates').document(rate.id).set(rate_dict)

    def delete_all(self) -> None:
        stream: Generator[DocumentSnapshot, None, None] = self.db.collection('rates').stream()
        for rate in stream:
            cast(DocumentSnapshot, rate.reference).delete()
