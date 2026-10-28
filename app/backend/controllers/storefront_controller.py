# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Updated - Iteration 5 - 4/20/26 - added edit storefront route, create listing route, S3 image upload endpoint, fixed session key

"""
storefront_controller.py

Purpose:
Defines both storefront page routes and storefront API endpoints.

Functions:
- render storefront HTML pages
- parse request input
- get current_user
- call service functions
- return JSON responses
"""

from flask import Blueprint, request, jsonify, render_template
from utils.auth_utils import get_session_user

from services.storefront_service import (
    create_storefront_service,
    get_my_storefront_service,
    update_storefront_service,
    deactivate_storefront_service,
    reactivate_storefront_service
)

from models.storefront_model import get_active_storefronts, get_storefront_by_id

# API blueprint
storefront_bp = Blueprint("storefront_bp", __name__, url_prefix="/api/storefronts")

# Page blueprint
storefront_pages_bp = Blueprint("storefront_pages_bp", __name__)


def get_current_user():
    """Signed-in user from the server-side session (never from request headers).
    Updated by Donovan Griffin, Iteration 3 - see utils/auth_utils.get_session_user."""
    return get_session_user()


#_________________________________________________________
# Page Routing
#_________________________________________________________

@storefront_pages_bp.route("/storefronts")
def storefront_home_page():
    return render_template("storefront.html")


@storefront_pages_bp.route("/storefronts/create")
def create_storefront_page():
    return render_template("create_storefront.html")


@storefront_pages_bp.route("/storefronts/my")
def my_storefront_page():
    return render_template("storefront.html")


@storefront_pages_bp.route("/storefronts/<int:storefront_id>")
def storefront_view_page(storefront_id):
    return render_template("storefront_view.html", storefront_id=storefront_id)


@storefront_pages_bp.route("/listings/create")
def create_listing_page():
    from flask import session, redirect, url_for
    if "user_id" not in session:
        return redirect(url_for("auth.login"))
    return render_template("create_listing.html")


# ________________________________________________________
# API Routing 
#________________________________________________________

# Get all active storefronts
# GET /api/storefronts
@storefront_bp.get("")
def get_all_storefronts_route():
    try:
        storefronts = get_active_storefronts()
        return jsonify(storefronts), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Get single storefront by ID (Public)
# GET /api/storefronts/<storefront_id>
@storefront_bp.get("/<int:storefront_id>")
def get_storefront_by_id_route(storefront_id):
    try:
        storefront = get_storefront_by_id(storefront_id)
        if storefront is None:
            return jsonify({"error": "Storefront not found."}), 404
        current_user = get_current_user()
        is_owner = current_user is not None and storefront["owner_id"] == current_user["id"]
        is_admin = current_user is not None and current_user.get("role") == "admin"
        if storefront.get("is_active") is False and not is_owner and not is_admin:
            return jsonify({"error": "Storefront not found."}), 404
        return jsonify(storefront), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Create Storefront
# POST /api/storefronts
@storefront_bp.post("")
def create_storefront_route():
    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Please sign in."}), 401

    data = request.get_json(silent=True) or {}

    try:
        storefront = create_storefront_service(current_user, data)
        return jsonify(storefront), 201
    except Exception as e:
        msg = str(e).lower()
        if "unauthorized" in msg:
            return jsonify({"error": str(e)}), 403
        return jsonify({"error": str(e)}), 400


# Get my storefront
# GET /api/storefronts/me
@storefront_bp.get("/me")
def get_my_storefront_route():
    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Please sign in."}), 401

    try:
        storefront = get_my_storefront_service(current_user)
        if storefront is None:
            return jsonify({"error": "No storefront found for this user."}), 404
        return jsonify(storefront), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# Update storefront
# PUT /api/storefronts/<storefront_id>
@storefront_bp.put("/<int:storefront_id>")
def update_storefront_route(storefront_id):
    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Please sign in."}), 401

    data = request.get_json(silent=True) or {}

    try:
        updated = update_storefront_service(current_user, storefront_id, data)
        return jsonify(updated), 200
    except Exception as e:
        msg = str(e).lower()
        if "unauthorized" in msg:
            return jsonify({"error": str(e)}), 403
        if "not found" in msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400


# Deactivate storefront
# PATCH /api/storefronts/<storefront_id>/deactivate
@storefront_bp.patch("/<int:storefront_id>/deactivate")
def deactivate_storefront_route(storefront_id):
    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Please sign in."}), 401

    try:
        updated = deactivate_storefront_service(current_user, storefront_id)
        return jsonify(updated), 200
    except Exception as e:
        msg = str(e).lower()
        if "unauthorized" in msg:
            return jsonify({"error": str(e)}), 403
        if "not found" in msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400


# PATCH /api/storefronts/<storefront_id>/reactivate
@storefront_bp.patch("/<int:storefront_id>/reactivate")
def reactivate_storefront_route(storefront_id):
    current_user = get_current_user()
    if current_user is None:
        return jsonify({"error": "Please sign in."}), 401

    try:
        updated = reactivate_storefront_service(current_user, storefront_id)
        return jsonify(updated), 200
    except Exception as e:
        msg = str(e).lower()
        if "unauthorized" in msg:
            return jsonify({"error": str(e)}), 403
        if "not found" in msg:
            return jsonify({"error": str(e)}), 404
        return jsonify({"error": str(e)}), 400

# Added 4/9/26 - My Storefront dashboard page
@storefront_pages_bp.route("/storefronts/dashboard")
def my_storefront_dashboard():
    from flask import session, redirect, url_for
    if not session.get("user"):
        return redirect(url_for("auth.login"))
    return render_template("my_storefront.html")


@storefront_pages_bp.route("/storefronts/<int:storefront_id>/edit")
def edit_storefront_page(storefront_id):
    from flask import session, redirect, url_for
    if not session.get("user"):
        return redirect(url_for("auth.login"))
    return render_template("edit_storefront.html", storefront_id=storefront_id)


@storefront_pages_bp.route("/listings/<int:listing_id>/edit")
def edit_listing_page(listing_id):
    from flask import session, redirect, url_for
    if not session.get("user"):
        return redirect(url_for("auth.login"))
    return render_template("edit_listing.html", listing_id=listing_id)

# Added 4/16/26 - handles image uploads to S3 for storefront creation
@storefront_bp.post("/upload-image")
def upload_storefront_image():
    from utils.s3 import upload_image_to_s3, InvalidUpload

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    folder = request.form.get("folder", "storefronts")

    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        return jsonify({"error": "Invalid file type"}), 400

    try:
        url = upload_image_to_s3(file, folder=folder)
    except InvalidUpload as e:  # bad folder / not a real image / too big - Iteration 3
        return jsonify({"error": str(e)}), 400
    if not url:
        return jsonify({"error": "Upload failed"}), 500

    return jsonify({"url": url}), 200
