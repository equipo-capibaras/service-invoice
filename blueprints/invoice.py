from flask import Blueprint
from flask.views import MethodView

from .util import class_route

blp = Blueprint('Invoice', __name__)


@class_route(blp, '/api/v1/invoice')
class GetInvoice(MethodView):
    init_every_request = False
