"""
return_controller.py

Routes for the returns page and return request submission.
"""

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session
from utils.auth_utils import get_session_user

from services.return_service import create_return_service, assert_order_belongs_to_user

returns_bp = Blueprint("returns_bp", __name__)


def get_current_user():
    """Signed-in user from the server-side session (never from request headers).
    Updated by Donovan Griffin, Iteration 3 - see utils/auth_utils.get_session_user."""
    return get_session_user()


@returns_bp.get("/returns")
def returns_page():
    if "user" not in session:
        return redirect(url_for("auth.login"))
    return render_template("returns.html")


@returns_bp.post("/returns")
def submit_return():
    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Unauthorized."}), 401

    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    damage_image_url = None

    # check the order before uploading any damage photo, so a bad order
    # number doesn't leave an orphaned upload - Iteration 3
    try:
        assert_order_belongs_to_user(current_user, data.get("order_number"))
    except Exception as e:
        return jsonify({"error": str(e)}), 400

    if "damage_image" in request.files and request.files["damage_image"].filename:
        from utils.s3 import upload_image_to_s3, InvalidUpload

        file = request.files["damage_image"]
        if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            return jsonify({"error": "Damage image must be PNG, JPG, JPEG, GIF, or WebP."}), 400

        try:
            damage_image_url = upload_image_to_s3(file, folder="returns/damage")
        except InvalidUpload as e:  # not a real image / too big - Iteration 3
            return jsonify({"error": str(e)}), 400
        if not damage_image_url:
            return jsonify({"error": "Damage image upload failed."}), 500

    try:
        created = create_return_service(current_user, data, damage_image_url=damage_image_url)
        return jsonify(created), 201
    except Exception as e:
        message = str(e)
        if "unauthorized" in message.lower():
            return jsonify({"error": message}), 401
        return jsonify({"error": message}), 400
