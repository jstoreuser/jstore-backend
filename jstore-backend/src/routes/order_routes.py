from flask import Blueprint, jsonify, current_app
from src.models.order import Order

order_bp = Blueprint("order", __name__)

@order_bp.route("/status/<int:order_id>", methods=["GET"])
def get_order_status(order_id):
    """Gets the status of a specific order."""
    # TODO: Add authentication/authorization check here
    # Ensure the user requesting the status is allowed to see this order
    # This might involve checking a session token, JWT, or other auth method
    
    try:
        order = Order.query.get_or_404(order_id)
        current_app.logger.info(f"Fetching status for Order ID: {order_id}")
        return jsonify({"status": order.status.name, "order_id": order.id})
    except Exception as e:
        current_app.logger.error(f"Error fetching status for order {order_id}: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred"}), 500

