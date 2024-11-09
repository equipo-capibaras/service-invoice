from dependency_injector import providers
from dependency_injector.containers import DeclarativeContainer, WiringConfiguration
from gcp_microservice_utils import access_token_provider

from repositories.firestore import FirestoreInvoiceRepository, FirestoreRateRepository
from repositories.rest import RestClientRepository, RestIncidentRepository


class Container(DeclarativeContainer):
    wiring_config = WiringConfiguration(packages=['blueprints'])
    config = providers.Configuration()

    access_token = providers.Callable(access_token_provider)

    rate_repo = providers.ThreadSafeSingleton(FirestoreRateRepository, database=config.firestore.database)
    invoice_repo = providers.ThreadSafeSingleton(FirestoreInvoiceRepository, database=config.firestore.database)

    client_repo = providers.ThreadSafeSingleton(
        RestClientRepository,
        base_url=config.svc.client.url,
        token_provider=config.svc.client.token_provider,
    )

    incidentquery_repo = providers.ThreadSafeSingleton(
        RestIncidentRepository,
        base_url=config.svc.incidentquery.url,
        token_provider=config.svc.incidentquery.token_provider,
    )
