from dependency_injector.wiring import Provide

from .util import class_route, json_response
from flask import Blueprint, Response, request
from flask.views import MethodView
from containers import Container
from repositories import ClientRepository

blp = Blueprint('Invoice', __name__)


@class_route(blp, '/api/v1/invoice')
class GetInvoice(MethodView):
    init_every_request = False

    def get(self, client_repo: ClientRepository = Provide[Container.client_repo]) -> Response:
        client_id = 'acfa53b4-58f3-46e8-809b-19ef52b437ed'
        client = client_repo.get(client_id)
        answee = {
            'id': client.id,
            'name': client.name,
            'plan': client.plan.value
        }
        return json_response(answee, 200)