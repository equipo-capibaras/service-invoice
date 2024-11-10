from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from dependency_injector.wiring import Provide
from flask import Blueprint, Response
from flask.views import MethodView

from containers import Container
from models import Channel, Client, Incident, Invoice, Month, PlanCost, Rate, Role
from repositories import ClientRepository, IncidentRepository, InvoiceRepository, RateRepository

from .util import class_route, error_response, json_response, requires_token

blp = Blueprint('Invoice', __name__)


def get_billing_period() -> tuple[Month, int]:
    now = datetime.now(UTC)
    month_number = now.month - 1 if now.month > 1 else 12
    billing_month = Month.from_int(month_number)
    billing_year = now.year if now.month > 1 else now.year - 1
    return billing_month, billing_year


def create_invoice(
    month_year: tuple[Month, int],
    client_id: str,
    rate: Rate,
    incident_repo: IncidentRepository,
    invoice_repo: InvoiceRepository,
) -> Invoice:
    incidents = get_incidents_by_client_and_month(client_id, month_year[0], month_year[1], incident_repo)
    total_web = sum(1 for incident in incidents if incident.channel == Channel.WEB.value)
    total_mobile = sum(1 for incident in incidents if incident.channel == Channel.MOBILE.value)
    total_email = sum(1 for incident in incidents if incident.channel == Channel.EMAIL.value)

    invoice = Invoice(
        id=str(uuid4()),
        client_id=client_id,
        rate_id=rate.id,
        generation_date=datetime.now(UTC),
        billing_month=month_year[0],
        billing_year=month_year[1],
        payment_due_date=datetime(month_year[1], month_year[0].to_int(), 27, tzinfo=UTC),
        total_incidents_web=total_web,
        total_incidents_mobile=total_mobile,
        total_incidents_email=total_email,
    )

    invoice_repo.create(invoice)

    return invoice


def get_incidents_by_client_and_month(
    client_id: str, month: Month, year: int, incident_repo: IncidentRepository
) -> list[Incident]:
    incidents = incident_repo.get_incidents_by_client_id(client_id=client_id) or []
    filtered_incidents = []
    for incident in incidents:
        created_date = incident.history[0].date
        if created_date.month == month.to_int() and created_date.year == year:
            filtered_incidents.append(incident)
    return filtered_incidents


def create_rate(client: Client, rate_repo: RateRepository) -> Rate:
    plan_cost = PlanCost.get_costs(client.plan)
    rate = Rate(
        id=str(uuid4()),
        plan=client.plan,
        client_id=client.id,
        fixed_cost=plan_cost.fixed_cost,
        cost_per_incident_web=plan_cost.web_incident_cost,
        cost_per_incident_mobile=plan_cost.mobile_incident_cost,
        cost_per_incident_email=plan_cost.email_incident_cost,
    )

    rate_repo.create(rate)
    return rate


def invoice_result_to_dict(invoice: Invoice, rate: Rate, client: Client) -> dict[str, Any]:
    total_cost = (
        rate.fixed_cost
        + (rate.cost_per_incident_web * invoice.total_incidents_web)
        + (rate.cost_per_incident_mobile * invoice.total_incidents_mobile)
        + (rate.cost_per_incident_email * invoice.total_incidents_email)
    )
    return {
        'billing_month': invoice.billing_month,
        'billing_year': invoice.billing_year,
        'client_id': invoice.client_id,
        'client_name': client.name,
        'due_date': invoice.payment_due_date.isoformat(),
        'client_plan': rate.plan,
        'total_cost': total_cost,
        'fixed_cost': rate.fixed_cost,
        'total_incidents': {
            'web': invoice.total_incidents_web,
            'mobile': invoice.total_incidents_mobile,
            'email': invoice.total_incidents_email,
        },
        'unit_cost_per_incident': {
            'web': rate.cost_per_incident_web,
            'mobile': rate.cost_per_incident_mobile,
            'email': rate.cost_per_incident_email,
        },
        'total_cost_per_incident': {
            'web': rate.cost_per_incident_web * invoice.total_incidents_web,
            'mobile': rate.cost_per_incident_mobile * invoice.total_incidents_mobile,
            'email': rate.cost_per_incident_email * invoice.total_incidents_email,
        },
    }


@class_route(blp, '/api/v1/invoice')
class GetInvoice(MethodView):
    init_every_request = False

    @requires_token
    def get(
        self,
        token: dict[str, Any],
        rate_repo: RateRepository = Provide[Container.rate_repo],
        invoice_repo: InvoiceRepository = Provide[Container.invoice_repo],
        incident_repo: IncidentRepository = Provide[Container.incidentquery_repo],
        client_repo: ClientRepository = Provide[Container.client_repo],
    ) -> Response:
        # 1. Validate token role is ADMIN and get client_id
        if token['role'] != Role.ADMIN.value:
            return error_response('Forbidden: You do not have access to this resource.', 403)

        client_id = token['cid']

        # 2. Obtain month and year for the invoice (last month)
        billing_month, billing_year = get_billing_period()

        # 3. Validate client exists
        client = client_repo.get(client_id)
        if client is None:
            return error_response('Client not found', 404)

        # 4. Get rate for client and plan
        rate = rate_repo.get_by_client_and_plan(client_id, client.plan)
        if rate is None:
            rate = create_rate(client, rate_repo)

        # 5. Get invoice for client and month
        invoice = invoice_repo.get_by_client_and_month(client_id=client_id, month=billing_month, year=billing_year)
        if invoice is not None:
            rate = rate_repo.get_by_id(invoice.rate_id)
        else:
            invoice = create_invoice(
                month_year=(billing_month, billing_year),
                client_id=client_id,
                rate=rate,
                incident_repo=incident_repo,
                invoice_repo=invoice_repo,
            )

        if rate is None:
            return error_response('Rate could not be determined', 500)
        # 6. Return invoice data
        return json_response(invoice_result_to_dict(invoice, rate, client), 200)
