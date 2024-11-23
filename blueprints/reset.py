from dependency_injector.wiring import Provide, inject
from flask import Blueprint, Response
from flask.views import MethodView

from containers import Container
from repositories import InvoiceRepository

from .util import class_route, json_response

blp = Blueprint('Reset database', __name__)


@class_route(blp, '/api/v1/reset/invoice')
class ResetDB(MethodView):
    init_every_request = False

    @inject
    def post(self, invoice_repo: InvoiceRepository = Provide[Container.invoice_repo]) -> Response:
        invoice_repo.delete_all()

        return json_response({'status': 'Ok'}, 200)
