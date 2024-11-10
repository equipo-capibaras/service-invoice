from models import Incident


class IncidentRepository:
    def get_incidents_by_client_id(self, client_id: str) -> list[Incident] | None:
        raise NotImplementedError  # pragma: no cover
