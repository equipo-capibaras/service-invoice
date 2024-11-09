from datetime import datetime, UTC
from typing import Any

from dependency_injector.wiring import Provide
from flask import Blueprint, Response
from flask.views import MethodView

from containers import Container
from repositories import RateRepository, InvoiceRepository
from .util import class_route, json_response, requires_token, error_response
from models import Role, Month

blp = Blueprint('Invoice', __name__)

def get_billing_period() -> tuple[Month, int]:
    now = datetime.now(UTC)
    billing_month = Month(now.month - 1) if now.month > 1 else Month(12)
    billing_year = now.year if now.month > 1 else now.year - 1
    return billing_month, billing_year

@class_route(blp, '/api/v1/invoice')
class GetInvoice(MethodView):
    init_every_request = False

    @requires_token
    def get(
        self,
        token: dict[str, Any],
        rate_repo: RateRepository = Provide[Container.rate_repo],
        invoice_repo: InvoiceRepository = Provide[Container.invoice_repo],
        incident_repo: InvoiceRepository = Provide[Container.incidentquery_repo],
        client_repo: InvoiceRepository = Provide[Container.client_repo],
    ) -> Response:
        # 1. Validate token role is ADMIN and get client_id
        if token['role'] != Role.ADMIN.value:
            return error_response('Forbidden: You do not have access to this resource.', 403)

        client_id = token['cid']

        # 2. Obtain month and year for the invoice (last month)
        billing_month, billing_year = get_billing_period()

        # 3. Get invoice from repository if exists by client_id and billing_month
