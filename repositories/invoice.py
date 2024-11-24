from collections.abc import Generator

from models import Invoice, Month


class InvoiceRepository:
    def get(self, invoice_id: str) -> Invoice | None:
        raise NotImplementedError  # pragma: no cover

    def get_by_client_and_month(self, client_id: str, month: Month, year: int) -> Invoice | None:
        raise NotImplementedError  # pragma: no cover

    def create(self, invoice: Invoice) -> None:
        raise NotImplementedError  # pragma: no cover

    def update(self, invoice: Invoice) -> None:
        raise NotImplementedError  # pragma: no cover

    def get_all(self) -> Generator[Invoice, None, None]:
        raise NotImplementedError  # pragma: no cover

    def delete_all(self) -> None:
        raise NotImplementedError  # pragma: no cover
