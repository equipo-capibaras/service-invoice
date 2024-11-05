from models import Client


class ClientRepository:
    def get(self, client_id: str) -> Client | None:
        raise NotImplementedError  # pragma: no cover
