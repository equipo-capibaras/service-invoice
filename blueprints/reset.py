from dependency_injector.wiring import inject
from flask import Blueprint, Response
from flask.views import MethodView

from .util import class_route, json_response

blp = Blueprint('Reset database', __name__)


@class_route(blp, '/api/v1/reset/invoice')
class ResetDB(MethodView):
    init_every_request = False

    @inject
    def post(self) -> Response:
        return json_response({'status': 'Ok'}, 200)
