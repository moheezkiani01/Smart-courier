from flask import Blueprint

dispatch_bp = Blueprint("dispatch", __name__)

from app.blueprints.dispatch import routes
