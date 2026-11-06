from flask import Blueprint

customers_bp = Blueprint("customers", __name__)

from app.blueprints.customers import routes
