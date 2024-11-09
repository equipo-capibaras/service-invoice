from flask import Blueprint, Response
from flask.views import MethodView

from .util import class_route, json_response

blp = Blueprint('Invoice', __name__)


@class_route(blp, '/api/v1/invoice')
class GetInvoice(MethodView):
    init_every_request = False

    def get(
        self,
    ) -> Response:
        return json_response({'status': 'ok'}, 200)
