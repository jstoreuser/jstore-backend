import os
import mercadopago
from flask import request, jsonify, current_app
from decimal import Decimal

from . import payment_bp
from src.models import db
from src.models.order import Order, OrderStatus

# TODO: Replace with user's actual Mercado Pago Access Token (use environment variable)
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "TEST-YOUR_ACCESS_TOKEN") # Use Test token for now

sdk = mercadopago.SDK(MP_ACCESS_TOKEN)

# TODO: Define base URL from environment variable for production
BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:3000") # Default to Next.js dev server

@payment_bp.route("/create", methods=["POST"])
def create_payment():
    """Creates a new order and a Mercado Pago payment preference."""
    try:
        # --- 1. Define Product Details ---
        # In a real scenario, you might get product ID from request
        # For now, hardcode the details for "JOGO TESTE"
        game_name = "JOGO TESTE (The Sims 4 Completo)"
        game_price = Decimal("59.90") # Use Decimal for currency
        game_quantity = 1
        # It's good practice to get customer email if possible
        customer_email = request.json.get("email", None) 

        # --- 2. Create Order in Database ---
        new_order = Order(
            status=OrderStatus.PENDING,
            customer_email=customer_email,
            game_name=game_name,
            price=game_price
        )
        db.session.add(new_order)
        db.session.flush() # Flush to get the new_order.id before committing
        order_id = new_order.id
        current_app.logger.info(f"Created Order ID: {order_id}")

        # --- 3. Create Mercado Pago Preference ---
        preference_data = {
            "items": [
                {
                    "title": game_name,
                    "quantity": game_quantity,
                    "unit_price": float(game_price), # MP API expects float
                    "currency_id": "BRL" # Brazil Real
                }
            ],
            "payer": {
                # Include email if available
                "email": customer_email if customer_email else None,
            },
            "back_urls": {
                # URL the user is redirected to after payment
                "success": f"{BASE_URL}/success?status=approved&order_id={order_id}",
                "failure": f"{BASE_URL}/success?status=rejected&order_id={order_id}",
                "pending": f"{BASE_URL}/success?status=pending&order_id={order_id}"
            },
            "auto_return": "approved", # Automatically return only on success
            "notification_url": f"{os.getenv('API_BASE_URL', 'http://localhost:5001')}/api/payment/webhook", # URL for Webhook notifications
            "external_reference": str(order_id), # Link preference to our Order ID
        }

        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]

        if preference_response["status"] != 201:
             current_app.logger.error(f"Mercado Pago preference creation failed: {preference}")
             db.session.rollback() # Rollback order creation
             return jsonify({"error": "Failed to create payment preference"}), 500

        preference_id = preference["id"]
        payment_url = preference["init_point"] # URL to redirect user for payment

        # --- 4. Update Order with Preference ID and Commit ---
        new_order.mercadopago_preference_id = preference_id
        db.session.commit()
        current_app.logger.info(f"Mercado Pago Preference ID: {preference_id} for Order ID: {order_id}")

        # --- 5. Return Payment URL to Frontend ---
        return jsonify({"payment_url": payment_url, "order_id": order_id})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating payment: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred"}), 500

@payment_bp.route("/webhook", methods=["POST"])
def payment_webhook():
    """Handles incoming payment notifications from Mercado Pago."""
    current_app.logger.info("Webhook received")
    data = request.json
    current_app.logger.debug(f"Webhook data: {data}")

    # TODO: Implement robust webhook validation and processing
    # 1. Validate request source (optional but recommended)
    # 2. Check notification type (e.g., 'payment')
    # 3. Get payment details from Mercado Pago API using data['data']['id']
    # 4. Find the corresponding order using external_reference (order_id)
    # 5. Update order status in the database based on payment status
    # 6. Handle potential errors and edge cases

    # Placeholder implementation:
    try:
        if data and data.get("type") == "payment":
            payment_id = data["data"]["id"]
            current_app.logger.info(f"Processing payment notification for ID: {payment_id}")
            
            # --- Fetch Payment Details from Mercado Pago --- 
            payment_info_response = sdk.payment().get(payment_id)
            if payment_info_response["status"] != 200:
                current_app.logger.error(f"Failed to get payment info for {payment_id}: {payment_info_response}")
                return jsonify({"error": "Failed to fetch payment info"}), 500
            
            payment_info = payment_info_response["response"]
            order_id = payment_info.get("external_reference")
            payment_status = payment_info.get("status") # e.g., 'approved', 'pending', 'rejected'
            
            if not order_id:
                current_app.logger.warning(f"Webhook for payment {payment_id} lacks external_reference.")
                return jsonify({"status": "ok - no external reference"}), 200

            # --- Find Order and Update Status --- 
            order = Order.query.get(int(order_id))
            if not order:
                current_app.logger.error(f"Order {order_id} not found for payment {payment_id}.")
                return jsonify({"error": "Order not found"}), 404

            new_status = None
            if payment_status == "approved":
                new_status = OrderStatus.APPROVED
            elif payment_status == "rejected" or payment_status == "cancelled" or payment_status == "refunded": # Consider other failure states
                new_status = OrderStatus.REJECTED
            elif payment_status == "pending" or payment_status == "in_process":
                new_status = OrderStatus.PENDING # Keep as pending or update if needed
            else:
                 current_app.logger.warning(f"Unhandled payment status 	'{payment_status}	' for order {order_id}")

            if new_status and order.status != new_status:
                order.status = new_status
                order.mercadopago_payment_id = str(payment_id) # Store the MP payment ID
                db.session.commit()
                current_app.logger.info(f"Order {order_id} status updated to {new_status.name}")
            else:
                 current_app.logger.info(f"Order {order_id} status 	'{order.status.name}	' not changed by webhook status 	'{payment_status}	'.")

        elif data and data.get("type") == "test.created":
             current_app.logger.info("Test webhook received successfully.")
        else:
            current_app.logger.warning(f"Received unhandled webhook type: {data.get('type')}")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Return 500 to signal MP to retry (if applicable), but be cautious of infinite loops
        return jsonify({"error": "Webhook processing failed"}), 500

    # Always return 200 OK to Mercado Pago to acknowledge receipt
    return jsonify({"status": "ok"}), 200

