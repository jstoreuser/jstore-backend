import os
from flask import Blueprint, jsonify, current_app, abort
from src.models.order import Order, OrderStatus

# TODO: Store these securely, e.g., in environment variables or a config file
INSTALLER_DOWNLOAD_URL = os.getenv("INSTALLER_URL", "PLACEHOLDER_INSTALLER_URL_FROM_HOSTINGER")
TUTORIAL_FILE_PATH = "/home/ubuntu/tutorial_instalacao.md" # Path to the tutorial file

download_bp = Blueprint("download", __name__)

@download_bp.route("/link/<int:order_id>", methods=["GET"])
def get_download_link(order_id):
    """Provides the download link and tutorial if the order is approved."""
    # TODO: Add robust authentication/authorization check here
    # Ensure the user requesting the link is the one who made the purchase
    
    try:
        order = Order.query.get_or_404(order_id)
        current_app.logger.info(f"Attempting to get download link for Order ID: {order_id}")

        if order.status != OrderStatus.APPROVED:
            current_app.logger.warning(f"Download attempt for non-approved Order ID: {order_id} (Status: {order.status.name})")
            # Return 403 Forbidden if status is not approved
            abort(403, description="O pagamento para este pedido não foi aprovado ou ainda está pendente.")

        # --- Read Tutorial Content --- 
        tutorial_content = "Tutorial não encontrado."
        try:
            # In a real app, consider caching this file content
            with open(TUTORIAL_FILE_PATH, 'r', encoding='utf-8') as f:
                tutorial_content = f.read()
        except FileNotFoundError:
            current_app.logger.error(f"Tutorial file not found at {TUTORIAL_FILE_PATH}")
            # Proceed without tutorial content or return an error, depending on requirements
        except Exception as file_err:
             current_app.logger.error(f"Error reading tutorial file: {file_err}")
             # Decide how to handle file read errors

        current_app.logger.info(f"Providing download link for approved Order ID: {order_id}")
        return jsonify({
            "download_url": INSTALLER_DOWNLOAD_URL,
            "tutorial_content": tutorial_content,
            "order_id": order.id,
            "status": order.status.name
        })

    except Exception as e:
        # Handle potential errors like order not found (already handled by get_or_404) or other exceptions
        current_app.logger.error(f"Error getting download link for order {order_id}: {e}", exc_info=True)
        # Avoid leaking internal error details unless in debug mode
        return jsonify({"error": "Não foi possível obter o link de download."}), 500

