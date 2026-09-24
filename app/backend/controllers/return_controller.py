"""
return_controller.py

Routes for the returns page and return request submission.
"""

from flask import Blueprint, jsonify, render_template, request, redirect, url_for, session

from services.return_service import create_return_service

returns_bp = Blueprint("returns_bp", __name__)


def get_current_user():
    header_user_id = request.headers.get("X-User-Id")
    header_role = request.headers.get("X-User-Role", session.get("role", "user"))

    if header_user_id:
        try:
            return {"id": int(header_user_id), "role": header_role}
        except Exception:
            return None

    if session.get("user_id"):
        return {"id": int(session["user_id"]), "role": session.get("role", "user")}

    return None


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

    if "damage_image" in request.files and request.files["damage_image"].filename:
        from utils.s3 import upload_image_to_s3

        file = request.files["damage_image"]
        if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
            return jsonify({"error": "Damage image must be PNG, JPG, JPEG, GIF, or WebP."}), 400

        damage_image_url = upload_image_to_s3(file, folder="returns/damage")
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
