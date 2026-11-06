from flask import Blueprint

hubs_bp = Blueprint("hubs", __name__)

from app.blueprints.hubs import routes
