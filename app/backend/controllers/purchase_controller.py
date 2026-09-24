# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created for Purchase History feature by Elali McNair 3/3/26
# The frontend protion of this code is not finished or implemented yet. Therfore, this code is not oporational or properly implemented yet.

"""
controllers/purchase_controller.py

Purpose:
This controller handles HTTP requests related to purchase operations.
It processes requests, calls service methods, and returns JSON responses.
"""

from flask import Blueprint, request, jsonify
from services.purchase_service import PurchaseService

purchase_bp = Blueprint('purchase', __name__, url_prefix="/api")
purchase_service = PurchaseService()


def get_current_user():
    """
    Temporary user identity method (until real auth is connected):
    Read user from headers.

    Required header for protected routes:
      X-User-Id: <int>
    """
    user_id = request.headers.get("X-User-Id")
    role = request.headers.get("X-User-Role", "user")

    if not user_id:
        return None

    try:
        return {"id": int(user_id), "role": role}
    except Exception:
        return None


@purchase_bp.route('/purchases', methods=['POST'])
def record_purchase():
    """
    Records a new purchase for the authenticated user.
    Expects JSON: {"listing_id": int, "quantity": int}
    """
    try:
        current_user = get_current_user()
        if current_user is None:
            return jsonify({"error": "Unauthorized: missing/invalid X-User-Id"}), 401

        data = request.get_json()
        if not data or 'listing_id' not in data or 'quantity' not in data:
            return jsonify({"error": "Missing required fields: listing_id, quantity"}), 400

        listing_id = data['listing_id']
        quantity = data['quantity']

        if not isinstance(listing_id, int) or not isinstance(quantity, int) or quantity <= 0:
            return jsonify({"error": "Invalid data types or values"}), 400

        success, result = purchase_service.record_purchase(current_user['id'], listing_id, quantity)

        if success:
            return jsonify({"message": "Purchase recorded successfully", "purchase": result}), 201
        else:
            return jsonify({"error": result}), 400

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@purchase_bp.route('/purchases', methods=['GET'])
def get_purchase_history():
    """
    Retrieves the purchase history for the authenticated user.
    """
    try:
        current_user = get_current_user()
        if current_user is None:
            return jsonify({"error": "Unauthorized: missing/invalid X-User-Id"}), 401

        success, result = purchase_service.get_user_purchase_history(current_user['id'])

        if success:
            return jsonify({"purchases": result}), 200
        else:
            return jsonify({"error": result}), 500

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@purchase_bp.route('/purchases/<int:purchase_id>', methods=['GET'])
def get_purchase_details(purchase_id):
    """
    Retrieves details of a specific purchase.
    """
    try:
        current_user = get_current_user()
        if current_user is None:
            return jsonify({"error": "Unauthorized: missing/invalid X-User-Id"}), 401

        success, result = purchase_service.get_purchase_details(purchase_id)

        if success:
            # Check if the purchase belongs to the current user
            if result['user_id'] != current_user['id']:
                return jsonify({"error": "Access denied"}), 403
            return jsonify({"purchase": result}), 200
        else:
            return jsonify({"error": result}), 404

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500