from flask import Blueprint

shipments_bp = Blueprint("shipments", __name__)

from app.blueprints.shipments import routes
