# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Updated by Day Ekoi - 4/22/26 - API-only blueprint

from flask import Blueprint, request, jsonify, session

from services.checkout_service import (
    complete_transaction_from_session,
    get_order_summary_service,
    get_user_orders_service,
)

checkout_bp = Blueprint("checkout", __name__)


@checkout_bp.route("/checkout/complete", methods=["POST"])
def complete_checkout():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    session_cart = session.get("cart", [])
    if not session_cart:
        return jsonify({"error": "Cart is empty"}), 400

    data = request.get_json() or {}

    try:
        result = complete_transaction_from_session(user_id, session_cart, data)
        session["cart"] = []
        session.modified = True
        return jsonify({
            "success": True,
            "confirmation_number": result["confirmation_number"],
            "order_id": result["order"]["id"],
            "total_amount": result["total_amount"],
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@checkout_bp.route("/orders/by-confirmation/<confirmation_number>", methods=["GET"])
def get_order_confirmation(confirmation_number):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    try:
        result = get_order_summary_service(confirmation_number, user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@checkout_bp.route("/orders/my", methods=["GET"])
def get_my_orders():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not logged in"}), 401

    try:
        orders = get_user_orders_service(user_id)
        return jsonify({"orders": orders}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
