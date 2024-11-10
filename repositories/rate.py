from models import Rate


class RateRepository:
    def get_by_id(self, rate_id: str) -> Rate | None:
        raise NotImplementedError  # pragma: no cover

    def get_by_client_and_plan(self, client_id: str, plan: str) -> Rate | None:
        raise NotImplementedError  # pragma: no cover

    def create(self, rate: Rate) -> None:
        raise NotImplementedError  # pragma: no cover

    def update(self, rate: Rate) -> None:
        raise NotImplementedError  # pragma: no cover

    def delete_all(self) -> None:
        raise NotImplementedError  # pragma: no cover
