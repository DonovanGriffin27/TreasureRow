# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created for Wishlist feature by Elali McNair 3/3/26
# The frontend protion of this code is not finished or implemented yet. Therfore, this code is not oporational or properly implemented yet.

"""
controllers/wishlist_controller.py

Purpose:
This controller handles HTTP requests related to wishlist operations.
It processes requests, calls service methods, and returns JSON responses.
"""

from flask import Blueprint, request, jsonify
from services.wishlist_service import WishlistService

wishlist_bp = Blueprint('wishlist', __name__, url_prefix="/api")
wishlist_service = WishlistService()


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


@wishlist_bp.route('/wishlist', methods=['POST'])
def add_to_wishlist():
    """
    Adds an item to the authenticated user's wishlist.
    Expects JSON: {"listing_id": int}
    """
    try:
        current_user = get_current_user()
        if current_user is None:
            return jsonify({"error": "Unauthorized: missing/invalid X-User-Id"}), 401

        data = request.get_json()
        if not data or 'listing_id' not in data:
            return jsonify({"error": "Missing required field: listing_id"}), 400

        listing_id = data['listing_id']

        if not isinstance(listing_id, int):
            return jsonify({"error": "Invalid listing_id"}), 400

        success, result = wishlist_service.add_item_to_wishlist(current_user['id'], listing_id)

        if success:
            return jsonify({"message": result}), 201
        else:
            return jsonify({"error": result}), 400

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@wishlist_bp.route('/wishlist', methods=['GET'])
def get_wishlist():
    """
    Retrieves the wishlist for the authenticated user.
    """
    try:
        current_user = get_current_user()
        if current_user is None:
            return jsonify({"error": "Unauthorized: missing/invalid X-User-Id"}), 401

        success, result = wishlist_service.get_user_wishlist(current_user['id'])

        if success:
            return jsonify({"wishlist": result}), 200
        else:
            return jsonify({"error": result}), 500

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@wishlist_bp.route('/wishlist/<int:listing_id>', methods=['DELETE'])
def remove_from_wishlist(listing_id):
    """
    Removes an item from the authenticated user's wishlist.
    """
    try:
        current_user = get_current_user()
        if current_user is None:
            return jsonify({"error": "Unauthorized: missing/invalid X-User-Id"}), 401

        success, result = wishlist_service.remove_item_from_wishlist(current_user['id'], listing_id)

        if success:
            return jsonify({"message": result}), 200
        else:
            return jsonify({"error": result}), 404

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@wishlist_bp.route('/wishlist/<int:listing_id>/check', methods=['GET'])
def check_wishlist_status(listing_id):
    """
    Checks if a listing is in the authenticated user's wishlist.
    """
    try:
        current_user = get_current_user()
        if current_user is None:
            return jsonify({"error": "Unauthorized: missing/invalid X-User-Id"}), 401

        success, result = wishlist_service.check_item_in_wishlist(current_user['id'], listing_id)

        if success:
            return jsonify({"in_wishlist": result}), 200
        else:
            return jsonify({"error": result}), 500

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@wishlist_bp.route('/wishlist/items/<int:wishlist_id>', methods=['GET'])
def get_wishlist_item_details(wishlist_id):
    """
    Retrieves details of a specific wishlist item.
    """
    try:
        current_user = get_current_user()
        if current_user is None:
            return jsonify({"error": "Unauthorized: missing/invalid X-User-Id"}), 401

        success, result = wishlist_service.get_wishlist_item_details(wishlist_id)

        if success:
            # Check if the wishlist item belongs to the current user
            if result['user_id'] != current_user['id']:
                return jsonify({"error": "Access denied"}), 403
            return jsonify({"wishlist_item": result}), 200
        else:
            return jsonify({"error": result}), 404

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500