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

