from flask import Blueprint

payment_bp = Blueprint("payment", __name__)

# Import routes after blueprint creation to avoid circular imports
from . import payment_routes

