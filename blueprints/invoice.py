from dependency_injector.wiring import Provide
from flask import Blueprint, Response
from flask.views import MethodView

from containers import Container
from repositories import IncidentRepository

from .util import class_route

blp = Blueprint('Invoice', __name__)


@class_route(blp, '/api/v1/invoice')
class GetInvoice(MethodView):
    init_every_request = False

    def get(
        self,
        incident_repo: IncidentRepository = Provide[Container.incidentquery_repo],
    ) -> Response:
        # Falta la lógica para obtener la factura
        pass
