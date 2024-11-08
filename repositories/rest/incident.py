import logging

from repositories import IncidentRepository

from .util import TokenProvider


class RestIncidentRepository(IncidentRepository):
    def __init__(self, base_url: str, token_provider: TokenProvider | None) -> None:
        self.base_url = base_url
        self.token_provider = token_provider
        self.logger = logging.getLogger(self.__class__.__name__)
